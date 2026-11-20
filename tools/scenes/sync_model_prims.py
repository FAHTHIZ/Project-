# SPDX-License-Identifier: Apache-2.0
"""Keep every scene's per-primitive prop entities in step with the model files.

    python3 tools/scenes/sync_model_prims.py [--check] [scene.vscene ...]

`Scene.prop()` (tools/scenes/vscene.py) writes one child entity "<name>[i]" with a MeshRenderer
(mesh = model uuid, mesh_index = i) per glTF primitive. When a model is rebuilt with more
primitives (e.g. the Blender PC-7 has 8 materials where the procedural one had 3), scenes written
earlier keep only the old children and the new parts silently never draw. This pass finds those
groups (siblings with the same model, indices 0..n-1, not skinned) and adds the missing children as
copies of "[0]" with stable uuid5 ids, or removes children past the model's primitive count.
--check only reports.
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.path.join(ROOT, 'game')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'characters'))
from gltf_util import read_glb  # noqa: E402

NS = uuid.UUID("5e3c1f0a-7b2d-4c11-9f6e-50b5a0c0e001")
PAT = re.compile(r'^(.*)\[(\d+)\]$')


def model_prims():
    out = {}
    for meta in glob.glob(os.path.join(GAME, 'assets', '**', '*.glb.meta'), recursive=True):
        try:
            u = json.load(open(meta))['uuid']
            j, _ = read_glb(meta[:-5])
        except Exception:
            continue
        out[u] = (os.path.relpath(meta[:-5], GAME), sum(len(m['primitives']) for m in j.get('meshes', [])))
    return out


def sync(path, prims, check):
    s = json.load(open(path))
    E = s['entities']
    groups = {}
    for k, e in enumerate(E):
        m = PAT.match(e.get('name', ''))
        c = e.get('components', {})
        mr = c.get('MeshRenderer')
        if not m or not mr or 'SkinnedMesh' in c or mr.get('mesh') not in prims:
            continue
        groups.setdefault((e.get('parent'), m.group(1), mr['mesh']), []).append((int(m.group(2)), k))
    add, drop, report = [], set(), []
    for (parent, base, mesh), items in groups.items():
        idx = sorted(i for i, _ in items)
        if idx != list(range(len(idx))):
            continue
        if any(E[k]['components']['MeshRenderer'].get('mesh_index') != i for i, k in items):
            continue
        need = prims[mesh][1]
        if len(idx) == need:
            continue
        report.append(f'{base}: {len(idx)} -> {need} ({prims[mesh][0]})')
        if len(idx) < need:
            first = E[dict(items)[0]]
            last = max(k for _, k in items)
            for i in range(len(idx), need):
                ne = json.loads(json.dumps(first))
                ne['name'] = f'{base}[{i}]'
                ne['uuid'] = str(uuid.uuid5(NS, f'sync/{os.path.basename(path)}/{parent}/{base}[{i}]'))
                ne['components']['MeshRenderer']['mesh_index'] = i
                add.append((last, ne))
        else:
            drop.update(k for i, k in items if i >= need)
    if report and not check:
        ins = {}
        for last, ne in add:
            ins.setdefault(last, []).append(ne)
        out = []
        for k, e in enumerate(E):
            if k in drop:
                continue
            out.append(e)
            out.extend(ins.get(k, []))
        s['entities'] = out
        with open(path, 'w') as f:
            json.dump(s, f, indent=1)
            f.write('\n')
    return report


def main(argv):
    check = '--check' in argv
    files = [a for a in argv if a.endswith('.vscene')] or sorted(glob.glob(os.path.join(GAME, 'scenes', '**', '*.vscene'), recursive=True))
    prims = model_prims()
    total = 0
    for f in files:
        rep = sync(f, prims, check)
        if rep:
            total += len(rep)
            print(os.path.relpath(f, ROOT))
            seen = {}
            for r in rep:
                seen[r] = seen.get(r, 0) + 1
            for r, n in seen.items():
                print(f'  {r}' + (f'  x{n}' if n > 1 else ''))
    print(f'{"would fix" if check else "fixed"} {total} prop groups in {len(files)} scenes')


if __name__ == '__main__':
    main(sys.argv[1:])
