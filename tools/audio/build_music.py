# SPDX-License-Identifier: Apache-2.0
"""Original SPECIAL OPS score, synthesised from code (numpy + scipy), deterministic.

    python3 tools/audio/build_music.py --out game/assets

Every cue is composed here (progressions, motifs and orchestration are written in this file) and
rendered offline to stereo Ogg Vorbis under <out>/audio/music/. No samples, loops or third-party
material are used (docs/ASSET_PROVENANCE.md).

Adaptive layers: each area has an `explore` bed and a `tension` layer of the same length, tempo
and harmony, so scripts/music.luau can crossfade between them in step as combat starts and ends.

The "Halyard" motif (scale degrees 1-5-4-3, then 1-2-3) is the squad's theme; it appears on the
horn in the briefing, on a soft piano at the ridge and in full for the credits. The V-01 reveal
cue deliberately deflates into a woodwind shrug (the reveal is comic, not horror).
"""
from __future__ import annotations
import argparse, os, subprocess, tempfile, wave
import numpy as np
from scipy import signal

SR = 44100
A4 = 440.0
NOTE = {n: i for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}


def hz(name):
    """'A3', 'F#4' -> frequency."""
    n, o = name[:-1], int(name[-1])
    return A4 * 2 ** ((NOTE[n] + 12 * (o - 4) - 9) / 12)


def midi_hz(m): return A4 * 2 ** ((m - 69) / 12)


def lp(x, f, order=2):
    b, a = signal.butter(order, min(f / (SR / 2), 0.99), 'low'); return signal.lfilter(b, a, x)


def hp(x, f, order=2):
    b, a = signal.butter(order, f / (SR / 2), 'high'); return signal.lfilter(b, a, x)


def adsr(n, a, d, s, r):
    t = np.arange(n) / SR
    dur = n / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((dur - t) / max(r, 1e-4), 0, 1)
    return e * rel


# ---- instruments ---------------------------------------------------------------------------------

def pad(f, dur, rng, bright=1800, det=0.006, voices=5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for v in range(voices):
        d = 1 + det * (v - (voices - 1) / 2) / ((voices - 1) / 2 + 1e-9)
        ph = rng.uniform(0, 2 * np.pi)
        x += signal.sawtooth(2 * np.pi * f * d * t + ph) * 0.5 + np.sin(2 * np.pi * f * d * t + ph) * 0.5
    x = lp(x / voices, bright)
    return x * adsr(n, min(1.2, dur * 0.3), 1.0, 0.85, min(1.5, dur * 0.4))


def strings(f, dur, rng, bright=2600):
    n = int(SR * dur)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t + rng.uniform(0, 6)) * np.clip(t / 0.8, 0, 1)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    x = sum(signal.sawtooth(ph * (1 + 0.003 * k) + k) for k in range(-1, 2)) / 3
    x = lp(x, bright) + lp(np.random.default_rng(int(f)).standard_normal(n), 4000) * 0.01
    return x * adsr(n, 0.25, 0.6, 0.8, 0.4)


