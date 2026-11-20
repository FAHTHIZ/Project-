# SPDX-License-Identifier: Apache-2.0
"""Rebuild the human cast from Microsoft Rocketbox avatars (MIT licence).

    BLENDER=/path/to/blender python3 tools/assets/build_rocketbox_cast.py [sops_anchor ...]

For every character the existing game file (game/assets/models/characters/sops_*.glb from
tools/characters/build_humans.py) supplies the skeleton: the 21 joint names, hierarchy, rest
rotations and all 22 animation clips, which scripts, IK, attachments and cutscenes rely on.
The Rocketbox avatar supplies everything visible:

- the scanned-quality mesh, posed into the rig's rest pose by tools/assets/blender_rocketbox.py;
- skin weights from its Biped bones merged onto the 21 joints;
- the 11 face morphs lib/face.luau drives (Blink, JawOpen, Smile, Frown, BrowUp, BrowDown,
  MouthO, LookL/R/Up/Down), mixed from its ARKit and viseme blendshapes, so lip sync, blinks
  and expressions are those of a real facial rig;
- colour, normal and roughness textures (from its specular map), resampled for mobile; the US
  ACU camouflage is re-dyed to each character's unit palette and national insignia are
  painted out (Halyard and Greyline are fictional).

Joint translations are rewritten to the avatar's proportions; animation translation channels
are re-based on the new rest offsets (the hips' motion is scaled by the hip-height ratio).
"""
from __future__ import annotations

import colorsys
import io
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'characters'))
from gltf_util import read_glb, accessor, Writer, node_globals, add_image  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
CHARS = os.path.join(ROOT, 'game', 'assets', 'models', 'characters')
RB = os.path.join(ROOT, '.cache', 'rocketbox')
BLENDER = os.environ.get('BLENDER', 'blender')
JOINTS = ["Hips", "Spine", "Chest", "Neck", "Head", "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
          "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R", "UpperLeg.L", "LowerLeg.L", "Foot.L", "Toe.L",
          "UpperLeg.R", "LowerLeg.R", "Foot.R", "Toe.R"]

# character -> (Rocketbox avatar, uniform dye (sRGB hex) or None, texture size for body)
CAST = {
    'sops_anchor': ('Military_Male_06', '#55603f'),
    'sops_brick': ('Military_Male_01', '#525c3e'),
    'sops_tally': ('Military_Male_03', '#606a48'),
    'sops_explorer': ('Military_Male_02', '#6a6a52'),   # Major Venn: auditor's older-pattern fatigues
    'sops_patch': ('Military_Female_01', '#5d6a55'),
    'sops_echo': ('Military_Female_02', '#4a5446'),
    'sops_ranger': ('Male_Adult_05', None),              # Hollis, forestry service
    'sops_greyline_a': ('Military_Male_04', '#5c6064'),  # Greyline contractor greys
    'sops_greyline_b': ('Security_Male_01', None),
}
HEAD_MATS = ('head', 'hair', 'eye', 'lash', 'teeth', 'tongue')
DROP_MATS = ('knife',)  # non-lethal canon: no blades on the kit


def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def hexrgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def load_img(path, size):
    im = Image.open(path)
    has_a = im.mode in ('RGBA', 'LA') and np.asarray(im.convert('RGBA'))[..., 3].min() < 250
    im = im.convert('RGBA' if has_a else 'RGB')
    if max(im.size) > size:
        im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0, has_a


def dye(rgb, target_hex, protect_bright=True):
    """Re-dye low-saturation camouflage to the unit colour, keeping its pattern and shading.
    Skin (warm, saturated), whites of the eyes and near-black hair are left alone."""
    hsv = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).convert('HSV')).astype(np.float32) / 255.0
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    lum = rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    camo = (s < 0.28) & (v > 0.12)
    if protect_bright:
        camo &= lum < 0.8
    skinish = (h < 0.14) & (s > 0.22)
    m = (camo & ~skinish).astype(np.float32)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255.0
    t = hexrgb(target_hex)
    ref = float((lum * m).sum() / max(m.sum(), 1.0))
    rel = (lum / max(ref, 1e-3))[..., None]
    tinted = t[None, None, :] * rel
    grey = np.repeat((float(t @ np.array([0.3, 0.59, 0.11])) * rel), 3, -1)
    out = np.clip(0.72 * tinted + 0.28 * grey, 0, 1)   # keep the dyed cloth from looking toy-saturated
    return rgb * (1 - m[..., None]) + out * m[..., None]


def enc(arr, alpha=False):
    """PNG when alpha matters, high-quality JPEG otherwise (photographic maps; the importer re-encodes
    to BC7/ASTC anyway, so this only keeps the public repo small)."""
    if alpha or arr.shape[-1] == 4:
        return png(arr), 'image/png'
    b = io.BytesIO(); Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(b, 'JPEG', quality=92, subsampling=0)
    return b.getvalue(), 'image/jpeg'


