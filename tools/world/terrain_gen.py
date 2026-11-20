# SPDX-License-Identifier: Apache-2.0
"""Kestrel Valley heightfield and splat generation (numpy), and the .vterrain writer.

Reads the layout in worldmap.py. Order of operations:
  1. macro landform: z profile, edge mountains, southern road gap, east saddle, relay knoll
  2. fractal detail scaled per region (gentle forest hummocks, ridged hillside, rocky mountains)
  3. creek channel with a bed that only ever descends downstream
  4. ravine walls either side of the ambush stretch of the trail
  5. compound plateau and fence strip
  6. roads and trail graded along their length (max grade), with banks blended to the terrain
  7. POI pads flattened
  8. splat: forest litter / rock / path / meadow from slope, masks and cover

The .vterrain layout (VICTUS engine/terrain/include/victus/terrain/terrain.hpp):
  "VTRN" u32 version(1) u32 resolution u32 flags(0) | u16 heights[res^2] | u32 splat[res^2]
  | u64 FNV-1a 64 over every preceding byte. Row-major, rows advance along +z, sample (0,0)
  at the -x/-z corner; layer 0 weight in the lowest byte.
"""
from __future__ import annotations

import struct

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

import worldmap as M

N = M.RES
CELL = M.SIZE / (N - 1)
XS = -M.SIZE / 2 + np.arange(N) * CELL
X, Z = np.meshgrid(XS, XS)  # X[j, i] = x of column i; Z[j, i] = z of row j


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def value_noise(seed, freq, octaves=5, persistence=0.5, lacunarity=2.0, ridge=False):
    """Fractal value noise over the grid, roughly in [-1, 1]. freq: cycles per metre."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(X)
    amp, f, tot = 1.0, freq, 0.0
    for _ in range(octaves):
        L = int(np.ceil(M.SIZE * f)) + 4
        lat = rng.uniform(-1, 1, (L, L))
        u = (X + M.SIZE / 2) * f + 1
        v = (Z + M.SIZE / 2) * f + 1
        n = ndimage.map_coordinates(lat, [v.ravel(), u.ravel()], order=3, mode='wrap').reshape(X.shape)
        if ridge:
            n = 1 - np.abs(n) * 1.6
        out += n * amp
        tot += amp
        amp *= persistence
        f *= lacunarity
    return out / tot


def catmull(points, step=1.0):
    """Dense Catmull-Rom polyline through (x, z) points at ~step metre spacing."""
    P = np.asarray(points, float)
    P = np.vstack([P[0] * 2 - P[1], P, P[-1] * 2 - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        seg = max(2, int(np.linalg.norm(p2 - p1) / step))
        t = np.linspace(0, 1, seg, endpoint=False)[:, None]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t ** 2
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2][None])
    return np.vstack(out)


def arclen(poly):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    return d


def sample_grid(H, x, z):
    """Bilinear height of grid H at world (x, z) arrays."""
    u = (np.asarray(x) + M.SIZE / 2) / CELL
    v = (np.asarray(z) + M.SIZE / 2) / CELL
    return ndimage.map_coordinates(H, [v, u], order=1, mode='nearest')


class Spline:
    def __init__(self, points, step=1.0):
        self.p = catmull(points, step)
        self.s = arclen(self.p)
        self.tree = cKDTree(self.p)
        d, idx = self.tree.query(np.c_[X.ravel(), Z.ravel()], distance_upper_bound=200)
        d[~np.isfinite(d)] = 1e4
        idx = np.minimum(idx, len(self.p) - 1)
        self.dist = d.reshape(X.shape)
        self.idx = idx.reshape(X.shape)

    def graded_profile(self, H, sigma_m, max_grade, drop=0.0, monotonic_down=False, max_cut=None, floor_m=0.0):
        # floor_m: grade from the lowest ground within that radius (water lines sit in the
        # valley bottom even where the authored line runs along a side slope)
        Hs = ndimage.minimum_filter(H, size=int(2 * floor_m / CELL) + 1, mode='nearest') if floor_m > 0 else H
        h = sample_grid(Hs, self.p[:, 0], self.p[:, 1])
        ds = np.mean(np.diff(self.s)) if len(self.s) > 1 else 1
        h = ndimage.gaussian_filter1d(h, sigma_m / ds, mode='nearest')
        if monotonic_down:
            h = np.minimum.accumulate(h)
        # Limit the grade without biasing the line up or down: the lower envelope
        # min_j(h_j + g|i-j|) and the upper envelope max_j(h_j - g|i-j|) are both g-Lipschitz and
        # bracket the smoothed ground; their mean is too and stays centred on it, so long climbs
        # become balanced cut-and-fill instead of an embankment dragged from the steep end.
        g = max_grade * ds
        lo, hi = h.copy(), h.copy()
        for i in range(1, len(h)):
            lo[i] = min(lo[i], lo[i - 1] + g)
            hi[i] = max(hi[i], hi[i - 1] - g)
        for i in range(len(h) - 2, -1, -1):
            lo[i] = min(lo[i], lo[i + 1] + g)
            hi[i] = max(hi[i], hi[i + 1] - g)
        hg = 0.5 * (lo + hi)
        if max_cut is not None:
            # earthworks budget: the line may sit at most max_cut above or below the smoothed
            # ground; past that it follows the ground (a steeper pitch) instead of an embankment
            hg = h + np.clip(hg - h, -max_cut, max_cut)
            hg = ndimage.gaussian_filter1d(hg, 4.0 / ds, mode='nearest')
        h = hg
        if monotonic_down:
            h = np.minimum.accumulate(h)
        return h - drop

    def carve(self, H, profile, half_width, bank, strength=1.0):
        target = profile[self.idx]
        w = (1 - smoothstep(half_width, half_width + bank, self.dist)) * strength
        return H * (1 - w) + target * w, w


def step_pools(creek, prof, length=26.0, depth=0.42, x_lim=None):
    """Turn the creek bed inside the play area into a step-pool stream.

    VICTUS water volumes are flat, axis-aligned boxes. The creek runs steadily west (x decreases
    downstream), so the channel is cut into x intervals: each pool gets a flat bed at the
    downstream end's height and one water surface `depth` above it, and the bed drops at the
    interval boundary (a riffle). Step-pool morphology is what real steep forest streams look like
    (Montgomery & Buffington 1997, RESEARCH_REGISTER section 10). Returns the new profile and the
    pools as dicts (x0, x1, z0, z1, bed, level).
    """
    x_lim = x_lim if x_lim is not None else M.PLAY_X + 60
    px = creek.p[:, 0]
    assert np.all(np.diff(px) < 0.5), 'creek must run toward -x for x-interval pools'
    prof = prof.copy()
    pools = []
    edges = np.arange(-x_lim, x_lim + 1e-6, length)
    for x0, x1 in zip(edges[:-1], edges[1:]):
        sel = (px >= x0) & (px < x1)
        if sel.sum() < 3:
            continue
        bed = float(prof[sel].min())
        prof[sel] = bed
        zs = creek.p[sel, 1]
        pools.append(dict(x0=float(x0), x1=float(x1), z0=float(zs.min()), z1=float(zs.max()), bed=bed,
                          level=bed + depth))
    return prof, pools


_WARP = {}


def warp():
    """Low-frequency domain warp so region boundaries and the basin rim are not straight lines."""
    if not _WARP:
        def unit(n): return n / (n.std() + 1e-9)
        _WARP['z'] = unit(value_noise(12, 1 / 300, 3)) * 30.0
        _WARP['x'] = unit(value_noise(13, 1 / 260, 3)) * 40.0
    return _WARP['x'], _WARP['z']


def edge_factor(lo=0.0, hi=200.0):
    wx, _ = warp()
    ax = np.abs(X + wx)
    return smoothstep(M.PLAY_X + lo, M.PLAY_X + hi, ax)


def macro():
    _, wz = warp()
    from scipy.interpolate import PchipInterpolator
    prof = PchipInterpolator(M.PROFILE_Z[::-1], M.PROFILE_H[::-1], extrapolate=True)
    h = prof(np.clip(Z + wz, -512, 512))
    # the access road reaches the basin through a stream gap in the southern hills: the valley
    # floor descends toward the turnout at a drivable grade instead of crossing the rim
    gap = np.exp(-((X + 50) / 75) ** 2) * smoothstep(330, 470, Z)
    h -= gap * np.maximum(h - 30.0, 0) * 0.8
    edge = edge_factor() * (78 + 28 * value_noise(11, 1 / 160, 3))
    # southern hills, with the road gap near x = -40
    south = smoothstep(380, 505, Z) * 40 * (1 - 0.95 * np.exp(-((X + 45) / 60) ** 2))
    # low east saddle so the service road crosses the ridge around x = 240
    saddle = -46 * np.exp(-(((X - 245) / 75) ** 2 + ((Z + 160) / 85) ** 2))
    # the ridge sags gently toward the west too, so its crest line is not a ruler
    crest = 10 * np.sin(X / 95.0) * np.exp(-((Z + 185) / 60) ** 2)
    p = M.POIS['relay']
    knoll = p['raise_'] * np.exp(-((X - p['x']) ** 2 + (Z - p['z']) ** 2) / (p['raise_r'] ** 2))
    return h + edge + south + saddle + crest + knoll


def detail():
    # region weights
    forest_lowland = smoothstep(-60, 40, Z)
    hill = smoothstep(40, -60, Z) * smoothstep(-300, -240, Z)
    mountain = np.maximum(edge_factor(-20, 180), smoothstep(-430, -470, Z + warp()[1] * 0.5))
    gentle = value_noise(21, 1 / 110, 4) * 7.0 + value_noise(22, 1 / 28, 3) * 1.4
    ridged = value_noise(23, 1 / 140, 5, ridge=True) * 16.0 + value_noise(24, 1 / 35, 3) * 2.5
    rocky = value_noise(25, 1 / 90, 6, 0.55, ridge=True) * 30.0
    d = gentle * (1 - hill) * (1 - mountain) + ridged * hill * (1 - mountain) + rocky * mountain
    return d + value_noise(26, 1 / 9, 2) * 0.35  # micro relief everywhere


def generate():
    H = macro() + detail()

    # creek: monotonic bed, banks
    creek = Spline(M.CREEK)
    prof = creek.graded_profile(H, 25, 0.06, drop=1.2, monotonic_down=True, floor_m=9.0)
    prof, pools = step_pools(creek, prof)
    H, creek_w = creek.carve(H, prof, M.CREEK_WIDTH / 2, 6.0)
    creek_bed = 1 - smoothstep(M.CREEK_WIDTH / 2, M.CREEK_WIDTH / 2 + 1.5, creek.dist)

    # ravine walls
    rav = Spline(M.RAVINE)
    along = rav.s[rav.idx] / rav.s[-1]
    taper = smoothstep(0.0, 0.25, along) * smoothstep(1.0, 0.75, along)
    wall = smoothstep(4.0, 9.0, rav.dist) * (1 - smoothstep(18.0, 34.0, rav.dist))
    rough = 0.75 + 0.5 * value_noise(31, 1 / 12, 3)
    H = H + wall * taper * 9.0 * rough

    # compound plateau + fence strip
    c = M.COMPOUND
    en = value_noise(42, 1 / 45, 2) * 14.0
    inside = smoothstep(c['x0'] - 40, c['x0'] + 10, X + en) * smoothstep(c['x1'] + 40, c['x1'] - 10, X - en) * \
        smoothstep(c['z0'] - 30, c['z0'] + 6, Z + en * 0.6) * smoothstep(c['z1'] + 45, c['z1'], Z - en * 0.5)
    plateau = c['h'] + value_noise(41, 1 / 80, 2) * 0.6
    H = H * (1 - inside) + plateau * inside
    fence = Spline(M.FENCE)
    fprof = fence.graded_profile(H, 30, 0.04)
    H, fence_w = fence.carve(H, fprof, M.FENCE_CLEAR, 12.0, 0.85)

    # POI pads (before the routes, so roads and the trail grade into the flattened pads)
    pads = np.zeros_like(H)
    for name, p in M.POIS.items():
        if p['r'] <= 0:
            continue
        d = np.hypot(X - p['x'], Z - p['z'])
        h0 = p.get('h', float(sample_grid(H, [p['x']], [p['z']])[0]))
        w = 1 - smoothstep(p['r'], p['r'] + p.get('fall', 9), d)
        if p.get('grade'):
            # slope-limited shoulder: around a pad dug into a hillside the ground may rise or fall at
            # most `grade` (rise over run) away from the pad edge, so the cut grades out as a bank
            # instead of a cliff wall; the correction is blurred so the bank has no crease
            lim = p['grade'] * np.maximum(d - p['r'], 0.0)
            delta = np.clip(H, h0 - lim, h0 + lim) - H
            delta = ndimage.gaussian_filter(delta, 2.0)
            H = H + delta * (1 - w)
        H = H * (1 - w) + h0 * w
        pads = np.maximum(pads, w)

    # roads and trail
    road_in = Spline(M.ROAD_IN)
    H, w_in = road_in.carve(H, road_in.graded_profile(H, 18, 0.08, max_cut=2.5), M.ROAD_WIDTH / 2 + 0.6, 6.0)
    road_sv = Spline(M.ROAD_SERVICE)
    sv_prof = road_sv.graded_profile(H, 18, 0.085, max_cut=3.0)
    # culvert: the road crosses the creek on a raised embankment
    H, w_sv = road_sv.carve(H, sv_prof, M.ROAD_WIDTH / 2 + 0.6, 6.0)
    trail = Spline(M.TRAIL, 0.5)
    tprof = trail.graded_profile(H, 6, 0.18, drop=0.15, max_cut=2.0)
    # the trail crosses the creek on the footbridge: keep the channel open under the deck
    keep_ch = smoothstep(M.CREEK_WIDTH / 2 + 1.0, M.CREEK_WIDTH / 2 + 5.0, creek.dist)
    tw = (1 - smoothstep(M.TRAIL_WIDTH / 2, M.TRAIL_WIDTH / 2 + 2.5, trail.dist)) * 0.9 * keep_ch
    H = H * (1 - tw) + tprof[trail.idx] * tw
    w_tr = tw

    # light smoothing of high frequencies created by the carves, keep detail elsewhere
    Hs = ndimage.gaussian_filter(H, 0.7)
    H = Hs

    # Pool levels against the final ground: a pool's flat water box must not reach terrain outside
    # its channel (low banks would show as flooded ground), and must keep some depth over its bed.
    half = M.CREEK_WIDTH / 2 + 1.6
    for p in pools:
        p['wx0'] = p['x0'] + 4.5      # water starts above the step; the step itself is the riffle
        sel = (X >= p['wx0']) & (X < p['x1']) & (Z >= p['z0'] - half) & (Z <= p['z1'] + half)
        bank = sel & (creek.dist > M.CREEK_WIDTH / 2 + 1.5)
        bed = sel & (creek.dist < M.CREEK_WIDTH / 2 - 0.4)
        if bed.any():
            p['bed'] = float(np.median(H[bed]))
        lvl = p['bed'] + 0.42
        if bank.any():
            lvl = min(lvl, float(H[bank].min()) - 0.06)
        p['level'] = max(lvl, p['bed'] + 0.12)
        p['wet'] = True
        # low banks: a natural levee up to 0.9 m keeps the water in its channel; if the side ground
        # falls away further than that (the culvert embankment) the pool is left as a dry gravel run
        bank_lo = sel & (creek.dist > M.CREEK_WIDTH / 2 + 0.6) & (H < p['level'] + 0.1)
        need = float((p['level'] + 0.1 - H[bank_lo]).max()) if bank_lo.any() else 0.0
        if need > 0.9:
            p['wet'] = False
        elif bank_lo.any():
            H[bank_lo] = p['level'] + 0.1

    road = np.maximum(1 - smoothstep(M.ROAD_WIDTH / 2, M.ROAD_WIDTH / 2 + 1.4, road_in.dist),
                      1 - smoothstep(M.ROAD_WIDTH / 2, M.ROAD_WIDTH / 2 + 1.4, road_sv.dist))
    path = 1 - smoothstep(M.TRAIL_WIDTH / 2 - 0.2, M.TRAIL_WIDTH / 2 + 0.8, trail.dist)
    masks = dict(road=road, path=path, creek=creek_bed, creek_dist=creek.dist, trail_dist=trail.dist,
                 road_dist=np.minimum(road_in.dist, road_sv.dist), pads=pads, fence=fence_w,
                 fence_dist=fence.dist, compound=inside, ravine=wall * taper, ravine_dist=rav.dist,
                 creek_pools=pools,
                 splines=dict(road_in=road_in, road_sv=road_sv, trail=trail, creek=creek, fence=fence,
                              ravine=rav))
    return H, masks


def slope_deg(H):
    gz, gx = np.gradient(H, CELL)
    return np.degrees(np.arctan(np.hypot(gx, gz)))


def forest_cover(H, masks):
    _, wz = warp()
    base = np.interp(Z + wz * 1.4, M.FOREST_Z[::-1], M.FOREST_C[::-1])
    # outside the play area (mountains) keep forest up to the tree line
    # the northern mountain behind the facility is forested on its lower slopes as well; the
    # facility apron and the compound stay clear (masks below)
    north = smoothstep(-455, -485, Z + wz * 0.6)
    outside = np.maximum(edge_factor(-30, 30), north)
    treeline = 1 - smoothstep(150, 190, H + 12 * value_noise(52, 1 / 60, 2))
    base = np.maximum(base, outside * 0.85) * treeline
    n = value_noise(51, 1 / 70, 3) * 0.5 + 0.5
    cover = np.clip(base * (0.55 + 0.9 * n), 0, 1)
    # clearings
    cover *= 1 - masks['pads']
    cover *= 1 - masks['compound']
    cover *= smoothstep(6, 20, masks['fence_dist'])
    return cover


def splat(H, masks, cover):
    s = slope_deg(H)
    # Steep ground is bare rock only where nothing grows on it: under forest, slopes up to about
    # 40 degrees keep their litter and undergrowth (a wooded valley side, not a scree face).
    rock = smoothstep(27, 40, s) * (1 - cover) + smoothstep(38, 52, s) * cover
    rock = np.maximum(rock, masks['ravine'] * smoothstep(5, 9, masks['ravine_dist']) * 0.9)
    outcrop = smoothstep(0.55, 0.75, value_noise(61, 1 / 30, 3) * 0.5 + 0.5) * smoothstep(60, 95, H) * \
        (1 - cover)
    rock = np.maximum(rock, outcrop * 0.85)
    # high ground: bare rock above the treeline, with grass ledges where the face is gentle
    high = smoothstep(170, 215, H + 14 * value_noise(62, 1 / 45, 3))
    ledge = (1 - smoothstep(18, 30, s)) * smoothstep(0.45, 0.6, value_noise(63, 1 / 25, 3) * 0.5 + 0.5)
    rock = np.maximum(rock, high * (1 - 0.8 * ledge))
    pathw = np.maximum(masks['road'], masks['path'] * 0.95)
    pathw = np.maximum(pathw, masks['creek'] * 0.7)               # gravel creek bed
    pathw = np.maximum(pathw, masks['compound'] * 0.55)           # packed yard
    meadow = np.clip(1 - cover * 1.4, 0, 1)
    forest = 1 - meadow
    w = np.stack([forest, rock * 1.6, pathw * 2.4, meadow * (1 - rock)], -1)
    # path and rock override the ground layers
    w[..., 0] *= (1 - pathw) * (1 - rock)
    w[..., 3] *= (1 - pathw) * (1 - rock)
    w[..., 1] *= (1 - pathw)
    w = np.maximum(w, 0) + 1e-4
    w /= w.sum(-1, keepdims=True)
    return w


def fnv1a64(data: bytes) -> int:
    h = 0xcbf29ce484222325
    prime = 0x100000001b3
    mask = (1 << 64) - 1
    # process in numpy-friendly chunks is not possible for FNV (sequential); use python ints
    for b in data:
        h ^= b
        h = (h * prime) & mask
    return h


def write_vterrain(path, H, W):
    n = H.shape[0]
    hn = np.clip(H / M.HEIGHT, 0, 1)
    h16 = np.round(hn * 65535).astype('<u2')
    w8 = np.round(W * 255).astype(np.uint32)
    # keep weights summing to 255 so the shader's normalization is stable
    w8[..., 0] += np.clip(255 - w8.sum(-1), 0, 255).astype(np.uint32)
    spl = (w8[..., 0] | (w8[..., 1] << 8) | (w8[..., 2] << 16) | (w8[..., 3] << 24)).astype('<u4')
    body = b'VTRN' + struct.pack('<III', 1, n, 0) + h16.tobytes() + spl.tobytes()
    h = fnv1a64_c(body)
    with open(path, 'wb') as f:
        f.write(body + struct.pack('<Q', h))


def fnv1a64_c(data: bytes) -> int:
    """FNV-1a 64 via a tiny compiled helper when available (sequential hash over ~1.6 MB)."""
    try:
        import ctypes, tempfile, subprocess, os
        so = os.path.join(tempfile.gettempdir(), 'sops_fnv.so')
        if not os.path.exists(so):
            src = so[:-3] + '.c'
            open(src, 'w').write('#include <stdint.h>\n#include <stddef.h>\nuint64_t fnv(const unsigned char*p,size_t n)'
                                 '{uint64_t h=0xcbf29ce484222325ULL;for(size_t i=0;i<n;i++){h^=p[i];h*=0x100000001b3ULL;}return h;}\n')
            subprocess.check_call(['cc', '-O2', '-shared', '-fPIC', src, '-o', so])
        lib = ctypes.CDLL(so)
        lib.fnv.restype = ctypes.c_uint64
        lib.fnv.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        return lib.fnv(data, len(data))
    except Exception:
        return fnv1a64(data)
