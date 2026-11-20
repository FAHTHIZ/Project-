# SPDX-License-Identifier: Apache-2.0
"""Southern backdrop: the land past the south edge of the Kestrel heightfield.

    python3 tools/world/south_backdrop.py      # idempotent: terrain asset, scene entities, cells

The staging camp (prologue) sits 25 m from the south edge of the 1024 m heightfield (z = 512),
where the ranger road enters the map. Looking south from the briefing showed the end of the
world: the ground stopped, the hill east of the camp ended in a cut face, and the sky ran down
to the fog. This tool adds a second, coarser terrain south of the edge:

  * assets/terrain/kestrel_south.vterrain, 257 x 257 samples over 1024 x 1024 m (4 m cells),
    starting 4 m inside the main terrain and 0.25 m below it so the seam never opens; its first
    rows copy the main edge, then it rises into forested southern hills with the road valley
    continuing south from the map edge (road splat along it);
  * a "Kestrel South Terrain" entity in every scene that has "Kestrel Terrain";
  * detailed trees on it in new streaming cells (z 512 to 640), same density rule as the
    hillside set, so the near ground past the edge is forest rather than bare hills.
"""
from __future__ import annotations

import copy
import json
import math
import sys
import uuid
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import worldgen as G  # noqa: E402
import terrain_gen as T  # noqa: E402
import worldmap as M  # noqa: E402
import add_hillside_trees as HT  # noqa: E402
from scipy import ndimage  # noqa: E402

GAME = G.ROOT / 'game'
ASSET = GAME / 'assets' / 'terrain' / 'kestrel_south.vterrain'
ASSET_UUID = 'b3f0c6e2-5d1a-4b7e-9c2f-8e4a1d6b7c35'
ENTITY_UUID = 'c1e7a9d4-3f2b-4a8c-b6e5-2d9f0a1c4e78'
N = 257
SX, SZ = 1024.0, 1024.0
Z0 = M.SIZE / 2 - 4.0           # first row, 4 m inside the main terrain
CENTER_Z = Z0 + SZ / 2
TREE_Z1 = 640.0
NS = uuid.UUID('0b8e7f3c-6a2d-4e51-8f9a-c4d2b1e0a7f6')


