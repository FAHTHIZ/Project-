# SPDX-License-Identifier: Apache-2.0
"""Forest the steep valley sides around the prologue camp without re-rolling the valley.

    python3 tools/world/add_hillside_trees.py           # idempotent: replaces earlier output

worldgen.place_trees keeps trees off slopes of 36 degrees and more, which left the valley side
east of the camp (32 to 45 degrees, forest cover 0.8 to 0.9) as a bare face filling the view from
the briefing. Re-running worldgen would reshuffle every tree in the valley (one random sequence),
so this tool adds a second, separate set: a jittered grid with its own seed over ground within
RING metres of the camp, slope 30 to 48 degrees, using the same cover-driven density, clear of
the existing trees, roads, trail and pads. Each tree is a copy of an existing cell tree of the
chosen type (trunk collider, LOD meshes), named "Hillside Tree <n>" with uuid5 ids, appended to
its streaming cell. Steeper ground grows smaller trees.
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
import uuid
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import worldgen as G  # noqa: E402
import terrain_gen as T  # noqa: E402
import worldmap as M  # noqa: E402

GAME = G.ROOT / 'game'
CELLS = GAME / 'worlds' / 'kestrel'
PREFIX = 'Hillside Tree '
NS = uuid.UUID('6f1d3c52-8b0e-4f43-9d7e-3a1e2c4b5a69')
RING = 150.0
SLOPE_MIN, SLOPE_MAX = 30.0, 48.0
MESH = {
    'broadleaf_a': '49aad981-75c0-4e80-98c0-3e84eac1da05',
    'broadleaf_b': '2fb4ce2e-553e-4e37-96ec-603bbfcb317f',
    'broadleaf_c': '87013beb-14ee-4187-901d-d13e3e96fada',
    'conifer_a': 'aafbdcb8-098e-4b76-8a30-0a997c291c33',
    'conifer_b': '883eba54-fbfd-4161-b30f-1ffab94c43a9',
}


def fmt(obj, ind=0):
    """JSON in the engine's scene style: objects one key per line, number arrays inline."""
    pad = '  ' * ind
    if isinstance(obj, dict):
        if not obj:
            return '{}'
        items = [f'{pad}  {json.dumps(k)}: {fmt(v, ind + 1)}' for k, v in obj.items()]
        return '{\n' + ',\n'.join(items) + f'\n{pad}}}'
    if isinstance(obj, list):
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in obj):
            return '[' + ', '.join(json.dumps(v) for v in obj) + ']'
        if not obj:
            return '[]'
        return '[\n' + ',\n'.join(f'{pad}  {fmt(v, ind + 1)}' for v in obj) + f'\n{pad}]'
    return json.dumps(obj)


def load_cells():
    cells = {}
    for p in sorted(CELLS.glob('cell_*.vscene')):
        cells[p] = json.loads(p.read_text())
    return cells


def templates(cells):
    """One root + children per tree type, taken from the existing cells."""
    out = {}
    for d in cells.values():
        kids = {}
        for e in d['entities']:
            if e.get('parent'):
                kids.setdefault(e['parent'], []).append(e)
        for e in d['entities']:
            if e.get('parent') or not e['name'].startswith('Tree '):
                continue
            ch = kids.get(e['uuid'], [])
            mesh = next((c['components'].get('MeshRenderer', {}).get('mesh') for c in ch), None)
            kind = next((k for k, m in MESH.items() if m == mesh), None)
            if kind and kind not in out:
                out[kind] = (e, ch)
        if len(out) == len(MESH):
            break
    return out


def strip_previous(cells):
    for p, d in cells.items():
        drop = {e['uuid'] for e in d['entities'] if e['name'].startswith(PREFIX) and not e.get('parent')}
        if not drop:
            continue
        d['entities'] = [e for e in d['entities'] if e['uuid'] not in drop and e.get('parent') not in drop]
        text = p.read_text()
        # remove the appended block: earlier runs append after the generator's own entities
        mark = text.find('"name": "' + PREFIX)
        start = text.rfind(',\n    {', 0, mark)
        end = text.rfind('\n  ]')
        p.write_text(text[:start] + text[end:])


