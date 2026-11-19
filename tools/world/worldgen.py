# SPDX-License-Identifier: Apache-2.0
"""Build the Kestrel Valley open world: terrain asset, vegetation, canopy proxies and scenes.

    python3 tools/world/worldgen.py terrain     # .vterrain + design map (then: victus import game)
    python3 tools/world/worldgen.py canopy      # far-canopy proxy GLBs (then: victus import game)
    python3 tools/world/worldgen.py scene       # scenes/world/kestrel.vscene (+ view scenes)
    python3 tools/world/worldgen.py all         # terrain, import, canopy, import, scene, stream

Outputs
  game/assets/terrain/kestrel.vterrain       513x513 heightfield (2 m), 4-layer splat
  game/assets/models/world/canopy_<i>_<j>.glb far canopy per 128 m block (always loaded)
  game/scenes/world/kestrel.vscene           the playable world (Op01 start at the trailhead)
  game/worlds/kestrel.vworld + cells         64 m streaming cells (victus world)
  docs/world/kestrel_map.png                 design map (hillshade, cover, routes, POIs)

Streaming plan (docs/world/KESTREL_VALLEY.md): detailed trees, rocks and props stream in 64 m
cells (load radius 96 m); the terrain, foliage scatter (ferns, grass, shrubs; draw distance
culled), the canopy proxies and gameplay entities stay resident. A tree's canopy proxy is a
low crown core sized inside the real crown, so up close it is hidden by the leaf cards and far
away it carries the forest silhouette after the detailed cell has unloaded.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools' / 'scenes'))
sys.path.insert(0, str(ROOT / 'tools' / 'props'))

import worldmap as M  # noqa: E402
import terrain_gen as T  # noqa: E402

ASSETS = ROOT / 'game' / 'assets'
TERRAIN_REL = 'terrain/kestrel.vterrain'
CANOPY_DIR = 'models/world'
BLOCK = 128.0         # far canopy blocks (outside the play area, always drawn)
CELL = 64.0           # near canopy blocks match the streaming cells one to one

# ---------------------------------------------------------------------------------------------
# vegetation placement (deterministic)

TREES = {
    # model, base height (m), crown centre y and radius (model units), trunk radius
    'broadleaf_a': dict(rel='models/env/tree_broadleaf_a.glb', crown_y=8.0, crown_r=3.6, crown_h=4.0, trunk=0.32, kind='broad'),
    'broadleaf_b': dict(rel='models/env/tree_broadleaf_b.glb', crown_y=9.2, crown_r=4.2, crown_h=4.2, trunk=0.36, kind='broad'),
    'broadleaf_c': dict(rel='models/env/tree_broadleaf_c.glb', crown_y=4.8, crown_r=2.6, crown_h=3.2, trunk=0.24, kind='broad'),
    'conifer_a':   dict(rel='models/env/tree_conifer_a.glb', crown_y=5.8, crown_r=3.9, crown_h=10.5, trunk=0.3, kind='conifer'),
    'conifer_b':   dict(rel='models/env/tree_conifer_b.glb', crown_y=4.2, crown_r=2.9, crown_h=7.6, trunk=0.22, kind='conifer'),
}


def _rng(seed):
    return np.random.default_rng(seed)


def place_trees(H, masks, cover, inner_only=True):
    """Jittered-grid tree positions. Returns list of dicts (type, x, z, y, yaw, scale)."""
    rng = _rng(7001)
    spacing = 3.4
    xs = np.arange(-M.SIZE / 2 + 4, M.SIZE / 2 - 4, spacing)
    gx, gz = np.meshgrid(xs, xs)
    px = gx + rng.uniform(-0.45, 0.45, gx.shape) * spacing
    pz = gz + rng.uniform(-0.45, 0.45, gz.shape) * spacing
    px, pz = px.ravel(), pz.ravel()

    def at(field):
        return T.sample_grid(field, px, pz)
    c = at(cover)
    slope = at(T.slope_deg(H))
    keep = rng.random(px.shape) < (c ** 1.15) * 0.62
    keep &= at(masks['road_dist']) > M.ROAD_WIDTH / 2 + 2.6
    keep &= at(masks['trail_dist']) > M.TRAIL_WIDTH / 2 + 1.2
    keep &= at(masks['creek_dist']) > M.CREEK_WIDTH / 2 + 1.8
    keep &= at(masks['pads']) < 0.05
    keep &= slope < 36
    # the ravine walls are bare rock (the Op01 ambush needs them readable as cover and high ground)
    keep &= at(masks['ravine']) < 0.25
    # beyond the play area only canopy proxies are drawn (the player cannot get near)
    inner = np.abs(px + T.sample_grid(T.warp()[0], px, pz)) < M.PLAY_X + 50
    trees_inner = keep & inner
    trees_outer = keep & ~inner
    y = at(H)
    trail_d = at(masks['trail_dist'])
    road_d = at(masks['road_dist'])
    out = []
    altitude = (y - 20) / 110
    for sel, region in ((trees_inner, 'inner'), (trees_outer, 'outer')):
        for i in np.nonzero(sel)[0]:
            a = altitude[i]
            p_conifer = np.clip(0.32 + a * 0.75, 0.25, 0.95)
            if rng.random() < p_conifer:
                t = 'conifer_a' if rng.random() < 0.55 else 'conifer_b'
            else:
                t = ['broadleaf_a', 'broadleaf_b', 'broadleaf_c'][rng.choice(3, p=[0.42, 0.38, 0.2])]
            s = rng.uniform(1.1, 1.6) if t != 'broadleaf_c' else rng.uniform(0.95, 1.35)
            # trees at forest edges grow lower and wider; keep it simple: smaller on the hillside
            s *= 0.85 + 0.15 * np.clip(c[i] * 1.5, 0, 1)
            # Trail and road corridors are kept clear of low branches (USFS clearing limits, see
            # RESEARCH_REGISTER section 10). A conifer is widest at its lowest whorl, which hangs at
            # head height, so one whose skirt (crown radius + 10 %) would reach within 1.2 m of the
            # corridor becomes a tall-trunk broadleaf (crown well above head height).
            if TREES[t]['kind'] == 'conifer':
                reach = 1.1 * TREES[t]['crown_r'] * s
                if trail_d[i] < M.TRAIL_WIDTH / 2 + 1.2 + reach or road_d[i] < M.ROAD_WIDTH / 2 + 1.0 + reach:
                    t = 'broadleaf_a' if (i * 2654435761) % 7 < 4 else 'broadleaf_b'
            out.append(dict(type=t, x=float(px[i]), z=float(pz[i]), y=float(y[i]) - 0.12,
                            yaw=float(rng.uniform(0, 360)), scale=float(s), region=region))
    return out


ROCKS = ['rock_a', 'rock_b', 'rock_c']


def place_rocks(H, masks, cover):
    rng = _rng(7101)
    pts = []
    slope = T.slope_deg(H)
    for spacing, p_base, smin, smax in ((5.0, 0.0, 0.8, 2.2), (9.0, 0.0, 2.0, 4.5)):
        xs = np.arange(-M.PLAY_X - 40, M.PLAY_X + 40, spacing)
        zs = np.arange(-470, 500, spacing)
        gx, gz = np.meshgrid(xs, zs)
        px = (gx + rng.uniform(-0.5, 0.5, gx.shape) * spacing).ravel()
        pz = (gz + rng.uniform(-0.5, 0.5, gz.shape) * spacing).ravel()
        sl = T.sample_grid(slope, px, pz)
        rav = T.sample_grid(masks['ravine'], px, pz)
        cov = T.sample_grid(cover, px, pz)
        hh = T.sample_grid(H, px, pz)
        prob = 0.02 + 0.5 * T.smoothstep(22, 38, sl) + 0.6 * rav + 0.05 * (1 - cov) * T.smoothstep(55, 90, hh)
        prob *= spacing / 5.0 * 0.5
        keep = rng.random(px.shape) < prob
        keep &= T.sample_grid(masks['road_dist'], px, pz) > M.ROAD_WIDTH / 2 + 1.5
        keep &= T.sample_grid(masks['trail_dist'], px, pz) > M.TRAIL_WIDTH / 2 + 0.6
        keep &= T.sample_grid(masks['pads'], px, pz) < 0.05
        keep &= T.sample_grid(masks['compound'], px, pz) < 0.1
        for i in np.nonzero(keep)[0]:
            pts.append(dict(type=ROCKS[rng.choice(3, p=[0.45, 0.35, 0.2])], x=float(px[i]), z=float(pz[i]),
                            y=float(hh[i]) - 0.25 * smin, yaw=float(rng.uniform(0, 360)),
                            scale=float(rng.uniform(smin, smax)), tilt=float(rng.uniform(-8, 8))))
    return pts


def place_deadwood(H, masks, cover):
    rng = _rng(7201)
    out = []
    xs = np.arange(-M.PLAY_X, M.PLAY_X, 14.0)
    zs = np.arange(-300, 480, 14.0)
    gx, gz = np.meshgrid(xs, zs)
    px = (gx + rng.uniform(-6, 6, gx.shape)).ravel()
    pz = (gz + rng.uniform(-6, 6, gz.shape)).ravel()
    cov = T.sample_grid(cover, px, pz)
    keep = rng.random(px.shape) < cov * 0.55
    keep &= T.sample_grid(masks['road_dist'], px, pz) > 6
    keep &= T.sample_grid(masks['trail_dist'], px, pz) > 2.4
    keep &= T.sample_grid(masks['creek_dist'], px, pz) > 2.5
    keep &= T.sample_grid(T.slope_deg(H), px, pz) < 24
    keep &= T.sample_grid(masks['pads'], px, pz) < 0.05
    hh = T.sample_grid(H, px, pz)
    for i in np.nonzero(keep)[0]:
        t = 'log_a' if rng.random() < 0.55 else 'stump_a'
        out.append(dict(type=t, x=float(px[i]), z=float(pz[i]), y=float(hh[i]) - 0.08,
                        yaw=float(rng.uniform(0, 360)), scale=float(rng.uniform(0.8, 1.3))))
    return out


# ---------------------------------------------------------------------------------------------
# canopy proxies


def build_canopy(trees):
    import build_forest as BF
    out_dir = ASSETS / CANOPY_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob('canopy_*.glb'):
        f.unlink()
    # Near blocks (inner trees) use the streaming cell grid: cell (i, j) covers
    # x in [i*64, (i+1)*64), z likewise (victus world floors world positions by the cell size),
    # so canopy.luau can show a block exactly while its cell's detailed trees are not loaded.
    blocks = {}
    for t in trees:
        if t['region'] == 'inner':
            key = ('near', int(math.floor(t['x'] / CELL)), int(math.floor(t['z'] / CELL)))
        else:
            key = ('far', int((t['x'] + M.SIZE / 2) // BLOCK), int((t['z'] + M.SIZE / 2) // BLOCK))
        blocks.setdefault(key, []).append(t)
    rng = _rng(7301)
    written = []
    # crown proxy geometry in unit space
    def ico():
        # octahedron subdivided once: 32 triangles, decent blob silhouette
        v = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
        f = [(0, 2, 4), (4, 2, 1), (1, 2, 5), (5, 2, 0), (0, 4, 3), (4, 1, 3), (1, 5, 3), (5, 0, 3)]
        V = [np.array(p, float) for p in v]
        F = []
        cache = {}
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = (V[a] + V[b]); m /= np.linalg.norm(m); V.append(m); cache[k] = len(V) - 1
            return cache[k]
        # plain octahedron (8 triangles): at proxy distances (>60 m) the silhouette noise comes
        # from the per-tree yaw and squash, not from tessellation
        return np.array(V), np.array(f)
    IV, IF = ico()
    def cone(seg=5):
        # open-bottom cone; the base is never seen from the ground or from above
        V = [(0, 1, 0)] + [(math.cos(a), 0, math.sin(a)) for a in np.linspace(0, 2 * math.pi, seg, endpoint=False)]
        F = [(0, 1 + (i + 1) % seg, 1 + i) for i in range(seg)]
        return np.array(V, float), np.array(F)
    CV, CF = cone()
    for (kind, bi, bj), lst in blocks.items():
        P, N, C, I = [], [], [], []
        n = 0
        if kind == 'near':
            ox, oz = (bi + 0.5) * CELL, (bj + 0.5) * CELL
        else:
            ox = -M.SIZE / 2 + (bi + 0.5) * BLOCK
            oz = -M.SIZE / 2 + (bj + 0.5) * BLOCK
        for t in lst:
            d = TREES[t['type']]
            s = t['scale']
            ya = math.radians(t['yaw'])
            Ry = np.array([[math.cos(ya), 0, math.sin(ya)], [0, 1, 0], [-math.sin(ya), 0, math.cos(ya)]])
            if d['kind'] == 'broad':
                V, F = IV @ Ry.T, IF
                r = d['crown_r'] * s * 0.78
                hgt = d['crown_h'] * s * 0.62
                ctr = np.array([t['x'] - ox, t['y'] + d['crown_y'] * s, t['z'] - oz])
                VV = V * np.array([r, hgt, r]) + ctr
                NN = V / np.array([r, hgt, r]); NN /= np.linalg.norm(NN, axis=1, keepdims=True)
                col = np.array([0.055, 0.085, 0.035]) * rng.uniform(0.8, 1.2)
            else:
                V, F = CV @ Ry.T, CF
                r = d['crown_r'] * s * 0.72
                hgt = d['crown_h'] * s * 0.95
                base = np.array([t['x'] - ox, t['y'] + (d['crown_y'] - d['crown_h'] * 0.45) * s, t['z'] - oz])
                VV = V * np.array([r, hgt, r]) + base
                NN = np.c_[V[:, 0], np.full(len(V), 0.45), V[:, 2]]
                NN /= np.linalg.norm(NN, axis=1, keepdims=True)
                col = np.array([0.035, 0.065, 0.035]) * rng.uniform(0.8, 1.2)
            # ambient darkening toward the bottom of each crown
            shade = np.clip(0.55 + 0.45 * (VV[:, 1] - VV[:, 1].min()) / max(1e-3, np.ptp(VV[:, 1])), 0, 1)
            P.append(VV); N.append(NN)
            C.append(np.c_[col[None] * shade[:, None], np.ones(len(VV))])
            I.append(F + n); n += len(VV)
        m = BF.Model(f'canopy_{kind}_{bi}_{bj}')
        mat = m.material('Canopy', rough=0.95)
        P = np.vstack(P); N = np.vstack(N); C = np.vstack(C); I = np.vstack(I).ravel()
        # outward winding check (glTF: counter-clockwise front faces)
        tri = I.reshape(-1, 3)
        fn = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
        flip = (fn * N[tri[:, 0]]).sum(1) < 0
        tri[flip] = tri[flip][:, ::-1]
        m.prim(P, N, C, tri.ravel(), np.zeros((len(P), 2)), mat)
        path = out_dir / f'canopy_{kind}_{bi}_{bj}.glb'
        m.save(str(path))
        written.append(dict(kind=kind, i=bi, j=bj, x=ox, z=oz, file=path.name, trees=len(lst)))
    (out_dir / 'canopy_blocks.json').write_text(json.dumps(written, indent=1) + '\n')
    return written


# ---------------------------------------------------------------------------------------------
# scene


def load_layout():
    H, masks = T.generate()
    cover = T.forest_cover(H, masks)
    return H, masks, cover


def cmd_terrain():
    import preview_map
    H, masks, cover = load_layout()
    W = T.splat(H, masks, cover)
    out = ASSETS / TERRAIN_REL
    out.parent.mkdir(parents=True, exist_ok=True)
    T.write_vterrain(out, H, W)
    (ROOT / 'docs' / 'world').mkdir(parents=True, exist_ok=True)
    preview_map.render(H, W, cover, str(ROOT / 'docs' / 'world' / 'kestrel_map.png'))
    np.save('/tmp/kestrel_H.npy', H)
    print('terrain', out, 'height', float(H.min()), float(H.max()))


def cmd_canopy():
    H, masks, cover = load_layout()
    trees = place_trees(H, masks, cover)
    w = build_canopy(trees)
    print('canopy blocks', len(w), 'trees', len(trees))


def victus(*args):
    env = dict(os.environ)
    env['PATH'] = str(Path.home() / '.local/bin') + ':' + env['PATH']
    subprocess.check_call(['victus', *args], cwd=str(ROOT), env=env)


def cmd_all():
    cmd_terrain()
    victus('import', 'game')
    cmd_canopy()
    victus('import', 'game')
    import world_scene
    world_scene.build()


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if what == 'terrain':
        cmd_terrain()
    elif what == 'canopy':
        cmd_canopy()
    elif what == 'scene':
        import world_scene
        world_scene.build()
    else:
        cmd_all()