def noise(seed, x, z, freq, octaves=4):
    """Smooth value noise in [-1, 1] at arbitrary points (separable lattice, cosine blend)."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(x)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        f = freq * 2 ** o
        lat = rng.uniform(-1, 1, (96, 96))
        gx, gz = (x * f) % 95, (z * f) % 95
        i, j = np.floor(gx).astype(int), np.floor(gz).astype(int)
        fx, fz = gx - i, gz - j
        fx, fz = (1 - np.cos(fx * np.pi)) / 2, (1 - np.cos(fz * np.pi)) / 2
        v = (lat[j, i] * (1 - fx) * (1 - fz) + lat[j, i + 1] * fx * (1 - fz) +
             lat[j + 1, i] * (1 - fx) * fz + lat[j + 1, i + 1] * fx * fz)
        out += v * amp
        tot += amp
        amp *= 0.5
    return out / tot


def road_x(z):
    # continues the last ranger-road leg (-44, 490) -> (-30, 540) south, easing into a bend
    return -30.0 + (z - 540.0) * 0.28 - 30.0 * T.smoothstep(600, 900, z)


def build_heights(Hmain):
    xs = -SX / 2 + np.arange(N) * (SX / (N - 1))
    zs = Z0 + np.arange(N) * (SZ / (N - 1))
    X, Z = np.meshgrid(xs, zs)
    edge = T.sample_grid(Hmain, xs, np.full_like(xs, M.SIZE / 2 - 0.01))
    inside = T.sample_grid(Hmain, X.ravel(), np.minimum(Z, M.SIZE / 2 - 0.01).ravel()).reshape(X.shape)
    hills = 100 + 38 * noise(901, X, Z, 1 / 260.0) + 16 * np.abs(noise(902, X, Z, 1 / 90.0))
    hills += 40 * T.smoothstep(700, 1200, Z)              # the land keeps rising into the range
    # the road valley: hills fall to a floor that climbs gently from the map edge
    floor = np.interp(np.clip(Z, 512, 1300), [512, 700, 1300], [edge[np.argmin(np.abs(xs + 30))], 58, 90])
    rd = np.abs(X - road_x(Z))
    valley = np.exp(-(rd / 70.0) ** 2)
    target = hills * (1 - valley) + floor * valley
    t = T.smoothstep(M.SIZE / 2, M.SIZE / 2 + 140, Z)
    H = np.broadcast_to(edge, X.shape) * (1 - t) + target * t
    H = ndimage.gaussian_filter(H, 1.0)
    # rows over the main terrain copy it, a little lower, so the main surface covers the seam
    over = Z <= M.SIZE / 2
    H[over] = inside[over] - 0.25
    blend = T.smoothstep(M.SIZE / 2, M.SIZE / 2 + 12, Z) * (1 - over)
    H = np.where(over, H, H * blend + (np.broadcast_to(edge, X.shape) - 0.1) * (1 - blend))
    return X, Z, H, rd


def build_splat(X, Z, H, rd):
    gz, gx = np.gradient(H, SZ / (N - 1), SX / (N - 1))
    s = np.degrees(np.arctan(np.hypot(gx, gz)))
    cover = np.clip(0.75 + 0.35 * noise(903, X, Z, 1 / 70.0), 0, 1)
    rock = T.smoothstep(38, 52, s) * cover + T.smoothstep(27, 40, s) * (1 - cover)
    road = 1 - T.smoothstep(M.ROAD_WIDTH / 2, M.ROAD_WIDTH / 2 + 1.4, rd)
    road *= 1 - T.smoothstep(560, 640, Z)                 # the track fades out past the edge
    meadow = np.clip(1 - cover * 1.4, 0, 1)
    w = np.stack([1 - meadow, rock * 1.6, road * 2.4, meadow * (1 - rock)], -1)
    w[..., 0] *= (1 - road) * (1 - rock)
    w[..., 3] *= (1 - road) * (1 - rock)
    w[..., 1] *= (1 - road)
    w = np.maximum(w, 0) + 1e-4
    w /= w.sum(-1, keepdims=True)
    return w, s, cover


def write_asset(H, W):
    T.write_vterrain(ASSET, H, W)
    meta = Path(str(ASSET) + '.meta')
    meta.write_text(json.dumps({'victus_meta': 1, 'uuid': ASSET_UUID, 'importer': '', 'settings': {}}, indent=2) + '\n\n')


def add_entities():
    count = 0
    for p in sorted((GAME / 'scenes').rglob('*.vscene')):
        if '/tests/view_' in str(p):
            continue
        text = p.read_text()
        if '"Kestrel Terrain"' not in text:
            continue
        d = json.loads(text)
        if any(e['uuid'] == ENTITY_UUID for e in d['entities']):
            d['entities'] = [e for e in d['entities'] if e['uuid'] != ENTITY_UUID]
            i = text.find('"uuid": "' + ENTITY_UUID + '"')
            s0 = text.rfind(',', 0, text.rfind('{', 0, i))
            depth, j = 0, text.rfind('{', 0, i)
            while True:
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            text = text[:s0] + text[j + 1:]
        main = next(e for e in json.loads(text)['entities'] if e['name'] == 'Kestrel Terrain')
        ent = copy.deepcopy(main)
        ent = {'uuid': ENTITY_UUID, 'name': 'Kestrel South Terrain', 'components': ent['components']}
        t = ent['components']['Terrain']
        t['data'] = ASSET_UUID
        t['size'] = [SX, M.HEIGHT, SZ]
        ent['components']['Transform'] = {'position': [0, 0, CENTER_Z], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]}
        end = text.rfind(']')
        body = text[:end].rstrip()
        out = body + ',\n' + HT.fmt(ent, 2).replace('\n', '\n    ').join(['    ', '']) + '\n  ' + text[end:]
        json.loads(out)
        p.write_text(out)
        count += 1
    return count


def add_trees(X, Z, H, s, cover):
    cells_dir = GAME / 'worlds' / 'kestrel'
    for j in (8, 9, 10):
        for p in cells_dir.glob(f'cell_*_{j}.vscene'):
            p.unlink()
    cells = HT.load_cells()
    tpl = HT.templates(cells)
    rng = np.random.default_rng(7511)
    spacing = 3.6
    xs = np.arange(-260.0, 160.0, spacing)
    zs = np.arange(M.SIZE / 2 + 1.0, TREE_Z1 - 2.0, spacing)
    gx, gz = np.meshgrid(xs, zs)
    px = (gx + rng.uniform(-0.45, 0.45, gx.shape) * spacing).ravel()
    pz = (gz + rng.uniform(-0.45, 0.45, gz.shape) * spacing).ravel()
    pz = np.maximum(pz, M.SIZE / 2 + 0.5)    # every tree stays on the backdrop, in the new cells
    fi = (px + SX / 2) / (SX / (N - 1))
    fj = (pz - Z0) / (SZ / (N - 1))
    samp = lambda f: ndimage.map_coordinates(f, [fj, fi], order=1)  # noqa: E731
    y, sl, cv = samp(H), samp(s), samp(cover)
    keep = (sl < 44) & (rng.random(px.shape) < (cv ** 1.15) * 0.26)
    keep &= np.abs(px - road_x(pz)) > M.ROAD_WIDTH / 2 + 2.6
    out = {}
    n = 0
    for i in np.nonzero(keep)[0]:
        x, z = float(px[i]), float(pz[i])
        a = (y[i] - 20) / 110
        if rng.random() < np.clip(0.45 + a * 0.75, 0.35, 0.95):
            kind = 'conifer_a' if rng.random() < 0.55 else 'conifer_b'
        else:
            kind = ['broadleaf_a', 'broadleaf_b', 'broadleaf_c'][rng.choice(3, p=[0.42, 0.38, 0.2])]
        sc = rng.uniform(1.05, 1.5)
        yaw = rng.uniform(0, 360)
        root, kids = tpl[kind]
        name = f'South Tree {n}'
        rid = str(uuid.uuid5(NS, name))
        r = copy.deepcopy(root)
        r['uuid'], r['name'] = rid, name
        h = math.radians(yaw) / 2
        r['components']['Transform'] = {'position': [round(x, 4), round(float(y[i]) - 0.12 - 0.02 * float(sl[i]), 4), round(z, 4)],
                                        'rotation': [0, round(math.sin(h), 7), 0, round(math.cos(h), 7)],
                                        'scale': [round(sc, 5)] * 3}
        ents = [r]
        ids = {k['uuid']: str(uuid.uuid5(NS, f'{name}[{j}]')) for j, k in enumerate(kids)}
        for j, k in enumerate(kids):
            kc = copy.deepcopy(k)
            kc['uuid'], kc['name'], kc['parent'] = ids[k['uuid']], f'{name}[{j}]', rid
            if kc.get('next'):
                kc['next'] = ids.get(kc['next'])
            ents.append(kc)
        key = (int(math.floor(x / 64.0)), int(math.floor(z / 64.0)))
        assert key[1] >= 8, key
        out.setdefault(key, []).append((ents, float(y[i])))
        n += 1
    world_p = GAME / 'worlds' / 'kestrel.vworld'
    world = json.loads(world_p.read_text())
    world['cells'] = [c for c in world['cells'] if not c['name'].endswith(('_8', '_9', '_10'))]
    for (ci, cj), items in sorted(out.items()):
        name = f'cell_{ci}_{cj}'
        ents = [e for es, _ in items for e in es]
        doc = {'format': 'victus.scene', 'version': 1, 'name': name, 'entities': ents}
        (cells_dir / f'{name}.vscene').write_text(HT.fmt(doc) + '\n')
        ys = [y for _, y in items]
        world['cells'].append({'id': str(uuid.uuid5(NS, name)), 'name': name, 'scene': f'worlds/kestrel/{name}.vscene',
                               'bounds': {'min': [ci * 64, min(ys) - 1.0, cj * 64],
                                          'max': [ci * 64 + 64, max(ys) + 24.0, cj * 64 + 64]}})
    world_p.write_text(HT.fmt(world) + '\n')
    return n, len(out)


def main():
    raw = (GAME / 'assets' / 'terrain' / 'kestrel.vterrain').read_bytes()
    n = int(np.frombuffer(raw[8:12], '<u4')[0])
    Hmain = np.frombuffer(raw[16:16 + 2 * n * n], '<u2').reshape(n, n).astype(np.float64) / 65535 * M.HEIGHT
    X, Z, H, rd = build_heights(Hmain)
    W, s, cover = build_splat(X, Z, H, rd)
    write_asset(H, W)
    print('south terrain', ASSET.name, 'height', float(H.min()), float(H.max()), 'max slope', float(s.max()))
    print('scenes', add_entities())
    print('trees, cells', add_trees(X, Z, H, s, cover))


if __name__ == '__main__':
    main()
