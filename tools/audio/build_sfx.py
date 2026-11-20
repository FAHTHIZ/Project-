# SPDX-License-Identifier: Apache-2.0
"""Synthesise the SPECIAL OPS sound effects from code (numpy + scipy), deterministic and original.

    python3 tools/audio/build_sfx.py --out game/assets

Writes 16-bit mono WAV files under <out>/audio/{weapons,foley,ui}. No recordings or third-party
samples are used (see docs/ASSET_PROVENANCE.md). The weapons are fictional "pulse" emitters, so
their sounds are designed as electrical zaps with a mechanical body rather than gunshots.
"""
from __future__ import annotations
import argparse, os, wave
import numpy as np
from scipy import signal

SR = 44100


def t_axis(sec):
    return np.arange(int(SR * sec)) / SR


def noise(sec, seed):
    return np.random.default_rng(seed).standard_normal(int(SR * sec))


def lp(x, hz, order=2):
    b, a = signal.butter(order, min(hz / (SR / 2), 0.99), 'low'); return signal.lfilter(b, a, x)


def hp(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2), 'high'); return signal.lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], 'band'); return signal.lfilter(b, a, x)


def env(t, attack, decay):
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) * decay)


def sweep(t, f0, f1, k):
    """Sine whose frequency glides exponentially from f0 to f1 with rate k."""
    f = f1 + (f0 - f1) * np.exp(-t * k)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def pad(x, sec):
    n = int(SR * sec); return np.r_[x, np.zeros(max(0, n - len(x)))][:max(n, len(x))]


def mix(*parts):
    n = max(len(p) for p in parts); out = np.zeros(n)
    for p in parts: out[:len(p)] += p
    return out


def at(x, sec, total):
    out = np.zeros(int(SR * total)); i = int(SR * sec); n = min(len(x), len(out) - i)
    out[i:i + n] += x[:n]; return out


def finish(x, peak=0.89, drive=1.4, fade=0.01):
    x = np.tanh(x * drive) / np.tanh(drive)
    nf = int(SR * fade); x[-nf:] *= np.linspace(1, 0, nf)
    x = x - np.mean(x)
    return x / (np.max(np.abs(x)) + 1e-9) * peak


def write(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())


# ---- weapons --------------------------------------------------------------------------------

def pulse_shot(seed, f0, f1, body_hz, length, bright, tail):
    t = t_axis(length)
    click = hp(noise(0.006, seed), 2500) * env(t_axis(0.006), 0.0002, 600)
    zap = sweep(t, f0, f1, 28) * env(t, 0.0015, 22)
    zap += 0.35 * sweep(t, f0 * 2.01, f1 * 2.0, 34) * env(t, 0.001, 38)
    fm = np.sin(2 * np.pi * 63 * t) * 0.5 + 0.5
    zap *= 0.75 + 0.25 * fm
    thump = np.sin(2 * np.pi * body_hz * t * (1 - 0.25 * t)) * env(t, 0.002, 30)
    air = lp(hp(noise(length, seed + 1), 300), bright) * env(t, 0.001, tail)
    crackle = bp(noise(length, seed + 2), 3000, 9000) * env(t, 0.0005, 70) * 0.6
    return finish(mix(click * 0.9, zap * 0.55, thump * 0.8, air * 0.7, crackle))


def dry_click(seed):
    t = t_axis(0.12)
    a = bp(noise(0.12, seed), 1800, 7000) * env(t, 0.0003, 160)
    b = at(bp(noise(0.05, seed + 1), 900, 4000) * env(t_axis(0.05), 0.0003, 220) * 0.6, 0.035, 0.12)
    beep = np.sin(2 * np.pi * 520 * t) * env(t, 0.004, 40) * 0.25
    return finish(mix(a, b, beep), 0.6)


def mech(seed, sec, events, tone=None):
    """Foley-like mechanical sequence from (time, gain, lo, hi, decay) clicks."""
    out = np.zeros(int(SR * sec))
    for i, (tm, g, lo, hi, dec) in enumerate(events):
        n = bp(noise(0.08, seed + i), lo, hi) * env(t_axis(0.08), 0.0004, dec) * g
        out += at(n, tm, sec)
    if tone:
        f0, f1, t0, t1, g = tone
        t = t_axis(t1 - t0)
        w = sweep(t, f0, f1, -2.5 / (t1 - t0)) if f1 > f0 else sweep(t, f0, f1, 6)
        e = np.sin(np.pi * np.clip(t / (t1 - t0), 0, 1)) ** 1.5
        out += at(w * e * g, t0, sec)
    return finish(out, 0.75, 1.1)


def rising_whine(sec, f0, f1, seed):
    t = t_axis(sec)
    f = f0 * (f1 / f0) ** (t / sec)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * 0.6 + np.sin(ph * 2) * 0.2 + 0.08 * bp(noise(sec, seed), 2000, 6000)
    e = np.clip(t / 0.03, 0, 1) * np.clip((sec - t) / 0.05, 0, 1)
    ding = at(np.sin(2 * np.pi * f1 * 1.5 * t_axis(0.25)) * env(t_axis(0.25), 0.002, 14) * 0.5, sec - 0.04, sec + 0.2)
    return finish(mix(x * e * 0.7, ding), 0.7, 1.0)


def power_down(sec, seed):
    t = t_axis(sec)
    w = sweep(t, 900, 70, 5) * np.exp(-t * 3) * 0.7
    buzz = signal.sawtooth(2 * np.pi * (120 - 80 * t / sec) * t) * np.exp(-t * 4) * 0.25
    sp = bp(noise(sec, seed), 2000, 8000) * env(t, 0.001, 18) * 0.5
    return finish(mix(w, lp(buzz, 2500), sp), 0.8)


def impact(seed, lo, hi, dec, thump_hz, sec=0.25):
    t = t_axis(sec)
    n = bp(noise(sec, seed), lo, hi) * env(t, 0.0003, dec)
    th = np.sin(2 * np.pi * thump_hz * t) * env(t, 0.001, 45) * 0.6
    fizz = bp(noise(sec, seed + 5), 4000, 12000) * env(t, 0.001, 30) * 0.25
    return finish(mix(n, th, fizz), 0.8)


def modes(t, freqs, decays, gains, seed):
    """Damped sinusoids (struck-object resonances) with a seeded phase."""
    rng = np.random.default_rng(seed)
    out = np.zeros(len(t))
    for f, d, g in zip(freqs, decays, gains):
        out += np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) * np.exp(-t * d) * g
    return out


