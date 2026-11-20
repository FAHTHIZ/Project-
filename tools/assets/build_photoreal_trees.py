# SPDX-License-Identifier: Apache-2.0
"""Woodland trees with photographic bark and baked photoscan foliage cards (Poly Haven, CC0).

    BLENDER=/path/to/blender python3 tools/assets/build_photoreal_trees.py

The tree shapes stay those of tools/props/build_forest.py (same seeds, sizes, two primitives per
tree: Bark + Leaves/Needles, so scenes and colliders stay valid and the triangle count is
unchanged, ~2-4k per tree). What changes is every texel:

- bark: Poly Haven scanned bark (bark_brown_02 broadleaf, pine_bark conifer), 512 px tiles;
- leaf clusters: orthographic crops of the scanned tree_small_02 crown, baked unlit (albedo +
  alpha) in Blender by tools/assets/blender_card.py, at true scale (a 1.5 m card shows 1.5 m of
  real crown), with an organic edge mask and baked inner shadowing so clusters read as volume;
- conifer boughs: fir_sapling whorls rendered top-down and layered along the bough axis.

Card textures are albedo; VICTUS lights them (wrap normals from the canopy centre).
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'props'))
sys.path.insert(0, os.path.join(HERE, '..', 'characters'))
import polyhaven as ph  # noqa: E402
import build_forest as bf  # noqa: E402

BLENDER = os.environ.get('BLENDER', 'blender')
CARD_WORKER = os.path.join(HERE, 'blender_card.py')
ENV = os.path.join(ph.ROOT, 'game', 'assets', 'models', 'env')
CARDS = os.path.join(ph.CACHE, '_cards')


def bake(job, out):
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    job = dict(job, out=out)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(job, f)
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', CARD_WORKER, '--', f.name],
                       capture_output=True, text=True)
    os.unlink(f.name)
    if 'CARD_OK' not in r.stdout:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f'card bake failed: {out}')
    return out


def rgba(path):
    return np.asarray(Image.open(path).convert('RGBA')).astype(np.float32) / 255.0


def organic_mask(h, w, seed, cx=0.5, cy=0.5, rx=0.5, ry=0.5, power=2.0):
    """Soft elliptical mask with a noisy rim, so card edges never read as rectangles."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    dx = (x / w - cx) / rx; dy = (y / h - cy) / ry
    ang = np.arctan2(dy, dx)
    rim = 0.82 + sum(rng.uniform(0.03, 0.07) * np.cos(k * ang + rng.uniform(0, 6.283)) for k in (3, 5, 7, 11))
    d = np.sqrt(dx * dx + dy * dy) / rim
    return np.clip((1.0 - d) * 6.0, 0.0, 1.0) ** (1.0 / power)


def ragged(mask, seed, scale=6):
    """Threshold a soft mask against blurred noise: the edge breaks up at leaf scale."""
    rng = np.random.default_rng(seed + 99)
    n = rng.random(mask.shape).astype(np.float32)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(scale))).astype(np.float32) / 255.0
    n = (n - n.mean()) / (n.std() + 1e-6) * 0.18 + 0.5
    return (mask > np.clip(n, 0.02, 0.98)).astype(np.float32)


def grade_leaves(c, a, shade):
    """Deep, slightly cool woodland green; darker toward the cluster core (baked self-shadow)."""
    rgb = c[..., :3]
    lum = rgb @ np.array([0.3, 0.59, 0.11])
    target = np.array([0.20, 0.33, 0.12])  # mean albedo of a broadleaf canopy (linear-ish, sRGB stored)
    mean = (rgb * a[..., None]).sum((0, 1)) / max(a.sum(), 1.0)
    rgb = rgb * (target / np.maximum(mean, 1e-3))[None, None, :]
    rgb = rgb * (0.55 + 0.45 * shade)[..., None]
    return np.clip(rgb, 0, 1), lum


