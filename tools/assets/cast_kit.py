# SPDX-License-Identifier: Apache-2.0
"""Per-character kit for tools/assets/build_rocketbox_cast.py.

The Rocketbox avatars are generic US soldiers, police and civilians; the bible's Halyard and
Greyline cast (docs/OPERATORS_AND_WEAPON_DESIGN.md section 10, docs/CHARACTERS_ANIMATION_AUDIO.md)
need specific silhouettes. Three tools close the gap without leaving the one-primitive-per-mesh
contract:

- borrow: whole materials (vest, webbing) taken from another Rocketbox avatar, baked onto the same
  rig, shifted joint-by-joint onto this body's proportions and dyed with this character's uniform;
- acc: small rigid accessories (headset cups and boom mic, radio pack and whip antenna, packs, the
  medic's teal armband, Patch's red bun) generated as rounded superellipsoids and tubes in the rest
  pose, weighted 100% to one joint, textured from a woven-fabric swatch tile that this module paints;
- fx: texture passes (Greyline's safety-orange goggle lenses, white medic gloves, painted-out unit
  patches, charcoal lift).

Everything here is generated from code: no third-party data beyond the MIT Rocketbox avatars.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

JOINTS = ["Hips", "Spine", "Chest", "Neck", "Head", "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
          "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R", "UpperLeg.L", "LowerLeg.L", "Foot.L", "Toe.L",
          "UpperLeg.R", "LowerLeg.R", "Foot.R", "Toe.R"]
JI = {n: i for i, n in enumerate(JOINTS)}

OLIVE = '#55603f'
TEAL = '#3fb7a4'
TEAL_CLOTH = '#2f9283'   # the bible's #3fb7a4 read as cloth under daylight, not as a plastic toy

# character -> kit. Colours are sRGB hex. 'acc' entries: (kind, colour); geometry comes from the
# body's own landmarks so the same spec fits any avatar.
KIT = {
    'sops_anchor': {'borrow': [('Military_Male_01', 'equipment')],          # plate carrier + pouches
                    'acc': [('backpack', '#4f5a3a')]},
    'sops_brick': {'acc': [('backpack', '#4b5537')]},
    'sops_tally': {'acc': [('headset', '#2a2c2a'), ('radio_pack', '#4d563a'), ('antenna', '#151515')]},
    'sops_patch': {'acc': [('armband', TEAL_CLOTH), ('bun', '#7e321a'), ('medic_pack', '#56613f')],
                   'fx': [('body', 'gloves', '#d9d9d2')]},
    'sops_echo': {'drop': ['equipment']},                                    # scout: slim, no vest
    'sops_greyline_a': {'fx': [('opacity', 'lens', '#ff6a0e'), ('helmet', 'goggles', '#ff6a0e'), ('', 'patches_yellow', None)]},
    'sops_greyline_b': {'fx': [('opacity', 'lens', '#ff6a0e'), ('helmet', 'goggles', '#ff6a0e'), ('', 'patches_yellow', None),
                               ('body', 'lift', 1.55), ('equipment', 'lift', 1.35)]},
}


def hexrgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


# ---------------------------------------------------------------- geometry -------------------------
def _vnormals(P, T):
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)


def _frame(fwd):
    """Rotation whose local z is `fwd` (unit), x roughly world x."""
    z = np.asarray(fwd, np.float64); z /= np.linalg.norm(z)
    up = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
    y = np.cross(z, up); y /= np.linalg.norm(y); x = np.cross(y, z)
    return np.stack([x, y, z], 1)


def superellipsoid(c, r, eps=1.0, R=None, seg=(18, 12)):
    """Rounded box (eps ~0.2) to ellipsoid (eps 1). Returns P, UV, T (closed, outward)."""
    nu, nv = seg
    u = np.linspace(-np.pi, np.pi, nu + 1)
    v = np.linspace(-np.pi / 2, np.pi / 2, nv + 1)
    U, V = np.meshgrid(u, v)
    f = lambda w, e: np.sign(w) * np.abs(w) ** e
    x = r[0] * f(np.cos(V), eps) * f(np.cos(U), eps)
    y = r[1] * f(np.sin(V), eps)
    z = r[2] * f(np.cos(V), eps) * f(np.sin(U), eps)
    P = np.stack([x, y, z], -1).reshape(-1, 3)
    if R is not None: P = P @ np.asarray(R).T
    P += c
    UV = np.stack([(U + np.pi) / (2 * np.pi), (V + np.pi / 2) / np.pi], -1).reshape(-1, 2)
    T = []
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i; b = a + 1; cc = a + nu + 1; d = cc + 1
            T += [(a, cc, b), (b, cc, d)]
    return P, UV, np.array(T, np.int64)


def tube(p0, p1, r0, r1=None, seg=16, cap=True):
    """Cylinder/cone from p0 to p1 (open sides capped if cap)."""
    r1 = r0 if r1 is None else r1
    p0 = np.asarray(p0, np.float64); p1 = np.asarray(p1, np.float64)
    R = _frame(p1 - p0)
    a = np.linspace(0, 2 * np.pi, seg + 1)
    ring = np.stack([np.cos(a), np.sin(a), np.zeros_like(a)], -1)
    P = np.concatenate([p0 + (ring * r0) @ R.T, p1 + (ring * r1) @ R.T])
    UV = np.concatenate([np.stack([a / (2 * np.pi), np.zeros_like(a)], -1), np.stack([a / (2 * np.pi), np.ones_like(a)], -1)])
    n = seg + 1
    T = []
    for i in range(seg):
        T += [(i, i + 1, n + i), (i + 1, n + i + 1, n + i)]
    T = np.array(T, np.int64)
    if cap:
        c0 = len(P); c1 = c0 + 1
        P = np.concatenate([P, [p0, p1]]); UV = np.concatenate([UV, [[0.5, 0.0], [0.5, 1.0]]])
        T = np.concatenate([T, [(c0, i + 1, i) for i in range(seg)], [(c1, n + i, n + i + 1) for i in range(seg)]])
    # make the winding outward
    cen = (p0 + p1) / 2
    fc = P[T].mean(1); fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    if np.mean(np.einsum('ij,ij->i', fn, fc - cen)) < 0: T = T[:, [0, 2, 1]]
    return P, UV, T


def band(c, axis, radius, height, thick=0.004, seg=24):
    """Closed ring (armband): outer and inner wall plus rims."""
    axis = np.asarray(axis, np.float64); axis /= np.linalg.norm(axis)
    po, uo, to = tube(c - axis * height / 2, c + axis * height / 2, radius, seg=seg, cap=False)
    pi, ui, ti = tube(c - axis * height / 2, c + axis * height / 2, radius - thick, seg=seg, cap=False)
    ti = ti[:, [0, 2, 1]] + len(po)
    n = seg + 1
    rim = []
    for i in range(seg):   # bottom and top rims joining outer (0..) and inner (len(po)..)
        o, q = i, len(po) + i
        rim += [(o, q, o + 1), (o + 1, q, q + 1)]
        o, q = n + i, len(po) + n + i
        rim += [(o, o + 1, q), (o + 1, q + 1, q)]
    return np.concatenate([po, pi]), np.concatenate([uo, ui]), np.concatenate([to, ti, np.array(rim, np.int64)])


# ---------------------------------------------------------------- landmarks ------------------------
class Body:
    def __init__(self, P, W, vmat_names, jpos):
        self.P = P; self.dom = W.argmax(1); self.vm = vmat_names; self.j = {n: np.asarray(p, np.float64) for n, p in jpos.items()}

    def sel(self, joints=None, mats=None, ylo=-9, yhi=9, xabs=9):
        m = (self.P[:, 1] >= ylo) & (self.P[:, 1] <= yhi) & (np.abs(self.P[:, 0]) <= xabs)
        if joints is not None: m &= np.isin(self.dom, [JI[n] for n in joints])
        if mats is not None: m &= np.array([any(k in s for k in mats) for s in self.vm])
        return self.P[m]


def accessory(kind, body: Body):
    """-> list of (P, UV, T, joint)"""
    j = body.j; H = j['Head']; C = j['Chest']; out = []
    if kind == 'armband':
        a, b = j['UpperArm.L'], j['LowerArm.L']
        ax = (b - a) / np.linalg.norm(b - a); c = a + (b - a) * 0.42
        v = body.sel(['UpperArm.L', 'Shoulder.L'])
        d = v - a; t = d @ ax / np.linalg.norm(b - a); v = v[(t > 0.34) & (t < 0.5)]
        rad = np.percentile(np.linalg.norm(np.cross(v - a, ax), axis=1), 88) + 0.003 if len(v) else 0.05
        out.append((*band(c, ax, rad, 0.055, thick=0.003), 'UpperArm.L'))
    elif kind == 'bun':
        v = body.sel(['Head', 'Neck'], ylo=H[1] + 0.03, yhi=H[1] + 0.12, xabs=0.05)
        back = v[:, 2].min() if len(v) else H[2] - 0.11
        P, UV, T = superellipsoid(np.array([0, H[1] + 0.06, back - 0.03]), (0.042, 0.038, 0.042), eps=1.0)
        out.append((P, UV, T, 'Head'))
    elif kind == 'headset':
        v = body.sel(['Head'], ylo=H[1] + 0.03, yhi=H[1] + 0.11)
        half = np.abs(v[:, 0]).max() if len(v) else 0.09
        sides = v[np.abs(v[:, 0]) > half * 0.85]
        zc = float(np.median(sides[:, 2])) if len(sides) else H[2] - 0.01
        y = H[1] + 0.07
        for s in (1, -1):
            out.append((*tube((s * (half - 0.006), y, zc), (s * (half + 0.026), y, zc), 0.031, 0.028, seg=20), 'Head'))
        fv = body.sel(['Head'], ylo=H[1] + 0.0, yhi=H[1] + 0.06, xabs=0.03)
        front = fv[:, 2].max() if len(fv) else H[2] + 0.11
        p0 = np.array([half + 0.02, y - 0.012, zc + 0.02]); p1 = np.array([0.03, H[1] + 0.03, front + 0.012])
        mid = (p0 + p1) / 2 + np.array([0.02, -0.015, 0.0])
        out.append((*tube(p0, mid, 0.0045, seg=8), 'Head'))
        out.append((*tube(mid, p1, 0.0045, seg=8), 'Head'))
        out.append((*superellipsoid(p1, (0.011, 0.009, 0.011), eps=0.8, seg=(10, 6)), 'Head'))
    elif kind in ('radio_pack', 'backpack', 'medic_pack', 'antenna'):
        y0, y1 = C[1] - 0.2, C[1] + 0.12
        v = body.sel(['Chest', 'Spine', 'Neck', 'Shoulder.L', 'Shoulder.R'], ylo=y0, yhi=y1, xabs=0.14)
        back = v[:, 2].min() if len(v) else C[2] - 0.13
        if kind == 'backpack':
            r = (0.165, 0.21, 0.085); c = np.array([0, C[1] - 0.06, back - r[2] + 0.02])
            out.append((*superellipsoid(c, r, eps=0.22), 'Chest'))
            out.append((*superellipsoid(c + (0, -0.08, -r[2] + 0.01), (0.12, 0.08, 0.035), eps=0.25), 'Chest'))
        elif kind == 'radio_pack':
            r = (0.12, 0.15, 0.06); c = np.array([0.02, C[1] - 0.02, back - r[2] + 0.015])
            out.append((*superellipsoid(c, r, eps=0.15), 'Chest'))
        elif kind == 'antenna':
            base = np.array([0.11, C[1] + 0.12, back - 0.04])
            out.append((*tube(base - (0, 0.03, 0), base + (0, 0.01, 0), 0.011, seg=10), 'Chest'))
            out.append((*tube(base, base + np.array([0.03, 0.42, -0.06]), 0.0035, 0.002, seg=6), 'Chest'))
        else:  # medic pack low on the back, rides the hips
            hv = body.sel(['Hips', 'Spine'], ylo=j['Hips'][1] - 0.02, yhi=j['Hips'][1] + 0.12, xabs=0.12)
            hb = hv[:, 2].min() if len(hv) else j['Hips'][2] - 0.13
            r = (0.12, 0.075, 0.05); c = np.array([0, j['Hips'][1] + 0.06, hb - r[2] + 0.012])
            out.append((*superellipsoid(c, r, eps=0.2), 'Hips'))
    return out


# ---------------------------------------------------------------- swatch tile ----------------------
GRID = 4  # 4x4 swatches of TILE/4


def _fabric(n, rng, weave=True):
    """Height field of a woven / ripstop fabric, 0..1."""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    h = rng.normal(0, 1, (n, n)).astype(np.float32)
    h = np.asarray(Image.fromarray(((h - h.min()) / (np.ptp(h) + 1e-6) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255
    if weave:
        k = 2 * np.pi / 5.0
        h = 0.55 * h + 0.25 * (0.5 + 0.5 * np.sin(xx * k) * np.sign(np.sin(yy * k * 0.5))) + \
            0.2 * (0.5 + 0.5 * np.sin(yy * k) * np.sign(np.sin(xx * k * 0.5)))
        grid = ((xx % 48) < 2) | ((yy % 48) < 2)          # ripstop grid
        h = h + 0.25 * grid
    lo = rng.normal(0, 1, (8, 8)).astype(np.float32)
    lo = np.asarray(Image.fromarray(((lo - lo.min()) / (np.ptp(lo) + 1e-6) * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)).astype(np.float32) / 255
    return h, lo


def swatch_tile(tile, colours, kinds):
    """colours: list of sRGB hex, one swatch each. Returns rgb, nor, rough arrays (tile x tile)."""
    n = tile // GRID
    rgb = np.zeros((tile, tile, 3), np.float32); nor = np.zeros((tile, tile, 3), np.float32); nor[...] = (0.5, 0.5, 1)
    ro = np.full((tile, tile), 0.85, np.float32)
    rng = np.random.default_rng(7)
    for k, (col, kind) in enumerate(zip(colours, kinds)):
        cy, cx = divmod(k, GRID)
        hard = kind in ('antenna', 'headset')
        hair = kind == 'bun'
        h, lo = _fabric(n, rng, weave=not (hard or hair))
        if hair:   # strands: stretched noise along v
            s = rng.normal(0, 1, (n, n // 16)).astype(np.float32)
            s = np.asarray(Image.fromarray(((s - s.min()) / np.ptp(s) * 255).astype(np.uint8)).resize((n, n), Image.BICUBIC)).astype(np.float32) / 255
            h = 0.7 * s.T + 0.3 * h
        base = hexrgb(col) ** 2.2
        shade = (0.78 + 0.3 * (h - 0.5) + 0.18 * (lo - 0.5))[..., None]
        if hard: shade = (0.9 + 0.08 * (h - 0.5))[..., None]
        c = np.clip(base * shade, 0, 1) ** (1 / 2.2)
        gy, gx = np.gradient(h * (0.6 if hard else 3.0 if hair else 2.2))
        nn = np.dstack([-gx, -gy, np.ones_like(h)]); nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
        ys, xs = slice(cy * n, (cy + 1) * n), slice(cx * n, (cx + 1) * n)
        rgb[ys, xs] = c; nor[ys, xs] = nn * 0.5 + 0.5
        ro[ys, xs] = (0.42 if hard else 0.55 if hair else 0.86) - 0.08 * (h - 0.5)
    return rgb, nor, ro


def swatch_uv(k, uv):
    n = 1.0 / GRID; cy, cx = divmod(k, GRID)
    return np.clip(uv, 0, 1) * (n * 0.92) + (cx * n + n * 0.04, cy * n + n * 0.04)


# ---------------------------------------------------------------- texture fx -----------------------
def uv_mask(tile, tris_uv):
    """Rasterise triangles (k,3,2 UV 0..1) into a TILE mask."""
    im = Image.new('L', (tile, tile), 0); d = ImageDraw.Draw(im)
    for t in tris_uv:
        d.polygon([(float(u * tile), float(v * tile)) for u, v in t], fill=255)
    return np.asarray(im.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255


def fx_apply(rgb, kind, arg, ctx):
    from scipy import ndimage
    H, W = rgb.shape[:2]
    lum = rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    if kind == 'goggles':
        # Rocketbox m158 helmet map: goggle lens window around (0.32..0.59, 0.10..0.22) of the tile.
        x0, y0, x1, y1 = int(0.322 * W), int(0.105 * H), int(0.586 * W), int(0.22 * H)
        c = rgb[y0:y1, x0:x1]; l = lum[y0:y1, x0:x1]
        m = ndimage.binary_opening(l < 0.14, iterations=2)
        lab, n = ndimage.label(m)
        if n:
            m = lab == (np.argmax(ndimage.sum(m, lab, range(1, n + 1))) + 1)
            cols = np.where(m.any(0))[0]
            for x in cols:            # fill each column between its first and last lens pixel
                r = np.where(m[:, x])[0]; m[r[0]:r[-1] + 1, x] = True
            m = ndimage.binary_erosion(m, iterations=1)
            mm = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32)[..., None] / 255
            o = hexrgb(arg)
            tint = np.clip(o * (0.62 + l[..., None] * 2.6), 0, 1)   # bright, reads at distance
            rgb[y0:y1, x0:x1] = c * (1 - mm) + tint * mm
    elif kind == 'lens':     # m158 goggle lens map: the whole texture is lens; tint it
        rgb[...] = np.clip(hexrgb(arg) * (0.55 + lum[..., None] * 2.8), 0, 1)
    elif kind == 'patches_yellow':
        hsv = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).convert('HSV')).astype(np.float32) / 255.0
        f = (hsv[..., 0] > 0.10) & (hsv[..., 0] < 0.19) & (hsv[..., 1] > 0.5) & (hsv[..., 2] > 0.35)
        f = ndimage.binary_dilation(ndimage.binary_closing(f, iterations=4), iterations=6)
        lab, n = ndimage.label(f)
        for sl in ndimage.find_objects(lab):
            ring = np.concatenate([rgb[max(sl[0].start - 4, 0):sl[0].start, sl[1]].reshape(-1, 3),
                                   rgb[sl[0].stop:sl[0].stop + 4, sl[1]].reshape(-1, 3)])
            fill = np.median(ring, 0) if len(ring) else np.array([0.08, 0.08, 0.08])
            blk = rgb[sl]; nz = blk.mean(-1, keepdims=True)
            rgb[sl] = np.clip(fill * (0.95 + 0.4 * (nz - nz.mean())), 0, 1)
        if n: print(f'  painted out {n} unit patches')
    elif kind == 'lift':     # charcoal -> Greyline mid grey, keeps weave/shading, skips skin
        hsv = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).convert('HSV')).astype(np.float32) / 255.0
        cloth = (hsv[..., 1] < 0.3)[..., None]
        g = np.clip(rgb * arg + 0.025, 0, 1)
        g = g * 0.85 + g.mean(-1, keepdims=True) * 0.15
        rgb[...] = np.where(cloth, g, rgb)
    elif kind == 'gloves':
        m = ctx['mask'](['Hand.L', 'Hand.R'])[..., None]
        t = hexrgb(arg)
        ref = float((lum * m[..., 0]).sum() / max(m.sum(), 1))
        rel = np.clip(lum / max(ref, 1e-3), 0.5, 1.4)[..., None]
        hsv_s = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).convert('HSV')).astype(np.float32)[..., 1:2] / 255
        skin = (hsv_s > 0.25).astype(np.float32)          # bare fingertips / wrists stay skin
        m = m * (1 - skin)
        rgb[...] = rgb * (1 - m) + np.clip(t * rel, 0, 1) * m
    return rgb