def add_tex(w, arr, name, alpha=False):
    data, mime = enc(arr, alpha)
    t = add_image(w, data, name)
    w.j['images'][-1]['mimeType'] = mime
    return t


def png(arr):
    mode = 'RGBA' if arr.shape[-1] == 4 else 'RGB'
    b = io.BytesIO(); Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), mode).save(b, 'PNG', optimize=True)
    return b.getvalue()


def find_tex(folder, mat, kind):
    base = mat.split('.')[0]
    cands = [f for f in os.listdir(folder) if f.startswith(base) and kind in f and f.endswith(('.tga', '.png', '.jpg'))]
    if not cands:
        stem = base.rsplit('_', 1)[-1]
        cands = [f for f in os.listdir(folder) if f'_{stem}_' in f and kind in f]
    return os.path.join(folder, sorted(cands)[0]) if cands else None


def bake(avatar, joints):
    fbx = os.path.join(RB, avatar, f'{avatar}_facial.fbx')
    out = os.path.join(tempfile.gettempdir(), f'rb_{avatar}.npz')
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'fbx': fbx, 'out': out, 'joints': joints}, f)
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', os.path.join(HERE, 'blender_rocketbox.py'), '--', f.name],
                       capture_output=True, text=True)
    os.unlink(f.name)
    if 'RB_OK' not in r.stdout:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:]); raise SystemExit(f'bake failed: {avatar}')
    return np.load(out, allow_pickle=False)


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def build(char):
    avatar, uniform = CAST[char]
    path = os.path.join(CHARS, char + '.glb')
    src = os.path.join(RB, '_src', char + '.glb')   # the build_humans.py original (rig + clips)
    if not os.path.exists(src):
        jj, _ = read_glb(path)
        if 'build_humans' not in jj['asset'].get('generator', ''):
            raise SystemExit(f'{src} missing: regenerate it with tools/characters/build_humans.py')
        os.makedirs(os.path.dirname(src), exist_ok=True); open(src, 'wb').write(open(path, 'rb').read())
    j, binc = read_glb(src)
    skin = j['skins'][0]
    jn = {j['nodes'][i]['name']: i for i in skin['joints']}
    g, parent = node_globals(j)
    old_pos = {n: np.array(g[i][0]) for n, i in jn.items()}
    D = bake(avatar, {n: list(map(float, p)) for n, p in old_pos.items()})
    new_pos = {n: D['jpos'][k].astype(np.float64) for k, n in enumerate(JOINTS)}

    # --- skeleton: new rest translations (rotations unchanged) ------------------------------
    old_t = {n: np.array(j['nodes'][i].get('translation', [0, 0, 0]), np.float64) for n, i in jn.items()}
    for n, i in jn.items():
        p = parent.get(i)
        if p is None or p not in skin['joints']:
            rootR = qmat(g[p][1]) if p is not None else np.eye(3)
            rootT = np.array(g[p][0]) if p is not None else np.zeros(3)
            t = rootR.T @ (new_pos[n] - rootT)
        else:
            pn = j['nodes'][p]['name']
            t = qmat(g[p][1]).T @ (new_pos[n] - new_pos[pn])
        j['nodes'][i]['translation'] = [float(x) for x in t]
    g2, _ = node_globals(j)
    hip_ratio = new_pos['Hips'][1] / max(old_pos['Hips'][1], 1e-3)

    # --- gather data that survives (animations), then rebuild the binary ----------------------
    anims = []
    for a in j.get('animations', []):
        samplers = []
        for s in a['samplers']:
            samplers.append((accessor(j, binc, s['input']).copy(), accessor(j, binc, s['output']).copy(),
                             s.get('interpolation', 'LINEAR'), j['accessors'][s['output']]['type']))
        anims.append((a, samplers))
    other_nodes_mesh = {}
    for i, n in enumerate(j['nodes']):
        if 'mesh' in n:
            other_nodes_mesh[n['mesh']] = i
    body_mesh = next(k for k, m in enumerate(j['meshes']) if m['name'].endswith('_Body'))
    head_mesh = next((k for k, m in enumerate(j['meshes']) if m['name'].endswith('_Head')), None)
    name = j['meshes'][body_mesh]['name'][:-5]

    w = Writer(j)
    j.pop('images', None); j.pop('textures', None); j.pop('samplers', None)
    j['materials'] = []
    # IBMs
    ibm = []
    for i in skin['joints']:
        p, q = g2[i]
        M = np.eye(4); M[:3, :3] = qmat(q); M[:3, 3] = p
        ibm.append(np.linalg.inv(M).T.reshape(-1))
    skin['inverseBindMatrices'] = w.add(np.array(ibm, np.float32), 'MAT4')
    # animations, translation channels re-based
    for a, samplers in anims:
        retarget = {}
        for c in a['channels']:
            if c['target']['path'] == 'translation':
                nn = j['nodes'][c['target']['node']].get('name')
                if nn in jn: retarget[c['sampler']] = nn
        for si, (inp, out, interp, typ) in enumerate(samplers):
            if si in retarget:
                n = retarget[si]; nt = np.array(j['nodes'][jn[n]]['translation'])
                out = out.astype(np.float64)
                rows = out.reshape(-1, 3)
                if n == 'Hips':
                    rows = (rows - old_t[n]) * hip_ratio + nt
                else:
                    rows = rows - old_t[n] + nt
                out = rows.astype(np.float32).reshape(out.shape)
            s = a['samplers'][si]
            s['input'] = w.add(inp.astype(np.float32), 'SCALAR', minmax=True)
            s['output'] = w.add(out.astype(np.float32), typ)

    # --- mesh -------------------------------------------------------------------------------
    folder = os.path.join(RB, avatar)
    mats = [str(m) for m in D['mats']]
    loop_v, loop_uv, loop_n = D['loop_v'], D['loop_uv'], D['loop_n']
    key = np.c_[loop_v, np.round(loop_uv * 4096), np.round(loop_n * 64)]
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    V = loop_v[first]
    P = D['base'][V]; N = loop_n[first]; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    UV = loop_uv[first]
    Wt = D['weights'][V]
    order = np.argsort(-Wt, axis=1)[:, :4]
    J4 = order.astype(np.uint16)
    W4 = np.take_along_axis(Wt, order, 1)
    W4 /= np.maximum(W4.sum(1, keepdims=True), 1e-6)
    tris = inv[D['tri_loops']]
    morphs = D['morphs'][:, V] if D['morphs'].size else None
    morph_names = [str(x) for x in D['morph_names']]

    sizes = {'head': 1024, 'body': 1024, 'equipment': 1024, 'helmet': 512, 'hair': 512}
    mat_index = {}
    for mi, mname in enumerate(mats):
        low = mname.lower()
        if any(d in low for d in DROP_MATS) or not np.any(D['tri_mat'] == mi):
            continue
        size = next((v for k, v in sizes.items() if k in low), 512)
        col_p = find_tex(folder, mname, '_color') or find_tex(folder, mname, 'color')
        nor_p = find_tex(folder, mname, 'normal')
        spec_p = find_tex(folder, mname, 'specular')
        col, alpha = load_img(col_p, size) if col_p else (np.full((4, 4, 3), 0.5, np.float32), False)
        rgb = col[..., :3]
        if uniform and not any(k in low for k in ('hair', 'eye', 'lash', 'teeth')):
            rgb = dye(rgb, uniform, protect_bright='head' in low)
        rgb = paint_out_insignia(rgb, avatar, low)
        base = np.dstack([rgb, col[..., 3]]) if alpha else rgb
        m = {'name': f'{name}_{low.split("_")[-1].title()}',
             'pbrMetallicRoughness': {'baseColorTexture': {'index': add_tex(w, base, mname + '_color', alpha)},
                                      'metallicFactor': 0.0, 'roughnessFactor': 1.0}}
        if alpha:
            m['alphaMode'] = 'MASK'; m['alphaCutoff'] = 0.45; m['doubleSided'] = True
        if nor_p:
            nimg, _ = load_img(nor_p, size)
            m['normalTexture'] = {'index': add_tex(w, nimg[..., :3], mname + '_normal'), 'scale': 1.0}
        if spec_p:
            sp, _ = load_img(spec_p, size)
            spl = sp[..., :3].mean(-1)
            skin_like = 'head' in low
            rough = np.clip((0.62 if skin_like else 0.9) - spl * (0.45 if skin_like else 0.6), 0.25, 1.0)
            mr = np.dstack([np.ones_like(rough), rough, np.zeros_like(rough)])
            m['pbrMetallicRoughness']['metallicRoughnessTexture'] = {'index': add_tex(w, mr, mname + '_mr')}
            m['pbrMetallicRoughness']['metallicFactor'] = 0.0
        j['materials'].append(m); mat_index[mi] = len(j['materials']) - 1

    def prims_for(sel_head):
        out = []
        for mi in sorted(mat_index):
            is_head = any(k in mats[mi].lower() for k in HEAD_MATS)
            if is_head != sel_head: continue
            T = tris[D['tri_mat'] == mi]
            vs, local = np.unique(T.reshape(-1), return_inverse=True)
            I = local.reshape(-1, 3).astype(np.uint32)
            # glTF winding is counter-clockwise; Blender's loop triangles already are
            pr = {'attributes': {'POSITION': w.add(P[vs].astype(np.float32), 'VEC3', target=34962, minmax=True),
                                 'NORMAL': w.add(N[vs].astype(np.float32), 'VEC3', target=34962),
                                 'TEXCOORD_0': w.add(UV[vs].astype(np.float32), 'VEC2', target=34962),
                                 'JOINTS_0': w.add(J4[vs], 'VEC4', target=34962),
                                 'WEIGHTS_0': w.add(W4[vs].astype(np.float32), 'VEC4', target=34962)},
                  'indices': w.add(I.reshape(-1), 'SCALAR', target=34963), 'material': mat_index[mi]}
            if sel_head and morphs is not None:
                pr['targets'] = [{'POSITION': w.add(morphs[k][vs].astype(np.float32), 'VEC3', minmax=True)}
                                 for k in range(len(morph_names))]
            out.append(pr)
        return out

    j['meshes'][body_mesh] = {'name': f'{name}_Body', 'primitives': prims_for(False)}
    hp = prims_for(True)
    if head_mesh is None:
        head_mesh = len(j['meshes']); j['meshes'].append({})
        hn = len(j['nodes']); j['nodes'].append({'name': f'{name}_Head', 'mesh': head_mesh, 'skin': 0})
        j['nodes'][j['scenes'][0]['nodes'][0]].setdefault('children', []).append(hn)
    j['meshes'][head_mesh] = {'name': f'{name}_Head', 'primitives': hp}
    if morphs is not None and hp:
        j['meshes'][head_mesh]['extras'] = {'targetNames': morph_names}
        j['meshes'][head_mesh]['weights'] = [0.0] * len(morph_names)
    j['asset'] = {'version': '2.0', 'generator': 'SPECIAL OPS build_rocketbox_cast.py (Microsoft Rocketbox, MIT)'}
    w.save(path)
    ntri = int(len(tris) - sum(np.sum(D['tri_mat'] == mi) for mi in range(len(mats)) if mi not in mat_index))
    print(f'CAST_OK {char} <- {avatar}: {len(P)} verts, {ntri} tris, {len(j["materials"])} materials, '
          f'{os.path.getsize(path) // 1024} KiB, height {P[:, 1].max():.2f} m')


