# SPDX-License-Identifier: Apache-2.0
"""Photoscanned terrain layers for the Kestrel Valley (replaces the procedural noise textures).

    python3 tools/assets/build_photoreal_terrain.py [--size 1024]

Sources are CC0 Poly Haven scans (fetched to .cache/ by polyhaven.py). Each layer is packed into
one RGBA texture the VICTUS terrain shader reads (ADR-0121):
    RGB  albedo with the scan's ambient occlusion multiplied in (soft, so crevices stay readable)
    A    height (displacement), stretched to the full 0..1 range
The texture keeps its existing path and .meta UUID, so every scene that references it is
unchanged; the .meta gains mobile texture compression (BC7 on desktop, ASTC 6x6 on phones).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import polyhaven as ph  # noqa: E402

ROOT = ph.ROOT
TEX = os.path.join(ROOT, 'game', 'assets', 'textures', 'terrain')

# layer file -> (Poly Haven id, albedo gain, saturation, AO strength)
# Gains keep albedo in a physically plausible range (forest litter ~0.08-0.15 linear) and nudge
# the palette toward the Stage 01 reference footage: deep wet greens and dark brown earth.
LAYERS = {
    'forest': ('brown_mud_leaves_01', 0.92, 1.00, 0.7),
    'rock': ('mossy_rock', 0.85, 0.95, 0.8),
    'path': ('mud_forest', 2.2, 0.95, 0.6),
    'meadow': ('forrest_ground_01', 0.85, 1.05, 0.7),
}


def load(path: str, size: int, mode: str = 'RGB') -> np.ndarray:
    im = Image.open(path)
    if im.mode in ('I;16', 'I;16B', 'I'):
        a = np.asarray(im, dtype=np.float32)
        a = a / (65535.0 if a.max() > 255 else 255.0)
        im = Image.fromarray((a * 65535).astype(np.uint16))
        im = im.resize((size, size), Image.LANCZOS) if im.size[0] != size else im
        return np.asarray(im, dtype=np.float32) / 65535.0
    im = im.convert(mode)
    if im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im, dtype=np.float32) / 255.0


def to_linear(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def build_layer(name: str, size: int) -> dict:
    asset, gain, sat, ao_k = LAYERS[name]
    src = ph.texture(asset, '2k', 'png', maps=('diff', 'disp', 'ao'))
    diff = to_linear(load(src['diff'], size))
    ao = load(src['ao'], size, 'L') if 'ao' in src else np.ones((size, size), np.float32)
    h = load(src['disp'], size, 'L') if 'disp' in src else np.ones((size, size), np.float32)
    if h.ndim == 3:
        h = h[..., 0]
    lum = (diff @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    diff = lum + (diff - lum) * sat
    diff *= gain * (1.0 - ao_k + ao_k * ao)[..., None]
    lo, hi = np.percentile(h, 0.5), np.percentile(h, 99.5)
    h = np.clip((h - lo) / max(hi - lo, 1e-4), 0, 1)
    rgba = np.dstack([to_srgb(diff), h])
    out = os.path.join(TEX, f'{name}.png')
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').save(out, optimize=True)
    meta_path = out + '.meta'
    meta = json.load(open(meta_path))
    meta['settings'].update({'srgb': True, 'mipmaps': True, 'max_size': size, 'compression': 'bc7+astc6x6'})
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
        f.write('\n')
    return {'file': os.path.relpath(out, ROOT), 'source': f'https://polyhaven.com/a/{asset}', 'linear_mean': float(diff.mean())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--size', type=int, default=1024)
    a = ap.parse_args()
    for name in LAYERS:
        print(json.dumps(build_layer(name, a.size)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