def grit(seed, sec, start, n, lo, hi, g):
    """Sparse debris ticks falling back after the hit (soil, stone chips, splinters)."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * sec))
    for _ in range(n):
        st = start + rng.exponential(0.06)
        if st > sec - 0.03:
            continue
        click = bp(noise(0.02, int(rng.integers(1 << 30))), lo, hi) * env(t_axis(0.02), 0.0002, 260)
        out += at(click * rng.uniform(0.2, 1.0) * g, st, sec)
    return out


# Surface impacts of a pulse round (lib/footsteps.luau Footsteps.impact_surface picks one).
def impact_dirt(seed, sec=0.45):
    t = t_axis(sec)
    thump = np.sin(2 * np.pi * (62 + 30 * np.exp(-t * 40)) * t) * env(t, 0.001, 30) * 0.9
    body = lp(bp(noise(sec, seed), 120, 1600) * env(t, 0.0005, 32), 1400)
    spray = grit(seed + 1, sec, 0.03, 18, 1500, 6000, 0.35)
    return finish(mix(thump, body * 0.9, spray), 0.8, 1.3)


def impact_wood(seed, sec=0.5):
    t = t_axis(sec)
    knock = modes(t, [340, 690, 1130, 1790], [38, 52, 70, 95], [0.8, 0.55, 0.35, 0.2], seed)
    crack = bp(noise(sec, seed + 2), 1500, 7000) * env(t, 0.0002, 140) * 0.9
    splinter = grit(seed + 3, sec, 0.02, 9, 2000, 7000, 0.3)
    return finish(mix(knock * env(t, 0.0008, 6), crack, splinter), 0.82, 1.5)


def impact_stone(seed, sec=0.5):
    t = t_axis(sec)
    crack = bp(noise(sec, seed), 1400, 10000) * env(t, 0.0002, 75)
    ring = modes(t, [2150, 3420, 4980], [60, 80, 110], [0.35, 0.25, 0.15], seed + 1)
    thud = np.sin(2 * np.pi * 120 * t) * env(t, 0.001, 50) * 0.4
    chips = grit(seed + 2, sec, 0.025, 14, 2500, 9000, 0.4)
    return finish(mix(crack, ring, thud, chips), 0.82, 1.6)


def impact_metal(seed, sec=0.8):
    t = t_axis(sec)
    clank = bp(noise(sec, seed), 2000, 11000) * env(t, 0.0002, 160) * 0.8
    ring = modes(t, [1240, 2710, 4160, 5630, 7350], [9, 12, 16, 22, 30], [0.55, 0.5, 0.35, 0.25, 0.15], seed + 1)
    body = np.sin(2 * np.pi * 410 * t) * env(t, 0.0005, 25) * 0.35
    return finish(mix(clank, ring, body), 0.8, 1.3)


def tick(freq, sec=0.07, g=0.8):
    t = t_axis(sec)
    return finish(np.sin(2 * np.pi * freq * t) * env(t, 0.0006, 70) + 0.3 * np.sin(2 * np.pi * freq * 2.7 * t) * env(t, 0.0003, 120), g, 1.0)


def scan_ping():
    t = t_axis(1.1)
    x = np.zeros(len(t))
    for i, f in enumerate((1320, 1760, 2640)):
        x += at(np.sin(2 * np.pi * f * t_axis(0.6)) * env(t_axis(0.6), 0.003, 7) * (0.6 - 0.15 * i), i * 0.07, 1.1)
    sw = sweep(t, 400, 2200, -1.8) * env(t, 0.05, 4) * 0.15
    return finish(mix(x, sw), 0.7, 1.0)


def cloth(seed, sec=0.25, g=0.5):
    t = t_axis(sec)
    e = np.sin(np.pi * np.clip(t / sec, 0, 1)) ** 2
    return finish(lp(hp(noise(sec, seed), 400), 3500) * e, g, 1.0)


# ---- foley ----------------------------------------------------------------------------------

def footstep(seed, surface):
    sec = 0.22
    t = t_axis(sec)
    r = np.random.default_rng(seed)
    if surface == 'dirt':
        x = lp(noise(sec, seed), 1400 + r.uniform(-200, 200)) * env(t, 0.004, 30)
        x += bp(noise(sec, seed + 9), 2000, 6000) * env(t, 0.02, 25) * 0.25  # leaf crunch
        x += np.sin(2 * np.pi * 70 * t) * env(t, 0.003, 50) * 0.5
    elif surface == 'concrete':
        x = bp(noise(sec, seed), 300, 5000) * env(t, 0.001, 55)
        x += at(bp(noise(0.08, seed + 3), 1500, 7000) * env(t_axis(0.08), 0.001, 70) * 0.4, 0.03, sec)
        x += np.sin(2 * np.pi * 95 * t) * env(t, 0.002, 60) * 0.4
    elif surface == 'gravel':  # trail grit and rock: a heel thud plus a cluster of small stone ticks
        x = lp(noise(sec, seed), 900) * env(t, 0.003, 38) * 0.7
        x += np.sin(2 * np.pi * 80 * t) * env(t, 0.003, 55) * 0.45
        for k in range(int(r.integers(9, 15))):
            d = r.uniform(0.0, 0.11)
            g = bp(noise(0.025, seed + 30 + k), 2500, 9000) * env(t_axis(0.025), 0.0005, 260) * r.uniform(0.15, 0.4)
            x += at(g, d, sec)
    elif surface == 'grass':  # meadow: a soft thump and a blade swish
        x = lp(noise(sec, seed), 700) * env(t, 0.006, 30) * 0.6
        x += np.sin(2 * np.pi * 65 * t) * env(t, 0.004, 45) * 0.35
        sw = bp(noise(sec, seed + 7), 1800, 7000) * np.sin(np.pi * np.clip(t / 0.16, 0, 1)) ** 2 * 0.28
        x += sw
    elif surface == 'mud':  # rain-soaked forest floor: heavy suction squelch with a wet release
        x = lp(noise(sec, seed), 600) * env(t, 0.008, 22) * 0.8
        x += np.sin(2 * np.pi * (55 + 30 * np.exp(-t * 20)) * t) * env(t, 0.006, 28) * 0.5
        rel = bp(noise(0.12, seed + 5), 700, 2600) * np.sin(np.pi * np.clip(t_axis(0.12) / 0.12, 0, 1)) ** 3
        rel *= 1 + 0.6 * np.sin(2 * np.pi * r.uniform(28, 40) * t_axis(0.12))  # bubbly suction
        x += at(rel * 0.45, 0.07 + r.uniform(0, 0.03), sec)
    elif surface == 'splash':  # foot into a puddle: sheet splash and droplets (layered on a step)
        x = bp(noise(sec, seed), 900, 8000) * env(t, 0.004, 18) * 0.7
        for k in range(int(r.integers(6, 11))):
            f0 = r.uniform(900, 2600)
            d = r.uniform(0.02, 0.17)
            tt = t_axis(0.03)
            x += at(np.sin(2 * np.pi * (f0 + 1800 * tt / 0.03) * tt) * env(tt, 0.001, 140) * r.uniform(0.1, 0.25), d, sec)
    elif surface == 'wood':  # plank floor: hollow knock with a short resonance
        x = bp(noise(sec, seed), 150, 3500) * env(t, 0.001, 45) * 0.7
        for k, f in enumerate((118, 236, 410)):
            x += np.sin(2 * np.pi * f * r.uniform(0.95, 1.05) * t) * env(t, 0.001, 26 + 10 * k) * (0.35 / (k + 1))
        x += at(bp(noise(0.05, seed + 4), 900, 4000) * env(t_axis(0.05), 0.001, 90) * 0.12, 0.04, sec)  # creak tick
    else:  # metal grating
        x = bp(noise(sec, seed), 500, 6000) * env(t, 0.001, 40)
        for k, f in enumerate((410, 655, 1230)):
            x += np.sin(2 * np.pi * f * r.uniform(0.97, 1.03) * t) * env(t, 0.001, 20 + 8 * k) * 0.18
    return finish(x, 0.55 + r.uniform(-0.05, 0.05), 1.2)


def gear_rattle(seed, sec=0.2):
    # webbing creak and buckle/mag-pouch ticks that ride on a running stride
    t = t_axis(sec)
    r = np.random.default_rng(seed)
    x = lp(hp(noise(sec, seed), 500), 3000) * np.sin(np.pi * np.clip(t / sec, 0, 1)) ** 2 * 0.25
    for k in range(int(r.integers(3, 6))):
        f = r.uniform(2200, 4800)
        tt = t_axis(0.035)
        x += at(np.sin(2 * np.pi * f * tt) * env(tt, 0.0005, 160) * r.uniform(0.15, 0.35), r.uniform(0.01, 0.15), sec)
    return finish(x, 0.42, 1.0)


def land(seed, heavy):
    # both feet and the kit settling after a drop
    sec = 0.45 if heavy else 0.3
    t = t_axis(sec)
    x = lp(noise(sec, seed), 500 if heavy else 800) * env(t, 0.004, 14 if heavy else 22)
    x += np.sin(2 * np.pi * (48 if heavy else 62) * t) * env(t, 0.003, 18 if heavy else 30) * (0.9 if heavy else 0.5)
    x += at(gear_rattle(seed + 1, 0.18) * 0.6, 0.05, sec)
    return finish(x, 0.8 if heavy else 0.6, 1.3)


# ---- vehicle --------------------------------------------------------------------------------

def loop_noise(sec, seed, lo=None, hi=None):
    """Noise that loops seamlessly: filtered over two periods, the second one kept."""
    x = np.tile(noise(sec, seed), 2)
    if lo and hi: x = bp(x, lo, hi)
    elif hi: x = lp(x, hi)
    elif lo: x = hp(x, lo)
    return x[len(x) // 2:]


def engine_idle(sec=2.0, fire_hz=28.0, seed=500):
    """Diesel-style idle loop: firing pulses with harmonics and pulsed intake/exhaust noise.
    The firing rate divides the loop length exactly, so the loop has no seam."""
    t = t_axis(sec)
    ph = 2 * np.pi * fire_hz * t
    pulses = (0.5 + 0.5 * np.cos(ph)) ** 6
    tone = sum(np.sin(ph * k + k * 0.7) / k ** 0.9 for k in range(1, 9))
    rumble = loop_noise(sec, seed, None, 380) * (0.35 + 0.65 * pulses)
    clatter = loop_noise(sec, seed + 1, 1200, 4200) * pulses ** 2 * 0.25
    half = np.sin(ph / 2) * 0.35  # uneven cylinder for character (fire_hz/2 still divides the loop)
    x = tone * 0.45 + rumble * 1.3 + clatter + half * 0.3
    x = lp(np.tile(x, 2), 2600)[len(x):]
    x = np.tanh(x * 1.2)
    return x / np.max(np.abs(x)) * 0.8


def engine_start(sec=1.8, seed=520):
    t = t_axis(sec)
    crank = np.zeros(len(t))
    k = int(SR * 0.7)
    tc = t[:k]
    crank[:k] = (bp(noise(0.7, seed), 200, 1400) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 9 * tc))) * 0.5 +
                 signal.sawtooth(2 * np.pi * 52 * tc) * 0.15)
    catch_t = t[k:] - t[k]
    rpm = 28 + 30 * np.exp(-catch_t * 2.5) * (1 - np.exp(-catch_t * 25))
    ph = 2 * np.pi * np.cumsum(rpm) / SR
    nz = lp(noise(sec, seed + 1), 450)[:len(ph)]
    run = sum(np.sin(ph * j) / j for j in range(1, 7)) * 0.5 + nz * 0.8
    out = crank.copy(); out[k:] += run * np.clip(catch_t / 0.05, 0, 1)
    return finish(out, 0.8, 1.2, 0.08)


def engine_stop(sec=1.6, seed=540):
    t = t_axis(sec)
    rpm = 28 * np.exp(-t * 2.2)
    ph = 2 * np.pi * np.cumsum(rpm) / SR
    run = (sum(np.sin(ph * j) / j for j in range(1, 7)) * 0.5 + lp(noise(sec, seed), 400) * 0.6) * np.exp(-t * 2.4)
    shudder = np.sin(2 * np.pi * 9 * t) * np.exp(-((t - 0.55) / 0.12) ** 2) * 0.3
    ticks = sum(at(bp(noise(0.03, seed + i), 2500, 7000) * env(t_axis(0.03), 0.0003, 200) * 0.12, 0.9 + i * 0.21, sec)
                for i in range(3))
    return finish(mix(run + shudder, ticks), 0.75, 1.1, 0.1)


def door(seed, opening):
    sec = 0.6 if opening else 0.5
    t = t_axis(sec)
    if opening:
        latch = bp(noise(0.05, seed), 900, 5000) * env(t_axis(0.05), 0.0003, 150)
        creak = bp(signal.sawtooth(2 * np.pi * (180 + 60 * t) * t) * 0.3, 300, 2500) * np.sin(np.pi * np.clip((t - 0.08) / 0.4, 0, 1)) * 0.2
        return finish(mix(latch, creak, at(cloth(seed + 3, 0.3, 0.3) * 0.4, 0.1, sec)), 0.7, 1.1)
    thump = np.sin(2 * np.pi * 70 * t) * env(t, 0.002, 18) + lp(noise(sec, seed), 600) * env(t, 0.001, 22) * 0.8
    latch = at(bp(noise(0.05, seed + 1), 1500, 6000) * env(t_axis(0.05), 0.0003, 180) * 0.6, 0.01, sec)
    rattle = bp(noise(sec, seed + 2), 2000, 5000) * env(t, 0.01, 30) * 0.15
    return finish(mix(thump, latch, rattle), 0.85, 1.3)


def hatch(seed, opening):
    sec = 1.4 if opening else 0.8
    t = t_axis(sec)
    if opening:
        latch = bp(noise(0.06, seed), 700, 4000) * env(t_axis(0.06), 0.0003, 120)
        strut = bp(noise(sec, seed + 1), 1800, 7000) * np.clip((t - 0.15) / 0.2, 0, 1) * np.clip((1.25 - t) / 0.2, 0, 1) * 0.12
        stop = at(np.sin(2 * np.pi * 110 * t_axis(0.2)) * env(t_axis(0.2), 0.002, 30) * 0.4, 1.2, sec)
        return finish(mix(latch, strut, stop), 0.7, 1.0, 0.05)
    swing = lp(noise(sec, seed + 4), 900) * np.clip((t - 0.0) / 0.3, 0, 1) * np.clip((0.4 - t) / 0.05, 0, 1) * 0.15
    thud = at(np.sin(2 * np.pi * 60 * t_axis(0.4)) * env(t_axis(0.4), 0.002, 16) + lp(noise(0.4, seed), 500) * env(t_axis(0.4), 0.001, 20) * 0.8, 0.38, sec)
    latch = at(bp(noise(0.05, seed + 2), 1500, 6000) * env(t_axis(0.05), 0.0003, 160) * 0.5, 0.39, sec)
    return finish(mix(swing, thud, latch), 0.85, 1.3)


def tyre_roll(sec=2.0, seed=600):
    """Tyres on a gravel road, loopable: rumble plus sparse stone crunches."""
    x = loop_noise(sec, seed, None, 500) * 0.8
    r = np.random.default_rng(seed)
    n = len(x)
    for _ in range(90):
        i = r.integers(0, n); g = r.uniform(0.05, 0.3)
        grain = bp(noise(0.02, int(r.integers(1e6))), 1500, 6000) * env(t_axis(0.02), 0.0003, 260) * g
        j = (np.arange(len(grain)) + i) % n
        x[j] += grain
    return x / np.max(np.abs(x)) * 0.7


def handle(seed, sec=0.35, weight=0.5):
    """Picking up or setting down a field item: fabric, a soft knock, a strap buckle."""
    t = t_axis(sec)
    c = cloth(seed, sec * 0.8, 0.5)
    knock = at(lp(noise(0.1, seed + 1), 900) * env(t_axis(0.1), 0.001, 40) * weight, sec * 0.45, sec)
    buckle = at(bp(noise(0.03, seed + 2), 2500, 8000) * env(t_axis(0.03), 0.0003, 220) * 0.3, sec * 0.25, sec)
    return finish(mix(c, knock, buckle), 0.6, 1.0)


# ---- world, mission and ambient beds -------------------------------------------------------------

def motor_run(sec, seed, hz=46.0, clunk=True):
    """Gate/lift motor: geared hum with a slow wobble, start and stop clunks."""
    t = t_axis(sec)
    wob = 1 + 0.015 * np.sin(2 * np.pi * 0.7 * t)
    ph = 2 * np.pi * np.cumsum(hz * wob) / SR
    hum = sum(np.sin(ph * k) / k for k in (1, 2, 3, 5)) * 0.35
    grind = bp(noise(sec, seed), 300, 1800) * (0.25 + 0.1 * np.sin(2 * np.pi * 3.1 * t))
    e = np.clip(t / 0.4, 0, 1) * np.clip((sec - t) / 0.5, 0, 1)
    x = (hum + grind) * e
    if clunk:
        x = mix(x, at(impact(seed + 3, 120, 1400, 30, 55, 0.4) * 0.8, 0.0, sec),
                at(impact(seed + 4, 120, 1400, 30, 50, 0.4) * 0.9, sec - 0.45, sec))
    return finish(x, 0.8, 1.2)


def beep_seq(freqs, gap=0.11, sec=0.13, g=0.55):
    total = gap * len(freqs) + sec + 0.05
    x = np.zeros(int(SR * total))
    for i, f in enumerate(freqs):
        tt = t_axis(sec)
        b = (np.sin(2 * np.pi * f * tt) + 0.2 * np.sign(np.sin(2 * np.pi * f * tt))) * np.clip((sec - tt) / 0.02, 0, 1) * np.clip(tt / 0.004, 0, 1)
        x += at(b * 0.5, i * gap, total)
    return finish(x, g, 1.0)


def keys(seed, sec=1.6, n=11):
    rng = np.random.default_rng(seed)
    ev = sorted(rng.uniform(0.02, sec - 0.1, n))
    return mech(seed, sec, [(tm, rng.uniform(0.5, 1.0), 1500, 6500, 160) for tm in ev])


def heavy_cell_out(seed):
    m = mech(seed, 1.4, [(0.0, 1.0, 500, 3500, 50), (0.18, 0.8, 300, 2400, 40), (0.6, 0.9, 200, 1600, 30)])
    return finish(mix(m, at(power_down(1.0, seed + 1) * 0.7, 0.35, 1.4)), 0.85)


def birds(sec, seed, density=0.5):
    """Sparse songbird phrases: short frequency-modulated chirps in groups."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * sec))
    tm = rng.uniform(0.5, 2.0)
    while tm < sec - 1.5:
        f0 = rng.uniform(2600, 4800)
        n = rng.integers(2, 6)
        g = rng.uniform(0.08, 0.22)
        for k in range(n):
            d = rng.uniform(0.05, 0.13)
            tt = t_axis(d)
            f = f0 * (1 + rng.uniform(-0.25, 0.25) * tt / d) + 300 * np.sin(2 * np.pi * rng.uniform(20, 45) * tt)
            ch = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / d) ** 2
            out += at(ch * g, tm + k * (d + rng.uniform(0.03, 0.09)), sec)
        tm += rng.uniform(1.2, 4.5) / density
    return out


