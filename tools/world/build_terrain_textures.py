# SPDX-License-Identifier: Apache-2.0
"""Tileable terrain layer textures for the Kestrel Valley world (all procedural, original).

    python3 tools/world/build_terrain_textures.py --out game/assets

Writes <out>/textures/terrain/{forest,rock,path,meadow}.png (1024 px, seamless). The VICTUS
terrain shader blends four base-colour layers by the splat map and has no per-layer normal map,
so each texture carries its own baked micro-shading (contact shadow under leaves and pebbles,
dark crack lines in rock) to read as relief under the sun.

Scale (set by the Terrain tiling in tools/world/worldgen.py): forest and meadow tile every 4 m,
rock every 6 m, path every 3 m.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'props'))
from build_forest import periodic_noise  # noqa: E402

N = 1024


def srgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def wrap_draw(n, fn):
    """Calls fn(dx, dy) for the 9 tile offsets so shapes crossing an edge wrap around."""
    for dy in (-n, 0, n):
        for dx in (-n, 0, n):
            fn(dx, dy)


def base_field(seed, c0, c1, beta=2.0, mix=1.0):
    t = periodic_noise(N, seed, beta)
    t = (t - t.mean()) * mix + 0.5
    t = np.clip(t, 0, 1)[..., None]
    return srgb(c0)[None, None] * (1 - t) + srgb(c1)[None, None] * t


def overlay_shapes(img, shapes, blur_shadow=3, shadow_offset=(3, 4), shadow_alpha=110):
    """shapes: list of (polygon points, rgb). Draws a soft contact shadow, then the shapes."""
    sh = Image.new('L', (N, N), 0)
    ds = ImageDraw.Draw(sh)
    for pts, _ in shapes:
        def f(dx, dy, pts=pts):
            ds.polygon([(x + dx + shadow_offset[0], y + dy + shadow_offset[1]) for x, y in pts], fill=shadow_alpha)
        wrap_draw(N, f)
    sh = sh.filter(ImageFilter.GaussianBlur(blur_shadow))
    a = np.asarray(img, float)
    a *= (1 - np.asarray(sh, float)[..., None] / 255 * 0.75)
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for pts, col in shapes:
        def g(dx, dy, pts=pts, col=col):
            d.polygon([(x + dx, y + dy) for x, y in pts], fill=tuple(int(v) for v in col))
        wrap_draw(N, g)
    return img


def leaf_poly(cx, cy, length, width, ang, lobes=0):
    pts = []
    for i in range(16):
        t = i / 15
        w = math.sin(math.pi * t) ** 0.8 * width * (1 + 0.15 * math.sin(t * math.pi * lobes * 2) if lobes else 1)
        pts.append((t * length - length / 2, w))
    for i in range(15, -1, -1):
        t = i / 15
        w = math.sin(math.pi * t) ** 0.8 * width
        pts.append((t * length - length / 2, -w * 0.9))
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


def tex_forest(seed=101):
    """Forest floor: humus with fallen broadleaf leaves, conifer needles and twigs."""
    rng = np.random.default_rng(seed)
    a = base_field(seed, '#2a2016', '#4a3a26', 1.6, 1.4)
    img = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(img)
    # needles (thin dark/rust strokes)
    for _ in range(5200):
        x, y = rng.uniform(0, N, 2)
        ang = rng.uniform(0, math.pi)
        L = rng.uniform(10, 22)
        col = tuple(int(v) for v in srgb(rng.choice(['#6b4a2a', '#5a3d22', '#7a5530', '#3e2c1a'])) * rng.uniform(0.8, 1.1))
        def f(dx, dy, x=x, y=y, ang=ang, L=L, col=col):
            d.line([(x + dx, y + dy), (x + dx + math.cos(ang) * L, y + dy + math.sin(ang) * L)], fill=col, width=1)
        wrap_draw(N, f)
    # twigs
    for _ in range(90):
        x, y = rng.uniform(0, N, 2)
        ang = rng.uniform(0, math.pi * 2)
        L = rng.uniform(30, 90)
        col = tuple(int(v) for v in srgb('#3b2a1b') * rng.uniform(0.8, 1.2))
        def g(dx, dy, x=x, y=y, ang=ang, L=L, col=col):
            d.line([(x + dx, y + dy), (x + dx + math.cos(ang) * L, y + dy + math.sin(ang) * L)], fill=col, width=3)
        wrap_draw(N, g)
    # fallen leaves (several layers so they overlap)
    pal = ['#7a5a2e', '#8c6a34', '#6a4a26', '#5d5a2c', '#9a7a3e', '#4f3f22', '#6e6230']
    for layer in range(3):
        shapes = []
        for _ in range(520):
            x, y = rng.uniform(0, N, 2)
            L = rng.uniform(22, 46)
            col = srgb(rng.choice(pal)) * rng.uniform(0.7, 1.05) * (0.8 + 0.1 * layer)
            shapes.append((leaf_poly(x, y, L, L * rng.uniform(0.28, 0.42), rng.uniform(0, math.pi * 2)), col))
        img = overlay_shapes(img, shapes, blur_shadow=2, shadow_offset=(2, 3), shadow_alpha=120)
    # moss patches
    m = periodic_noise(N, seed + 7, 2.4)
    mask = np.clip((m - 0.68) * 6, 0, 1)[..., None] * 0.4
    moss = base_field(seed + 8, '#2f3d1c', '#4c5a26', 1.0)
    a = np.asarray(img, float) * (1 - mask) + moss * mask
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def voronoi_edges(n, cells, seed):
    rng = np.random.default_rng(seed)
    pts = rng.uniform(0, n, (cells, 2))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d1 = np.full((n, n), 1e9, np.float32)
    d2 = np.full((n, n), 1e9, np.float32)
    for px, py in pts:
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                dd = (xx - px - ox) ** 2 + (yy - py - oy) ** 2
                m = dd < d1
                d2 = np.where(m, d1, np.minimum(d2, dd))
                d1 = np.where(m, dd, d1)
    return np.sqrt(d2) - np.sqrt(d1)


def tex_rock(seed=202):
    """Weathered granite/gneiss face: two joint sets, bedding strata, ridged relief, lichen.

    Real outcrops break along a few roughly parallel joint sets rather than into polygon cells,
    so fractures are thin warped line families on integer frequency vectors (which keeps the tile
    seamless), broken into discontinuous segments, over ridged noise relief with banded strata.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    a = base_field(seed, '#66625b', '#9a958b', 1.6, 1.1)
    warp = periodic_noise(N, seed + 9, 1.5) - 0.5

    def joints(kx, ky, sharp, seed_off, strength):
        ph = 2 * np.pi * (kx * xx + ky * yy) + 5.0 * warp + 2.5 * (periodic_noise(N, seed + seed_off, 2.2) - 0.5)
        line = (1 - np.abs(np.sin(ph))) ** (1.0 / sharp)   # 1 on the fracture, thin
        gate = np.clip((periodic_noise(N, seed + seed_off + 1, 1.8) - 0.38) * 3.0, 0, 1)
        return line * gate * strength

    crack = joints(3, 7, 0.14, 20, 0.85) + joints(-6, 2, 0.11, 22, 0.7) + joints(11, -5, 0.06, 24, 0.35)
    crack = np.clip(crack, 0, 1)
    # bedding strata: soft bands with varying hardness
    strata = 0.5 + 0.5 * np.sin(2 * np.pi * (1 * xx + 9 * yy) + 4 * warp + 3 * periodic_noise(N, seed + 11, 2.4))
    ridge = 1 - np.abs(periodic_noise(N, seed + 3, 1.3) - 0.5) * 2
    relief = 0.7 + 0.45 * ridge ** 1.6 + 0.12 * (periodic_noise(N, seed + 4, 2.6) - 0.5)
    shade = relief * (0.88 + 0.16 * strata) * (1 - 0.6 * crack)
    # light catches the upper lip of each fracture (baked relief: the shader has no normal map)
    lip = np.roll(crack, 2, axis=0)
    shade *= 1 + 0.18 * np.clip(lip - crack, 0, 1)
    a = a * shade[..., None]
    sp = rng.random((N, N))
    a[sp > 0.988] *= 1.3
    a[sp < 0.008] *= 0.6
    # lichen and stain streaks running down the face
    lich = periodic_noise(N, seed + 5, 2.0)
    lm = np.clip((lich - 0.68) * 4, 0, 1)[..., None] * 0.4
    lc = base_field(seed + 6, '#6f7456', '#9b9a76', 0.8)
    a = a * (1 - lm) + lc * lm
    streak = np.clip(periodic_noise(N, seed + 7, 2.8) - 0.55, 0, 1)
    streak = np.asarray(Image.fromarray((streak * 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1)), float) / 255
    a *= (1 - 0.35 * streak)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.SMOOTH)


