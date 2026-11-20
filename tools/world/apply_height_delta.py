# SPDX-License-Identifier: Apache-2.0
"""Re-seat placed content after a local terrain regrade, without re-rolling the world.

    git show HEAD:game/assets/terrain/kestrel.vterrain > /tmp/old.vterrain
    python3 tools/world/worldgen.py terrain
    python3 tools/world/apply_height_delta.py /tmp/old.vterrain

`worldgen.py all` re-places every tree from one random sequence, so a regrade of one pad would
reshuffle the whole valley and drop the hand edits in scenes/world/kestrel.vscene. This tool keeps
every placement and moves it with the ground instead:

  * root entities of every scene and streaming cell that stand on the old ground (their y within
    -3..+4 m of it) move by the height change at their x/z;
  * canopy proxy GLB vertices move by the height change under each vertex;
  * the vworld cell bounds widen by the change inside each cell.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'game'
SIZE = 1024.0
N = 513


def load_heights(path):
    b = Path(path).read_bytes()
    magic, ver, n, _ = struct.unpack('<4sIII', b[:16])
    assert magic == b'VTRN' and n == N, (magic, n)
    return np.frombuffer(b[16:16 + n * n * 2], dtype='<u2').reshape(n, n).astype(np.float64) / 65535.0 * 300.0


def sampler(G):
    def at(x, z):
        x = np.asarray(x, dtype=np.float64)
        z = np.asarray(z, dtype=np.float64)
        gx = np.clip((x + SIZE / 2) / SIZE * (N - 1), 0, N - 1.000001)
        gz = np.clip((z + SIZE / 2) / SIZE * (N - 1), 0, N - 1.000001)
        i = np.floor(gx).astype(int)
        j = np.floor(gz).astype(int)
        fx = gx - i
        fz = gz - j
        return (G[j, i] * (1 - fx) * (1 - fz) + G[j, i + 1] * fx * (1 - fz) +
                G[j + 1, i] * (1 - fx) * fz + G[j + 1, i + 1] * fx * fz)
    return at


def _num(v):
    t = f'{v:.4f}'.rstrip('0').rstrip('.')
    return t if t not in ('-0', '') else '0'


def patch_scene(path, old, delta):
    """Moves ground-standing root entities. Edits the position lines in place so the scene keeps
    the engine's own formatting (a json round trip would reflow every inline array)."""
    text = path.read_text()
    d = json.loads(text)
    target = {}
    for e in d.get('entities', []):
        if e.get('parent'):
            continue
        t = e.get('components', {}).get('Transform')
        if not t or 'position' not in t:
            continue
        x, y, z = t['position']
        dh = float(delta(x, z))
        if abs(dh) < 0.02:
            continue
        g = float(old(x, z))
        if not (g - 3.0 <= y <= g + 4.0):
            continue
        target[e['uuid']] = y + dh
    if not target:
        return 0
    # any formatting: find the entity's uuid key, then its first position array, and swap only the
    # middle number (whitespace and line breaks inside the array are kept)
    import re
    out = text
    for u, y in target.items():
        m = re.search(r'"uuid":\s*"' + re.escape(u) + '"', out)
        q = out.index('"position"', m.end())
        o = out.index('[', q)
        c = out.index(']', o)
        parts = out[o + 1:c].split(',')
        lead = parts[1][:len(parts[1]) - len(parts[1].lstrip())]
        trail = parts[1][len(parts[1].rstrip()):]
        parts[1] = lead + _num(y) + trail
        out = out[:o + 1] + ','.join(parts) + out[c:]
    chk = json.loads(out)
    for e in chk['entities']:
        if e['uuid'] in target:
            assert abs(e['components']['Transform']['position'][1] - target[e['uuid']]) < 1e-3
    path.write_text(out)
    return len(target)


def world_offsets(scene):
    by = {e['uuid']: e for e in scene['entities']}

    def off(e):
        p = e['components'].get('Transform', {}).get('position', [0, 0, 0])
        if e.get('parent') in by:
            q = off(by[e['parent']])
            return [p[0] + q[0], p[1] + q[1], p[2] + q[2]]
        return list(p)
    return by, off