def wind_bed(sec, seed, lo=80, hi=900, gust=0.12):
    x = loop_noise(sec, seed, lo, hi)
    t = t_axis(sec)
    # gusts: periods that divide the loop so it stays seamless
    g = 0.75 + gust * np.sin(2 * np.pi * t * 2 / sec) + gust * 0.6 * np.sin(2 * np.pi * t * 5 / sec + 1.3)
    leaves = loop_noise(sec, seed + 7, 2500, 7000) * 0.12 * (g - 0.55)
    return x * g + leaves


def loopify(x, xf=0.6):
    """Crossfades the tail into the head so a bed with one-off events loops without a click."""
    n = int(SR * xf)
    head, tail = x[:n].copy(), x[-n:]
    w = np.linspace(0, 1, n)
    x = x[:-n].copy()
    x[:n] = head * w + tail * (1 - w)
    return x


def forest_bed(sec=24.0, seed=900):
    x = wind_bed(sec, seed) * 0.55 + birds(sec, seed + 1, 0.6)
    return loopify(x / np.max(np.abs(x)) * 0.6)


def creek_bed(sec=12.0, seed=920):
    t = t_axis(sec)
    base = loop_noise(sec, seed, 300, 2400) * 0.6
    burble = loop_noise(sec, seed + 1, 900, 5000)
    mod = 0.5 + 0.5 * np.sin(2 * np.pi * t * 37 / sec) * np.sin(2 * np.pi * t * 11 / sec)
    x = base + burble * mod * 0.35
    return x / np.max(np.abs(x)) * 0.55


