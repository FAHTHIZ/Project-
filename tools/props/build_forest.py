# SPDX-License-Identifier: Apache-2.0
"""Generate the SPECIAL OPS environment art: textures and GLB models, all procedural and original.

    python3 tools/props/build_forest.py --out game/assets

Writes into <out>/textures/env and <out>/models/env. Every output is deterministic (fixed
seeds), so regenerating produces identical bytes. Licence: Apache-2.0, see
docs/ASSET_PROVENANCE.md. No third-party art is used.

Model conventions: +Y up, metres, origin at the ground contact point. Opaque parts use vertex
colours multiplied with a tiling texture; leaf cards use alpha-tested (MASK) double-sided
materials whose PNG alpha carries the silhouette, and their normals point away from the plant
centre so canopies shade as volumes rather than as flat cards.
"""
from __future__ import annotations
import argparse, io, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'characters'))
from gltf_util import Writer, add_image  # noqa: E402
import meshkit as mk  # noqa: E402


def lin(c):
    c = np.asarray(c, float)
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def hexc(h):
    h = h.lstrip('#'); return lin([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


# ------------------------------------------------------------------------------------------------
# textures

def periodic_noise(n, seed, beta=2.0, rng=None):
    """Tileable fractal noise in [0, 1] from a power-law spectrum."""
    r = np.random.default_rng(seed)
    f = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    f[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j * r.normal(size=(n, n))) / f ** (beta / 2)
    spec[0, 0] = 0
    x = np.real(np.fft.ifft2(spec))
    x = (x - x.min()) / (x.max() - x.min())
    return x


def to_png(arr):
    b = io.BytesIO(); Image.fromarray(arr).save(b, 'PNG', optimize=True); return b.getvalue()


def tex_ground(n, seed, base, var, speck=None, streak=False):
    a = periodic_noise(n, seed, 2.2); b = periodic_noise(n, seed + 1, 1.2)
    t = 0.65 * a + 0.35 * b
    col = np.asarray(base)[None, None, :] * (1 - var) + np.asarray(base)[None, None, :] * var * 2 * t[..., None]
    if speck is not None:
        s = periodic_noise(n, seed + 2, 0.6)
        m = (s > 0.72)[..., None]
        col = np.where(m, np.asarray(speck)[None, None, :] * (0.7 + 0.6 * t[..., None]), col)
    if streak:
        s = periodic_noise(n, seed + 3, 1.0)
        s = np.roll(s, 0, 0)
        col *= (0.85 + 0.3 * s[..., None])
    rgb = np.clip(col, 0, 1)
    srgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * rgb ** (1 / 2.4) - 0.055)
    return (srgb * 255).astype(np.uint8)


def tex_bark(n=256, seed=7):
    r = np.random.default_rng(seed)
    x = periodic_noise(n, seed, 1.6)
    # vertical furrows: stretch noise along v
    f = np.fft.fftfreq(n)
    spec = (r.normal(size=(n, n)) + 1j * r.normal(size=(n, n))) / ((f[:, None] * 8) ** 2 + f[None, :] ** 2 + 1e-4) ** 0.9
    spec[0, 0] = 0
    v = np.real(np.fft.ifft2(spec)); v = (v - v.min()) / (v.max() - v.min())
    t = 0.6 * v + 0.4 * x
    t = np.clip((t - 0.2) / 0.7, 0, 1)
    rgb = np.clip(0.35 + 0.75 * t, 0, 1)
    g = (rgb ** (1 / 2.2) * 255).astype(np.uint8)
    return np.stack([g, g, g], -1)


def leaf_shape(d, cx, cy, length, width, angle, color, vein=None):
    ca, sa = np.cos(angle), np.sin(angle)
    pts = []
    for t in np.linspace(0, 1, 14):
        w = width * np.sin(np.pi * t) ** 0.8 * (1 - 0.25 * t)
        pts.append((t * length, w))
    pts += [(t * length, -w) for t, w in [(p[0] / length, p[1]) for p in reversed(pts)]]
    poly = [(cx + ca * u - sa * v, cy + sa * u + ca * v) for u, v in pts]
    d.polygon(poly, fill=color)
    if vein:
        d.line([(cx, cy), (cx + ca * length * 0.95, cy + sa * length * 0.95)], fill=vein, width=2)


def tex_leaves(n=512, seed=11, palette=('#3d5a2a', '#4f6d32', '#2f4a24', '#5b7a3a'), count=160, size=(70, 26)):
    S = n * 2
    img = Image.new('RGBA', (S, S), (60, 85, 40, 0)); d = ImageDraw.Draw(img)
    r = np.random.default_rng(seed)
    cols = [tuple(int(palette[i % len(palette)].lstrip('#')[k:k + 2], 16) for k in (0, 2, 4)) for i in range(len(palette))]
    for i in range(count):
        # gaussian cluster so edges are ragged and the centre dense
        cx, cy = r.normal(S / 2, S * 0.2, 2)
        if not (0.08 * S < cx < 0.92 * S and 0.08 * S < cy < 0.92 * S): continue
        ang = r.uniform(0, 2 * np.pi)
        L = r.uniform(0.7, 1.3) * size[0] * S / 1024; W = L * size[1] / size[0]
        c = cols[r.integers(len(cols))]; k = r.uniform(0.75, 1.15)
        col = tuple(int(np.clip(v * k, 0, 255)) for v in c) + (255,)
        vein = tuple(int(np.clip(v * k * 1.25, 0, 255)) for v in c) + (255,)
        leaf_shape(d, cx, cy, L, W / 2, ang, col, vein)
    # thin twigs
    for i in range(10):
        a = r.uniform(0, 2 * np.pi); l = r.uniform(0.2, 0.4) * S
        d.line([(S / 2, S / 2), (S / 2 + np.cos(a) * l, S / 2 + np.sin(a) * l)], fill=(70, 55, 40, 255), width=4)
    img = img.resize((n, n), Image.LANCZOS)
    a = np.array(img); a[..., 3] = np.where(a[..., 3] > 110, 255, 0)
    return dilate_rgb(a)


def dilate_rgb(a, it=6):
    """Bleed opaque colours into transparent texels so mips do not pick up a dark fringe."""
    rgb = a[..., :3].astype(float); m = (a[..., 3] > 0).astype(float)
    for _ in range(it):
        s = np.zeros_like(rgb); c = np.zeros_like(m)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            s += np.roll(np.roll(rgb * m[..., None], dy, 0), dx, 1); c += np.roll(np.roll(m, dy, 0), dx, 1)
        fill = (m == 0) & (c > 0)
        rgb[fill] = s[fill] / c[fill][:, None]; m = np.where(fill, 1.0, m)
    a = a.copy(); a[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    return a


def tex_fern(n=512, seed=21):
    """A single fern frond, base at the bottom (v=1), tip at the top (v=0)."""
    W, H = n, n * 2
    img = Image.new('RGBA', (W, H), (70, 100, 45, 0)); d = ImageDraw.Draw(img)
    r = np.random.default_rng(seed)
    cx = W / 2
    pinnae = 26
    for i in range(pinnae):
        t = (i + 0.5) / pinnae  # 0 base .. 1 tip
        y = H * (0.97 - 0.93 * t)
        L = W * 0.46 * np.sin(np.pi * (0.12 + 0.88 * t)) ** 0.9 * (1.05 - 0.55 * t)
        for side in (-1, 1):
            ang = np.pi / 2 + side * (np.pi / 2 - 0.55) - np.pi / 2
            ang = -np.pi / 2 + side * 1.05  # angled toward the tip
            ang = (np.pi if side < 0 else 0) + side * -0.42
            base = (cx, y)
            # each pinna is a row of small rounded lobes
            lobes = 9
            for k in range(lobes):
                u = (k + 0.5) / lobes
                px = base[0] + np.cos(ang) * L * u; py = base[1] + np.sin(ang) * L * u
                rr = W * 0.022 * (1 - 0.6 * u) * (1.1 - 0.5 * t)
                g = int(95 + 40 * r.random() + 30 * t); col = (int(55 + 20 * r.random()), g, int(35 + 10 * r.random()), 255)
                d.ellipse([px - rr * 1.3, py - rr, px + rr * 1.3, py + rr], fill=col)
            d.line([base, (base[0] + np.cos(ang) * L, base[1] + np.sin(ang) * L)], fill=(80, 110, 50, 255), width=3)
    d.line([(cx, H * 0.995), (cx, H * 0.03)], fill=(90, 105, 55, 255), width=6)
    a = np.array(img.resize((n // 2, n), Image.LANCZOS)); a[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    return dilate_rgb(a)


def tex_grass(n=256, seed=31):
    S = n * 2
    img = Image.new('RGBA', (S, S), (90, 110, 50, 0)); d = ImageDraw.Draw(img)
    r = np.random.default_rng(seed)
    for i in range(70):
        x0 = r.uniform(0.1, 0.9) * S; h = r.uniform(0.45, 0.97) * S; lean = r.normal(0, 0.12) * S
        w = r.uniform(5, 10) * S / 512
        g = int(r.uniform(85, 140)); col = (int(g * 0.62), g, int(g * 0.38), 255)
        pts = [(x0 - w, S), (x0 + lean * 0.5 - w * 0.4, S - h * 0.6), (x0 + lean, S - h), (x0 + lean * 0.5 + w * 0.4, S - h * 0.6), (x0 + w, S)]
        d.polygon(pts, fill=col)
    a = np.array(img.resize((n, n), Image.LANCZOS)); a[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    return dilate_rgb(a)


def tex_needles(n=512, seed=41):
    """Conifer spray atlas: five drooping boughs. Each bough is a dense fan of needle tufts over
    a darker inner mass (real spruce/fir sprays read as solid shapes with a needled fringe;
    single-pixel needles alone dissolve into hair at distance, as the first version did)."""
    S = n * 2
    img = Image.new('RGBA', (S, S), (34, 52, 34, 0)); d = ImageDraw.Draw(img)
    r = np.random.default_rng(seed)
    for b in range(5):
        y = S * (0.12 + 0.19 * b); x0 = S * 0.04
        ts = np.linspace(0, 1, 44)
        pts = [(x0 + (S * 0.92) * t, y + np.sin(t * 3) * S * 0.025) for t in ts]
        # inner mass: overlapping ellipses that taper toward the tip
        for (x, yy), t in zip(pts, ts):
            w = S * 0.055 * (1.15 - 0.75 * t)
            g = int(r.uniform(40, 58))
            d.ellipse([x - w * 0.8, yy - w * 0.75, x + w * 0.8, yy + w * 0.75],
                      fill=(int(g * 0.6), g, int(g * 0.55), 255))
        # needle tufts (both sides, angled forward) and side twigs
        for (x, yy), t in zip(pts, ts):
            for side in (-1, 1):
                for k in range(6):
                    l = S * 0.085 * (1.15 - 0.6 * t) * r.uniform(0.6, 1.2)
                    a = side * r.uniform(0.5, 1.35)
                    g = int(r.uniform(62, 112))
                    d.line([(x, yy), (x + np.cos(a) * l * 0.45, yy + np.sin(a) * l)],
                           fill=(int(g * 0.55), g, int(g * 0.5), 255), width=5)
        d.line(pts, fill=(66, 52, 38, 255), width=6)
    a = np.array(img.resize((n, n), Image.LANCZOS)); a[..., 3] = np.where(a[..., 3] > 96, 255, 0)
    return dilate_rgb(a)


def tex_chainlink(n=256):
    S = n * 2
    img = Image.new('RGBA', (S, S), (150, 150, 145, 0)); d = ImageDraw.Draw(img)
    k = 8; step = S / k
    for i in range(-1, k + 1):
        for j in range(-1, k + 1):
            cx, cy = i * step, j * step
            d.line([(cx, cy - step / 2), (cx + step / 2, cy), (cx, cy + step / 2), (cx - step / 2, cy), (cx, cy - step / 2)],
                   fill=(160, 162, 158, 255), width=6)
    a = np.array(img.resize((n, n), Image.LANCZOS)); a[..., 3] = np.where(a[..., 3] > 90, 255, 0)
    return dilate_rgb(a)


def tex_sign(n=256, seed=51):
    """Weathered wooden sign board face (planks, faded painted arrow and band; no text)."""
    r = np.random.default_rng(seed)
    w = periodic_noise(n, seed, 1.4)
    planks = (np.arange(n)[:, None] // (n // 4)) % 2
    base = np.array([0.42, 0.31, 0.2])[None, None, :] * (0.8 + 0.4 * w[..., None]) * (0.93 + 0.07 * planks[..., None])
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)); d = ImageDraw.Draw(img)
    d.rectangle([0, n * 0.08, n, n * 0.2], fill=(196, 150, 60))
    d.polygon([(n * 0.15, n * 0.55), (n * 0.62, n * 0.55), (n * 0.62, n * 0.42), (n * 0.88, n * 0.62), (n * 0.62, n * 0.82),
               (n * 0.62, n * 0.69), (n * 0.15, n * 0.69)], fill=(225, 220, 200))
    for y in (n // 4, n // 2, 3 * n // 4):
        d.line([(0, y), (n, y)], fill=(60, 42, 28), width=2)
    a = np.array(img).astype(float)
    wear = periodic_noise(n, seed + 5, 1.0)[..., None]
    a = a * (0.75 + 0.35 * wear)
    return np.clip(a, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------------------------------------
# geometry helpers

def frame_along(pts):
    T = np.gradient(pts, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.array([1.0, 0, 0]) if abs(T[0, 1]) > 0.9 else np.array([0, 1.0, 0])
    Ns, Bs = [], []
    n = np.cross(T[0], up); n /= np.linalg.norm(n)
    for t in T:
        n = n - t * np.dot(n, t); n /= np.linalg.norm(n)
        Ns.append(n); Bs.append(np.cross(t, n))
    return T, np.array(Ns), np.array(Bs)


def tube(pts, radii, segs=8, cap_end=True, noise=0.0, seed=0, v_scale=1.0):
    pts = np.asarray(pts, float); T, Nn, B = frame_along(pts)
    r = np.random.default_rng(seed)
    P, N, UV = [], [], []
    vlen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    for i, (p, rad) in enumerate(zip(pts, radii)):
        for k in range(segs + 1):
            a = 2 * np.pi * k / segs
            d = np.cos(a) * Nn[i] + np.sin(a) * B[i]
            rr = rad * (1 + noise * (np.sin(a * 3 + i * 1.7 + seed) * 0.5 + r.normal() * 0.3))
            P.append(p + d * rr); N.append(d); UV.append((k / segs, vlen[i] * v_scale / max(rad * 6.283, 1e-3)))
    I = []
    for i in range(len(pts) - 1):
        for k in range(segs):
            a = i * (segs + 1) + k; b = a + segs + 1
            I += [a, b, a + 1, a + 1, b, b + 1]
    P, N, UV = np.array(P), np.array(N), np.array(UV)
    if cap_end:
        c = len(P); P = np.r_[P, [pts[-1]]]; N = np.r_[N, [T[-1]]]; UV = np.r_[UV, [(0.5, UV[-1, 1])]]
        base = (len(pts) - 1) * (segs + 1)
        for k in range(segs): I += [base + k, base + k + 1, c]
    return P, N, np.array(I, np.uint32), UV


def card(center, normal_hint, size, rot, uv=(0, 0, 1, 1)):
    """One quad with the given rotation matrix; normals set later."""
    w, h = size
    loc = np.array([[-w / 2, -h / 2, 0], [w / 2, -h / 2, 0], [w / 2, h / 2, 0], [-w / 2, h / 2, 0]])
    P = loc @ rot.T + center
    u0, v0, u1, v1 = uv
    UV = np.array([[u0, v1], [u1, v1], [u1, v0], [u0, v0]])
    return P, UV


def rot_axis(axis, ang):
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * K @ K


class Leaves:
    """Accumulates alpha cards with volume normals."""
    def __init__(self): self.P, self.N, self.UV, self.C, self.I, self.n = [], [], [], [], [], 0
    def add_card(self, P, UV, normals, color):
        self.P.append(P); self.UV.append(UV); self.N.append(normals)
        self.C.append(np.tile(list(color) + [1], (len(P), 1)))
        self.I.append(np.array([0, 1, 2, 0, 2, 3]) + self.n); self.n += len(P)
    def add_strip(self, P, UV, normals, color, cols):
        rows = len(P) // cols
        self.P.append(P); self.UV.append(UV); self.N.append(normals)
        self.C.append(np.tile(list(color) + [1], (len(P), 1)) if np.ndim(color) == 1 else color)
        I = []
        for r_ in range(rows - 1):
            for c in range(cols - 1):
                a = r_ * cols + c; b = a + cols
                I += [a, b, a + 1, a + 1, b, b + 1]
        self.I.append(np.array(I) + self.n); self.n += len(P)
    def arrays(self):
        if not self.P: return None
        N = np.concatenate(self.N).astype(float); N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
        return (np.concatenate(self.P).astype(np.float32), N.astype(np.float32), np.concatenate(self.C).astype(np.float32),
                np.concatenate(self.I).astype(np.uint32), np.concatenate(self.UV).astype(np.float32))


def cluster(leaves, center, radius, tree_center, rng, color, n_cards=3, card_size=1.6, up_bias=0.4):
    """Three crossed cards at `center`; normals blend from the canopy centre outward."""
    base = rot_axis((0, 1, 0), rng.uniform(0, np.pi))
    tilt = rot_axis((1, 0, 0), rng.uniform(-0.6, 0.6))
    for k in range(n_cards):
        R = base @ rot_axis((0, 1, 0), k * np.pi / n_cards) @ tilt
        if k == n_cards - 1:
            R = base @ rot_axis((1, 0, 0), np.pi / 2 + rng.uniform(-0.3, 0.3))
        s = card_size * rng.uniform(0.8, 1.2)
        P, UV = card(center, None, (s, s), R)
        nrm = P - tree_center; nrm[:, 1] += up_bias * np.linalg.norm(nrm, axis=1)
        k2 = rng.uniform(0.85, 1.12)
        leaves.add_card(P, UV, nrm, np.clip(np.asarray(color) * k2, 0, 1))


# ------------------------------------------------------------------------------------------------
# models

class Model:
    def __init__(self, name):
        self.name = name; self.j = {'asset': {'version': '2.0', 'generator': 'SPECIAL OPS build_forest.py'},
                                    'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': name, 'mesh': 0}],
                                    'meshes': [{'name': name, 'primitives': []}], 'materials': []}
        self.w = Writer(self.j); self.textures = {}
    def texture(self, key, png):
        if key not in self.textures: self.textures[key] = add_image(self.w, png, key)
        return self.textures[key]
    def material(self, name, tex=None, rough=0.85, mask=False, double=False, metal=0.0, emissive=None, strength=1.0, color=(1, 1, 1, 1)):
        m = {'name': name, 'pbrMetallicRoughness': {'baseColorFactor': list(color), 'metallicFactor': metal, 'roughnessFactor': rough}}
        if tex is not None: m['pbrMetallicRoughness']['baseColorTexture'] = {'index': tex}
        if mask: m['alphaMode'] = 'MASK'; m['alphaCutoff'] = 0.5
        if double: m['doubleSided'] = True
        if emissive is not None:
            m['emissiveFactor'] = list(emissive)
            if strength != 1.0:
                m['extensions'] = {'KHR_materials_emissive_strength': {'emissiveStrength': strength}}
                self.j.setdefault('extensionsUsed', [])
                if 'KHR_materials_emissive_strength' not in self.j['extensionsUsed']:
                    self.j['extensionsUsed'].append('KHR_materials_emissive_strength')
        self.j['materials'].append(m); return len(self.j['materials']) - 1
    def prim(self, P, N, C, I, UV, mat):
        w = self.w
        m = self.j['materials'][mat]
        if m.get('doubleSided') and m.get('alphaMode') == 'MASK':
            # Cutout cards carry up-biased "foliage" normals so both sides light like the plant
            # mass. glTF double-sided rendering flips the normal on back faces (VICTUS pbr.frag
            # does), which turns those faces black; emit explicit back faces with the same
            # normals instead and render single-sided.
            # The back copy gets its own vertices: sharing them would make every card edge
            # non-manifold and the importer's LOD simplifier would collapse the cards.
            I = np.asarray(I).reshape(-1, 3)
            nv = len(P)
            P, N, C, UV = (np.vstack([a, a]) for a in (np.asarray(P), np.asarray(N), np.asarray(C), np.asarray(UV)))
            I = np.vstack([I, I[:, ::-1] + nv]).ravel()
            m.pop('doubleSided')
        self.j['meshes'][0]['primitives'].append({'attributes': {
            'POSITION': w.add(P.astype(np.float32), 'VEC3', 34962, True), 'NORMAL': w.add(N.astype(np.float32), 'VEC3', 34962),
            'TEXCOORD_0': w.add(UV.astype(np.float32), 'VEC2', 34962), 'COLOR_0': w.add(C.astype(np.float32), 'VEC4', 34962)},
            'indices': w.add(I.astype(np.uint32), 'SCALAR', 34963), 'material': mat})
        return len(I) // 3
    def solid(self, mesh, mat):
        P, N, C, T, I, UV = mesh.arrays(); return self.prim(P, N, C, I, UV, mat)
    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True); self.w.save(path)


def solid_from_tube(m, t, color):
    P, N, I, UV = t
    m.P.append(P); m.N.append(N); m.UV.append(UV)
    col = np.asarray(color, float)
    m.C.append(np.c_[col, np.ones(len(P))] if col.ndim == 2 else np.tile(list(col) + [1], (len(P), 1)))
    m.T.append(np.zeros(len(P))); m.I.append(fix_or(I, P, N) + m.n); m.n += len(P)


def fix_or(I, P, N):
    return mk.fix_winding(P, N, I)


def branch_curve(start, direction, length, droop, n=6, rng=None):
    pts = []
    d = np.asarray(direction, float); d /= np.linalg.norm(d)
    for t in np.linspace(0, 1, n):
        p = np.asarray(start) + d * length * t
        p[1] -= droop * length * t * t
        if rng is not None and 0 < t < 1: p += rng.normal(0, 0.04 * length, 3)
        pts.append(p)
    return np.array(pts)


def build_broadleaf_tree(name, seed, height, trunk_r, canopy, textures, lean=0.0, bare_lower=0.45):
    """Deciduous woodland tree: curved trunk, 5-8 limbs, leaf-cluster canopy."""
    r = np.random.default_rng(seed)
    m = Model(name)
    bark = m.texture('bark', textures['bark']); leaf = m.texture('leaves', textures['leaves'])
    mb = m.material(name + '_Bark', bark, 0.92); ml = m.material(name + '_Leaves', leaf, 0.75, mask=True, double=True)
    body = mk.Mesh()
    n = 9; ys = np.linspace(0, height * 0.82, n)
    lean_dir = np.array([np.cos(seed), 0, np.sin(seed)])
    trunk = np.array([[0, y, 0] + lean_dir * lean * (y / height) ** 1.6 + r.normal(0, 0.03, 3) * (i > 0) for i, y in enumerate(ys)])
    trunk[:, 1] = ys
    radii = trunk_r * (1.0 - 0.72 * (ys / ys[-1]) ** 0.9)
    radii[0] *= 1.45; radii[1] *= 1.12  # root flare
    bark_col = np.array([0.20, 0.16, 0.12])
    solid_from_tube(body, tube(trunk, radii, 12, True, 0.06, seed, 1.0), bark_col)
    # roots
    for k in range(4):
        a = k * np.pi / 2 + r.uniform(-0.4, 0.4)
        d = np.array([np.cos(a), -0.15, np.sin(a)])
        pts = branch_curve(np.array([0, 0.25, 0]), d, trunk_r * 3.2, 0.25, 4, r)
        solid_from_tube(body, tube(pts, np.linspace(trunk_r * 0.45, trunk_r * 0.12, len(pts)), 6, True, 0.05, seed + k), bark_col * 0.9)
    leaves = Leaves()
    canopy_c = np.array([0, height * 0.75, 0]) + lean_dir * lean * 0.8
    leaf_col = np.array([1.0, 1.0, 1.0])
    limbs = r.integers(5, 9)
    for b in range(limbs):
        t0 = bare_lower + (1 - bare_lower) * 0.85 * (b + r.uniform(0, 0.8)) / limbs
        i0 = min(n - 2, int(t0 * (n - 1)))
        start = trunk[i0]
        a = b * 2.4 + r.uniform(-0.3, 0.3)
        d = np.array([np.cos(a), r.uniform(0.35, 0.9), np.sin(a)])
        L = canopy * r.uniform(0.55, 0.9)
        pts = branch_curve(start, d, L, 0.15, 6, r)
        solid_from_tube(body, tube(pts, np.linspace(radii[i0] * 0.55, 0.02, len(pts)), 7, True, 0.05, seed + 10 + b), bark_col)
        # twigs and leaf clusters along the outer half
        for k in range(2, len(pts)):
            for _ in range(2):
                c = pts[k] + r.normal(0, canopy * 0.18, 3); c[1] += canopy * 0.1
                cluster(leaves, c, 0.5, canopy_c, r, leaf_col, 3, canopy * r.uniform(0.38, 0.55))
    # fill the crown top
    for _ in range(int(30 + canopy * 9)):  # crown fill: woodland crowns read as masses, not twigs
        u = r.normal(size=3); u /= np.linalg.norm(u); u[1] = abs(u[1]) * 0.8 + 0.1
        c = canopy_c + u * canopy * r.uniform(0.35, 0.95) * np.array([1, 0.7, 1])
        cluster(leaves, c, 0.5, canopy_c, r, leaf_col, 3, canopy * r.uniform(0.4, 0.6))
    tb = m.solid(body, mb)
    P, N, C, I, UV = leaves.arrays(); tl = m.prim(P, N, C, I, UV, ml)
    return m, tb + tl


def build_conifer(name, seed, height, trunk_r, textures):
    r = np.random.default_rng(seed)
    m = Model(name)
    bark = m.texture('bark', textures['bark']); nd = m.texture('needles', textures['needles'])
    mb = m.material(name + '_Bark', bark, 0.92); ml = m.material(name + '_Needles', nd, 0.8, mask=True, double=True)
    body = mk.Mesh()
    ys = np.linspace(0, height, 8)
    trunk = np.c_[r.normal(0, 0.02, 8), ys, r.normal(0, 0.02, 8)]; trunk[0, [0, 2]] = 0
    radii = trunk_r * (1 - 0.92 * ys / height); radii[0] *= 1.3
    solid_from_tube(body, tube(trunk, radii, 10, True, 0.05, seed), np.array([0.19, 0.14, 0.11]))
    leaves = Leaves()
    tiers = int(height / 0.55)
    for t in range(tiers):
        h = height * (0.22 + 0.78 * t / tiers)
        spread = (height - h) * 0.42 + 0.25
        for b in range(int(5 + spread * 2)):
            a = b * 2.39996 + t * 0.7 + r.uniform(-0.2, 0.2)
            d = np.array([np.cos(a), -0.25, np.sin(a)])
            start = np.array([0, h, 0])
            end = start + d * spread
            mid = (start + end) / 2
            L = spread * 1.15; W = max(0.5, spread * 0.65)
            # bough card lying along the branch, tilted down
            R = rot_axis((0, 1, 0), -a) @ rot_axis((1, 0, 0), -np.pi / 2 + 0.35 + r.uniform(-0.15, 0.15))
            loc = np.array([[0, -W / 2, 0], [L, -W / 2, 0], [L, W / 2, 0], [0, W / 2, 0]])
            Rr = rot_axis((0, 1, 0), -a)
            loc2 = np.array([[0, 0, -W / 2], [L, -L * 0.25, -W / 2], [L, -L * 0.25, W / 2], [0, 0, W / 2]])
            P = loc2 @ Rr.T + start
            UV = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
            nrm = P - np.array([0, h - 0.4, 0])
            leaves.add_card(P, UV, nrm, np.clip(np.ones(3) * r.uniform(0.85, 1.1), 0, 1))
            if spread > 0.8:
                Rv = rot_axis((0, 1, 0), -a) @ rot_axis((1, 0, 0), np.pi / 2)
                loc3 = np.array([[0, -W * 0.4, 0], [L * 0.9, -W * 0.4 - L * 0.22, 0], [L * 0.9, W * 0.4 - L * 0.22, 0], [0, W * 0.4, 0]])
                P = loc3 @ Rr.T + start
                leaves.add_card(P, UV, P - np.array([0, h - 0.4, 0]), np.clip(np.ones(3) * r.uniform(0.8, 1.05), 0, 1))
    tb = m.solid(body, mb)
    P, N, C, I, UV = leaves.arrays(); tl = m.prim(P, N, C, I, UV, ml)
    return m, tb + tl


def build_fern(name, seed, size, textures, fronds=12):
    r = np.random.default_rng(seed)
    m = Model(name)
    tx = m.texture('fern', textures['fern'])
    ml = m.material(name + '_Fronds', tx, 0.7, mask=True, double=True)
    leaves = Leaves()
    for f in range(fronds):
        a = f * 2 * np.pi / fronds + r.uniform(-0.2, 0.2)
        L = size * r.uniform(0.7, 1.15); W = L * 0.42
        rise = r.uniform(0.5, 1.0)
        rows = 8
        d = np.array([np.cos(a), 0, np.sin(a)]); side = np.array([-np.sin(a), 0, np.cos(a)])
        P, UV, Nn = [], [], []
        twist = r.uniform(-0.25, 0.25)
        for i in range(rows):
            t = i / (rows - 1)
            # arch: rises then droops
            pos = d * L * t * 0.95 + np.array([0, L * (rise * np.sin(t * np.pi * 0.75) * 0.75 - 0.25 * t * t), 0])
            wv = side * np.cos(twist * t) + np.array([0, np.sin(twist * t), 0])
            for c in range(2):
                s = (c - 0.5) * W
                P.append(pos + wv * s); UV.append((c, 1 - t))
                up = np.array([0, 1, 0]) * 0.8 + d * 0.3; Nn.append(up)
        k = r.uniform(0.85, 1.12)
        leaves.add_strip(np.array(P), np.array(UV), np.array(Nn), np.clip(np.ones(3) * k, 0, 1), 2)
    P, N, C, I, UV = leaves.arrays(); t = m.prim(P, N, C, I, UV, ml)
    return m, t


def build_shrub(name, seed, radius, textures, height=None):
    r = np.random.default_rng(seed)
    m = Model(name)
    tx = m.texture('leaves', textures['leaves'])
    ml = m.material(name + '_Leaves', tx, 0.75, mask=True, double=True)
    leaves = Leaves(); height = height or radius * 1.1
    c0 = np.array([0, height * 0.45, 0])
    for _ in range(int(10 + radius * 14)):
        u = r.normal(size=3); u /= np.linalg.norm(u); u[1] = abs(u[1])
        c = c0 + u * np.array([radius, height * 0.55, radius]) * r.uniform(0.3, 0.95)
        cluster(leaves, c, 0.4, c0 - np.array([0, height * 0.3, 0]), r, np.ones(3), 3, radius * r.uniform(0.7, 1.0))
    P, N, C, I, UV = leaves.arrays(); t = m.prim(P, N, C, I, UV, ml)
    return m, t


def build_grass(name, seed, textures, size=0.6):
    r = np.random.default_rng(seed)
    m = Model(name)
    tx = m.texture('grass', textures['grass'])
    ml = m.material(name + '_Blades', tx, 0.8, mask=True, double=True)
    leaves = Leaves()
    for k in range(3):
        a = k * np.pi / 3 + r.uniform(-0.2, 0.2)
        R = rot_axis((0, 1, 0), a)
        w, h = size * r.uniform(0.9, 1.2), size * r.uniform(0.8, 1.1)
        loc = np.array([[-w / 2, 0, 0], [w / 2, 0, 0], [w / 2, h, 0], [-w / 2, h, 0]])
        P = loc @ R.T
        UV = np.array([[0, 1], [1, 1], [1, 0], [0, 0]])
        leaves.add_card(P, UV, np.tile([0, 1, 0.2], (4, 1)), np.clip(np.ones(3) * r.uniform(0.85, 1.1), 0, 1))
    P, N, C, I, UV = leaves.arrays(); t = m.prim(P, N, C, I, UV, ml)
    return m, t


def rock_mesh(seed, size, moss=True):
    r = np.random.default_rng(seed)
    P, N, I = mk.ellipsoid((0, 0, 0), (1, 1, 1), 16, 11)
    # low-frequency lumps + flattened base
    k = np.zeros(len(P))
    for _ in range(6):
        d = r.normal(size=3); d /= np.linalg.norm(d)
        k += r.uniform(0.05, 0.18) * np.clip(P @ d, 0, 1) ** 3
    P = P * (1 + k)[:, None] * np.array(size)
    P[:, 1] = np.where(P[:, 1] < -size[1] * 0.4, -size[1] * 0.4, P[:, 1])
    P[:, 1] += size[1] * 0.35
    # recompute normals
    I3 = I.reshape(-1, 3); fn = np.cross(P[I3[:, 1]] - P[I3[:, 0]], P[I3[:, 2]] - P[I3[:, 0]])
    Nn = np.zeros_like(P)
    for c in range(3): np.add.at(Nn, I3[:, c], fn)
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True) + 1e-9
    stone = np.array([0.30, 0.30, 0.28]); mossc = np.array([0.16, 0.24, 0.09])
    w = np.clip(Nn[:, 1] * 1.4 - 0.3, 0, 1) if moss else np.zeros(len(P))
    C = stone[None] * (1 - w[:, None]) + mossc[None] * w[:, None]
    C *= (0.85 + 0.3 * r.random(len(P)))[:, None]
    UV = np.c_[P[:, 0] + P[:, 2], P[:, 1]] * 0.8
    return P, Nn, C, I, UV


def build_rock(name, seed, size, textures):
    m = Model(name)
    tx = m.texture('rock', textures['rock'])
    mt = m.material(name + '_Stone', tx, 0.9)
    P, N, C, I, UV = rock_mesh(seed, size)
    t = m.prim(P, N, np.c_[C, np.ones(len(C))], mk.fix_winding(P, N, I), UV, mt)
    return m, t


def build_log(name, seed, length, radius, textures):
    r = np.random.default_rng(seed)
    m = Model(name)
    bark = m.texture('bark', textures['bark']); mb = m.material(name + '_Bark', bark, 0.95)
    body = mk.Mesh()
    xs = np.linspace(-length / 2, length / 2, 9)
    pts = np.c_[xs, radius * 0.85 + r.normal(0, 0.02, 9), r.normal(0, 0.05, 9)]
    rad = radius * (1 - 0.15 * np.abs(xs) / length)
    col = np.array([0.17, 0.14, 0.1])
    solid_from_tube(body, tube(pts, rad, 12, True, 0.07, seed), col)
    solid_from_tube(body, tube(pts[::-1], rad[::-1], 12, True, 0.07, seed + 1), col)  # caps both ends
    # moss band on top
    top = pts.copy(); top[:, 1] += rad * 0.55
    solid_from_tube(body, tube(top[1:-1], rad[1:-1] * 0.55, 8, False, 0.12, seed + 2), np.array([0.14, 0.22, 0.08]))
    # broken stub branch
    stub = branch_curve(pts[3], np.array([0.2, 0.9, 0.3]), radius * 3, 0.1, 4, r)
    solid_from_tube(body, tube(stub, np.linspace(radius * 0.3, radius * 0.12, 4), 6, True, 0.05, seed + 3), col)
    t = m.solid(body, mb)
    return m, t


def build_stump(name, seed, radius, textures):
    m = Model(name)
    bark = m.texture('bark', textures['bark']); mb = m.material(name + '_Bark', bark, 0.95)
    body = mk.Mesh()
    pts = np.array([[0, 0, 0], [0, 0.15, 0], [0, 0.4, 0], [0, 0.55, 0]])
    solid_from_tube(body, tube(pts, [radius * 1.5, radius * 1.1, radius, radius * 0.98], 12, True, 0.1, seed), np.array([0.18, 0.14, 0.1]))
    body.add(mk.loft((0, 0.55, 0), (0, 0.565, 0), [(0, radius * 0.93, radius * 0.93), (1, radius * 0.9, radius * 0.9)], 16),
             (0.45, 0.33, 0.2))
    t = m.solid(body, mb)
    return m, t


def build_trail_marker(name, textures):
    m = Model(name)
    tx = m.texture('bark', textures['bark']); mw = m.material(name + '_Wood', tx, 0.85)
    paint = m.material(name + '_Paint', None, 0.6, color=(1, 1, 1, 1))
    wood = mk.Mesh(); pm = mk.Mesh()
    wood.add(mk.rounded_box((0, 0.6, 0), (0.06, 0.6, 0.06), 0.2), (0.32, 0.24, 0.16))
    wood.add(mk.rounded_box((0, 1.21, 0), (0.065, 0.015, 0.065), 0.4), (0.25, 0.19, 0.13))
    pm.add(mk.rounded_box((0, 1.05, 0), (0.063, 0.07, 0.063), 0.2), hexc('#c8691f'))
    pm.add(mk.rounded_box((0, 0.85, 0.064), (0.04, 0.05, 0.004), 0.3), hexc('#d8d4c6'))
    return m, m.solid(wood, mw) + m.solid(pm, paint)


def build_sign(name, textures):
    m = Model(name)
    bk = m.texture('bark', textures['bark']); st = m.texture('sign', textures['sign'])
    mw = m.material(name + '_Posts', bk, 0.9); ms = m.material(name + '_Board', st, 0.8)
    posts = mk.Mesh()
    for sx in (-0.55, 0.55):
        posts.add(mk.rounded_box((sx, 0.75, -0.02), (0.05, 0.75, 0.05), 0.2), (0.3, 0.23, 0.16))
    # board: front face with sign texture UVs
    board = mk.Mesh()
    P, N, I = mk.rounded_box((0, 1.15, 0.04), (0.65, 0.3, 0.025), 0.15)
    UV = np.c_[(P[:, 0] + 0.65) / 1.3, 1 - (P[:, 1] - 0.85) / 0.6]
    board.add((P, N, I), (1, 1, 1), uv=UV)
    return m, m.solid(posts, mw) + m.solid(board, ms)


def build_sensor_post(name, textures):
    """A weathered environmental monitoring box on a pole: perimeter hint (stage 01 end, stage 02)."""
    m = Model(name)
    metal = m.material(name + '_Metal', None, 0.55, metal=0.6)
    glow = m.material(name + '_Lamp', None, 0.3, emissive=(1.0, 0.55, 0.15), strength=6.0)
    a = mk.Mesh(); g = mk.Mesh()
    a.add(mk.capsule((0, 0, 0), (0, 1.9, 0), 0.04, 0.035), (0.35, 0.36, 0.34))
    a.add(mk.rounded_box((0, 1.45, 0.09), (0.16, 0.2, 0.08), 0.25), (0.42, 0.45, 0.4))
    a.add(mk.rounded_box((0, 1.67, 0.1), (0.19, 0.02, 0.1), 0.4), (0.3, 0.32, 0.3))
    a.add(mk.rounded_box((0, 1.4, 0.172), (0.1, 0.07, 0.006), 0.3), (0.08, 0.09, 0.09))
    a.add(mk.capsule((0.12, 1.68, 0.05), (0.14, 2.1, 0.05), 0.008, 0.005), (0.2, 0.2, 0.2))
    a.add(mk.rounded_box((0, 0.02, 0), (0.18, 0.02, 0.18), 0.3), (0.4, 0.4, 0.38))
    g.add(mk.ellipsoid((0.1, 1.58, 0.172), (0.015, 0.015, 0.008)), (1, 0.6, 0.2))
    return m, m.solid(a, metal) + m.solid(g, glow)


def build_backpack(name, textures):
    m = Model(name)
    cloth = m.material(name + '_Cloth', None, 0.85)
    a = mk.Mesh()
    a.add(mk.rounded_box((0, 0.2, 0), (0.17, 0.2, 0.11), 0.55, rot=mk.rot_x(-70)), hexc('#7a4a2a'))
    a.add(mk.rounded_box((0, 0.13, 0.17), (0.12, 0.08, 0.05), 0.5, rot=mk.rot_x(-70)), hexc('#5e3a22'))
    a.add(mk.rounded_box((0.0, 0.1, -0.12), (0.15, 0.03, 0.04), 0.5), hexc('#2a2d30'))
    a.add(mk.capsule((-0.25, 0.06, 0.05), (0.25, 0.07, -0.02), 0.06, 0.06), hexc('#3a5a3a'))  # bedroll
    return m, m.solid(a, cloth)


def build_fence(name, textures, length=4.0, height=2.4):
    """Chain-link fence panel with posts and top rail (stage 02 perimeter)."""
    m = Model(name)
    cl = m.texture('chainlink', textures['chainlink'])
    metal = m.material(name + '_Posts', None, 0.5, metal=0.8)
    mesh_mat = m.material(name + '_Mesh', cl, 0.5, mask=True, double=True, metal=0.7)
    a = mk.Mesh()
    for x in (-length / 2, length / 2):
        a.add(mk.capsule((x, 0, 0), (x, height, 0), 0.035, 0.035), (0.55, 0.56, 0.55))
    a.add(mk.capsule((-length / 2, height - 0.05, 0), (length / 2, height - 0.05, 0), 0.022, 0.022), (0.55, 0.56, 0.55))
    leaves = Leaves()
    P = np.array([[-length / 2, 0.03, 0], [length / 2, 0.03, 0], [length / 2, height - 0.05, 0], [-length / 2, height - 0.05, 0]])
    UV = np.array([[0, height * 2.2], [length * 2.2, height * 2.2], [length * 2.2, 0], [0, 0]]) / 2
    leaves.add_card(P, UV, np.tile([0, 0, 1], (4, 1)), np.ones(3))
    t = m.solid(a, metal)
    P, N, C, I, UV = leaves.arrays()
    return m, t + m.prim(P, N, C, I, UV, mesh_mat)


def build_field_device(name):
    """The player's handheld survey scanner (not a weapon): grip, body, screen, lens lamp."""
    m = Model(name)
    shell = m.material(name + '_Shell', None, 0.5, metal=0.1)
    screen = m.material(name + '_Screen', None, 0.2, emissive=(0.25, 0.85, 0.75), strength=2.0)
    lamp = m.material(name + '_Lens', None, 0.1, emissive=(0.9, 0.95, 1.0), strength=4.0)
    a, s, l = mk.Mesh(), mk.Mesh(), mk.Mesh()
    # local frame: grip along -Y, lens pointing +Z
    a.add(mk.rounded_box((0, 0, 0.02), (0.035, 0.03, 0.085), 0.45), hexc('#3b4045'))
    a.add(mk.capsule((0, -0.02, -0.02), (0, -0.1, -0.035), 0.018, 0.016), hexc('#23272a'))
    a.add(mk.loft((0, 0, 0.1), (0, 0, 0.125), [(0, 0.024, 0.024), (1, 0.026, 0.026)], 16, hint=(0, 1, 0)), hexc('#c48a2c'))
    a.add(mk.capsule((0.025, 0.03, -0.04), (0.03, 0.09, -0.05), 0.004, 0.003), hexc('#222222'))
    s.add(mk.rounded_box((0, 0.031, -0.01), (0.025, 0.002, 0.04), 0.3), (1, 1, 1))
    l.add(mk.ellipsoid((0, 0, 0.126), (0.019, 0.019, 0.004)), (1, 1, 1))
    return m, m.solid(a, shell) + m.solid(s, screen) + m.solid(l, lamp)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    tdir = os.path.join(a.out, 'textures', 'env'); mdir = os.path.join(a.out, 'models', 'env')
    os.makedirs(tdir, exist_ok=True); os.makedirs(mdir, exist_ok=True)
    tex = {
        'bark': to_png(tex_bark()), 'leaves': to_png(tex_leaves()), 'fern': to_png(tex_fern()), 'grass': to_png(tex_grass()),
        'needles': to_png(tex_needles()), 'chainlink': to_png(tex_chainlink()), 'sign': to_png(tex_sign()),
        'rock': to_png(tex_ground(256, 61, [0.75, 0.75, 0.72], 0.35)),
    }
    # tiling terrain layers (standalone PNGs for the Terrain component)
    ground = {
        'ground_moss.png': tex_ground(512, 71, hexc('#2c3a1c'), 0.45, speck=hexc('#4a5a26')),
        'ground_path.png': tex_ground(512, 72, hexc('#4a3a2a'), 0.4, speck=hexc('#6a5a46')),
        'ground_litter.png': tex_ground(512, 73, hexc('#3d3020'), 0.5, speck=hexc('#6b4a24')),
        'ground_gravel.png': tex_ground(512, 74, hexc('#56544e'), 0.45, speck=hexc('#7a776e')),
    }
    for fn, arr in ground.items():
        Image.fromarray(arr).save(os.path.join(tdir, fn), optimize=True)
    builds = [
        build_broadleaf_tree('tree_broadleaf_a', 1, 11.0, 0.32, 3.6, tex, lean=0.4),
        build_broadleaf_tree('tree_broadleaf_b', 2, 13.5, 0.4, 4.2, tex, lean=0.7, bare_lower=0.55),
        build_broadleaf_tree('tree_broadleaf_c', 3, 8.0, 0.22, 2.8, tex, lean=0.25, bare_lower=0.35),
        build_conifer('tree_conifer_a', 4, 12.0, 0.28, tex),
        build_conifer('tree_conifer_b', 5, 8.5, 0.2, tex),
        build_fern('fern_a', 11, 0.9, tex, 12), build_fern('fern_b', 12, 0.6, tex, 9), build_fern('fern_hero', 13, 1.4, tex, 16),
        build_shrub('shrub_a', 21, 0.8, tex), build_shrub('shrub_b', 22, 1.3, tex, 1.6),
        build_grass('grass_a', 31, tex, 0.55), build_grass('grass_b', 32, tex, 0.35),
        build_rock('rock_a', 41, (0.7, 0.45, 0.55), tex), build_rock('rock_b', 42, (1.4, 0.8, 1.1), tex),
        build_rock('rock_c', 43, (0.35, 0.22, 0.3), tex),
        build_log('log_a', 51, 4.5, 0.28, tex), build_stump('stump_a', 52, 0.3, tex),
        build_trail_marker('trail_marker', tex), build_sign('trail_sign', tex), build_sensor_post('sensor_post', tex),
        build_backpack('abandoned_pack', tex), build_fence('fence_panel', tex),
        build_field_device('field_device'),
    ]
    for m, tris in builds:
        p = os.path.join(mdir, m.name + '.glb'); m.save(p)
        print(f"{m.name:20s} {tris:6d} tris  {os.path.getsize(p) // 1024:5d} KiB")


if __name__ == '__main__':
    main()