def pluck(f, dur, rng, damp=0.996, bright=0.5):
    """Karplus-Strong string, computed one period at a time."""
    n = int(SR * dur)
    p = max(2, int(SR / f))
    buf = rng.uniform(-1, 1, p)
    if p > 12:
        buf = lp(buf, 1500 + 6000 * bright)
    periods = -(-n // p)
    out = np.empty(periods * p)
    for k in range(periods):
        out[k * p:(k + 1) * p] = buf
        buf = damp * 0.5 * (buf + np.roll(buf, 1))
    return out[:n] * adsr(n, 0.002, 0.4, 0.6, 0.08)


def piano(f, dur, rng):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, g in ((1, 1.0), (2, 0.45), (3, 0.22), (4, 0.12), (5, 0.07)):
        inh = 1 + 0.0004 * k * k
        x += g * np.sin(2 * np.pi * f * k * inh * t) * np.exp(-t * (1.2 + 0.9 * k))
    ham = np.random.default_rng(int(f * 10)).standard_normal(int(SR * 0.01)) * 0.05
    x[:len(ham)] += lp(ham, 3000)
    return x * adsr(n, 0.003, 2.0, 1.0, 0.15)


def horn(f, dur, rng):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = 2 * np.pi * f * t * (1 + 0.003 * np.sin(2 * np.pi * 4.6 * t))
    x = sum((0.9 ** k) * np.sin(ph * k) for k in range(1, 8))
    x = lp(x, 1200 + 400 * np.clip(t / 0.3, 0, 1).mean())
    return x * adsr(n, 0.12, 0.5, 0.75, 0.3) * 0.5


def flute(f, dur, rng):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = 2 * np.pi * f * t * (1 + 0.005 * np.sin(2 * np.pi * 5 * t) * np.clip(t / 0.4, 0, 1))
    breath = lp(np.random.default_rng(int(f)).standard_normal(n), 3000) * 0.08
    x = np.sin(ph) + 0.2 * np.sin(2 * ph) + breath
    return x * adsr(n, 0.06, 0.3, 0.8, 0.12) * 0.5


def bassoon(f, dur, rng):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = 2 * np.pi * f * t
    x = signal.square(ph, 0.3) * 0.5 + signal.sawtooth(ph) * 0.3
    return lp(x, 900) * adsr(n, 0.04, 0.3, 0.7, 0.1) * 0.6


def sub_bass(f, dur, rng):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    return x * adsr(n, 0.02, 0.4, 0.8, 0.2)


def drum(kind, rng):
    if kind == 'taiko':
        n = int(SR * 1.2); t = np.arange(n) / SR
        f = 55 + 70 * np.exp(-t * 20)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
        x += lp(rng.standard_normal(n), 900) * np.exp(-t * 30) * 0.4
        return x
    if kind == 'low_tom':
        n = int(SR * 0.6); t = np.arange(n) / SR
        f = 90 + 60 * np.exp(-t * 25)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 8) * 0.7
    if kind == 'shaker':
        n = int(SR * 0.09); t = np.arange(n) / SR
        return hp(rng.standard_normal(n), 5000) * np.exp(-t * 60) * 0.25
    if kind == 'rim':
        n = int(SR * 0.08); t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 1700 * t) * 0.5 + hp(rng.standard_normal(n), 2000) * 0.5) * np.exp(-t * 90) * 0.4
    if kind == 'pulse':  # muted ticking clock-like pulse
        n = int(SR * 0.12); t = np.arange(n) / SR
        return np.sin(2 * np.pi * 820 * t) * np.exp(-t * 70) * 0.3
    raise ValueError(kind)


INSTR = dict(pad=pad, strings=strings, pluck=pluck, piano=piano, horn=horn, flute=flute, bassoon=bassoon,
             sub=sub_bass)


# ---- arrangement helpers -------------------------------------------------------------------------

class Track:
    def __init__(self, sec, seed):
        self.n = int(SR * sec)
        self.L = np.zeros(self.n)
        self.R = np.zeros(self.n)
        self.rng = np.random.default_rng(seed)
        self.sec = sec

    def add(self, x, at, gain=1.0, pan=0.0):
        i = int(at * SR)
        if i >= self.n:
            return
        x = x[:self.n - i] * gain
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.L[i:i + len(x)] += x * l
        self.R[i:i + len(x)] += x * r

    def note(self, inst, f, at, dur, gain=1.0, pan=0.0, **kw):
        self.add(INSTR[inst](f, dur, self.rng, **kw), at, gain, pan)

    def hit(self, kind, at, gain=1.0, pan=0.0):
        self.add(drum(kind, self.rng), at, gain, pan)

    def wrap_tail(self, tail):
        """Folds anything past the end back to the start so the cue loops seamlessly."""
        pass

    def mix(self, reverb=0.25, peak=0.7, loop=True):
        st = np.stack([self.L, self.R])
        if loop:
            # render a reverb over two periods and keep the second, so the tail wraps into the head
            st2 = np.concatenate([st, st], axis=1)
        else:
            st2 = np.concatenate([st, np.zeros((2, int(SR * 3)))], axis=1)
        out = np.stack([st2[c] + reverb * self.reverb(st2[c], c) for c in range(2)])
        if loop:
            out = out[:, self.n:]
        out = np.tanh(out * 1.1)
        return out / (np.max(np.abs(out)) + 1e-9) * peak

    def reverb(self, x, c):
        # Schroeder-style: four combs and two allpasses (different per channel for width), each run
        # block-wise (a block of `d` samples only depends on the previous block)
        delays = [1557, 1617, 1491, 1422] if c == 0 else [1580, 1640, 1513, 1445]
        src = lp(x, 5000, 1)
        y = np.zeros(len(x))
        for d in delays:
            y += comb(src, d, 0.84)
        y /= len(delays)
        for d in (225, 556) if c == 0 else (241, 571):
            y = allpass(y, d, 0.5)
        return y