def hum_bed(sec=8.0, seed=940, mains=50.0, air=0.4):
    t = t_axis(sec)
    hum = sum(np.sin(2 * np.pi * mains * k * t + k) / k ** 1.3 for k in (1, 2, 3, 4, 6))
    hvac = loop_noise(sec, seed, 60, 700) * air
    x = hum * 0.12 + hvac
    return x / np.max(np.abs(x)) * 0.45


def bunker_bed(sec=12.0, seed=960):
    t = t_axis(sec)
    drone = np.sin(2 * np.pi * 41.25 * t) * 0.3 + np.sin(2 * np.pi * 61.25 * t) * 0.12
    air = loop_noise(sec, seed, 40, 380) * 0.8
    drip_rng = np.random.default_rng(seed)
    drips = np.zeros(len(t))
    for tm in drip_rng.uniform(0.5, sec - 0.5, 7):
        drips += at(tick(drip_rng.uniform(900, 1700), 0.12, 0.6) * 0.2, tm, sec)
    x = drone + air + drips
    return loopify(x / np.max(np.abs(x)) * 0.5)


def camp_bed(sec=16.0, seed=980):
    gen = engine_idle(2.0, 25.0, seed)  # distant generator
    gen = lp(np.tile(gen, int(sec / 2)), 700) * 0.3
    x = wind_bed(sec, seed + 2, 80, 700, 0.08) * 0.5 + gen[:int(SR * sec)] + birds(sec, seed + 3, 0.3) * 0.7
    return loopify(x / np.max(np.abs(x)) * 0.55)



