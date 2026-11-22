# SPDX-License-Identifier: Apache-2.0
"""Tileable textures for the first-person combat-shirt sleeve (hand_r / hand_l primitive 1).

    python3 tools/assets/sleeve_camo.py [out_dir]     # writes sleeve_{color,normal,mr}.png previews

The squad wears a MultiCam-style pattern (docs/BUILD_AND_TEST_LOG.md "Modern combat kit"); the old
viewmodel sleeve was one flat olive colour. Everything here is synthesised (original, Apache-2.0)
except the weave, which is the ambientCG CC0 Fabric030 scan already used by retexture.py:

- colour: a tan ground with brown, olive and dark-green blobs and cream specks, each layer a
  thresholded, domain-warped band-limited noise (periodic, so the texture tiles in both axes),
  multiplied by the weave luminance;
- normal: the weave normal plus soft compression folds that run round the forearm (v is along
  the arm), broken up by noise, from a height field;
- metallic-roughness: rough cotton/nylon (0.86-0.95), slightly smoother on the darker print.

The sleeve UVs are cylindrical (u = angle round the forearm, one turn = 1; v = distance along
the arm / mean circumference), so one tile covers the whole visible sleeve without a seam.
"""
from __future__ import annotations

import io
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ambientcg as acg  # noqa: E402

SIZE = 512


def _noise(rng, size, scale, aniso=1.0):
    """Periodic low-pass noise (feature size about `scale` px): Gaussian-shaped random spectrum."""
    f = np.fft.fftfreq(size)[:, None], np.fft.fftfreq(size)[None, :]
    fy, fx = f[0], f[1] * aniso      # aniso < 1: narrower across columns, so features run down rows (v)
    r = np.sqrt(fx * fx + fy * fy) * size
    k = size / scale
    amp = np.exp(-(r / (k + 1e-6)) ** 2) * (1 + 0.6 * np.exp(-((r - 2.5 * k) / k) ** 2))   # soft lowpass blobs
    amp[0, 0] = 0
    ph = rng.uniform(0, 2 * np.pi, (size, size))
    n = np.real(np.fft.ifft2(amp * np.exp(1j * ph)))
    return (n - n.mean()) / (n.std() + 1e-9)


def _warp(img, dx, dy):
    s = img.shape[0]
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    x = (xx + dx) % s; y = (yy + dy) % s
    x0, y0 = x.astype(int), y.astype(int); x1, y1 = (x0 + 1) % s, (y0 + 1) % s
    tx, ty = x - x0, y - y0
    return (img[y0, x0] * (1 - tx) * (1 - ty) + img[y0, x1] * tx * (1 - ty) +
            img[y1, x0] * (1 - tx) * ty + img[y1, x1] * tx * ty)


def _srgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def _png(a, mode='RGB'):
    b = io.BytesIO()
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), mode).save(b, 'PNG', optimize=True)
    return b.getvalue()


def _tile_scan(path, mode, reps):
    """Fabric scan resized so it repeats `reps` times across the tile (keeps it periodic)."""
    t = SIZE // reps
    a = np.asarray(Image.open(path).convert(mode).resize((t, t), Image.LANCZOS)).astype(np.float32) / 255.0
    return np.tile(a, (reps, reps) + ((1,) if a.ndim == 3 else ()))


def build(seed=4107):
    rng = np.random.default_rng(seed)
    s = SIZE
    wx, wy = _noise(rng, s, 60) * 9, _noise(rng, s, 60) * 9
    # MultiCam reads as soft vertical-ish brush blobs: elongated along v (down the arm) with aniso < 1
    lay = lambda sc, an=0.7: _warp(_noise(rng, s, sc, an), wx, wy)
    col = np.empty((s, s, 3), np.float32); col[:] = _srgb('#a3916b')                 # tan ground
    # (colour, feature px, threshold, anisotropy, edge sharpness); a tile is about 30 cm of sleeve
    for hexc, sc, thr, an, sh in (('#b9a67f', 150, 0.3, 0.8, 2.0),   # light tan clouds
                                  ('#8a7553', 110, 0.5, 0.6, 3.0),   # mid brown
                                  ('#6e6e47', 90, 0.55, 0.55, 4.0),  # olive green
                                  ('#4f5536', 60, 0.9, 0.5, 5.0),    # dark green
                                  ('#4c3c2b', 34, 1.35, 0.6, 6.0),   # dark brown branches
                                  ('#d3c6a2', 14, 1.8, 1.0, 6.0)):   # cream specks
        n = lay(sc, an)
        m = np.clip((n - thr) * sh, 0, 1)[..., None]
        col = col * (1 - m) + _srgb(hexc) * m
    fab = acg.material('Fabric030')
    weave = _tile_scan(fab['diff'], 'L', 8)
    weave = 1.0 + (weave - weave.mean()) / (weave.std() + 1e-6) * 0.07
    # folds: compression rings round the forearm (constant v), wobbling and fading with noise
    v = np.arange(s, dtype=np.float32)[:, None] / s
    u = np.arange(s, dtype=np.float32)[None, :] / s
    wob = _noise(rng, s, 160) * 0.05
    fade = np.clip(_noise(rng, s, 200, 1.0) * 0.6 + 0.55, 0, 1)
    folds = (np.sin(2 * np.pi * (v * 7 + wob + 0.05 * np.sin(2 * np.pi * u))) * 0.5 + 0.5) ** 2 * fade
    folds2 = (np.sin(2 * np.pi * (v * 13 + wob * 1.7 + 0.3)) * 0.5 + 0.5) ** 3 * (1 - fade) * 0.5
    h = (folds + folds2)
    shade = 1.0 - 0.10 * (1 - h)                                                          # cavity darkening
    color = np.clip(col * weave[..., None] * shade[..., None], 0, 1)
    # height to normal (OpenGL +Y), fold height 1 = about 2.5 mm over a 6 cm fold
    gy, gx = np.gradient(h * 3.2)
    nw = _tile_scan(fab['nor'], 'RGB', 8) * 2 - 1
    nx, ny = -gx + nw[..., 0] * 0.8, gy + nw[..., 1] * 0.8
    nz = np.ones_like(nx)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.dstack([nx / ln, ny / ln, nz / ln]) * 0.5 + 0.5
    lum = col.mean(-1)
    rough = np.clip(0.95 - (0.62 - lum) * 0.2 - h * 0.03, 0.8, 1.0)
    mr = np.dstack([np.ones_like(rough), rough, np.ones_like(rough)])
    return color, normal, mr


def pngs():
    c, n, mr = build()
    return _png(c), _png(n), _png(mr)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp'
    for name, data in zip(('color', 'normal', 'mr'), pngs()):
        p = os.path.join(out, f'sleeve_{name}.png')
        open(p, 'wb').write(data); print(p)
