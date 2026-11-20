#!/usr/bin/env python3
"""Outdoor ambience from real field recordings (Freesound, CC0) instead of synthesis.

build_sfx.py used to generate the storm beds from filtered noise. These are recorded rain,
water, thunder and birds. Each source is downloaded once (Freesound's public HQ preview) into
.cache/field/, cut to the listed window, made mono 44.1 kHz, shaped (filter, gain) and either
crossfade-looped (beds) or faded (one-shots), then written to the same game paths, so the .meta
UUIDs and every scene reference stay as they are.

Level: a bed gets the RMS the synthetic file had (the mix in the scenes was balanced for that,
LEVEL below), with a look-ahead limiter on close drops; a thunder one-shot gets the old peak. Run from the repo root:  python3 tools/audio/build_field_ambience.py
"""
import os
import subprocess
import sys
import wave

import numpy as np
from scipy.signal import butter, sosfiltfilt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, '.cache', 'field')
AMB = os.path.join(ROOT, 'game', 'assets', 'audio', 'ambient')
SR = 44100
UA = 'Mozilla/5.0'

# id: (author, preview url, title) - all Creative Commons 0 (checked on each sound page)
SOURCES = {
    383064: ('AlanCat', 'https://cdn.freesound.org/previews/383/383064_5486695-hq.mp3', 'ForestRainShower1a'),
    630424: ('KaleidacousticsAudio', 'https://cdn.freesound.org/previews/630/630424_13875907-hq.mp3', 'Heavy Rain'),
    784160: ('thadzo', 'https://cdn.freesound.org/previews/784/784160_14911928-hq.mp3', 'Rain_on_plastic_tarp'),
    477554: ('fionablau', 'https://cdn.freesound.org/previews/477/477554_4046112-hq.mp3', 'Stream in a Beech Forest'),
    661914: ('sertuser', 'https://cdn.freesound.org/previews/661/661914_14502819-hq.mp3', '5AM Forest Dawn Chorus'),
    522025: ('Nimlos', 'https://cdn.freesound.org/previews/522/522025_4710044-hq.mp3', 'THREE MIGHTY THUNDERS IN ROW'),
}

# RMS (beds) / peak (thunder) of the synthetic files these replace (build_sfx.py at 4bc226b)
LEVEL = {'forest.wav': 0.114, 'camp.wav': 0.119, 'roof_rain.wav': 0.112, 'creek.wav': 0.110,
         'forest_day.wav': 0.092, 'thunder_0.wav': 0.85, 'thunder_1.wav': 0.85, 'thunder_2.wav': 0.85}

# out file: (source id, start s, length s, kind, highpass Hz, lowpass Hz, mix [(id, start, gain)])
CUTS = {
    'forest.wav':    (383064, 209.0, 23.4, 'bed', 40, None, []),
    'camp.wav':      (784160, 9.0, 15.4, 'bed', 60, None, [(383064, 150.0, 1.5)]),
    'roof_rain.wav': (630424, 10.0, 11.4, 'bed', 30, 1300, []),     # through a concrete slab
    'creek.wav':     (477554, 32.0, 12.0, 'bed', 50, None, []),
    'forest_day.wav': (661914, 90.0, 23.4, 'bed', 60, None, []),
    'thunder_0.wav': (522025, 27.6, 7.5, 'shot', 25, None, []),     # near strike
    'thunder_1.wav': (522025, 95.0, 6.0, 'shot', 25, 4000, []),
    'thunder_2.wav': (522025, 126.6, 8.5, 'shot', 25, 1800, []),    # far roll
}


def fetch(sid):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'{sid}.mp3')
    if not os.path.exists(path):
        # the first 4 MB (about four minutes) is all any cut needs
        subprocess.run(['curl', '-sfL', '-A', UA, '-r', '0-4000000', '-o', path, SOURCES[sid][1]], check=True)
    return path


def load(sid, start, length):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{start}', '-t', f'{length}', '-i', fetch(sid),
                          '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float64) / 32768
    assert len(x) >= int(SR * length) - 2, (sid, start, len(x) / SR)
    return x


def read_wav(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64) / 32768


def write_wav(path, x):
    d = (np.clip(x, -1, 1) * 32767).round().astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())


def filt(x, hp, lp):
    if hp:
        x = sosfiltfilt(butter(2, hp, 'highpass', fs=SR, output='sos'), x)
    if lp:
        x = sosfiltfilt(butter(4, lp, 'lowpass', fs=SR, output='sos'), x)
    return x


def loop(x, n, xf):
    """n samples that loop seamlessly: the tail past n is crossfaded (equal power) into the head."""
    y = x[:n].copy()
    a = np.linspace(0, np.pi / 2, xf)
    y[:xf] = x[:xf] * np.sin(a) + x[n:n + xf] * np.cos(a)
    return y


def limit(x, ceiling=0.7, attack=0.002, release=0.06):
    """Peak limiter (look-ahead = attack): close raindrops are far louder than the bed, so the
    bed would sit too low if it were only scaled. Gain dips for a few ms around each drop."""
    a = np.abs(x)
    la = int(SR * attack)
    ahead = np.maximum.reduce([np.roll(a, -k) for k in range(0, la + 1, max(1, la // 8))])
    need = np.minimum(1.0, ceiling / np.maximum(ahead, 1e-9))
    g = np.empty_like(need)
    rel = np.exp(-1.0 / (SR * release))
    cur = 1.0
    for i, v in enumerate(need):  # instant attack, exponential release
        cur = v if v < cur else v + (cur - v) * rel
        g[i] = cur
    return x * g


def rms(x):
    return float(np.sqrt(np.mean(x ** 2)))


def build(name):
    sid, start, length, kind, hp, lp, mix = CUTS[name]
    n = int(round(SR * length))
    xf = int(SR * 1.5) if kind == 'bed' else 0
    x = load(sid, start, length + xf / SR + 0.05)
    for mid, mstart, g in mix:
        x = x + g * load(mid, mstart, length + xf / SR + 0.05)[:len(x)]
    x = filt(x - x.mean(), hp, lp)
    if kind == 'bed':
        target = LEVEL[name]
        x = limit(x * target / rms(x))
        x *= target / rms(x)
        x = limit(x, 0.85)
        y = loop(x, n, xf)
    else:
        y = x[:n].copy()
        fi, fo = int(SR * 0.12), int(SR * 2.0)
        y[:fi] *= np.linspace(0, 1, fi)
        y[-fo:] *= np.linspace(1, 0, fo) ** 2
        target = LEVEL[name]
        y *= target / np.max(np.abs(y))
    peak = np.max(np.abs(y))
    if peak > 0.97:
        y *= 0.97 / peak
    return y


def main(names):
    for name in names or CUTS:
        y = build(name)
        write_wav(os.path.join(AMB, name), y)
        print(f'{name:15s} {len(y) / SR:5.1f} s  rms {rms(y):.3f} peak {np.max(np.abs(y)):.2f}  (target {LEVEL[name]})')


if __name__ == '__main__':
    main(sys.argv[1:])