# ---- scares and atmosphere (false alarms: every one has an ordinary cause in the story) ------

def howl(sec, seed, f0=420.0, f1=640.0, far=True):
    """Distant canine howl: a gliding voiced tone with vibrato and formants, low-passed by distance."""
    t = t_axis(sec)
    rng = np.random.default_rng(seed)
    shape = np.interp(t / sec, [0, 0.18, 0.55, 0.85, 1.0], [f0 * 0.8, f1, f1 * 0.97, f0 * 0.9, f0 * 0.7])
    vib = 1 + 0.012 * np.sin(2 * np.pi * (5.2 + rng.uniform(-0.4, 0.4)) * t)
    ph = 2 * np.pi * np.cumsum(shape * vib) / SR
    voiced = np.sin(ph) + 0.45 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph) + 0.08 * np.sin(4 * ph)
    breath = bp(noise(sec, seed + 1), 600, 2600) * 0.08
    amp = np.interp(t / sec, [0, 0.12, 0.7, 1.0], [0, 1, 0.8, 0])
    x = (voiced + breath) * amp
    x = bp(x, 250, 1800) if far else bp(x, 180, 4000)
    if far:  # a soft valley echo
        x = mix(x, at(lp(x, 900) * 0.35, 0.42, sec + 0.5))
    return finish(pad(x, sec + 0.6), 0.6 if far else 0.85, 1.0, 0.2)


def growl(sec, seed):
    t = t_axis(sec)
    rumble = lp(noise(sec, seed), 260) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * t) ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(82 + 9 * np.sin(2 * np.pi * 0.8 * t)) / SR) * 0.35
    amp = np.interp(t / sec, [0, 0.2, 0.8, 1.0], [0, 1, 0.9, 0])
    return finish((rumble * 1.4 + tone) * amp, 0.75, 1.6, 0.15)


def rustle(sec, seed, n=14):
    out = np.zeros(int(SR * sec))
    rng = np.random.default_rng(seed)
    for i in range(n):
        g = cloth(seed + i * 3, rng.uniform(0.08, 0.22), rng.uniform(0.3, 0.8))
        out += at(hp(g, 900), rng.uniform(0, sec - 0.25), sec)
    return finish(out, 0.6, 1.2, 0.08)


def branch_snap(seed):
    crack = mech(seed, 0.5, [(0.0, 1.0, 1500, 9000, 160), (0.012, 0.8, 700, 5000, 90), (0.05, 0.4, 2000, 8000, 200)])
    return finish(mix(crack, at(lp(noise(0.3, seed + 5), 700) * env(t_axis(0.3), 0.004, 14) * 0.4, 0.02, 0.5)), 0.85)