def bleed(rgb, a):
    """Fill transparent texels with blurred neighbour colour (clean mips, no dark halos)."""
    fill = rgb.copy(); filled = a > 0.5
    pre = Image.fromarray((np.dstack([rgb * a[..., None], a]) * 255).astype(np.uint8), 'RGBA')
    for r in (2, 6, 16, 48):
        bl = np.asarray(pre.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255.0
        w = bl[..., 3]; ok = (~filled) & (w > 0.01)
        fill[ok] = bl[..., :3][ok] / w[ok][:, None]; filled = filled | ok
    mean = (rgb * a[..., None]).sum((0, 1)) / max(a.sum(), 1)
    fill[~filled] = mean
    return rgb * a[..., None] + fill * (1.0 - a[..., None])


def png(rgb, a, size=None):
    im = Image.fromarray((np.dstack([rgb, a]) * 255).astype(np.uint8), 'RGBA')
    if size: im = im.resize(size, Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True); return b.getvalue()


def leaf_card(center, seed):
    src = ph.model('tree_small_02', '1k')
    path = bake({'src': src, 'size': [768, 768], 'center': list(center), 'view': [0, 1, 0], 'up': [0, 0, 1],
                 'width': 1.5, 'depth': 1.2}, os.path.join(CARDS, f'leaf_{seed}.png'))
    c = rgba(path)
    m = organic_mask(c.shape[0], c.shape[1], seed)
    r, g = c[..., 0], c[..., 1]
    leafy = np.clip((g / np.maximum(r, 1e-3) - 1.02) * 3.0, 0, 1)  # drop brown wood, keep leaves
    a = np.clip(c[..., 3] * 1.15, 0, 1) * leafy * ragged(m, seed)
    a = np.where(a > 0.5, 1.0, a * 0.9)
    shade = np.clip(m * 1.4, 0, 1)
    rgb, _ = grade_leaves(c, a, shade)
    rgb = bleed(rgb, a)
    return png(rgb, a, (512, 512))


def needle_card(seed):
    """Dense fir bough: layered top-down crops of fir_sapling whorls, trunk end at u = 0."""
    src = ph.model('fir_sapling', '1k')
    acc = np.zeros((256, 512, 4), np.float32)
    k = 0
    for z in (0.42, 0.62, 0.85):
        for ang in (0, 144, 288):
            th = np.radians(ang)
            fwd = np.array([np.cos(th), np.sin(th), 0.0])  # bough axis in Blender XY
            reach = 0.40 if z < 0.6 else 0.30
            centre = fwd * reach * 0.5 + np.array([0, 0, z])
            up = np.array([-np.sin(th), np.cos(th), 0.0])
            p = bake({'src': src, 'objects': ['fir_sapling_a'], 'size': [512, 256], 'center': centre.tolist(),
                      'view': [0, 0, -1], 'up': up.tolist(), 'width': reach, 'depth': 0.16},
                     os.path.join(CARDS, f'fir_{z}_{ang}.png'))
            c = rgba(p)
            # camera right = view x up; with view -Z this is fwd or -fwd: make u grow along fwd
            right = np.cross(np.array([0, 0, -1.0]), up)
            if np.dot(right, fwd) < 0: c = c[:, ::-1]
            a = c[..., 3:4]
            acc[..., :3] = acc[..., :3] * (1 - a) + c[..., :3] * a
            acc[..., 3:4] = 1 - (1 - acc[..., 3:4]) * (1 - a)
            k += 1
    a = acc[..., 3]
    h, w = a.shape
    y, x = np.mgrid[0:h, 0:w]
    taper = np.clip(1.0 - np.abs(y / h - 0.5) * 2.0 / (0.55 + 0.45 * (1 - x / w) + 0.15), 0, 1)
    a = np.clip(a * 1.2, 0, 1) * ragged(np.clip(taper * 1.3, 0, 1), seed, 2)
    a = np.where(a > 0.5, 1.0, a)
    shade = 0.6 + 0.4 * taper
    rgb = acc[..., :3] * shade[..., None]
    mean = (rgb * a[..., None]).sum((0, 1)) / max(a.sum(), 1)
    rgb = np.clip(rgb * (np.array([0.13, 0.21, 0.10]) / np.maximum(mean, 1e-3)), 0, 1)
    rgb = bleed(rgb, a)
    return png(rgb, a, (512, 256))


def bark_png(asset, size=512):
    t = ph.texture(asset, '1k', 'jpg', maps=('diff',))
    p = t['diff'] if isinstance(t, dict) else t
    im = Image.open(p).convert('RGB').resize((size, size), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True); return b.getvalue()


_orig_tube = bf.solid_from_tube


def _photo_tube(m, t, color):
    """The generator multiplies a dark brown vertex colour into a grey procedural bark; the
    photo bark already carries its colour, so keep only the relative shading (roots darker)."""
    col = np.asarray(color, float)
    k = float(np.mean(col)) / 0.16
    return _orig_tube(m, t, np.clip(np.ones(3) * 0.62 * k, 0, 1))


def main():
    bf.solid_from_tube = _photo_tube
    broad_bark, pine_bark = bark_png('bark_brown_02'), bark_png('pine_bark')
    leaves = {1: leaf_card((0.0, -0.76, 4.0), 1), 2: leaf_card((0.6, -0.76, 3.9), 2),
              3: leaf_card((-0.5, -0.76, 3.8), 3)}
    needles = needle_card(4)
    jobs = [
        ('tree_broadleaf_a', lambda t: bf.build_broadleaf_tree('tree_broadleaf_a', 1, 11.0, 0.32, 3.6, t, lean=0.4), leaves[1], broad_bark),
        ('tree_broadleaf_b', lambda t: bf.build_broadleaf_tree('tree_broadleaf_b', 2, 13.5, 0.4, 4.2, t, lean=0.7, bare_lower=0.55), leaves[2], broad_bark),
        ('tree_broadleaf_c', lambda t: bf.build_broadleaf_tree('tree_broadleaf_c', 3, 8.0, 0.22, 2.8, t, lean=0.25, bare_lower=0.35), leaves[3], broad_bark),
        ('tree_conifer_a', lambda t: bf.build_conifer('tree_conifer_a', 4, 12.0, 0.28, t), None, pine_bark),
        ('tree_conifer_b', lambda t: bf.build_conifer('tree_conifer_b', 5, 8.5, 0.2, t), None, pine_bark),
    ]
    for name, fn, leaf, bark in jobs:
        tex = {'bark': bark, 'leaves': leaf or needles, 'needles': needles}
        m, tris = fn(tex)
        p = os.path.join(ENV, name + '.glb'); m.save(p)
        print(f'TREE_OK {name} {tris} tris {os.path.getsize(p) // 1024} KiB')


if __name__ == '__main__':
    main()
