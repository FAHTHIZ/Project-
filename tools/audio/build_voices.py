# SPDX-License-Identifier: Apache-2.0
"""Render every line in tools/dialogue/lines.py to speech offline and write lip-sync data.

Voice pass v3 (current): human-performance takes. Casting and delivery direction live in
tools/dialogue/performance.py; each line is performed by Gemini 3.8 Flash TTS at authoring time
(one prebuilt voice per character, see CAST) and the takes are edited here:

    python3 tools/audio/build_voices.py --jobs /tmp/vo_jobs     # list lines whose take is missing/stale
    (perform each /tmp/vo_jobs/<id>.txt with the voice in jobs.json -> <id>.wav; keep each
     <id>.txt beside its <id>.wav in the takes directory: a take is only ingested for the exact
     script it was performed from)
    python3 tools/audio/build_voices.py --takes /tmp/vo_takes   # edit, level, radio-filter, lip, encode

Editing per take: silence trimmed to a 40 ms lead and a natural 160 ms tail with a 60 ms fade,
active-speech loudness levelled to -16 dBFS RMS (the level the game mix was balanced on), peaks
soft-limited at 0.89, then the radio chain for radio/PA/recording speakers. A line whose take is
missing or stale is never silently re-rendered with Kokoro; it keeps its previous audio and is
listed by --jobs. The Kokoro path below stays available with --engine kokoro.

    pip install kokoro-onnx soundfile scipy numpy
    python3 tools/audio/build_voices.py --model <dir with kokoro-v1.0.int8.onnx and voices-v1.0.bin>

TTS: Kokoro-82M (hexgrad, Apache-2.0 weights; model card states training on permissive /
non-copyrighted audio) run through kokoro-onnx (MIT). Only the rendered audio ships; the model,
runtime and phonemizer stay on the authoring machine (no runtime TTS). See ASSET_PROVENANCE.md.

Outputs
  game/assets/audio/voice/<id>.ogg        mono Vorbis, 24 kHz
  game/assets/scripts/lib/voice_data.luau timing, subtitle name and per-frame (30 fps) mouth data
  tools/dialogue/voice_manifest.json      text hashes so unchanged lines are not re-rendered

Lip data per frame: `jaw` (0-9, openness from a compressed RMS envelope) and `shape`
(o = rounded, e = wide, - = neutral) from the balance of low/high formant-band energy. The
face script turns these into JawOpen / MouthO / Smile morph weights.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile
import numpy as np
from scipy import signal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'dialogue'))
from lines import LINES, VOICES  # noqa: E402
from performance import CAST, DELIVERY  # noqa: E402

OUT = os.path.join(ROOT, 'game', 'assets', 'audio', 'voice')
LUAU = os.path.join(ROOT, 'game', 'assets', 'scripts', 'lib', 'voice_data.luau')
MANIFEST = os.path.join(ROOT, 'tools', 'dialogue', 'voice_manifest.json')
FPS = 30
# Delivery pacing per emotion tag: Kokoro has no emotion control, so tempo carries it (a startled
# line comes out quicker, a deadpan one a touch slower). Small factors keep each voice recognisable.
EMOTION_PACE = {'surprise': 1.08, 'focus': 1.03, 'smile': 1.02, 'neutral': 1.0, 'concern': 0.98, 'deadpan': 0.96}


def radio(x, sr, seed):
    b, a = signal.butter(4, [320 / (sr / 2), 3300 / (sr / 2)], 'band')
    y = signal.lfilter(b, a, x) * 1.6
    y = np.tanh(y * 1.8) / np.tanh(1.8)
    rng = np.random.default_rng(seed)
    y = y + rng.normal(0, 0.004, len(y))
    click = np.zeros(int(sr * 0.05)); n = len(click)
    click[: n // 3] = rng.normal(0, 0.08, n // 3) * np.linspace(1, 0, n // 3)
    return np.concatenate([click, y, click[::-1] * 0.7])


def lip(x, sr):
    hop = sr // FPS
    n = max(1, len(x) // hop)
    b1, a1 = signal.butter(2, [250 / (sr / 2), 900 / (sr / 2)], 'band')
    b2, a2 = signal.butter(2, [1200 / (sr / 2), 4000 / (sr / 2)], 'band')
    lo, hi = signal.lfilter(b1, a1, x), signal.lfilter(b2, a2, x)
    rms = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    elo = np.array([np.mean(lo[i * hop:(i + 1) * hop] ** 2) for i in range(n)])
    ehi = np.array([np.mean(hi[i * hop:(i + 1) * hop] ** 2) for i in range(n)])
    peak = np.percentile(rms, 95) + 1e-9
    v = np.clip(rms / peak, 0, 1.2)
    v = np.where(v < 0.1, 0, v ** 0.85)
    v = np.convolve(v, [0.25, 0.5, 0.25], 'same')
    jaw = ''.join(str(int(round(min(9, k * 9)))) for k in v)
    ratio = np.log10((elo + 1e-12) / (ehi + 1e-12))
    shape = ''.join('-' if j == '0' else ('o' if r > 1.25 else ('e' if r < 0.55 else '-')) for j, r in zip(jaw, ratio))
    return jaw, shape


TAKE_ENGINE = 'gemini-3.8-flash-tts'


def take_hash(lid, spk, text):
    script = DELIVERY.get(lid, text)
    return 'g' + hashlib.sha1(f'{TAKE_ENGINE}|{CAST[spk]}|{VOICES[spk][2]}|{script}|v3'.encode()).hexdigest()[:15]


def read_audio(path):
    raw = subprocess.run(['ffmpeg', '-loglevel', 'error', '-i', path, '-f', 'f64le', '-ac', '1', '-ar', '24000', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float64).copy(), 24000


def edit_take(x, sr):
    """Trim, level and limit one performed take."""
    hop = sr // 100
    fr = x[: len(x) // hop * hop].reshape(-1, hop)
    rms = np.sqrt((fr ** 2).mean(1) + 1e-12)
    on = np.nonzero(rms > max(rms.max() * 0.03, 1e-4))[0]
    if len(on):
        a, b = max(0, on[0] * hop - int(0.02 * sr)), min(len(x), (on[-1] + 1) * hop + int(0.10 * sr))
        x = x[a:b]
    fade = int(0.06 * sr)
    x = np.concatenate([x, np.zeros(int(0.06 * sr))])
    x[-fade:] *= np.linspace(1, 0, fade) ** 2
    x[: int(0.005 * sr)] *= np.linspace(0, 1, int(0.005 * sr))
    fr = x[: len(x) // hop * hop].reshape(-1, hop)
    r = np.sqrt((fr ** 2).mean(1))
    act = r[r > r.max() * 0.1]
    level = np.sqrt((act ** 2).mean()) if len(act) else 1e-3
    x = x * (10 ** (-16 / 20) / level)
    knee = 0.7
    big = np.abs(x) > knee
    x[big] = np.sign(x[big]) * (knee + (0.89 - knee) * np.tanh((np.abs(x[big]) - knee) / (0.89 - knee)))
    return np.concatenate([np.zeros(int(0.04 * sr)), x, np.zeros(int(0.10 * sr))])


def write_ogg(x, sr, ogg):
    import soundfile as sf
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        sf.write(f.name, (np.clip(x, -1, 1) * 32767).astype(np.int16), sr, subtype='PCM_16')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f.name, '-ac', '1', '-c:a', 'libvorbis', '-q:a', '4', ogg],
                       check=True)
        os.unlink(f.name)


def takes_pass(a, man):
    """List (--jobs) or ingest (--takes) human-performance takes."""
    jobs = []
    for lid, spk, text, *rest in LINES:
        h = take_hash(lid, spk, text)
        ogg = os.path.join(OUT, lid + '.ogg')
        if man.get(lid, {}).get('hash') == h and os.path.exists(ogg):
            continue
        wav = os.path.join(a.takes, lid + '.wav') if a.takes else None
        script = os.path.join(a.takes, lid + '.txt') if a.takes else None
        # a take is only valid for the script it was performed from (<id>.txt next to <id>.wav)
        fresh = wav and os.path.exists(wav) and os.path.exists(script) and \
            open(script).read().strip() == DELIVERY.get(lid, text).strip()
        if fresh:
            x, sr = read_audio(wav)
            x = edit_take(x, sr)
            jaw, shape = lip(x, sr)
            if VOICES[spk][2]:
                x = radio(x, sr, int(h[1:7], 16)); x = x / (np.max(np.abs(x)) + 1e-9) * 0.8
                pad = int(0.05 * FPS)
                jaw, shape = '0' * pad + jaw + '0' * pad, '-' * pad + shape + '-' * pad
            write_ogg(x, sr, ogg)
            man[lid] = {'hash': h, 'dur': round(len(x) / sr, 3), 'jaw': jaw, 'shape': shape, 'src': TAKE_ENGINE}
            print(f'{lid}: {man[lid]["dur"]:.2f}s {spk} ({CAST[spk]})', flush=True)
            continue
        jobs.append({'id': lid, 'voice': CAST[spk], 'text': DELIVERY.get(lid, text)})
    if a.jobs:
        os.makedirs(a.jobs, exist_ok=True)
        for j in jobs:
            open(os.path.join(a.jobs, j['id'] + '.txt'), 'w').write(j['text'])
        json.dump(jobs, open(os.path.join(a.jobs, 'jobs.json'), 'w'), indent=1)
    print(f'{len(jobs)} line(s) still need a performed take', flush=True)
    return jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', choices=['takes', 'kokoro'], default='takes')
    ap.add_argument('--jobs', help='write the missing/stale takes to perform into this directory')
    ap.add_argument('--takes', help='directory of performed <id>.wav takes to edit and ingest')
    ap.add_argument('--model', default='/tmp/kok')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--relip', action='store_true', help='recompute lip data from the existing ogg files')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    kok = None
    if a.engine == 'takes':
        takes_pass(a, man)
    for lid, spk, text, *rest in (LINES if a.engine == 'kokoro' else []):
        voice, speed, is_radio, _ = VOICES[spk]
        if lid.startswith(('react_', 'grey_')):   # reactive barks (story lines keep their reviewed takes)
            speed = round(speed * EMOTION_PACE.get(rest[0] if rest else 'neutral', 1.0), 3)
        h = hashlib.sha1(f'{voice}|{speed}|{is_radio}|{text}|v2'.encode()).hexdigest()[:16]
        ogg = os.path.join(OUT, lid + '.ogg')
        if not a.force and man.get(lid, {}).get('hash') == h and os.path.exists(ogg):
            if a.relip:
                import soundfile as sf
                y, ysr = sf.read(ogg)
                man[lid]['jaw'], man[lid]['shape'] = lip(np.asarray(y, np.float64), ysr)
            continue
        if kok is None:
            from kokoro_onnx import Kokoro
            kok = Kokoro(os.path.join(a.model, 'kokoro-v1.0.int8.onnx'), os.path.join(a.model, 'voices-v1.0.bin'))
        lang = 'en-gb' if voice.startswith('b') else 'en-us'
        x, sr = kok.create(text, voice=voice, speed=speed, lang=lang)
        x = np.asarray(x, np.float64)
        x = x / (np.max(np.abs(x)) + 1e-9) * 0.85
        lead = np.zeros(int(sr * 0.04))
        x = np.concatenate([lead, x, np.zeros(int(sr * 0.08))])
        jaw, shape = lip(x, sr)
        if is_radio:
            x = radio(x, sr, int(h[:6], 16)); x = x / (np.max(np.abs(x)) + 1e-9) * 0.8
            pad = int(0.05 * FPS)
            jaw, shape = '0' * pad + jaw + '0' * pad, '-' * pad + shape + '-' * pad
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            import soundfile as sf
            sf.write(f.name, (x * 32767).astype(np.int16), sr, subtype='PCM_16')
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', f.name, '-ac', '1', '-c:a', 'libvorbis', '-q:a', '3', ogg],
                           check=True)
            os.unlink(f.name)
        man[lid] = {'hash': h, 'dur': round(len(x) / sr, 3), 'jaw': jaw, 'shape': shape}
        print(f'{lid}: {man[lid]["dur"]:.2f}s {spk}', flush=True)
        # save progress after every line so an interrupted render resumes where it stopped
        json.dump(man, open(MANIFEST, 'w'), indent=0, sort_keys=True)
    # drop lines that no longer exist
    ids = {l[0] for l in LINES}
    for k in list(man):
        if k not in ids:
            man.pop(k)
            p = os.path.join(OUT, k + '.ogg')
            if os.path.exists(p): os.unlink(p)
    json.dump(man, open(MANIFEST, 'w'), indent=0, sort_keys=True)
    out = ['-- Generated by tools/audio/build_voices.py from tools/dialogue/lines.py. Do not edit.',
           '-- id = { s = speaker key, n = subtitle name, t = text, e = emotion, d = seconds, r = radio,',
           '--        j = jaw openness per 1/30 s (0-9), m = mouth shape per frame (o round, e wide, - neutral) }',
           'local V = {}']
    def q(s): return json.dumps(s)
    for lid, spk, text, *rest in LINES:
        voice, speed, is_radio, name = VOICES[spk]
        m = man.get(lid)
        if m is None:
            print(f'warning: {lid} has no audio yet', flush=True); continue
        out.append(f'V[{q(lid)}] = {{ s = {q(spk)}, n = {q(name)}, t = {q(text)}, e = {q(rest[0] if rest else "neutral")}, '
                   f'd = {m["dur"]}, r = {str(is_radio).lower()}, j = {q(m["jaw"])}, m = {q(m["shape"])} }}')
    out.append('return V')
    open(LUAU, 'w').write('\n'.join(out) + '\n')
    print(f'{len(LINES)} lines -> {LUAU}')


if __name__ == '__main__':
    main()
