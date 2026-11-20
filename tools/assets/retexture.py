# SPDX-License-Identifier: Apache-2.0
"""Give procedural GLB props scanned PBR surfaces (CC0, ambientCG / Poly Haven).

    python3 tools/assets/retexture.py weapons        # game/assets/models/weapons + props
    python3 tools/assets/retexture.py <file.glb> ... # explicit files, default rules

The generators (tools/props/*.py) author shape and design colour as vertex colours with flat
materials. This pass keeps both and adds what a flat surface lacks:

- box-projected UVs (per vertex, dominant normal axis, metres x density) on primitives that get
  a surface, so texel density is uniform and no unwrap is needed;
- a base-colour *detail* texture (scan luminance, mean ~1, so it modulates the design colour
  instead of replacing it) with baked edge-wear/scratch highlights for worn presets;
- the scan's normal map (OpenGL convention, VICTUS generates tangents at import);
- a metallic-roughness texture (G = scan roughness, B = 1) with the factors rescaled so the
  mean roughness stays what the designer chose.

Emissive, glass and already-textured materials are left alone, as are skinned primitives.
Textures are 512 px (mobile budget: one detail + one normal + one MR per surface preset, shared
by every material in the file using that preset). Re-running is idempotent.
"""
from __future__ import annotations

import io
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'characters'))
import ambientcg as acg  # noqa: E402
from gltf_util import read_glb, accessor, Writer, add_image  # noqa: E402

ROOT = acg.ROOT
MODELS = os.path.join(ROOT, 'game', 'assets', 'models')
SIZE = 512

# preset: scan id, tile size in metres, detail contrast, wear amount, normal strength
PRESETS = {
    'polymer': dict(src='Plastic006', tile=0.22, contrast=0.55, wear=0.35, nor=0.8),
    'metal':   dict(src='Metal032', tile=0.30, contrast=0.6, wear=0.5, nor=0.6),
    'rubber':  dict(src='Rubber004', tile=0.12, contrast=0.7, wear=0.0, nor=1.0),
    'leather': dict(src='Leather037', tile=0.10, contrast=0.6, wear=0.15, nor=1.0),
    'fabric':  dict(src='Fabric030', tile=0.08, contrast=0.7, wear=0.0, nor=1.0),
    'paint':   dict(src='PaintedMetal004', tile=0.8, contrast=0.35, wear=0.6, nor=0.7),
}

# material-name rules, first match wins; None = leave untouched
RULES = [
    (r'glow|dot|sight$|lens|glass|mark|light|lamp|emit', None),
    (r'grip|pad|rubber|tyre|tire|seal', 'rubber'),
    (r'glove', 'leather'),
    (r'sleeve|cuff|cloth|web|foam|strap|canvas|fabric|seat', 'fabric'),
    (r'metal|steel|barrel|rail|hinge|bolt', 'metal'),
    (r'shell|frame|slide|body|cell|case|trim|plate', 'polymer'),
]

WEAPON_FILES = [os.path.join(MODELS, 'weapons', f) for f in sorted(os.listdir(os.path.join(MODELS, 'weapons')))
                if f.endswith('.glb') and not f.startswith(('pulse_bolt', 'stun_target'))] + \
               [os.path.join(MODELS, 'props', f) for f in ('arms_case.glb', 'cell_pack.glb', 'field_kit.glb')]


def preset_for(name, rules=RULES):
    n = name.lower()
    for pat, pre in rules:
        if re.search(pat, n):
            return pre
    return None


def _img(path, mode='RGB'):
    return np.asarray(Image.open(path).convert(mode).resize((SIZE, SIZE), Image.LANCZOS)).astype(np.float32) / 255.0


def _png(arr, mode='RGB'):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), mode)
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True); return b.getvalue()


_cache = {}


def wear_mask():
    """Scratch/chip mask from the worn-paint scan: bright, desaturated pixels are bare metal."""
    if 'wear' not in _cache:
        c = _img(acg.material('PaintedMetal004')['diff'])
        sat = c.max(-1) - c.min(-1)
        _cache['wear'] = np.clip((0.35 - sat) * 4.0, 0, 1) * np.clip((c.mean(-1) - 0.35) * 3.0, 0, 1)
    return _cache['wear']


def surface(pre):
    """(detail png, normal png, mr png, mean roughness) for a preset, cached."""
    if pre in _cache:
        return _cache[pre]
    p = PRESETS[pre]; m = acg.material(p['src'])
    lum = _img(m['diff']) @ np.array([0.3, 0.59, 0.11], np.float32)
    lum = lum / max(lum.mean(), 1e-3)
    det = 1.0 + (lum - 1.0) * p['contrast']
    rough = _img(m['rough'], 'L') if 'rough' in m else np.full((SIZE, SIZE), 0.6, np.float32)
    if p['wear']:
        w = wear_mask() * p['wear']
        det = det * (1 - w) + 1.9 * w           # scuffs lighten toward bare substrate
        rough = rough * (1 - w * 0.6)            # and polish smoother
    det = np.clip(det / 1.6, 0, 1)               # stored /1.6, baseColorFactor *1.6 below
    mean_r = float(rough.mean())
    rough_n = np.clip(rough / max(mean_r, 1e-3) * 0.6, 0, 1)
    nor = _img(m['nor'])
    if p['nor'] != 1.0:
        v = nor * 2 - 1; v[..., :2] *= p['nor']; v /= np.linalg.norm(v, axis=-1, keepdims=True); nor = v * 0.5 + 0.5
    mr = np.dstack([np.ones_like(rough_n), rough_n, np.ones_like(rough_n)])
    _cache[pre] = (_png(np.dstack([det] * 3)), _png(nor), _png(mr))
    return _cache[pre]