def sign_tap(seed, n=3):
    """A loose metal sign knocking against its post in the wind."""
    sec = 0.35 * n + 0.6
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * sec))
    for i in range(n):
        t = t_axis(0.5)
        f = rng.uniform(780, 920)
        ring = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t)) * env(t, 0.001, 22)
        knock = bp(noise(0.5, seed + i), 300, 2500) * env(t, 0.001, 70)
        out += at((ring * 0.5 + knock) * rng.uniform(0.6, 1.0), i * 0.35 + rng.uniform(0, 0.08), sec)
    return finish(out, 0.75, 1.2, 0.05)


def vent_growl(sec=3.2, seed=1210):
    """A ventilation fan spinning up through a rattling duct: reads as the building growling."""
    t = t_axis(sec)
    spin = np.interp(t / sec, [0, 0.5, 1.0], [18, 34, 30])
    blade = np.sin(2 * np.pi * np.cumsum(spin * 7) / SR)
    rattle = bp(noise(sec, seed), 120, 700) * (0.5 + 0.5 * np.sign(blade))
    rum = lp(noise(sec, seed + 1), 160) * 1.5
    amp = np.interp(t / sec, [0, 0.35, 0.85, 1.0], [0, 1, 1, 0])
    return finish((rattle + rum + 0.3 * blade) * amp, 0.8, 1.8, 0.2)


def pa_chime_cut(seed=1220):
    """Three-note announcement chime that dies on the third note (power fails mid-chime)."""
    c = mix(at(tick(660, 0.5, 0.6), 0.0, 1.4), at(tick(830, 0.5, 0.6), 0.3, 1.4), at(tick(990, 0.08, 0.6), 0.6, 1.4))
    hiss = bp(noise(1.4, seed), 1500, 6000) * 0.05 * (t_axis(1.4) < 0.68)
    return finish(c + hiss, 0.6, 1.0, 0.02)


def pipe_knock(seed, n=4):
    sec = n * 0.42 + 0.8
    out = np.zeros(int(SR * sec))
    rng = np.random.default_rng(seed)
    for i in range(n):
        t = t_axis(0.8)
        f = rng.uniform(150, 210)
        k = (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * f * 3.1 * t)) * env(t, 0.002, 9)
        out += at(k * rng.uniform(0.6, 1.0), i * rng.uniform(0.32, 0.5), sec)
    return finish(mix(out, at(lp(out, 600) * 0.3, 0.25, sec)), 0.8, 1.3, 0.1)


def pressure_groan(sec=3.5, seed=1240):
    """A heavy pressure door seal flexing: slow metallic moan with creaks."""
    t = t_axis(sec)
    f = 62 + 18 * np.sin(2 * np.pi * 0.25 * t) + 6 * np.sin(2 * np.pi * 1.7 * t)
    moan = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(2 * np.pi * np.cumsum(f * 2.3) / SR)
    creak = bp(noise(sec, seed), 400, 1800) * (np.sin(2 * np.pi * 23 * t) > 0.6) * 0.5
    amp = np.interp(t / sec, [0, 0.25, 0.8, 1.0], [0, 1, 0.8, 0])
    return finish((moan + creak) * amp, 0.8, 1.6, 0.2)


def fan_breath(sec=6.0, seed=1250):
    """Rack cooling fans cycling: slow in-out swells, like breathing."""
    t = t_axis(sec)
    air = bp(noise(sec, seed), 200, 1800)
    swell = 0.25 + 0.75 * (0.5 - 0.5 * np.cos(2 * np.pi * t / 3.0)) ** 1.5
    hum = np.sin(2 * np.pi * 118 * t) * 0.05
    return finish(air * swell + hum, 0.6, 1.0, 0.3)


def tag_tap(seed=1260, n=5):
    sec = n * 0.55 + 0.4
    out = np.zeros(int(SR * sec))
    rng = np.random.default_rng(seed)
    for i in range(n):
        k = hp(noise(0.06, seed + i), 1800) * env(t_axis(0.06), 0.0005, 120)
        out += at(k * rng.uniform(0.5, 1.0), i * 0.55 + rng.uniform(-0.08, 0.08) + 0.08, sec)
    return finish(out, 0.55, 1.0, 0.05)


def speaker_fragment(seed=1270):
    """A dying PA speaker: crackle and a band-limited buzz that drops out."""
    sec = 1.4
    t = t_axis(sec)
    buzz = bp(np.sign(np.sin(2 * np.pi * 100 * t)) + noise(sec, seed) * 0.3, 300, 3200)
    gate = (t < 1.0) * (np.random.default_rng(seed).random(len(t)) > 0.02)
    crack = bp(noise(sec, seed + 1), 2000, 8000) * (np.random.default_rng(seed + 2).random(len(t)) > 0.995) * 3
    return finish(buzz * gate * 0.4 + crack, 0.6, 1.2, 0.05)


# ---- storm night (tools/world/night.py) ------------------------------------------------------

def rain_layer(sec, seed, lo=1200, hi=9000, drops=180.0, drop_lo=2500, drop_hi=7000, g=0.5):
    """Rain on foliage: a dense hiss plus individual drop ticks on leaves (Poisson timed)."""
    hiss = loop_noise(sec, seed, lo, hi)
    t = t_axis(sec)
    hiss *= 0.85 + 0.15 * np.sin(2 * np.pi * t * 3 / sec + 0.4)
    rng = np.random.default_rng(seed + 1)
    out = np.zeros(len(t))
    for tm in np.sort(rng.uniform(0, sec - 0.05, int(drops * sec))):
        f = rng.uniform(drop_lo, drop_hi)
        d = rng.uniform(0.006, 0.02)
        tt = t_axis(d)
        ch = np.sin(2 * np.pi * f * tt) * np.exp(-tt * rng.uniform(160, 420)) * rng.uniform(0.15, 1.0)
        out += at(ch, tm, sec)
    return hiss * g + out * 0.18


def night_forest_bed(sec=24.0, seed=1900):
    """Storm night in the forest: rain through the canopy, heavy drips, wind in the crowns.
    No birdsong (it is 03:00 in a storm)."""
    rain = rain_layer(sec, seed)
    wind = wind_bed(sec, seed + 5, 60, 600, 0.22) * 0.55
    drips = np.zeros(int(SR * sec))
    rng = np.random.default_rng(seed + 9)
    for tm in rng.uniform(0.2, sec - 0.4, int(sec * 3)):
        f = rng.uniform(500, 1400)
        tt = t_axis(0.09)
        drips += at(np.sin(2 * np.pi * f * tt * (1 + tt * 3)) * np.exp(-tt * 55) * rng.uniform(0.1, 0.35), tm, sec)
    x = rain + wind + lp(drips, 3000)
    return loopify(x / np.max(np.abs(x)) * 0.62)