def pebble_poly(cx, cy, r, rng):
    k = 10
    pts = []
    for i in range(k):
        ang = i / k * math.pi * 2
        rr = r * rng.uniform(0.75, 1.15)
        pts.append((cx + math.cos(ang) * rr * 1.25, cy + math.sin(ang) * rr))
    return pts


def tex_path(seed=303):
    """Packed dirt and gravel of a ranger road / footpath: wheel-worn, pebbles pressed in."""
    rng = np.random.default_rng(seed)
    a = base_field(seed, '#5a4632', '#7d664a', 1.5, 1.2)
    img = Image.fromarray(a.astype(np.uint8))
    pal = ['#8b8478', '#6f6a62', '#a39a8a', '#5e574d', '#7a6c5a', '#958870']
    for layer, (count, rmin, rmax) in enumerate([(2400, 2, 5), (700, 5, 10), (90, 10, 18)]):
        shapes = []
        for _ in range(count):
            x, y = rng.uniform(0, N, 2)
            col = srgb(rng.choice(pal)) * rng.uniform(0.8, 1.1)
            shapes.append((pebble_poly(x, y, rng.uniform(rmin, rmax), rng), col))
        img = overlay_shapes(img, shapes, blur_shadow=1.5, shadow_offset=(1, 2), shadow_alpha=150)
    a = np.asarray(img, float)
    # pebble highlights: lighten the top-left of every bright blob slightly via an emboss
    emb = np.asarray(img.convert('L').filter(ImageFilter.EMBOSS), float) - 128
    a += emb[..., None] * 0.25
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def tex_meadow(seed=404):
    """Upland meadow: dense mixed grass blades with dry stems and clover."""
    rng = np.random.default_rng(seed)
    a = base_field(seed, '#2e3a18', '#4d5a24', 1.4, 1.2)
    img = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(img)
    pal = ['#5f7a2c', '#6d8a34', '#4c6a24', '#829a40', '#9a9a52', '#7a7a3c', '#3e5a1e']
    for _ in range(26000):
        x, y = rng.uniform(0, N, 2)
        ang = -math.pi / 2 + rng.normal(0, 0.5)
        L = rng.uniform(10, 26)
        col = tuple(int(v) for v in srgb(rng.choice(pal)) * rng.uniform(0.75, 1.15))
        w = 1 if rng.random() < 0.7 else 2
        def f(dx, dy, x=x, y=y, ang=ang, L=L, col=col, w=w):
            d.line([(x + dx, y + dy), (x + dx + math.cos(ang) * L, y + dy + math.sin(ang) * L)], fill=col, width=w)
        wrap_draw(N, f)
    a = np.asarray(img, float)
    dry = periodic_noise(N, seed + 3, 2.2)
    dm = np.clip((dry - 0.6) * 4, 0, 1)[..., None] * 0.35
    a = a * (1 - dm) + srgb('#8f8a52')[None, None] * dm * (a / 110)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', nargs='*')
    args = ap.parse_args()
    out = os.path.join(args.out, 'textures', 'terrain')
    os.makedirs(out, exist_ok=True)
    for name, fn in [('forest', tex_forest), ('rock', tex_rock), ('path', tex_path), ('meadow', tex_meadow)]:
        if args.only and name not in args.only:
            continue
        im = fn()
        im.save(os.path.join(out, f'{name}.png'), optimize=True)
        print('wrote', name)


if __name__ == '__main__':
    main()
