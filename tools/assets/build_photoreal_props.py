# SPDX-License-Identifier: Apache-2.0
"""Replace the generated forest props with photoscanned CC0 models (Poly Haven).

    BLENDER=/path/to/blender python3 tools/assets/build_photoreal_props.py [names...]

Each output keeps its path, .meta UUID, primitive count and footprint, so the world cells, the
foliage scatter and the colliders generated earlier stay valid. Sources are decimated to a
per-instance triangle budget sized for the scatter density (VICTUS then builds 3 coarser LODs on
import, ADR model importer v5). Budgets assume the Hot 10S class GPU (Mali-G52): ground cover is
drawn thousands of times, so grass clumps stay under 100 triangles and ferns around 400.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import polyhaven as ph  # noqa: E402

ROOT = ph.ROOT
ENV = os.path.join(ROOT, 'game', 'assets', 'models', 'env')
BLENDER = os.environ.get('BLENDER', 'blender')
WORKER = os.path.join(os.path.dirname(__file__), 'blender_prop.py')


def src(asset):
    return ph.model(asset, '1k')


def part(asset, objects=None, offset=(0, 0, 0), yaw=0.0, scale=1.0):
    return {'src': src(asset), 'objects': objects or [], 'offset': list(offset), 'yaw': yaw, 'scale': scale}


# name -> job (see blender_prop.py). Sizes match the generated originals (tools/props/build_forest.py).
JOBS = {
    'rock_a': dict(groups=[dict(name='rock_a_Stone', tris=900, alpha='opaque',
                                parts=[part('rock_moss_set_02', ['rock_moss_set_02_rock07'])])],
                   fit={'axis': 'length', 'size': 1.67}, sink=0.04),
    'rock_b': dict(groups=[dict(name='rock_b_Stone', tris=1400, alpha='opaque',
                                parts=[part('rock_moss_set_02', ['rock_moss_set_02_rock11'])])],
                   fit={'axis': 'height', 'size': 1.25}, sink=0.06),
    'rock_c': dict(groups=[dict(name='rock_c_Stone', tris=500, alpha='opaque',
                                parts=[part('rock_moss_set_02', ['rock_moss_set_02_rock09'])])],
                   fit={'axis': 'length', 'size': 0.77}, sink=0.02),
    'log_a': dict(groups=[dict(name='log_a_Bark', tris=1600, alpha='opaque',
                               parts=[part('dead_tree_trunk_02')])],
                  fit={'axis': 'length', 'size': 4.5}, sink=0.05),
    'stump_a': dict(groups=[dict(name='stump_a_Bark', tris=1000, alpha='opaque',
                                 parts=[part('tree_stump_01')])],
                    fit={'axis': 'height', 'size': 0.62}, sink=0.03),
    'fern_a': dict(groups=[dict(name='fern_a_Fronds', tris=420, alpha='mask', double=True,
                                parts=[part('fern_02', ['fern_02_b'])])],
                   fit={'axis': 'height', 'size': 0.5}),
    'fern_b': dict(groups=[dict(name='fern_b_Fronds', tris=360, alpha='mask', double=True,
                                parts=[part('fern_02', ['fern_02_c'])])],
                   fit={'axis': 'height', 'size': 0.45}),
    'fern_hero': dict(groups=[dict(name='fern_hero_Fronds', tris=1800, alpha='mask', double=True,
                                   parts=[part('fern_02', ['fern_02_b'], (0, 0, 0), 0),
                                          part('fern_02', ['fern_02_c'], (0.35, 0, 0.25), 120),
                                          part('fern_02', ['fern_02_a'], (-0.3, 0, 0.2), 230),
                                          part('fern_02', ['fern_02_d'], (0.05, 0, -0.35), 300)])],
                      fit={'axis': 'height', 'size': 0.95}),
    'grass_a': dict(groups=[dict(name='grass_a_Blades', tris=72, alpha='mask', double=True,
                                 parts=[part('grass_medium_01', ['grass_medium_01_tall_a_LOD0']),
                                        part('grass_medium_01', ['grass_medium_01_tall_c_LOD0'], (0.08, 0, 0.05), 140)])],
                    fit={'axis': 'height', 'size': 0.55}),
    'grass_b': dict(groups=[dict(name='grass_b_Blades', tris=40, alpha='mask', double=True,
                                 parts=[part('grass_medium_01', ['grass_medium_01_tall_b_LOD0'])])],
                    fit={'axis': 'height', 'size': 0.38}),
    'shrub_a': dict(groups=[dict(name='shrub_a_Leaves', tris=1500, alpha='mask', double=True,
                                 parts=[part('shrub_02', ['shrub_02_d'])])],
                    fit={'axis': 'height', 'size': 1.05}),
    'shrub_b': dict(groups=[dict(name='shrub_b_Leaves', tris=2200, alpha='mask', double=True,
                                 parts=[part('shrub_02', ['shrub_02_c'])])],
                    fit={'axis': 'height', 'size': 1.7}),
}


def build(name: str) -> str:
    job = dict(JOBS[name])
    job['out'] = os.path.join(ENV, f'{name}.glb')
    job.setdefault('tex_size', 1024)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(job, f)
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '-P', WORKER, '--', f.name],
                       capture_output=True, text=True)
    os.unlink(f.name)
    ok = [l for l in r.stdout.splitlines() if l.startswith('PROP_OK')]
    if r.returncode != 0 or not ok:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f'{name}: blender failed')
    return ok[0]


def main() -> int:
    names = sys.argv[1:] or list(JOBS)
    for n in names:
        print(build(n), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
