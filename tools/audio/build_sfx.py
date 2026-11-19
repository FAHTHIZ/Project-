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
    else:  # metal grating
        x = bp(noise(sec, seed), 500, 6000) * env(t, 0.001, 40)
        for k, f in enumerate((410, 655, 1230)):
            x += np.sin(2 * np.pi * f * r.uniform(0.97, 1.03) * t) * env(t, 0.001, 20 + 8 * k) * 0.18
    return finish(x, 0.55 + r.uniform(-0.05, 0.05), 1.2)


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
        'ambient/forest.wav': forest_bed(),
        'ambient/creek.wav': creek_bed(),
        'ambient/camp.wav': camp_bed(),
        'ambient/interior.wav': hum_bed(),
        'ambient/bunker.wav': bunker_bed(),
        'ambient/basement.wav': hum_bed(10.0, 950, 60.0, 0.9),
    })
    for i in range(4):
        files[f'foley/step_dirt_{i}.wav'] = footstep(200 + i, 'dirt')
        files[f'foley/step_concrete_{i}.wav'] = footstep(300 + i, 'concrete')
        files[f'foley/step_metal_{i}.wav'] = footstep(400 + i, 'metal')
    for rel, x in sorted(files.items()):
        write(os.path.join(w, rel), x)
        print(f"{rel:28s} {len(x) / SR:5.2f}s")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True)
    build(ap.parse_args().out)