def comb(x, d, g):
    n = len(x)
    m = -(-n // d)
    xb = np.zeros(m * d); xb[:n] = x
    xb = xb.reshape(m, d)
    y = np.empty_like(xb)
    prev = np.zeros(d)
    for k in range(m):
        prev = xb[k] + g * prev
        y[k] = prev
    return y.reshape(-1)[:n]


def allpass(x, d, g):
    n = len(x)
    m = -(-n // d)
    xb = np.zeros(m * d); xb[:n] = x
    xb = xb.reshape(m, d)
    y = np.empty_like(xb)
    px = np.zeros(d); py = np.zeros(d)
    for k in range(m):
        cur = -g * xb[k] + px + g * py
        y[k] = cur
        px, py = xb[k], cur
    return y.reshape(-1)[:n]


def chord_tones(root, quality):
    iv = {'m': (0, 3, 7), 'M': (0, 4, 7), 'sus2': (0, 2, 7), 'm7': (0, 3, 7, 10), 'M7': (0, 4, 7, 11),
          'add9': (0, 4, 7, 14), 'madd9': (0, 3, 7, 14), 'dim': (0, 3, 6)}[quality]
    r = NOTE[root]
    return [r + i for i in iv]


def voiced(root, quality, octave=3):
    base = 12 * (octave + 1)
    return [midi_hz(base + t) for t in chord_tones(root, quality)]


# ---- cues ----------------------------------------------------------------------------------------

def area_cue(name, prog, bpm, bars_per_chord, seed, mood):
    """Explore bed and tension layer over the same progression and length."""
    beat = 60.0 / bpm
    bar = beat * 4
    sec = len(prog) * bars_per_chord * bar
    ex = Track(sec, seed)
    te = Track(sec, seed + 1)
    for ci, (root, q) in enumerate(prog):
        t0 = ci * bars_per_chord * bar
        dur = bars_per_chord * bar
        for k, f in enumerate(voiced(root, q, 3)):
            ex.note('pad', f, t0, dur + 0.6, 0.22, pan=-0.4 + 0.4 * k, bright=mood['bright'])
        ex.note('sub', voiced(root, q, 1)[0], t0, dur, 0.35)
        # sparse plucked arpeggio (explore)
        tones = voiced(root, q, 4)
        steps = int(dur / (beat / 2))
        for s in range(steps):
            if ex.rng.random() < mood['arp']:
                f = tones[(s * 2 + ci) % len(tones)] * (2 if ex.rng.random() < 0.15 else 1)
                ex.note('pluck', f, t0 + s * beat / 2, beat * 1.5, 0.16, pan=ex.rng.uniform(-0.6, 0.6),
                        bright=0.35)
        if mood.get('motif') and ci % 2 == 0:
            mt = voiced(root, q, 4)
            for j, deg in enumerate(mood['motif']):
                ex.note(mood.get('motif_inst', 'flute'), mt[deg % len(mt)] * (2 if deg >= 3 else 1),
                        t0 + bar + j * beat, beat * 0.95, 0.12, pan=0.2)
        # tension: low string ostinato in eighths, taiko on 1 and the "and" of 3, rim pulses
        lo = voiced(root, q, 2)
        for s in range(int(dur / (beat / 2))):
            f = lo[0] if s % 4 != 3 else lo[1]
            te.note('strings', f, t0 + s * beat / 2, beat * 0.45, 0.2, pan=-0.3)
        for b in range(bars_per_chord):
            tb = t0 + b * bar
            te.hit('taiko', tb, 0.7)
            te.hit('taiko', tb + beat * 2.5, 0.45)
            te.hit('low_tom', tb + beat * 3.5, 0.35, pan=0.3)
            for q8 in range(8):
                te.hit('rim' if q8 % 2 else 'shaker', tb + q8 * beat / 2, 0.35, pan=0.4)
        for k, f in enumerate(voiced(root, q, 4)[:2]):
            te.note('strings', f, t0, dur, 0.09, pan=0.5 - k)
    return {f'{name}_explore': ex.mix(0.3, 0.55), f'{name}_tension': te.mix(0.2, 0.6)}


def halyard_theme(sec_per_chord=3.2, seed=31, inst='horn', final=False):
    prog = [('D', 'm'), ('A#', 'M'), ('F', 'M'), ('C', 'M'), ('D', 'm'), ('G', 'm'), ('A#', 'M'), ('A', 'M')]
    sec = sec_per_chord * len(prog) + (4 if final else 0)
    tr = Track(sec, seed)
    for ci, (root, q) in enumerate(prog):
        t0 = ci * sec_per_chord
        for k, f in enumerate(voiced(root, q, 3)):
            tr.note('strings', f, t0, sec_per_chord + 0.3, 0.16, pan=-0.5 + 0.5 * k)
        tr.note('sub', voiced(root, q, 1)[0], t0, sec_per_chord, 0.3)
    # motif: D A G F | D E F (scale degrees 1 5 4 3, 1 2 3), then answer
    melody = [('D4', 0, 1.0), ('A4', 1.0, 1.0), ('G4', 2.0, 0.8), ('F4', 2.8, 1.8),
              ('D4', 6.4, 0.8), ('E4', 7.2, 0.8), ('F4', 8.0, 2.2),
              ('A4', 12.8, 1.0), ('A#4', 13.8, 0.6), ('C5', 14.4, 1.4), ('A4', 16.0, 2.6),
              ('G4', 19.2, 0.8), ('F4', 20.0, 0.8), ('E4', 20.8, 1.0), ('C#4', 21.8, 1.2), ('D4', 23.0, 2.6)]
    for n, t, d in melody:
        tr.note(inst, hz(n), t, d, 0.3 if inst == 'horn' else 0.25, pan=0.1)
    if final:
        for k, f in enumerate(voiced('D', 'M', 3)):
            tr.note('strings', f, len(prog) * sec_per_chord, 4.0, 0.2, pan=-0.5 + 0.5 * k)
        tr.hit('taiko', len(prog) * sec_per_chord, 0.5)
    return tr.mix(0.35, 0.6, loop=not final)


def reveal_cue(seed=41):
    """Rising suspense that deflates: a held tremolo chord climbs, stops on a rest, then a bassoon
    and flute play a little shrug (major, light, slightly silly)."""
    sec = 16.0
    tr = Track(sec, seed)
    for i, (r, q) in enumerate((('E', 'm'), ('F', 'M'), ('F#', 'dim'), ('G', 'M'))):
        for k, f in enumerate(voiced(r, q, 3)):
            for s in range(int(2.0 / 0.08)):
                tr.note('strings', f * (1 + 0.002 * k), i * 2.0 + s * 0.08, 0.09, 0.05 + 0.02 * i, pan=-0.5 + 0.5 * k)
        tr.hit('taiko', i * 2.0, 0.25 + 0.12 * i)
    # silence at 8.0 - 8.9, then the shrug in C major
    shrug = [('G2', 'bassoon', 8.9, 0.35), ('C3', 'bassoon', 9.3, 0.35), ('G2', 'bassoon', 9.75, 0.6),
             ('E5', 'flute', 10.6, 0.25), ('D5', 'flute', 10.9, 0.25), ('C5', 'flute', 11.2, 0.6),
             ('G4', 'pluck', 12.0, 0.4), ('C5', 'pluck', 12.4, 1.2)]
    for n, inst, t, d in shrug:
        tr.note(inst, hz(n), t, d, 0.35)
    for k, f in enumerate(voiced('C', 'M', 3)):
        tr.note('pad', f, 12.0, 3.8, 0.12, pan=-0.5 + 0.5 * k)
    return tr.mix(0.3, 0.6, loop=False)


def credits_cue(seed=51):
    """The Halyard theme on piano, then the full orchestra pass."""
    a = halyard_theme(3.0, seed, 'piano', final=False)
    b = halyard_theme(3.2, seed + 1, 'horn', final=True)
    gap = np.zeros((2, int(SR * 0.5)))
    return np.concatenate([a * 0.85, gap, b], axis=1)


def menu_cue(seed=61):
    prog = [('D', 'madd9'), ('A#', 'M7'), ('F', 'add9'), ('C', 'sus2')]
    beat = 60 / 72
    sec = len(prog) * 2 * beat * 4
    tr = Track(sec, seed)
    for ci, (r, q) in enumerate(prog):
        t0 = ci * 2 * beat * 4
        for k, f in enumerate(voiced(r, q, 3)):
            tr.note('pad', f, t0, 8 * beat + 0.8, 0.2, pan=-0.5 + 0.35 * k, bright=1400)
        for s in range(8):
            tones = voiced(r, q, 4)
            tr.note('piano', tones[(s * 3) % len(tones)], t0 + s * beat, beat * 2.5, 0.12, pan=0.25)
    return tr.mix(0.4, 0.5)


def encode(path, st):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        tmp = f.name
    d = (np.clip(st.T, -1, 1) * 32767).astype('<i2')
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-c:a', 'libvorbis', '-q:a', '4', path])
    os.unlink(tmp)


AREAS = {
    # name: progression, bpm, bars per chord, seed, mood
    'forest': ([('E', 'm'), ('C', 'M'), ('G', 'M'), ('D', 'M'), ('E', 'm'), ('C', 'M'), ('A', 'm'), ('B', 'm')], 84, 2, 101,
               dict(bright=1600, arp=0.45, motif=[0, 2, 1, 0], motif_inst='flute')),
    'perimeter': ([('A', 'm'), ('F', 'M'), ('D', 'm'), ('E', 'M'), ('A', 'm'), ('G', 'M'), ('F', 'M'), ('E', 'M')], 92, 2, 201,
                  dict(bright=1300, arp=0.3)),
    'facility': ([('C', 'm'), ('G#', 'M'), ('F', 'm'), ('G', 'M'), ('C', 'm'), ('A#', 'M'), ('G#', 'M'), ('G', 'M')], 76, 2, 301,
                 dict(bright=1100, arp=0.25)),
    'deep': ([('F', 'm'), ('C#', 'M'), ('A#', 'm'), ('C', 'M'), ('F', 'm'), ('D#', 'M'), ('C#', 'M'), ('C', 'M')], 70, 2, 401,
             dict(bright=900, arp=0.2)),
}


def build(out, only=None):
    cues = {}
    for name, (prog, bpm, bpc, seed, mood) in AREAS.items():
        if only and name not in only:
            continue
        cues.update(area_cue(name, prog, bpm, bpc, seed, mood))
    if not only or 'themes' in only:
        cues['briefing'] = halyard_theme(3.4, 31, 'horn')
        cues['ridge'] = halyard_theme(3.0, 33, 'piano')
        cues['reveal'] = reveal_cue()
        cues['credits'] = credits_cue()
        cues['menu'] = menu_cue()
    for k, st in cues.items():
        p = os.path.join(out, 'audio', 'music', f'{k}.ogg')
        encode(p, st)
        print(f'{k:20s} {st.shape[1] / SR:6.1f}s')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    build(a.out, a.only)