INSIGNIA = {}  # filled per avatar after inspecting the textures: {avatar: {mat_substr: [(x0, y0, x1, y1), ...]}}


def paint_out_insignia(rgb, avatar, mat_low):
    """Cover national flags with plain cloth: saturated red/blue blobs (nothing else on the kit is
    that colour) are found automatically; extra rectangles (UV 0..1) can be listed in INSIGNIA."""
    from scipy import ndimage
    if 'head' not in mat_low and 'hair' not in mat_low:
        hsv = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).convert('HSV')).astype(np.float32) / 255.0
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        flag = (s > 0.38) & (v > 0.2) & (((h > 0.92) | (h < 0.015)) | ((h > 0.55) & (h < 0.72)))
        flag = ndimage.binary_closing(flag, iterations=3)
        lab, n = ndimage.label(flag)
        H, W = rgb.shape[:2]
        rects = []
        for sl in ndimage.find_objects(lab):
            hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
            if hh * ww < (H * W) * 4e-5 or hh * ww > (H * W) * 0.01: continue
            pad = max(2, int(0.08 * max(hh, ww)))
            rects.append(((sl[1].start - pad) / W, (sl[0].start - pad) / H, (sl[1].stop + pad) / W, (sl[0].stop + pad) / H))
        if rects:
            INSIGNIA.setdefault(avatar, {}).setdefault('_auto_' + mat_low, rects)
            print(f'  painted out {len(rects)} insignia in {mat_low}')
    for sub, rects in INSIGNIA.get(avatar, {}).items():
        if sub.removeprefix('_auto_') not in mat_low: continue
        h, wd = rgb.shape[:2]
        for x0, y0, x1, y1 in rects:
            a, b, c, d = int(x0 * wd), int(y0 * h), int(x1 * wd), int(y1 * h)
            ring = np.concatenate([rgb[max(b - 6, 0):b, a:c].reshape(-1, 3), rgb[d:d + 6, a:c].reshape(-1, 3)])
            fill = np.median(ring, axis=0) if len(ring) else rgb[b:d, a:c].mean((0, 1))
            noise = rgb[b:d, a:c].mean(-1, keepdims=True)
            rgb[b:d, a:c] = np.clip(fill[None, None, :] * (0.92 + 0.16 * (noise - noise.mean())), 0, 1)
    return rgb


def main(argv):
    for c in (argv or list(CAST)):
        build(c)


if __name__ == '__main__':
    main(sys.argv[1:])