def box_uv(P, N, tile):
    ax = np.abs(N).argmax(1)
    u = np.where(ax == 0, P[:, 2], P[:, 0])
    v = np.where(ax == 1, P[:, 2], P[:, 1])
    flip = np.take_along_axis(N, ax[:, None], 1)[:, 0] < 0
    u = np.where(flip, -u, u)
    return (np.stack([u, -v], 1) / tile).astype(np.float32)


def retexture(path, rules=RULES, presets=None):
    j, binc = read_glb(path)
    mats = j.get('materials', [])
    plan = {}
    for i, m in enumerate(mats):
        pbr = m.setdefault('pbrMetallicRoughness', {})
        if 'baseColorTexture' in pbr or 'normalTexture' in m or m.get('emissiveFactor') and max(m['emissiveFactor']) > 0:
            continue
        pre = (presets or {}).get(m.get('name')) or preset_for(m.get('name', ''), rules)
        if pre:
            plan[i] = pre
    if not plan:
        return 0
    # Rebuild the binary chunk, keeping accessor and image indices.
    olda = j['accessors']; arrays = []
    for i, a in enumerate(olda):
        arrays.append((accessor(j, binc, i), a))
    imgs = [(im, bytes(binc[j['bufferViews'][im['bufferView']].get('byteOffset', 0):
                            j['bufferViews'][im['bufferView']].get('byteOffset', 0) + j['bufferViews'][im['bufferView']]['byteLength']]))
            for im in j.get('images', []) if 'bufferView' in im]
    oldbv = j['bufferViews']
    w = Writer(j)
    for arr, a in arrays:
        bvt = oldbv[a['bufferView']].get('target')
        idx = w.add(arr if arr.ndim == 1 else arr, a['type'], target=bvt, normalized=a.get('normalized', False))
        na = j['accessors'][idx]
        for k in ('min', 'max'):
            if k in a: na[k] = a[k]
    for im, data in imgs:
        while len(w.bin) % 4: w.bin.append(0)
        j['bufferViews'].append({'buffer': 0, 'byteOffset': len(w.bin), 'byteLength': len(data)})
        w.bin += data; im['bufferView'] = len(j['bufferViews']) - 1
    tex = {}
    for pre in sorted(set(plan.values())):
        d, n, mr = surface(pre)
        tex[pre] = (add_image(w, d, f'{pre}_detail'), add_image(w, n, f'{pre}_normal'), add_image(w, mr, f'{pre}_mr'))
    done, lift = set(), set()
    for mesh in j.get('meshes', []):
        for prim in mesh['primitives']:
            mi = prim.get('material')
            if mi not in plan or 'JOINTS_0' in prim['attributes']:
                continue
            at = prim['attributes']
            P = accessor(j, w.bin, at['POSITION']); N = accessor(j, w.bin, at['NORMAL'])
            at['TEXCOORD_0'] = w.add(box_uv(P, N, PRESETS[plan[mi]]['tile']), 'VEC2')
            at.pop('TANGENT', None)
            if 'COLOR_0' in at:  # detail is stored /1.6: lift the design colour to compensate
                C = accessor(j, w.bin, at['COLOR_0']).astype(np.float32)
                ca = j['accessors'][at['COLOR_0']]
                if ca['componentType'] != 5126: C = C / (255.0 if ca['componentType'] == 5121 else 65535.0)
                C = C.copy(); C[:, :3] = np.clip(C[:, :3] * 1.6, 0, 1)
                at['COLOR_0'] = w.add(C.astype(np.float32), ca['type'])
            else:
                lift.add(mi)
            done.add(mi)
    for mi in done:
        m = mats[mi]; pbr = m['pbrMetallicRoughness']; t = tex[plan[mi]]
        pbr['baseColorTexture'] = {'index': t[0]}
        if mi in lift:
            cf = pbr.get('baseColorFactor', [1, 1, 1, 1])
            pbr['baseColorFactor'] = [min(c * 1.6, 1.0) for c in cf[:3]] + [cf[3]]
        pbr['metallicRoughnessTexture'] = {'index': t[2]}
        pbr['roughnessFactor'] = float(min(1.0, pbr.get('roughnessFactor', 0.8) / 0.6))
        m['normalTexture'] = {'index': t[1], 'scale': 1.0}
    w.save(path)
    return len(done)


def main(argv):
    files = WEAPON_FILES if argv[:1] == ['weapons'] else argv
    for f in files:
        n = retexture(f)
        print(f'RETEX {os.path.relpath(f, ROOT)}: {n} materials')


if __name__ == '__main__':
    main(sys.argv[1:])
