# SPDX-License-Identifier: Apache-2.0
"""Procedural structures for the Kestrel Valley world and the Vellwood compound (all original).

    python3 tools/props/build_structures.py --out game/assets

Writes <out>/models/structures/*.glb and tools/props/structures_layout.json. Every model is built
from boxes, prisms and lofts with box-projected UVs onto small tileable textures generated here
(planks, logs, corrugated sheet, concrete, canvas, painted steel, stencilled signs), so the
surfaces carry real material detail rather than flat vertex colour.

Model frame: metres, +Y up, the front (door side) faces -Z, origin on the ground at the centre
of the footprint. The layout file lists, per model, the collision boxes (centre, half extents,
yaw) the world builder turns into static box colliders, and named anchor points (doors,
interaction spots, seats) used by the mission scripts.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'characters'))
from build_forest import Model, hexc, periodic_noise  # noqa: E402
import meshkit as mk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = 512
LAYOUT = {}


# ------------------------------------------------------------------------------------------------
# textures (sRGB PNG bytes)

def _png(arr):
    b = io.BytesIO()
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(b, 'PNG', optimize=True)
    return b.getvalue()


def _rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def _shade(base, k):
    return base[None, None, :] * k[..., None]


def tex_planks(seed, base='#7a5c3e', boards=8, vertical=False):
    """Weathered boards: per-board tone, grain streaks, dark gaps and a few knots."""
    n = TEX
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n
    u, v = (x, y) if not vertical else (y, x)
    board = np.floor(v * boards).astype(int)
    tone = r.uniform(0.78, 1.12, boards + 1)[board]
    grain = periodic_noise(n, seed + 1, beta=1.2)
    streak = np.sin((u * 3 + grain * 1.7 + board * 0.37) * 2 * np.pi * 9) * 0.5 + 0.5
    if vertical:
        streak = streak.T
    k = tone * (0.86 + 0.14 * streak) * (0.9 + 0.2 * periodic_noise(n, seed + 2, beta=2.2))
    fv = (v * boards) % 1.0
    gap = np.clip(1 - np.minimum(fv, 1 - fv) / 0.035, 0, 1)
    k *= 1 - 0.65 * gap
    # butt joints along each board
    off = r.uniform(0, 1, boards + 1)[board]
    fu = (u * 1.5 + off) % 1.0
    k *= 1 - 0.5 * np.clip(1 - np.minimum(fu, 1 - fu) / 0.006, 0, 1)
    img = _shade(_rgb(base), k)
    for _ in range(5):
        cx, cy = r.uniform(0, 1, 2)
        d = np.hypot((u - cx) * 4, (v - cy) * 16)
        img *= (1 - 0.45 * np.exp(-(d * 9) ** 2))[..., None]
    return _png(img)


def tex_logs(seed, base='#6e5236'):
    """Horizontal log courses with rounded shading and chinking between them."""
    n = TEX
    y, x = np.mgrid[0:n, 0:n] / n
    courses = 6
    f = (y * courses) % 1.0
    round_k = 0.55 + 0.45 * np.sin(f * np.pi) ** 0.6
    grain = periodic_noise(n, seed, beta=1.3)
    bark = 0.85 + 0.15 * np.sin((x * 14 + grain * 2.2) * 2 * np.pi)
    k = round_k * bark * (0.88 + 0.24 * periodic_noise(n, seed + 3, beta=2.4))
    img = _shade(_rgb(base), k)
    chink = np.clip(1 - np.minimum(f, 1 - f) / 0.05, 0, 1)
    img = img * (1 - chink[..., None]) + _shade(_rgb('#8f877a'), 0.8 + 0.2 * grain) * chink[..., None]
    return _png(img)


def tex_corrugated(seed, base='#7d8486', rust=0.25):
    """Corrugated sheet: sinusoidal ridges with streaks, rust runs and panel laps."""
    n = TEX
    y, x = np.mgrid[0:n, 0:n] / n
    ridge = 0.72 + 0.28 * np.sin(x * 2 * np.pi * 16)
    streak = periodic_noise(n, seed, beta=1.6)
    streak = 0.85 + 0.3 * np.clip(np.abs(np.gradient(streak, axis=1)) * 60, 0, 1) * 0 + 0.15 * streak
    k = ridge * streak
    img = _shade(_rgb(base), k)
    rr = periodic_noise(n, seed + 7, beta=2.0)
    runs = np.clip((rr - (1 - rust)) / rust, 0, 1) * (0.5 + 0.5 * np.sin(x * 2 * np.pi * 16) ** 2)
    img = img * (1 - runs[..., None]) + _shade(_rgb('#7a4a2a'), 0.7 + 0.3 * rr) * runs[..., None]
    lap = np.clip(1 - np.abs((y % 0.5) - 0.0) / 0.01, 0, 1)
    img *= (1 - 0.35 * lap)[..., None]
    return _png(img)


def tex_concrete(seed, base='#9a9890', panels=2, stain=0.5):
    """Cast concrete: mottling, form-tie holes, panel joints and run-off stains."""
    n = TEX
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n
    mott = periodic_noise(n, seed, beta=2.2)
    fine = periodic_noise(n, seed + 1, beta=0.8)
    k = 0.84 + 0.12 * mott + 0.08 * fine
    run = periodic_noise(n, seed + 2, beta=2.6)
    k *= 1 - stain * 0.25 * np.clip((run - 0.55) * 3, 0, 1) * (0.6 + 0.4 * y)
    fx, fy = (x * panels) % 1.0, (y * panels) % 1.0
    joint = np.clip(1 - np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy)) / 0.006, 0, 1)
    k *= 1 - 0.45 * joint
    img = _shade(_rgb(base), k)
    for i in range(panels * 2):
        for j in range(panels * 2):
            cx, cy = (i + 0.5) / (panels * 2), (j + 0.5) / (panels * 2)
            d = np.hypot(x - cx, y - cy)
            img *= (1 - 0.55 * np.clip(1 - d / 0.007, 0, 1))[..., None]
    return _png(img)


def tex_canvas(seed, base='#5d6247'):
    n = TEX
    y, x = np.mgrid[0:n, 0:n] / n
    weave = 0.93 + 0.035 * np.sin(x * 2 * np.pi * 120) + 0.035 * np.sin(y * 2 * np.pi * 120)
    k = weave * (0.85 + 0.25 * periodic_noise(n, seed, beta=2.0))
    seam = np.clip(1 - np.abs(((x * 2) % 1.0) - 0.5) / 0.008, 0, 1)
    k *= 1 - 0.25 * seam
    return _png(_shade(_rgb(base), k))


def tex_paint(seed, base='#59605a', wear=0.15, rivets=True):
    """Painted steel: soft mottling, edge-free wear spots to bare metal, optional rivet rows."""
    n = TEX
    y, x = np.mgrid[0:n, 0:n] / n
    m = periodic_noise(n, seed, beta=2.4)
    k = 0.9 + 0.15 * m
    img = _shade(_rgb(base), k)
    w = periodic_noise(n, seed + 5, beta=1.4)
    chip = np.clip((w - (1 - wear)) / max(wear, 1e-3), 0, 1) ** 0.5
    img = img * (1 - chip[..., None]) + _shade(_rgb('#8a8c88'), 0.8 + 0.2 * m) * chip[..., None]
    if rivets:
        fx, fy = (x * 8) % 1.0, (y * 2) % 1.0
        d = np.hypot(fx - 0.5, (fy - 0.06) * 4)
        img *= (1 - 0.3 * np.clip(1 - d / 0.08, 0, 1))[..., None]
    return _png(img)


def tex_stone(seed, base='#7b786f'):
    """Rubble stone: irregular blocks (jittered grid cells) with mortar."""
    n = TEX
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n] / n
    rows = 5
    row = np.floor(y * rows).astype(int)
    shift = r.uniform(0, 1, rows + 1)[row]
    cols = 4
    fx = (x * cols + shift) % 1.0
    fy = (y * rows) % 1.0
    cell = (np.floor(x * cols + shift).astype(int) * 7 + row * 13) % 97
    tone = r.uniform(0.7, 1.15, 97)[cell]
    edge = np.minimum(np.minimum(fx, 1 - fx) * 1.2, np.minimum(fy, 1 - fy))
    bevel = np.clip(edge / 0.12, 0, 1) ** 0.5
    mortar = edge < 0.035
    k = tone * (0.6 + 0.4 * bevel) * (0.85 + 0.25 * periodic_noise(n, seed + 1, beta=1.8))
    img = _shade(_rgb(base), k)
    img[mortar] = _rgb('#9c968a') * 0.75
    return _png(img)


def tex_sign(text, sub='', bg='#d8d4c6', fg='#1e2224', stripe=None, w=1024, h=512):
    img = Image.new('RGB', (w, h), bg)
    d = ImageDraw.Draw(img)
    try:
        f1 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 112)
        f2 = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 54)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    if stripe:
        for i in range(-2, 12):
            d.polygon([(i * 110, h), (i * 110 + 55, h), (i * 110 + 105, h - 70), (i * 110 + 50, h - 70)], fill=stripe)
    d.rectangle([14, 14, w - 15, h - 15], outline=fg, width=10)
    tw = d.textlength(text, font=f1)
    d.text(((w - tw) / 2, 120 if sub else 190), text, font=f1, fill=fg)
    if sub:
        sw = d.textlength(sub, font=f2)
        d.text(((w - sw) / 2, 290), sub, font=f2, fill=fg)
    arr = np.asarray(img).astype(float)
    arr *= (0.9 + 0.12 * periodic_noise(256, 3, beta=2.0)[np.arange(h)[:, None] * 256 // h,
                                                          np.arange(w)[None, :] * 256 // w])[..., None]
    return _png(arr)


# ------------------------------------------------------------------------------------------------
# geometry

def _face_uv(q, n, tile):
    """Box projection: the two axes most perpendicular to the face normal, in metres / tile."""
    a = int(np.argmax(np.abs(n)))
    if a == 1:
        uv = q[:, [0, 2]]
    elif a == 0:
        uv = q[:, [2, 1]]
    else:
        uv = q[:, [0, 1]]
    return uv / tile * np.array([1.0, -1.0])


def hexa(c, tile=1.0):
    c = np.asarray(c, float)
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    cen = c.mean(axis=0)
    P, N, I, UV = [], [], [], []
    for f in faces:
        q = c[list(f)]
        nn = np.cross(q[1] - q[0], q[2] - q[0])
        if np.linalg.norm(nn) < 1e-9:
            nn = np.cross(q[2] - q[0], q[3] - q[0])
        ln = np.linalg.norm(nn)
        if ln < 1e-9:
            continue
        nn /= ln
        if np.dot(nn, q.mean(axis=0) - cen) < 0:
            nn = -nn
        b = len(P)
        P.extend(q); N.extend([nn] * 4); UV.extend(_face_uv(q, nn, tile))
        I += [b, b + 1, b + 2, b, b + 2, b + 3]
    return np.array(P), np.array(N), np.array(I, dtype=np.uint32), np.array(UV)


def box_c(lo, hi):
    x0, y0, z0 = lo; x1, y1, z1 = hi
    return [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]


def _rot_pts(pts, yaw, about=(0, 0, 0)):
    a = math.radians(yaw)
    c, s = math.cos(a), math.sin(a)
    p = np.asarray(pts, float) - about
    out = p.copy()
    out[:, 0] = c * p[:, 0] + s * p[:, 2]
    out[:, 2] = -s * p[:, 0] + c * p[:, 2]
    return out + about


class Part:
    """One textured surface set (material) of a model; parts collect boxes then become prims."""

    def __init__(self, model, name, png, tile=1.0, rough=0.85, metal=0.0, color=(1, 1, 1),
                 emissive=None, strength=1.0, mask=False):
        tex = model.texture(name, png) if png is not None else None
        self.mat = model.material(name, tex, rough, metal=metal, emissive=emissive, strength=strength,
                                  mask=mask)
        self.mesh = mk.Mesh()
        self.tile = tile
        self.color = color
        self.model = model

    def box(self, lo, hi, yaw=0.0, color=None, tile=None):
        c = box_c(lo, hi)
        if yaw:
            cen = (np.asarray(lo) + np.asarray(hi)) / 2
            c = _rot_pts(c, yaw, cen)
        return self.hexa(c, color, tile)

    def hexa(self, c, color=None, tile=None):
        P, N, I, UV = hexa(c, tile or self.tile)
        self.mesh.add((P, N, I), color or self.color, uv=UV)
        return self

    def raw(self, part, color=None):
        P, N, I = part
        UV = np.zeros((len(P), 2))
        for k in range(len(P)):
            UV[k] = _face_uv(P[k:k + 1], N[k], self.tile)[0]
        self.mesh.add((P, N, I), color or self.color, uv=UV)
        return self

    def beam(self, a, b, t=0.08, color=None):
        """Square-section member from point a to point b (struts, braces, rails)."""
        a, b = np.asarray(a, float), np.asarray(b, float)
        d = b - a
        L = np.linalg.norm(d)
        if L < 1e-6:
            return self
        f = d / L
        up = np.array([0, 1.0, 0]) if abs(f[1]) < 0.95 else np.array([1.0, 0, 0])
        s = np.cross(f, up); s /= np.linalg.norm(s)
        u = np.cross(s, f)
        h = t / 2
        c = [a - s * h - u * h, a + s * h - u * h, a + s * h + u * h, a - s * h + u * h,
             b - s * h - u * h, b + s * h - u * h, b + s * h + u * h, b - s * h + u * h]
        return self.hexa(c, color)

    def emit(self):
        if self.mesh.n:
            self.model.solid(self.mesh, self.mat)


class Layout:
    def __init__(self, name):
        self.d = LAYOUT.setdefault(name, {'colliders': [], 'anchors': {}})

    def col(self, lo, hi, yaw=0.0):
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        c = (lo + hi) / 2
        self.d['colliders'].append({'c': [round(float(v), 3) for v in c],
                                    'h': [round(float(v), 3) for v in (hi - lo) / 2], 'yaw': yaw})

    def anchor(self, key, pos, yaw=0.0):
        self.d['anchors'][key] = {'p': [round(float(v), 3) for v in pos], 'yaw': yaw}


def save(m, parts, out):
    for p in parts:
        p.emit()
    m.save(os.path.join(out, 'models', 'structures', m.name + '.glb'))


def wall_with_openings(part, lay, axis, fixed, span, y0, y1, t, openings, col=True):
    """A wall along `axis` ('x' or 'z') at `fixed` (other axis), from span[0]..span[1], with
    rectangular openings [(a0, a1, b0, b1)] (along-wall range, height range)."""
    a0, a1 = span
    cuts = sorted(openings)
    segs = []  # (a0, a1, b0, b1)
    cur = a0
    for (o0, o1, h0, h1) in cuts:
        if o0 > cur:
            segs.append((cur, o0, y0, y1))
        if h0 > y0:
            segs.append((o0, o1, y0, h0))
        if h1 < y1:
            segs.append((o0, o1, h1, y1))
        cur = o1
    if cur < a1:
        segs.append((cur, a1, y0, y1))
    for (s0, s1, b0, b1) in segs:
        if axis == 'x':
            lo, hi = (s0, b0, fixed - t / 2), (s1, b1, fixed + t / 2)
        else:
            lo, hi = (fixed - t / 2, b0, s0), (fixed + t / 2, b1, s1)
        part.box(lo, hi)
        if col and b1 - b0 > 0.3:
            lay.col(lo, hi)


def gable_roof(part, x0, x1, z0, z1, eave, ridge, thick=0.06, along='x'):
    """Two sloped slabs; the ridge runs along `along`."""
    if along == 'x':
        zm = (z0 + z1) / 2
        for za, zb in ((z0, zm), (z1, zm)):
            c = [(x0, eave, za), (x1, eave, za), (x1, ridge, zb), (x0, ridge, zb),
                 (x0, eave + thick, za), (x1, eave + thick, za), (x1, ridge + thick, zb), (x0, ridge + thick, zb)]
            part.hexa(c)
    else:
        xm = (x0 + x1) / 2
        for xa, xb in ((x0, xm), (x1, xm)):
            c = [(xa, eave, z0), (xa, eave, z1), (xb, ridge, z1), (xb, ridge, z0),
                 (xa, eave + thick, z0), (xa, eave + thick, z1), (xb, ridge + thick, z1), (xb, ridge + thick, z0)]
            part.hexa(c)


def gable_end(part, x0, x1, z, eave, ridge, t=0.12):
    """Triangular gable infill on the x-span at z (a thin wedge)."""
    xm = (x0 + x1) / 2
    c = [(x0, eave, z - t / 2), (x1, eave, z - t / 2), (xm + 0.01, ridge, z - t / 2), (xm - 0.01, ridge, z - t / 2),
         (x0, eave, z + t / 2), (x1, eave, z + t / 2), (xm + 0.01, ridge, z + t / 2), (xm - 0.01, ridge, z + t / 2)]
    part.hexa(c)


# ------------------------------------------------------------------------------------------------
# structures

def ranger_cabin(out):
    """Hollis's ranger cabin: log walls on a rubble plinth, a deep front porch, metal gable roof,
    stone chimney, two windows each side and a lived-in interior (stove, bunk, table, map)."""
    m = Model('ranger_cabin')
    lay = Layout('ranger_cabin')
    logs = Part(m, 'cabin_Logs', tex_logs(11), tile=1.8, rough=0.9)
    planks = Part(m, 'cabin_Planks', tex_planks(12, '#6b5034'), tile=1.6, rough=0.88)
    roof = Part(m, 'cabin_Roof', tex_corrugated(13, '#6e756f', 0.35), tile=1.2, rough=0.55, metal=0.4)
    stone = Part(m, 'cabin_Stone', tex_stone(14), tile=1.4, rough=0.92)
    trim = Part(m, 'cabin_Trim', tex_paint(15, '#3e4a3c', 0.25, rivets=False), tile=1.0, rough=0.7)
    glass = Part(m, 'cabin_Glass', None, rough=0.08, metal=0.0, color=(0.05, 0.07, 0.08))
    warm = Part(m, 'cabin_Lamp', None, rough=0.4, emissive=(1.0, 0.72, 0.4), strength=2.5, color=(1, 0.8, 0.5))
    W, D = 3.6, 2.8           # half extents of the log box
    F = 0.45                  # floor height (plinth)
    H = F + 2.55              # wall top
    t = 0.24
    # plinth and floor
    stone.box((-W - 0.05, 0, -D - 0.05), (W + 0.05, F, D + 0.05))
    lay.col((-W, 0, -D), (W, F, D))
    planks.box((-W + t / 2, F, -D + t / 2), (W - t / 2, F + 0.04, D - t / 2), tile=1.2)
    # walls: front (-Z) door + two windows, back two windows, sides one window each
    door = (-0.5, 0.5, F, F + 2.1)
    front_open = [door, (-2.6, -1.4, F + 0.95, F + 1.95), (1.4, 2.6, F + 0.95, F + 1.95)]
    wall_with_openings(logs, lay, 'x', -D, (-W, W), F, H, t, front_open)
    wall_with_openings(logs, lay, 'x', D, (-W, W), F, H, t, [(-2.2, -1.0, F + 0.95, F + 1.95), (1.0, 2.2, F + 0.95, F + 1.95)])
    wall_with_openings(logs, lay, 'z', -W, (-D, D), F, H, t, [(-0.6, 0.6, F + 0.95, F + 1.95)])
    wall_with_openings(logs, lay, 'z', W, (-D, D), F, H, t, [(-0.6, 0.6, F + 0.95, F + 1.95)])
    # corner log ends
    for sx in (-1, 1):
        for sz in (-1, 1):
            logs.box((sx * W - 0.18, F, sz * D - 0.18), (sx * W + 0.18, H + 0.1, sz * D + 0.18))
    # window frames + glass + sills
    def window_x(z, x0, x1, inner_sign):
        y0, y1 = F + 0.95, F + 1.95
        trim.box((x0 - 0.06, y0 - 0.08, z - 0.16), (x1 + 0.06, y0, z + 0.16))
        trim.box((x0 - 0.06, y1, z - 0.14), (x1 + 0.06, y1 + 0.07, z + 0.14))
        for xx in (x0 - 0.06, x1):
            trim.box((xx, y0, z - 0.14), (xx + 0.06, y1, z + 0.14))
        trim.box(((x0 + x1) / 2 - 0.025, y0, z - 0.03), ((x0 + x1) / 2 + 0.025, y1, z + 0.03))
        trim.box((x0, (y0 + y1) / 2 - 0.025, z - 0.03), (x1, (y0 + y1) / 2 + 0.025, z + 0.03))
        glass.box((x0, y0, z - 0.01), (x1, y1, z + 0.01))
    def window_z(x, z0, z1):
        y0, y1 = F + 0.95, F + 1.95
        trim.box((x - 0.16, y0 - 0.08, z0 - 0.06), (x + 0.16, y0, z1 + 0.06))
        trim.box((x - 0.14, y1, z0 - 0.06), (x + 0.14, y1 + 0.07, z1 + 0.06))
        trim.box((x - 0.03, y0, (z0 + z1) / 2 - 0.025), (x + 0.03, y1, (z0 + z1) / 2 + 0.025))
        glass.box((x - 0.01, y0, z0), (x + 0.01, y1, z1))
    window_x(-D, -2.6, -1.4, 1); window_x(-D, 1.4, 2.6, 1)
    window_x(D, -2.2, -1.0, -1); window_x(D, 1.0, 2.2, -1)
    window_z(-W, -0.6, 0.6); window_z(W, -0.6, 0.6)
    # door frame and a door standing open inward (hinged on the left jamb)
    trim.box((-0.6, F, -D - 0.15), (-0.5, F + 2.2, -D + 0.15))
    trim.box((0.5, F, -D - 0.15), (0.6, F + 2.2, -D + 0.15))
    trim.box((-0.6, F + 2.1, -D - 0.15), (0.6, F + 2.2, -D + 0.15))
    planks.box((-0.48, F + 0.02, -D + 0.14), (-0.43, F + 2.06, -D + 1.08), tile=1.0)
    lay.col((-0.5, F, -D + 0.14), (-0.42, F + 2.06, -D + 1.08))
    # gable ends and roof (ridge along X, generous overhang over the porch)
    gable_end(logs, -W, W, -D, H, H + 1.55)
    gable_end(logs, -W, W, D, H, H + 1.55)
    roof.box((-W - 0.5, H - 0.02, -D - 2.6), (W + 0.5, H + 0.0, -D - 0.0)) if False else None
    gable_roof(roof, -W - 0.45, W + 0.45, -D - 0.55, D + 0.55, H - 0.25, H + 1.62, 0.05)
    planks.box((-W - 0.45, H + 1.58, -0.12), (W + 0.45, H + 1.72, 0.12))  # ridge cap board
    # porch: deck, steps, posts, rail, lean-to roof
    PD = 2.2
    planks.box((-W, F - 0.06, -D - PD), (W, F, -D), tile=1.4)
    lay.col((-W, 0, -D - PD), (W, F, -D))
    for i, (h, dz) in enumerate(((0.3, 0.32), (0.15, 0.64))):
        planks.box((-0.9, 0, -D - PD - dz), (0.9, h, -D - PD - dz + 0.34))
        lay.col((-0.9, 0, -D - PD - dz), (0.9, h, -D - PD - dz + 0.34))
    for x in (-W + 0.1, -1.1, 1.1, W - 0.1):
        planks.box((x - 0.08, F, -D - PD + 0.02), (x + 0.08, H - 0.15, -D - PD + 0.18))
        lay.col((x - 0.08, F, -D - PD + 0.02), (x + 0.08, H - 0.15, -D - PD + 0.18))
    for (xa, xb) in ((-W + 0.1, -1.1), (1.1, W - 0.1)):
        planks.box((xa, F + 0.9, -D - PD + 0.06), (xb, F + 0.98, -D - PD + 0.14))
        planks.box((xa, F + 0.45, -D - PD + 0.07), (xb, F + 0.5, -D - PD + 0.13))
        lay.col((xa, F, -D - PD + 0.04), (xb, F + 1.0, -D - PD + 0.16))
    c = [(-W - 0.45, H - 0.45, -D - PD - 0.4), (W + 0.45, H - 0.45, -D - PD - 0.4), (W + 0.45, H - 0.05, -D), (-W - 0.45, H - 0.05, -D),
         (-W - 0.45, H - 0.4, -D - PD - 0.4), (W + 0.45, H - 0.4, -D - PD - 0.4), (W + 0.45, H, -D), (-W - 0.45, H, -D)]
    roof.hexa(c)
    planks.box((-W, H - 0.55, -D - PD + 0.02), (W, H - 0.4, -D - PD + 0.18))  # porch beam
    # chimney on the east gable
    stone.box((W - 0.05, 0, 0.6), (W + 0.75, H + 2.2, 1.5))
    lay.col((W - 0.05, 0, 0.6), (W + 0.75, H + 2.2, 1.5))
    trim.box((W + 0.05, H + 2.2, 0.7), (W + 0.65, H + 2.32, 1.4))
    # interior: stove, bunk, table + bench, shelf, map board, lantern
    trim.box((W - 1.0, F, 0.7), (W - 0.35, F + 0.8, 1.4))
    trim.box((W - 0.8, F + 0.8, 0.95), (W - 0.65, H + 0.4, 1.1))
    lay.col((W - 1.0, F, 0.7), (W - 0.35, F + 0.8, 1.4))
    planks.box((-W + 0.2, F, 0.8), (-W + 1.1, F + 0.5, D - 0.2))
    Part.box(planks, (-W + 0.25, F + 0.5, 0.85), (-W + 1.05, F + 0.62, D - 0.25), color=(0.45, 0.48, 0.4))
    lay.col((-W + 0.2, F, 0.8), (-W + 1.1, F + 0.6, D - 0.2))
    planks.box((-0.7, F + 0.72, 0.2), (0.7, F + 0.78, 1.1))
    for x, z in ((-0.62, 0.28), (0.62, 0.28), (-0.62, 1.02), (0.62, 1.02)):
        planks.box((x - 0.04, F, z - 0.04), (x + 0.04, F + 0.72, z + 0.04))
    lay.col((-0.7, F, 0.2), (0.7, F + 0.78, 1.1))
    planks.box((-0.7, F + 0.42, 1.25), (0.7, F + 0.47, 1.55))
    planks.box((-W + 0.15, F + 1.5, -1.6), (-W + 0.45, F + 1.54, 0.3))
    trim.box((0.9, F + 1.0, D - 0.16), (2.3, F + 1.9, D - 0.13), color=(0.85, 0.82, 0.7))
    warm.box((-0.08, F + 0.78, 0.55), (0.08, F + 1.0, 0.71))
    lay.anchor('door_out', (0.0, F, -D - 1.2), 180.0)
    lay.anchor('porch', (-1.8, F, -D - 1.0), 180.0)
    lay.anchor('inside', (0.0, F, -0.6), 0.0)
    lay.anchor('table', (0.0, F, 0.65), 0.0)
    lay.anchor('lamp', (0.0, F + 0.9, 0.63), 0.0)
    save(m, [logs, planks, roof, stone, trim, glass, warm], out)


def relay_mast(out):
    """Greyline's portable sensor relay: a tapered lattice mast on a ballast skid, sensor head,
    two panel antennas, solar wing and a cabinet with the power-cell bay (interaction point)."""
    m = Model('relay_mast')
    lay = Layout('relay_mast')
    steel = Part(m, 'relay_Steel', tex_paint(21, '#8b8f8c', 0.1, rivets=False), tile=0.8, rough=0.5, metal=0.6)
    case = Part(m, 'relay_Case', tex_paint(22, '#4a4f53', 0.12), tile=0.9, rough=0.55, metal=0.3)
    skid = Part(m, 'relay_Skid', tex_concrete(23, '#86847c', 1, 0.6), tile=1.2, rough=0.9)
    panel = Part(m, 'relay_Solar', None, rough=0.15, metal=0.2, color=(0.08, 0.1, 0.16))
    led = Part(m, 'relay_Led', None, rough=0.3, emissive=(1.0, 0.25, 0.1), strength=6.0, color=(1, 0.3, 0.1))
    skid.box((-1.3, 0, -1.3), (1.3, 0.35, 1.3))
    lay.col((-1.3, 0, -1.3), (1.3, 0.35, 1.3))
    Hm = 9.0
    base_w, top_w = 0.55, 0.16
    legs = []
    for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        a = (sx * base_w, 0.35, sz * base_w); b = (sx * top_w, Hm, sz * top_w)
        steel.beam(a, b, 0.07)
        legs.append((np.array(a), np.array(b)))
    lay.col((-0.6, 0.35, -0.6), (0.6, 3.0, 0.6))
    nseg = 9
    for k in range(nseg):
        t0, t1 = k / nseg, (k + 1) / nseg
        for i in range(4):
            a0 = legs[i][0] + (legs[i][1] - legs[i][0]) * t0
            b1 = legs[(i + 1) % 4][0] + (legs[(i + 1) % 4][1] - legs[(i + 1) % 4][0]) * t1
            a1 = legs[i][0] + (legs[i][1] - legs[i][0]) * t1
            steel.beam(a0, b1, 0.035)
            steel.beam(a1, legs[(i + 1) % 4][0] + (legs[(i + 1) % 4][1] - legs[(i + 1) % 4][0]) * t1, 0.035)
    # sensor head (drum + dome) and two panel antennas
    case.raw(mk.capsule((0, Hm, 0), (0, Hm + 0.5, 0), 0.32, 0.32, segs=14, rings=3))
    steel.beam((0, Hm + 0.5, 0), (0, Hm + 1.6, 0), 0.04)
    for yaw in (0, 120):
        a = math.radians(yaw)
        cx, cz = math.sin(a) * 0.3, math.cos(a) * 0.3
        c = box_c((-0.18, Hm - 1.2, -0.04), (0.18, Hm - 0.2, 0.04))
        c = _rot_pts(c, yaw) + np.array([cx * 1.6, 0, cz * 1.6])
        case.hexa(c)
    led.box((-0.04, Hm + 1.55, -0.04), (0.04, Hm + 1.65, 0.04))
    # cabinet with the cell bay, cable conduit up the mast
    case.box((0.7, 0.35, -0.95), (1.25, 1.55, -0.2))
    lay.col((0.7, 0.35, -0.95), (1.25, 1.55, -0.2))
    steel.box((0.68, 0.9, -0.97), (0.72, 1.4, -0.6), color=(0.55, 0.57, 0.55))
    led.box((0.69, 1.45, -0.5), (0.71, 1.5, -0.45))
    steel.beam((0.9, 1.55, -0.6), (0.2, 3.0, -0.2), 0.05)
    # solar wing on its own frame
    steel.beam((-1.0, 0.35, 0.7), (-1.0, 1.4, 0.7), 0.06)
    c = box_c((-1.7, 1.35, 0.15), (-0.3, 1.39, 1.25))
    c = np.asarray(c, float)
    c[:, 1] += (c[:, 2] - 0.7) * 0.6
    panel.hexa(c)
    lay.anchor('cell_bay', (0.68, 1.15, -0.78), -90.0)
    lay.anchor('stand', (0.0, 0.35, -1.9), 0.0)
    save(m, [steel, case, skid, panel, led], out)


def camp_tent(out):
    """Halyard staging tent: ridge tent on a frame with open front flaps, guy lines and pegs."""
    m = Model('camp_tent')
    lay = Layout('camp_tent')
    canvas = Part(m, 'tent_Canvas', tex_canvas(31), tile=2.0, rough=0.95)
    pole = Part(m, 'tent_Pole', tex_paint(32, '#3c3f38', 0.05, rivets=False), tile=1.0, rough=0.6, metal=0.4)
    floor = Part(m, 'tent_Floor', tex_canvas(33, '#3b3e33'), tile=2.0, rough=0.95)
    W, D, Hr, He = 2.1, 2.6, 2.6, 1.5
    floor.box((-W, 0, -D), (W, 0.02, D))
    # roof slopes
    for s in (-1, 1):
        c = [(s * W, He, -D), (s * W, He, D), (0, Hr, D), (0, Hr, -D),
             (s * (W + 0.03), He + 0.03, -D), (s * (W + 0.03), He + 0.03, D), (0, Hr + 0.04, D), (0, Hr + 0.04, -D)]
        canvas.hexa(c)
        canvas.box((s * W - 0.02, 0, -D), (s * W + 0.02, He, D))
        lay.col((s * W - 0.05, 0, -D), (s * W + 0.05, He, D))
    # back gable closed, front open with flaps tied back
    c = [(-W, 0, D), (W, 0, D), (W, He, D), (-W, He, D), (-W, 0, D + 0.03), (W, 0, D + 0.03), (W, He, D + 0.03), (-W, He, D + 0.03)]
    canvas.hexa(c)
    canvas.hexa([(-W, He, D), (W, He, D), (0.02, Hr, D), (-0.02, Hr, D),
                 (-W, He, D + 0.03), (W, He, D + 0.03), (0.02, Hr, D + 0.03), (-0.02, Hr, D + 0.03)])
    lay.col((-W, 0, D - 0.05), (W, He, D + 0.05))
    for s in (-1, 1):
        canvas.hexa([(s * W, 0, -D), (s * (W - 0.5), 0, -D - 0.25), (s * (W - 0.5), He, -D - 0.25), (s * W, He, -D),
                     (s * W, 0, -D + 0.03), (s * (W - 0.5), 0, -D - 0.22), (s * (W - 0.5), He, -D - 0.22), (s * W, He, -D + 0.03)])
    for z in (-D, 0, D):
        pole.beam((0, 0, z), (0, Hr, z), 0.05)
    pole.beam((0, Hr, -D), (0, Hr, D), 0.05)
    for s in (-1, 1):
        for z in (-D, D):
            pole.beam((s * W, He, z), (s * (W + 1.3), 0, z + (0.4 if z > 0 else -0.4)), 0.012)
    lay.anchor('front', (0, 0, -D - 1.5), 180.0)
    save(m, [canvas, pole, floor], out)


def camp_props(out):
    """Staging-camp clutter in one model each: folding table with a map and radio, supply crates,
    a generator and a floodlight tripod."""
    # table + map + radio
    m = Model('camp_table')
    lay = Layout('camp_table')
    top = Part(m, 'table_Top', tex_planks(41, '#8a7556', 5), tile=1.0, rough=0.8)
    leg = Part(m, 'table_Leg', None, rough=0.5, metal=0.6, color=(0.25, 0.26, 0.25))
    mp = Part(m, 'table_Map', tex_sign('KESTREL VALLEY', '1:25 000  HALYARD', bg='#cfc6a6', fg='#3c4a3a'), tile=1.0, rough=0.9)
    radio = Part(m, 'table_Radio', tex_paint(42, '#3f4535', 0.1), tile=0.4, rough=0.6)
    top.box((-0.9, 0.72, -0.45), (0.9, 0.76, 0.45))
    for x in (-0.82, 0.82):
        leg.beam((x, 0, -0.38), (x, 0.72, 0.38), 0.03)
        leg.beam((x, 0, 0.38), (x, 0.72, -0.38), 0.03)
    lay.col((-0.9, 0, -0.45), (0.9, 0.76, 0.45))
    P, N, I, UV = hexa(box_c((-0.55, 0.761, -0.3), (0.35, 0.765, 0.3)))
    UV = np.c_[(P[:, 0] + 0.55) / 0.9, 1 - (P[:, 2] + 0.3) / 0.6]
    mp.mesh.add((P, N, I), (1, 1, 1), uv=UV)
    radio.box((0.45, 0.76, -0.2), (0.82, 0.98, 0.1))
    radio.beam((0.78, 0.98, 0.05), (0.8, 1.5, 0.07), 0.01)
    lay.anchor('map', (-0.1, 0.76, 0.0), 0.0)
    save(m, [top, leg, mp, radio], out)
    # crate stack
    m = Model('supply_crates')
    lay = Layout('supply_crates')
    wood = Part(m, 'crate_Wood', tex_planks(43, '#76694a', 4), tile=0.8, rough=0.85)
    stencil = Part(m, 'crate_Stencil', tex_sign('HALYARD', 'FIELD SUPPLY', bg='#76694a', fg='#2a2a22'), tile=1.0, rough=0.85)
    for (x, y, z, w, h, d) in ((0, 0, 0, 1.2, 0.8, 0.8), (1.3, 0, 0.1, 0.8, 0.6, 0.6), (0.2, 0.8, 0.05, 0.8, 0.6, 0.6)):
        wood.box((x - w / 2, y, z - d / 2), (x + w / 2, y + h, z + d / 2))
        lay.col((x - w / 2, y, z - d / 2), (x + w / 2, y + h, z + d / 2))
        P, N, I, UV = hexa(box_c((x - w * 0.35, y + h * 0.2, z - d / 2 - 0.005), (x + w * 0.35, y + h * 0.8, z - d / 2 - 0.004)))
        UV = np.c_[(P[:, 0] - (x - w * 0.35)) / (w * 0.7), 1 - (P[:, 1] - (y + h * 0.2)) / (h * 0.6)]
        stencil.mesh.add((P, N, I), (1, 1, 1), uv=UV)
    save(m, [wood, stencil], out)
    # generator
    m = Model('generator')
    lay = Layout('generator')
    body = Part(m, 'gen_Body', tex_paint(44, '#6d7340', 0.18), tile=0.6, rough=0.55, metal=0.3)
    frame = Part(m, 'gen_Frame', None, rough=0.5, metal=0.7, color=(0.15, 0.15, 0.15))
    body.box((-0.45, 0.1, -0.3), (0.45, 0.65, 0.3))
    for x in (-0.48, 0.48):
        for z in (-0.32, 0.32):
            frame.beam((x, 0, z), (x, 0.75, z), 0.03)
    frame.beam((-0.48, 0.75, -0.32), (0.48, 0.75, -0.32), 0.03)
    frame.beam((-0.48, 0.75, 0.32), (0.48, 0.75, 0.32), 0.03)
    lay.col((-0.5, 0, -0.34), (0.5, 0.78, 0.34))
    save(m, [body, frame], out)
    # floodlight tripod
    m = Model('floodlight')
    lay = Layout('floodlight')
    frame = Part(m, 'flood_Frame', None, rough=0.5, metal=0.7, color=(0.2, 0.21, 0.2))
    lamp = Part(m, 'flood_Lens', None, rough=0.2, emissive=(1.0, 0.95, 0.85), strength=8.0, color=(1, 1, 1))
    for a in (0, 120, 240):
        r = math.radians(a)
        frame.beam((math.sin(r) * 0.7, 0, math.cos(r) * 0.7), (0, 1.8, 0), 0.035)
    frame.beam((0, 1.8, 0), (0, 2.6, 0), 0.04)
    frame.box((-0.25, 2.55, -0.12), (0.25, 2.85, 0.08))
    lamp.box((-0.21, 2.59, -0.135), (0.21, 2.81, -0.12))
    lay.col((-0.3, 0, -0.3), (0.3, 2.6, 0.3))
    lay.anchor('lens', (0, 2.7, -0.2), 0.0)
    save(m, [frame, lamp], out)


def perimeter(out):
    """Vellwood perimeter: watchtower, vehicle gate with guard booth, warning sign, jersey barrier
    and a floodlight pole."""
    m = Model('watchtower')
    lay = Layout('watchtower')
    steel = Part(m, 'tower_Steel', tex_paint(51, '#5c615e', 0.2, rivets=False), tile=1.0, rough=0.55, metal=0.5)
    deck = Part(m, 'tower_Deck', tex_planks(52, '#5e5446', 6), tile=1.2, rough=0.85)
    roof = Part(m, 'tower_Roof', tex_corrugated(53, '#61686a', 0.3), tile=1.2, rough=0.6, metal=0.4)
    Hd = 5.2
    for sx in (-1, 1):
        for sz in (-1, 1):
            steel.beam((sx * 1.5, 0, sz * 1.5), (sx * 1.2, Hd, sz * 1.2), 0.12)
            lay.col((sx * 1.5 - 0.1, 0, sz * 1.5 - 0.1), (sx * 1.5 + 0.1, Hd, sz * 1.5 + 0.1))
    for y0, y1 in ((0.3, 2.6), (2.6, Hd)):
        for i, (a, b) in enumerate((((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1)))):
            k0 = 1.5 - 0.3 * y0 / Hd; k1 = 1.5 - 0.3 * y1 / Hd
            steel.beam((a[0] * k0, y0, a[1] * k0), (b[0] * k1, y1, b[1] * k1), 0.05)
    deck.box((-1.6, Hd, -1.6), (1.6, Hd + 0.12, 1.6))
    lay.col((-1.6, Hd, -1.6), (1.6, Hd + 0.12, 1.6))
    for (lo, hi) in (((-1.6, Hd, -1.6), (1.6, Hd + 1.05, -1.5)), ((-1.6, Hd, 1.5), (1.6, Hd + 1.05, 1.6)),
                     ((-1.6, Hd, -1.6), (-1.5, Hd + 1.05, 1.6)), ((1.5, Hd, -1.6), (1.6, Hd + 1.05, 1.6))):
        deck.box(lo, hi)
        lay.col(lo, hi)
    for sx in (-1, 1):
        for sz in (-1, 1):
            steel.beam((sx * 1.55, Hd, sz * 1.55), (sx * 1.55, Hd + 2.3, sz * 1.55), 0.07)
    roof.hexa([(-1.9, Hd + 2.3, -1.9), (1.9, Hd + 2.3, -1.9), (1.9, Hd + 2.5, 1.9), (-1.9, Hd + 2.5, 1.9),
               (-1.9, Hd + 2.36, -1.9), (1.9, Hd + 2.36, -1.9), (1.9, Hd + 2.56, 1.9), (-1.9, Hd + 2.56, 1.9)])
    # ladder on the back
    for x in (-0.25, 0.25):
        steel.beam((x, 0, 1.75), (x, Hd + 1.0, 1.35), 0.05)
    for k in range(17):
        y = 0.3 + k * 0.3
        z = 1.75 - 0.4 * y / (Hd + 1.0)
        steel.beam((-0.25, y, z), (0.25, y, z), 0.03)
    lay.anchor('deck', (0, Hd + 0.12, 0), 180.0)
    save(m, [steel, deck, roof], out)

    m = Model('gate_booth')
    lay = Layout('gate_booth')
    conc = Part(m, 'booth_Concrete', tex_concrete(54, '#9c9a92', 1), tile=1.5, rough=0.9)
    siding = Part(m, 'booth_Siding', tex_corrugated(55, '#c9c6bb', 0.15), tile=1.0, rough=0.6, metal=0.3)
    glass = Part(m, 'booth_Glass', None, rough=0.08, color=(0.06, 0.08, 0.09))
    roofp = Part(m, 'booth_Roof', tex_paint(56, '#3a3d3c', 0.1, rivets=False), tile=1.0, rough=0.6, metal=0.3)
    conc.box((-1.4, 0, -1.2), (1.4, 0.25, 1.2))
    lay.col((-1.4, 0, -1.2), (1.4, 0.25, 1.2))
    wall_with_openings(siding, lay, 'x', -1.0, (-1.2, 1.2), 0.25, 2.6, 0.1, [(-0.9, 0.9, 1.1, 2.2)])
    wall_with_openings(siding, lay, 'x', 1.0, (-1.2, 1.2), 0.25, 2.6, 0.1, [(-0.4, 0.5, 0.25, 2.3)])
    wall_with_openings(siding, lay, 'z', -1.2, (-1.0, 1.0), 0.25, 2.6, 0.1, [(-0.7, 0.7, 1.1, 2.2)])
    wall_with_openings(siding, lay, 'z', 1.2, (-1.0, 1.0), 0.25, 2.6, 0.1, [(-0.7, 0.7, 1.1, 2.2)])
    glass.box((-0.9, 1.1, -1.01), (0.9, 2.2, -0.99))
    glass.box((-1.21, 1.1, -0.7), (-1.19, 2.2, 0.7))
    glass.box((1.19, 1.1, -0.7), (1.21, 2.2, 0.7))
    roofp.box((-1.6, 2.6, -1.4), (1.6, 2.75, 1.4))
    conc.box((-0.9, 0.25, -0.9), (0.9, 1.05, -0.6))
    lay.anchor('inside', (0, 0.25, 0.2), 180.0)
    save(m, [conc, siding, glass, roofp], out)

    m = Model('gate_leaf')  # one sliding leaf, 5 m; origin at its closing edge on the ground
    lay = Layout('gate_leaf')
    steel = Part(m, 'gate_Steel', tex_paint(57, '#6f7470', 0.15, rivets=False), tile=1.0, rough=0.5, metal=0.6)
    mesh = Part(m, 'gate_Mesh', None, rough=0.6, metal=0.6, color=(0.4, 0.42, 0.41))
    for y in (0.15, 1.2, 2.25):
        steel.box((0, y - 0.05, -0.05), (5.0, y + 0.05, 0.05))
    for x in np.linspace(0, 5.0, 6):
        steel.box((x - 0.04, 0.1, -0.05), (x + 0.04, 2.3, 0.05))
    for k in range(5):
        x0 = k
        steel.beam((x0 + 0.05, 0.2, 0), (x0 + 0.95, 2.2, 0), 0.04)
    for x in np.linspace(0.1, 4.9, 25):
        mesh.box((x - 0.006, 0.2, -0.006), (x + 0.006, 2.2, 0.006))
    lay.col((0, 0, -0.08), (5.0, 2.3, 0.08))
    save(m, [steel, mesh], out)

    m = Model('warning_sign')
    lay = Layout('warning_sign')
    face = Part(m, 'sign_Face', tex_sign('RESTRICTED AREA', 'VELLWOOD RESEARCH  SITE 4', bg='#e3dfcf', fg='#8c1c14',
                                         stripe='#2a2a2a'), tile=1.0, rough=0.6)
    post = Part(m, 'sign_Post', None, rough=0.5, metal=0.6, color=(0.3, 0.31, 0.3))
    P, N, I, UV = hexa(box_c((-0.9, 1.0, -0.02), (0.9, 1.9, 0.0)))
    UV = np.c_[(P[:, 0] + 0.9) / 1.8, 1 - (P[:, 1] - 1.0) / 0.9]
    face.mesh.add((P, N, I), (1, 1, 1), uv=UV)
    for x in (-0.7, 0.7):
        post.box((x - 0.03, 0, 0.0), (x + 0.03, 1.95, 0.05))
    lay.col((-0.9, 0, -0.05), (0.9, 1.95, 0.06))
    save(m, [face, post], out)

    m = Model('jersey_barrier')
    lay = Layout('jersey_barrier')
    conc = Part(m, 'barrier_Concrete', tex_concrete(58, '#a9a69c', 1, 0.8), tile=1.2, rough=0.9)
    prof = [(-0.3, 0), (0.3, 0), (0.25, 0.25), (0.08, 0.8), (-0.08, 0.8), (-0.25, 0.25)]
    for (a0, a1) in ((0, 1), (1, 2), (5, 0)):
        pass
    conc.hexa([(-1.5, 0, -0.3), (1.5, 0, -0.3), (1.5, 0.8, -0.08), (-1.5, 0.8, -0.08),
               (-1.5, 0, 0.3), (1.5, 0, 0.3), (1.5, 0.8, 0.08), (-1.5, 0.8, 0.08)])
    lay.col((-1.5, 0, -0.3), (1.5, 0.8, 0.3))
    save(m, [conc], out)

    m = Model('light_pole')
    lay = Layout('light_pole')
    pole = Part(m, 'pole_Steel', tex_paint(59, '#7c807e', 0.1, rivets=False), tile=1.0, rough=0.45, metal=0.7)
    lens = Part(m, 'pole_Lens', None, rough=0.2, emissive=(1.0, 0.93, 0.8), strength=6.0, color=(1, 1, 1))
    pole.raw(mk.capsule((0, 0, 0), (0, 7.5, 0), 0.11, 0.07, segs=10, rings=2))
    pole.beam((0, 7.3, 0), (0, 7.5, -1.2), 0.07)
    pole.box((-0.25, 7.3, -1.55), (0.25, 7.5, -1.0))
    lens.box((-0.22, 7.28, -1.52), (0.22, 7.3, -1.03))
    lay.col((-0.15, 0, -0.15), (0.15, 7.5, 0.15))
    lay.anchor('lamp', (0, 7.2, -1.3), 0.0)
    save(m, [pole, lens], out)


def compound(out):
    """Vellwood compound buildings: prefab site office, maintenance garage, shipping container and
    the facility portal set into the hillside (frame + two blast-door leaves)."""
    m = Model('site_office')
    lay = Layout('site_office')
    siding = Part(m, 'office_Siding', tex_corrugated(61, '#b8b9b0', 0.12), tile=1.0, rough=0.55, metal=0.3)
    base = Part(m, 'office_Base', tex_concrete(62, '#8d8b84', 1), tile=1.5, rough=0.9)
    trim = Part(m, 'office_Trim', tex_paint(63, '#2f3a44', 0.1, rivets=False), tile=1.0, rough=0.6, metal=0.3)
    glass = Part(m, 'office_Glass', None, rough=0.06, color=(0.05, 0.07, 0.09))
    floor = Part(m, 'office_Floor', tex_concrete(64, '#6f726d', 3, 0.2), tile=2.0, rough=0.8)
    W, D, F, H = 6.0, 3.0, 0.4, 3.3
    base.box((-W, 0, -D), (W, F, D))
    lay.col((-W, 0, -D), (W, F, D))
    floor.box((-W + 0.1, F, -D + 0.1), (W - 0.1, F + 0.02, D - 0.1))
    win = [(-4.8, -3.0, F + 1.0, F + 2.1), (-1.8, -0.0, F + 1.0, F + 2.1), (2.6, 4.6, F + 1.0, F + 2.1)]
    wall_with_openings(siding, lay, 'x', -D, (-W, W), F, H, 0.12, win + [(0.9, 1.9, F, F + 2.15)])
    wall_with_openings(siding, lay, 'x', D, (-W, W), F, H, 0.12, [(-3.0, -1.2, F + 1.0, F + 2.1), (1.2, 3.0, F + 1.0, F + 2.1)])
    wall_with_openings(siding, lay, 'z', -W, (-D, D), F, H, 0.12, [])
    wall_with_openings(siding, lay, 'z', W, (-D, D), F, H, 0.12, [(-0.5, 0.5, F, F + 2.15)])
    for (x0, x1, y0, y1) in win:
        glass.box((x0, y0, -D - 0.01), (x1, y1, -D + 0.01))
        trim.box((x0 - 0.05, y0 - 0.06, -D - 0.1), (x1 + 0.05, y0, -D + 0.02))
    for (x0, x1) in ((-3.0, -1.2), (1.2, 3.0)):
        glass.box((x0, F + 1.0, D - 0.01), (x1, F + 2.1, D + 0.01))
    trim.box((-W - 0.2, H, -D - 0.2), (W + 0.2, H + 0.25, D + 0.2))
    for (x0, x1) in ((0.85, 1.95),):
        trim.box((x0, F, -D - 0.08), (x0 + 0.06, F + 2.2, -D + 0.08))
        trim.box((x1 - 0.06, F, -D - 0.08), (x1, F + 2.2, -D + 0.08))
    base.box((0.4, 0, -D - 1.2), (2.4, F - 0.15, -D))
    lay.col((0.4, 0, -D - 1.2), (2.4, F - 0.15, -D))
    # desks
    for x in (-4.0, -1.0):
        trim.box((x - 0.7, F + 0.72, D - 1.0), (x + 0.7, F + 0.76, D - 0.3), color=(0.7, 0.68, 0.62))
        trim.box((x - 0.65, F, D - 0.95), (x - 0.6, F + 0.72, D - 0.35))
        trim.box((x + 0.6, F, D - 0.95), (x + 0.65, F + 0.72, D - 0.35))
        lay.col((x - 0.7, F, D - 1.0), (x + 0.7, F + 0.76, D - 0.3))
    lay.anchor('door', (1.4, F, -D - 1.0), 180.0)
    lay.anchor('desk', (-1.0, F, D - 1.4), 0.0)
    save(m, [siding, base, trim, glass, floor], out)

    m = Model('garage')
    lay = Layout('garage')
    siding = Part(m, 'garage_Siding', tex_corrugated(65, '#8a8f88', 0.3), tile=1.2, rough=0.6, metal=0.35)
    conc = Part(m, 'garage_Concrete', tex_concrete(66, '#94918a', 2), tile=2.0, rough=0.9)
    door = Part(m, 'garage_Door', tex_corrugated(67, '#4c5862', 0.1), tile=0.8, rough=0.5, metal=0.4)
    W, D, H = 7.0, 5.0, 5.0
    conc.box((-W, 0, -D), (W, 0.15, D))
    wall_with_openings(siding, lay, 'x', -D, (-W, W), 0.15, H, 0.15, [(-5.5, -1.5, 0.15, 3.9), (1.5, 5.5, 0.15, 3.9)])
    wall_with_openings(siding, lay, 'x', D, (-W, W), 0.15, H, 0.15, [])
    wall_with_openings(siding, lay, 'z', -W, (-D, D), 0.15, H, 0.15, [(1.5, 2.5, 0.15, 2.3)])
    wall_with_openings(siding, lay, 'z', W, (-D, D), 0.15, H, 0.15, [])
    gable_roof(siding, -W - 0.3, W + 0.3, -D - 0.3, D + 0.3, H - 0.1, H + 1.4, 0.06)
    gable_end(siding, -W, W, -D, H, H + 1.4, 0.15)
    gable_end(siding, -W, W, D, H, H + 1.4, 0.15)
    door.box((1.5, 2.6, -D - 0.12), (5.5, 3.9, -D - 0.04))   # right roller door half up
    door.box((-5.5, 0.15, -D - 0.12), (-1.5, 3.9, -D - 0.04))  # left roller door shut
    lay.col((-5.5, 0.15, -D - 0.12), (-1.5, 3.9, -D - 0.04))
    lay.anchor('bay', (3.5, 0.15, -D + 2.0), 0.0)
    save(m, [siding, conc, door], out)

    m = Model('container')
    lay = Layout('container')
    steel = Part(m, 'container_Steel', tex_corrugated(68, '#7a3f2c', 0.4), tile=0.9, rough=0.6, metal=0.3)
    frame = Part(m, 'container_Frame', tex_paint(69, '#5b3428', 0.25, rivets=False), tile=1.0, rough=0.6, metal=0.4)
    L, Wc, Hc = 3.05, 1.22, 2.59
    steel.box((-L, 0.05, -Wc), (L, Hc, Wc))
    for x in (-L, L):
        for z in (-Wc, Wc):
            frame.box((x - 0.08 if x > 0 else x, 0, z - 0.08 if z > 0 else z), (x if x > 0 else x + 0.08, Hc + 0.02, z if z > 0 else z + 0.08))
    lay.col((-L, 0, -Wc), (L, Hc, Wc))
    save(m, [steel, frame], out)

    m = Model('facility_portal')
    lay = Layout('facility_portal')
    conc = Part(m, 'portal_Concrete', tex_concrete(71, '#8e8d86', 2, 0.9), tile=3.0, rough=0.92)
    steel = Part(m, 'portal_Steel', tex_paint(72, '#5f6a62', 0.25), tile=1.5, rough=0.5, metal=0.6)
    sign = Part(m, 'portal_Sign', tex_sign('VELLWOOD', 'SITE 4  -  AUTHORISED ACCESS ONLY', bg='#d6d2c3', fg='#24292c'),
                tile=1.0, rough=0.6)
    lampm = Part(m, 'portal_Lamp', None, rough=0.3, emissive=(1.0, 0.6, 0.2), strength=5.0, color=(1, 0.6, 0.2))
    # massive frame (wing walls splayed into the slope), lintel, tunnel lining 12 m deep
    Wd, Hd, T = 4.0, 5.0, 1.2
    conc.box((-Wd - 3.5, 0, -0.5), (-Wd, Hd + 2.2, 0.8))
    conc.box((Wd, 0, -0.5), (Wd + 3.5, Hd + 2.2, 0.8))
    conc.box((-Wd, Hd, -0.5), (Wd, Hd + 2.2, 0.8))
    lay.col((-Wd - 3.5, 0, -0.5), (-Wd, Hd + 2.2, 0.8))
    lay.col((Wd, 0, -0.5), (Wd + 3.5, Hd + 2.2, 0.8))
    for s in (-1, 1):
        c = box_c((0, 0, 0), (0.8, Hd + 2.0, 6.0))
        c = _rot_pts(c, s * 35.0) + np.array([s * (Wd + 3.1) - (0.8 if s < 0 else 0), 0, -6.0 * 0 - 4.6])
        conc.hexa(c)
    conc.box((-Wd - 0.4, 0, 0.8), (-Wd, Hd, 12.0))
    conc.box((Wd, 0, 0.8), (Wd + 0.4, Hd, 12.0))
    conc.box((-Wd - 0.4, Hd, 0.8), (Wd + 0.4, Hd + 0.4, 12.0))
    conc.box((-Wd, -0.02, -0.5), (Wd, 0.02, 12.0), tile=2.0)
    lay.col((-Wd - 0.4, 0, 0.8), (-Wd, Hd, 12.0))
    lay.col((Wd, 0, 0.8), (Wd + 0.4, Hd, 12.0))
    lay.col((-Wd - 0.4, Hd, 0.8), (Wd + 0.4, Hd + 0.4, 12.0))
    conc.box((-Wd, 0, 11.8), (Wd, Hd, 12.2))   # inner bulkhead (the interior is a separate scene)
    lay.col((-Wd, 0, 11.8), (Wd, Hd, 12.2))
    steel.box((-Wd + 0.05, 0, 5.8), (-0.02, Hd - 0.05, 6.2))  # blast door leaves (closed)
    steel.box((0.02, 0, 5.8), (Wd - 0.05, Hd - 0.05, 6.2))
    lay.col((-Wd, 0, 5.8), (Wd, Hd, 6.2))
    for x in np.linspace(-Wd + 0.5, Wd - 0.5, 8):
        steel.box((x - 0.06, 0.2, 5.76), (x + 0.06, Hd - 0.3, 5.8))
    P, N, I, UV = hexa(box_c((-2.6, Hd + 0.55, -0.53), (2.6, Hd + 1.85, -0.51)))
    UV = np.c_[(P[:, 0] + 2.6) / 5.2, 1 - (P[:, 1] - (Hd + 0.55)) / 1.3]
    sign.mesh.add((P, N, I), (1, 1, 1), uv=UV)
    for x in (-Wd - 1.0, Wd + 1.0):
        lampm.box((x - 0.2, Hd - 0.6, -0.62), (x + 0.2, Hd - 0.4, -0.5))
    lay.anchor('door', (0, 0, 5.4), 0.0)
    lay.anchor('front', (0, 0, -4.0), 180.0)
    lay.anchor('panel', (Wd + 1.2, 1.2, -0.55), 180.0)
    save(m, [conc, steel, sign, lampm], out)

    m = Model('culvert')
    lay = Layout('culvert')
    conc = Part(m, 'culvert_Concrete', tex_concrete(73, '#8a877e', 1, 0.9), tile=1.5, rough=0.92)
    pipe = Part(m, 'culvert_Pipe', tex_corrugated(74, '#6f706a', 0.5), tile=0.6, rough=0.6, metal=0.4)
    pipe.raw(mk.loft((0, 0.6, -4.5), (0, 0.6, 4.5), [(0.0, 0.6, 0.6), (1.0, 0.6, 0.6)], segs=14, caps=False))
    for z in (-4.5, 4.5):
        conc.box((-2.2, 0, z - 0.25), (-0.65, 1.6, z + 0.25))
        conc.box((0.65, 0, z - 0.25), (2.2, 1.6, z + 0.25))
        conc.box((-0.65, 1.25, z - 0.25), (0.65, 1.6, z + 0.25))
    save(m, [conc, pipe], out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(HERE, '..', '..', 'game', 'assets'))
    a = ap.parse_args()
    for fn in (ranger_cabin, relay_mast, camp_tent, camp_props, perimeter, compound):
        fn(a.out)
    with open(os.path.join(HERE, 'structures_layout.json'), 'w') as f:
        json.dump(LAYOUT, f, indent=1)
    print('structures:', ', '.join(sorted(LAYOUT)))


if __name__ == '__main__':
    main()