def patch_canopy(delta):
    persistent = json.loads((GAME / 'scenes/world/kestrel.vscene').read_text())
    by, off = world_offsets(persistent)
    text = {e['uuid']: json.dumps(e['components']) for e in persistent['entities']}
    moved = 0
    for glb in sorted((GAME / 'assets/models/world').glob('canopy_*.glb')):
        uuid = json.loads(Path(str(glb) + '.meta').read_text())['uuid']
        owner = next((u for u, s in text.items() if uuid in s), None)
        if owner is None:
            continue
        ox, oy, oz = off(by[owner])
        b = bytearray(glb.read_bytes())
        jlen = struct.unpack('<I', b[12:16])[0]
        j = json.loads(b[20:20 + jlen])
        bin0 = 20 + jlen + 8
        changed = False
        for mesh in j['meshes']:
            for prim in mesh['primitives']:
                acc = j['accessors'][prim['attributes']['POSITION']]
                bv = j['bufferViews'][acc['bufferView']]
                start = bin0 + bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
                pos = np.frombuffer(bytes(b[start:start + acc['count'] * 12]), dtype='<f4').reshape(-1, 3).copy()
                dh = delta(pos[:, 0] + ox, pos[:, 2] + oz)
                if np.abs(dh).max() < 0.02:
                    continue
                pos[:, 1] += dh.astype(np.float32)
                b[start:start + pos.nbytes] = pos.astype('<f4').tobytes()
                acc['min'] = [float(v) for v in pos.min(axis=0)]
                acc['max'] = [float(v) for v in pos.max(axis=0)]
                changed = True
        if changed:
            js = json.dumps(j, separators=(',', ':')).encode()
            js += b' ' * ((4 - len(js) % 4) % 4)
            assert len(js) <= jlen, 'json chunk grew past its slot; rebuild with worldgen canopy'
            js += b' ' * (jlen - len(js))
            b[20:20 + jlen] = js
            glb.write_bytes(bytes(b))
            moved += 1
    return moved


def patch_world_bounds(D):
    path = GAME / 'worlds/kestrel.vworld'
    text = path.read_text()
    w = json.loads(text)
    grow = {}
    for c in w['cells']:
        lo, hi = c['bounds']['min'], c['bounds']['max']
        i0 = int(np.floor((lo[0] + SIZE / 2) / SIZE * (N - 1)))
        i1 = int(np.ceil((hi[0] + SIZE / 2) / SIZE * (N - 1)))
        j0 = int(np.floor((lo[2] + SIZE / 2) / SIZE * (N - 1)))
        j1 = int(np.ceil((hi[2] + SIZE / 2) / SIZE * (N - 1)))
        blk = D[max(j0, 0):min(j1, N - 1) + 1, max(i0, 0):min(i1, N - 1) + 1]
        if blk.size and np.abs(blk).max() >= 0.02:
            grow[c['name']] = (lo[1] + min(float(blk.min()), 0.0), hi[1] + max(float(blk.max()), 0.0))
    lines = text.split('\n')
    cur = None
    for k, line in enumerate(lines):
        st = line.lstrip()
        if st.startswith('"name": "cell_'):
            cur = st.split('"')[3]
        elif cur in grow and (st.startswith('"min": [') or st.startswith('"max": [')):
            head, rest = line.split('[', 1)
            xs, ys, zs = rest.split(']', 1)[0].split(',')
            y = grow[cur][0 if st.startswith('"min"') else 1]
            lines[k] = f'{head}[{xs.strip()}, {y!r}, {zs.strip()}]' + rest.split(']', 1)[1]
    out = '\n'.join(lines)
    json.loads(out)
    path.write_text(out)
    return len(grow)


def main():
    old_h = load_heights(sys.argv[1])
    new_h = load_heights(GAME / 'assets/terrain/kestrel.vterrain')
    D = new_h - old_h
    old, delta = sampler(old_h), sampler(D)
    total = 0
    for p in sorted(list((GAME / 'scenes').rglob('*.vscene')) + list((GAME / 'worlds/kestrel').glob('*.vscene'))):
        m = patch_scene(p, old, delta)
        if m:
            print(f'{p.relative_to(GAME)}: {m} entities re-seated')
            total += m
    print('canopy proxies patched', patch_canopy(delta))
    print('cells widened', patch_world_bounds(D))
    print('entities re-seated', total, 'max change', float(np.abs(D).max()))


if __name__ == '__main__':
    main()
