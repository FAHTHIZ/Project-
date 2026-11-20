# SPDX-License-Identifier: Apache-2.0
"""Render every line in tools/dialogue/lines.py to speech offline and write lip-sync data.

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='/tmp/kok')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--relip', action='store_true', help='recompute lip data from the existing ogg files')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    kok = None
    for lid, spk, text, *rest in LINES:
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
        m = man[lid]
        out.append(f'V[{q(lid)}] = {{ s = {q(spk)}, n = {q(name)}, t = {q(text)}, e = {q(rest[0] if rest else "neutral")}, '
                   f'd = {m["dur"]}, r = {str(is_radio).lower()}, j = {q(m["jaw"])}, m = {q(m["shape"])} }}')
    out.append('return V')
    open(LUAU, 'w').write('\n'.join(out) + '\n')
    print(f'{len(LINES)} lines -> {LUAU}')


if __name__ == '__main__':
    main()