def main():
    cells = load_cells()
    strip_previous(cells)
    cells = load_cells()
    tpl = templates(cells)
    H, masks, cover = G.load_layout()
    slope = T.slope_deg(H)
    camp = M.POIS['camp']
    rng = np.random.default_rng(7411)
    spacing = 3.6
    xs = np.arange(camp['x'] - RING, camp['x'] + RING, spacing)
    zs = np.arange(camp['z'] - RING, min(camp['z'] + RING, M.SIZE / 2 - 4), spacing)
    gx, gz = np.meshgrid(xs, zs)
    px = (gx + rng.uniform(-0.45, 0.45, gx.shape) * spacing).ravel()
    pz = (gz + rng.uniform(-0.45, 0.45, gz.shape) * spacing).ravel()
    at = lambda f: T.sample_grid(f, px, pz)  # noqa: E731
    s = at(slope)
    c = at(cover)
    keep = np.hypot(px - camp['x'], pz - camp['z']) < RING
    keep &= (s >= SLOPE_MIN) & (s < SLOPE_MAX)
    keep &= rng.random(px.shape) < (c ** 1.15) * 0.62
    keep &= at(masks['road_dist']) > M.ROAD_WIDTH / 2 + 2.6
    keep &= at(masks['trail_dist']) > M.TRAIL_WIDTH / 2 + 1.2
    keep &= at(masks['creek_dist']) > M.CREEK_WIDTH / 2 + 1.8
    keep &= at(masks['pads']) < 0.05
    keep &= at(masks['ravine']) < 0.25
    existing = []
    for d in cells.values():
        for e in d['entities']:
            if not e.get('parent') and e['name'].startswith(('Tree ', 'Rock ')):
                p = e['components']['Transform']['position']
                existing.append((p[0], p[2]))
    ex = np.array(existing)
    y = at(H)
    added = {}
    n = 0
    for i in np.nonzero(keep)[0]:
        x, z = float(px[i]), float(pz[i])
        if len(ex) and np.min((ex[:, 0] - x) ** 2 + (ex[:, 1] - z) ** 2) < 2.6 ** 2:
            continue
        a = (y[i] - 20) / 110
        if rng.random() < np.clip(0.45 + a * 0.75, 0.35, 0.95):
            kind = 'conifer_a' if rng.random() < 0.55 else 'conifer_b'
        else:
            kind = ['broadleaf_a', 'broadleaf_b', 'broadleaf_c'][rng.choice(3, p=[0.42, 0.38, 0.2])]
        sc = rng.uniform(1.0, 1.45) * (1.0 - 0.25 * (s[i] - SLOPE_MIN) / (SLOPE_MAX - SLOPE_MIN))
        yaw = rng.uniform(0, 360)
        root, kids = tpl[kind]
        name = f'{PREFIX}{n}'
        rid = str(uuid.uuid5(NS, name))
        r = copy.deepcopy(root)
        r['uuid'] = rid
        r['name'] = name
        h = math.radians(yaw) / 2
        # sink the root on the downhill side so no trunk base floats on a slope
        r['components']['Transform'] = {'position': [round(x, 4), round(float(y[i]) - 0.12 - 0.02 * s[i], 4), round(z, 4)],
                                        'rotation': [0, round(math.sin(h), 7), 0, round(math.cos(h), 7)],
                                        'scale': [round(sc, 5)] * 3}
        ents = [r]
        ids = {k['uuid']: str(uuid.uuid5(NS, f'{name}[{j}]')) for j, k in enumerate(kids)}
        for j, k in enumerate(kids):
            kc = copy.deepcopy(k)
            kc['uuid'] = ids[k['uuid']]
            kc['name'] = f'{name}[{j}]'
            kc['parent'] = rid
            if kc.get('next'):
                kc['next'] = ids.get(kc['next'])
            ents.append(kc)
        ci, cj = int(math.floor(x / 64.0)), int(math.floor(z / 64.0))
        added.setdefault(CELLS / f'cell_{ci}_{cj}.vscene', []).extend(ents)
        ex = np.vstack([ex, [x, z]])
        n += 1
    for p, ents in added.items():
        if p not in cells:
            print('skip (no cell)', p.name, len(ents))
            continue
        text = p.read_text()
        end = text.rfind('\n  ]')
        block = ''.join(',\n    ' + fmt(e, 2) for e in ents)
        out = text[:end] + block + text[end:]
        json.loads(out)
        p.write_text(out)
        print(p.name, sum(1 for e in ents if not e.get('parent')), 'trees')
    print('hillside trees', n)


if __name__ == '__main__':
    main()