def night_camp_bed(sec=16.0, seed=1980):
    """Staging camp in the rain: generator, rain drumming on tent fabric and crates."""
    gen = engine_idle(2.0, 25.0, seed)
    gen = lp(np.tile(gen, int(sec / 2)), 700)[:int(SR * sec)] * 0.28
    tarp = rain_layer(sec, seed + 3, 300, 3500, drops=260.0, drop_lo=380, drop_hi=1500, g=0.35)
    x = rain_layer(sec, seed + 4) * 0.8 + tarp + gen
    return loopify(x / np.max(np.abs(x)) * 0.58)


def roof_rain_bed(sec=12.0, seed=2040):
    """Heard from inside a concrete building: low muffled roar and gutter run-off."""
    roar = loop_noise(sec, seed, 60, 900) * 0.8
    gutter = loop_noise(sec, seed + 1, 300, 1800)
    t = t_axis(sec)
    gutter *= 0.4 + 0.25 * np.sin(2 * np.pi * t * 4 / sec) ** 2
    x = lp(roar + gutter * 0.4, 1400)
    return loopify(x / np.max(np.abs(x)) * 0.5)


def thunder(seed, sec=7.0, near=0.5):
    """Thunder: a crack (near strikes) into a long rolling rumble with random swells."""
    t = t_axis(sec)
    rng = np.random.default_rng(seed)
    rumble = lp(noise(sec, seed), 140, 3) * 3.0
    sw = np.zeros(len(t))
    for _ in range(rng.integers(4, 8)):
        c = rng.uniform(0.2, sec * 0.7)
        w = rng.uniform(0.3, 1.2)
        sw += rng.uniform(0.4, 1.0) * np.exp(-((t - c) / w) ** 2)
    shape = (sw + 0.2) * np.clip(t / 0.15, 0, 1) * np.exp(-t * 0.35)
    crack = bp(noise(0.5, seed + 1), 400, 4000) * env(t_axis(0.5), 0.004, 9.0) * near
    x = rumble * shape + at(crack, 0.0, sec)
    return finish(x, 0.85, 1.2, 0.5)


def torch_click(seed=2100):
    return finish(mix(tick(2600, 0.03, 0.8), at(tick(1700, 0.04, 0.5), 0.035, 0.1)), 0.6, 1.0)


def build(out):
    w = os.path.join(out, 'audio')
    files = {
        'weapons/pc7_fire.wav': pulse_shot(10, 2400, 220, 85, 0.5, 6000, 9),
        'weapons/sp2_fire.wav': pulse_shot(20, 3200, 380, 120, 0.35, 7500, 13),
        'weapons/dry.wav': dry_click(30),
        'weapons/pc7_cell_out.wav': mech(40, 0.45, [(0.0, 1.0, 900, 5000, 90), (0.05, 0.6, 400, 2500, 60), (0.22, 0.4, 600, 3000, 120)]),
        'weapons/pc7_cell_in.wav': mech(50, 0.4, [(0.0, 0.5, 600, 3000, 120), (0.12, 1.0, 800, 6000, 140), (0.15, 0.7, 300, 1500, 70)]),
        'weapons/pc7_charge.wav': rising_whine(0.42, 420, 1650, 55),
        'weapons/sp2_cell_out.wav': mech(60, 0.3, [(0.0, 0.9, 1200, 6000, 120), (0.08, 0.4, 500, 3000, 90)]),
        'weapons/sp2_cell_in.wav': mech(70, 0.3, [(0.0, 1.0, 1000, 7000, 150), (0.04, 0.5, 400, 2000, 80)]),
        'weapons/sp2_charge.wav': rising_whine(0.3, 600, 2100, 75),
        'weapons/equip.wav': mech(80, 0.45, [(0.0, 0.4, 300, 2000, 30), (0.2, 0.9, 900, 5000, 110), (0.26, 0.5, 1500, 6000, 150)]),
        'weapons/aim.wav': cloth(90, 0.18, 0.35),
        'weapons/impact_soft.wav': impact(100, 150, 2000, 40, 60),
        'weapons/impact_hard.wav': impact(110, 900, 8000, 55, 140),
        'weapons/impact_dirt_0.wav': impact_dirt(2000),
        'weapons/impact_dirt_1.wav': impact_dirt(2010),
        'weapons/impact_wood_0.wav': impact_wood(2020),
        'weapons/impact_wood_1.wav': impact_wood(2030),
        'weapons/impact_stone_0.wav': impact_stone(2040),
        'weapons/impact_stone_1.wav': impact_stone(2050),
        'weapons/impact_metal_0.wav': impact_metal(2060),
        'weapons/impact_metal_1.wav': impact_metal(2070),
        'weapons/target_down.wav': power_down(0.7, 120),
        'weapons/target_up.wav': mech(130, 0.5, [(0.0, 0.6, 300, 2500, 25), (0.32, 1.0, 600, 4000, 60)], tone=(300, 700, 0.0, 0.3, 0.2)),
        'ui/hit_tick.wav': tick(2600, 0.06, 0.6),
        'ui/ok.wav': tick(1400, 0.12, 0.5),
        'ui/objective.wav': finish(mix(at(tick(880, 0.4), 0.0, 0.6), at(tick(1320, 0.4), 0.09, 0.6)), 0.55, 1.0),
        'foley/scan.wav': scan_ping(),
        'foley/cloth_a.wav': cloth(140, 0.3, 0.4),
        'foley/land.wav': finish(mix(lp(noise(0.3, 150), 900) * env(t_axis(0.3), 0.003, 18),
                                     np.sin(2 * np.pi * 60 * t_axis(0.3)) * env(t_axis(0.3), 0.004, 25)), 0.7),
    }
    files.update({
        'weapons/lr4_fire.wav': pulse_shot(25, 1700, 130, 62, 0.85, 4500, 5),
        'weapons/lr4_cell_out.wav': mech(42, 0.5, [(0.0, 1.0, 700, 4500, 80), (0.06, 0.7, 350, 2200, 55), (0.26, 0.45, 500, 2600, 110)]),
        'weapons/lr4_cell_in.wav': mech(52, 0.45, [(0.0, 0.5, 500, 2600, 110), (0.14, 1.0, 700, 5000, 130), (0.18, 0.8, 250, 1300, 60)]),
        'weapons/lr4_charge.wav': rising_whine(0.6, 260, 1200, 57),
        # Halyard kit additions: snappy PDW, heavy breacher fan with a pump stroke, crisp DMR.
        'weapons/kv5_fire.wav': pulse_shot(27, 3000, 300, 105, 0.38, 7000, 14),
        'weapons/br9_fire.wav': finish(mix(pulse_shot(28, 1300, 90, 48, 0.9, 3800, 4),
                                           lp(noise(0.9, 281), 1400) * env(t_axis(0.9), 0.001, 7) * 0.9,
                                           np.sin(2 * np.pi * 38 * t_axis(0.9)) * env(t_axis(0.9), 0.003, 9) * 0.7)),
        'weapons/br9_pump.wav': mech(282, 0.42, [(0.0, 0.9, 500, 3500, 70), (0.03, 0.5, 250, 1500, 40),
                                                 (0.2, 1.0, 600, 4500, 90), (0.23, 0.6, 300, 1800, 50)]),
        'weapons/mr6_fire.wav': pulse_shot(29, 2100, 170, 72, 0.7, 5200, 7),
        'weapons/lr4_zoom.wav': mech(58, 0.18, [(0.0, 0.8, 1800, 7000, 220), (0.05, 0.5, 1200, 5000, 200)]),
        'weapons/kit_use.wav': finish(mix(at(bp(noise(0.35, 700), 1500, 7000) * np.sin(np.pi * np.clip(t_axis(0.35) / 0.35, 0, 1)) * 0.6, 0.0, 1.5),
                                          at(cloth(701, 0.4, 0.5), 0.4, 1.5), at(tick(1100, 0.2, 0.4), 1.2, 1.5)), 0.7, 1.0),
        'vehicle/engine_idle.wav': engine_idle(),
        'vehicle/engine_start.wav': engine_start(),
        'vehicle/engine_stop.wav': engine_stop(),
        'vehicle/door_open.wav': door(560, True),
        'vehicle/door_close.wav': door(570, False),
        'vehicle/hatch_open.wav': hatch(580, True),
        'vehicle/hatch_close.wav': hatch(590, False),
        'vehicle/tyre_roll.wav': tyre_roll(),
        'foley/item_pick.wav': handle(610, 0.35, 0.3),
        'foley/item_place.wav': handle(620, 0.4, 0.8),
    })
    files.update({
        'foley/cell_out.wav': heavy_cell_out(700),
        'foley/gate_motor.wav': motor_run(6.2, 710),
        'foley/lift_motor.wav': motor_run(9.0, 715, hz=38.0),
        'foley/card_accept.wav': beep_seq((1200, 1600, 2100)),
        'foley/card_deny.wav': beep_seq((420, 360), gap=0.18, sec=0.16),
        'foley/panel_keys.wav': keys(720),
        'foley/pickup.wav': handle(725, 0.3, 0.25),
        'foley/breaker.wav': mech(730, 0.6, [(0.0, 1.0, 300, 3000, 40), (0.05, 0.7, 1500, 7000, 120)]),
        'foley/crank.wav': mech(735, 1.2, [(i * 0.15, 0.7, 500, 3500, 70) for i in range(8)]),
        'foley/blast_door.wav': motor_run(7.0, 740, hz=28.0),
        'foley/door_slide.wav': motor_run(1.6, 745, hz=70.0, clunk=False),
        # storm night: the valley beds are rain, not birdsong (the day versions stay for the menu)
        'ambient/forest_day.wav': forest_bed(),
        'ambient/forest.wav': night_forest_bed(),
        'ambient/roof_rain.wav': roof_rain_bed(),
        'ambient/thunder_0.wav': thunder(2001, 7.5, 0.9),
        'ambient/thunder_1.wav': thunder(2002, 6.0, 0.3),
        'ambient/thunder_2.wav': thunder(2003, 8.5, 0.0),
        'foley/torch_click.wav': torch_click(),
        'ambient/creek.wav': creek_bed(),
        'ambient/camp_day.wav': camp_bed(),
        'ambient/camp.wav': night_camp_bed(),
        'ambient/interior.wav': hum_bed(),
        'ambient/bunker.wav': bunker_bed(),
        'ambient/basement.wav': hum_bed(10.0, 950, 60.0, 0.9),
    })
    files.update({
        'scare/howl_far.wav': howl(3.4, 1200),
        'scare/howl_answer.wav': howl(2.8, 1201, 380.0, 560.0),
        'scare/growl.wav': growl(2.4, 1202),
        'scare/rustle.wav': rustle(2.2, 1203),
        'scare/branch_snap.wav': branch_snap(1204),
        'scare/sign_tap_0.wav': sign_tap(1205, 3),
        'scare/sign_tap_1.wav': sign_tap(1206, 2),
        'scare/sign_tap_2.wav': sign_tap(1207, 4),
        'scare/vent_growl.wav': vent_growl(),
        'scare/pa_chime_cut.wav': pa_chime_cut(),
        'scare/pipe_knock.wav': pipe_knock(1230),
        'scare/pressure_groan.wav': pressure_groan(),
        'scare/fan_breath.wav': fan_breath(),
        'scare/tag_tap.wav': tag_tap(),
        'scare/speaker_fragment.wav': speaker_fragment(),
    })
    for i in range(4):
        files[f'foley/step_dirt_{i}.wav'] = footstep(200 + i, 'dirt')
        files[f'foley/step_concrete_{i}.wav'] = footstep(300 + i, 'concrete')
        files[f'foley/step_metal_{i}.wav'] = footstep(400 + i, 'metal')
        files[f'foley/step_gravel_{i}.wav'] = footstep(500 + i, 'gravel')
        files[f'foley/step_grass_{i}.wav'] = footstep(600 + i, 'grass')
        files[f'foley/step_mud_{i}.wav'] = footstep(700 + i, 'mud')
        files[f'foley/step_wood_{i}.wav'] = footstep(800 + i, 'wood')
        files[f'foley/step_splash_{i}.wav'] = footstep(900 + i, 'splash')
    for i in range(3):
        files[f'foley/gear_{i}.wav'] = gear_rattle(1000 + i)
    files['foley/land_soft.wav'] = land(1100, False)
    files['foley/land_hard.wav'] = land(1110, True)
    for rel, x in sorted(files.items()):
        write(os.path.join(w, rel), x)
        print(f"{rel:28s} {len(x) / SR:5.2f}s")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
    build(ap.parse_args().out)
