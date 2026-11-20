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
sys.path.insert(0, HERE)
import cast_kit  # noqa: E402

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
    # Greyline: charcoal tactical kit, helmet, balaclava and goggles (lenses tinted safety orange
    # in cast_kit); _b is the lighter-grey shift.
    'sops_greyline_a': ('Police_Male_02', None),
    'sops_greyline_b': ('Police_Male_02', None),
}
HEAD_MATS = ('head', 'hair', 'opacity', 'eye', 'lash', 'teeth', 'tongue')
DROP_MATS = ('knife', 'pistol')  # non-lethal canon: no blades or real firearms on the kit


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
    K = cast_kit.KIT.get(char, {})
    drop = DROP_MATS + tuple(K.get('drop', ()))

    def flatten(DD):
        lv, luv, ln = DD['loop_v'], DD['loop_uv'], DD['loop_n']
        key = np.c_[lv, np.round(luv * 4096), np.round(ln * 64)]
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
        inv = inv.reshape(-1)
        V = lv[first]
        n = ln[first]; n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
        return V, DD['base'][V].astype(np.float64), n, luv[first], DD['weights'][V], inv[DD['tri_loops']]

    V, P, N, UV, Wt, tris = flatten(D)
    mats = [str(m) for m in D['mats']]
    TRI_MAT = D['tri_mat'].copy()
    mat_folder = [folder] * len(mats)
    morphs = D['morphs'][:, V] if D['morphs'].size else None
    morph_names = [str(x) for x in D['morph_names']]

    def append(P2, N2, UV2, W2, T2, TM2):
        nonlocal P, N, UV, Wt, tris, TRI_MAT
        o = len(P)
        P = np.concatenate([P, P2]); N = np.concatenate([N, N2]); UV = np.concatenate([UV, UV2])
        Wt = np.concatenate([Wt, W2]); tris = np.concatenate([tris, T2 + o]); TRI_MAT = np.concatenate([TRI_MAT, TM2])

    # borrowed materials from another avatar, shifted joint-by-joint onto this body
    for dav, dsub in K.get('borrow', []):
        DD = bake(dav, {n: list(map(float, p)) for n, p in old_pos.items()})
        dV, dP, dN, dUV, dW, dT = flatten(DD)
        delta = np.array([new_pos[n] - DD['jpos'][k] for k, n in enumerate(JOINTS)])
        dP = dP + (dW / np.maximum(dW.sum(1, keepdims=True), 1e-6)) @ delta
        for dmi, dm in enumerate(str(m) for m in DD['mats']):
            if dsub not in dm.lower(): continue
            sel = DD['tri_mat'] == dmi
            used = np.unique(dT[sel]); remap = -np.ones(len(dP), np.int64); remap[used] = np.arange(len(used))
            mats.append(dm); mat_folder.append(os.path.join(RB, dav))
            append(dP[used], dN[used], dUV[used], dW[used], remap[dT[sel]], np.full(sel.sum(), len(mats) - 1))
            print(f'  borrowed {dm} from {dav}: {sel.sum()} tris')

    # procedural accessories (rigid, one swatch each in a kit tile)
    acc_specs = K.get('acc', [])
    if acc_specs:
        vmat = np.empty(len(P), object); vmat[:] = ''
        for mi, mname in enumerate(mats):
            vmat[np.unique(tris[TRI_MAT == mi])] = mname.lower()
        body_lm = cast_kit.Body(P, Wt, list(vmat), new_pos)
        mats.append('kit_acc'); mat_folder.append(None); acc_mi = len(mats) - 1
        for k, (kind, col) in enumerate(acc_specs):
            for aP, aUV, aT, jname in cast_kit.accessory(kind, body_lm):
                aW = np.zeros((len(aP), len(JOINTS)), np.float32); aW[:, JOINTS.index(jname)] = 1
                append(aP, cast_kit._vnormals(aP, aT), cast_kit.swatch_uv(k, aUV), aW, aT, np.full(len(aT), acc_mi))
        print(f'  accessories: {", ".join(a for a, _ in acc_specs)}')

    order = np.argsort(-Wt, axis=1)[:, :4]
    J4 = order.astype(np.uint16)
    W4 = np.take_along_axis(Wt, order, 1)
    W4 /= np.maximum(W4.sum(1, keepdims=True), 1e-6)

    # One primitive per mesh (scene tools address primitives by index, and it is one draw call on
    # the phone): every material of a group is packed into a texture atlas and its UVs remapped.
    TILE = 1024
    groups = {False: [], True: []}
    for mi, mname in enumerate(mats):
        low = mname.lower()
        if any(d in low for d in drop) or not np.any(TRI_MAT == mi):
            continue
        groups[mname != 'kit_acc' and any(k in low for k in HEAD_MATS)].append(mi)

    def tile_maps(mi):
        mname = mats[mi]; low = mname.lower(); folder = mat_folder[mi]
        if mname == 'kit_acc':
            rgb, nor, rough = cast_kit.swatch_tile(TILE, [c for _, c in acc_specs], [a for a, _ in acc_specs])
            return rgb, np.ones(rgb.shape[:2], np.float32), False, nor, rough
        col_p = find_tex(folder, mname, '_color') or find_tex(folder, mname, 'color')
        nor_p = find_tex(folder, mname, 'normal')
        spec_p = find_tex(folder, mname, 'specular')
        col, alpha = load_img(col_p, TILE) if col_p else (np.full((TILE, TILE, 3), 0.5, np.float32), False)
        if col.shape[0] != TILE:
            col = np.asarray(Image.fromarray((col * 255).astype(np.uint8)).resize((TILE, TILE), Image.LANCZOS)).astype(np.float32) / 255
        rgb = col[..., :3].copy()
        if uniform and not any(k in low for k in ('hair', 'eye', 'lash', 'teeth', 'opacity')):
            rgb = dye(rgb, uniform, protect_bright='head' in low)
        rgb = paint_out_insignia(rgb, avatar, low)
        for sub, kind, arg in K.get('fx', []):
            if sub == '' and 'opacity' in low: continue
            if sub in low and (kind == 'lens' or not any(k in low for k in ('opacity', 'eye', 'lash'))):
                ctx = {'mask': lambda js, mi=mi: cast_kit.uv_mask(TILE, UV[tris[(TRI_MAT == mi) &
                       np.isin(Wt[tris].sum(1).argmax(1), [JOINTS.index(x) for x in js])]])}
                rgb = cast_kit.fx_apply(rgb, kind, arg, ctx)
        a = col[..., 3] if alpha else np.ones(rgb.shape[:2], np.float32)
        nor = load_img(nor_p, TILE)[0][..., :3] if nor_p else np.dstack([np.full((TILE, TILE), v, np.float32) for v in (0.5, 0.5, 1.0)])
        if nor.shape[0] != TILE:
            nor = np.asarray(Image.fromarray((nor * 255).astype(np.uint8)).resize((TILE, TILE), Image.LANCZOS)).astype(np.float32) / 255
        skin_like = 'head' in low
        if spec_p:
            spl = load_img(spec_p, TILE)[0][..., :3].mean(-1)
            if spl.shape[0] != TILE:
                spl = np.asarray(Image.fromarray((spl * 255).astype(np.uint8)).resize((TILE, TILE))).astype(np.float32) / 255
            rough = np.clip((0.62 if skin_like else 0.9) - spl * (0.45 if skin_like else 0.6), 0.25, 1.0)
        else:
            rough = np.full((TILE, TILE), 0.8, np.float32)
        return rgb, a, alpha, nor, rough

    def atlas(group, label):
        n = len(group)
        cols, rows = (1, 1) if n == 1 else (2, 1) if n == 2 else (2, 2)
        H, W = rows * TILE, cols * TILE
        RGB = np.zeros((H, W, 3), np.float32); A = np.ones((H, W), np.float32)
        NOR = np.zeros((H, W, 3), np.float32); NOR[..., :] = (0.5, 0.5, 1.0)
        RO = np.full((H, W), 0.8, np.float32)
        any_alpha = False; place = {}
        for k, mi in enumerate(group):
            cx, cy = k % cols, k // cols
            rgb, a, has_a, nor, rough = tile_maps(mi)
            ys, xs = slice(cy * TILE, (cy + 1) * TILE), slice(cx * TILE, (cx + 1) * TILE)
            RGB[ys, xs] = rgb; A[ys, xs] = a; NOR[ys, xs] = nor; RO[ys, xs] = rough
            any_alpha |= has_a
            place[mi] = (cx / cols, cy / rows, 1 / cols, 1 / rows)
        m = {'name': f'{name}_{label}',
             'pbrMetallicRoughness': {
                 'baseColorTexture': {'index': add_tex(w, np.dstack([RGB, A]) if any_alpha else RGB, f'{name}_{label}_color', any_alpha)},
                 'metallicRoughnessTexture': {'index': add_tex(w, np.dstack([np.ones_like(RO), RO, np.zeros_like(RO)]), f'{name}_{label}_mr')},
                 'metallicFactor': 0.0, 'roughnessFactor': 1.0},
             'normalTexture': {'index': add_tex(w, NOR, f'{name}_{label}_normal'), 'scale': 1.0}}
        if any_alpha:
            m['alphaMode'] = 'MASK'; m['alphaCutoff'] = 0.45; m['doubleSided'] = True
        j['materials'].append(m)
        return len(j['materials']) - 1, place

    def prim_for(sel_head, label):
        group = groups[sel_head]
        if not group: return None
        mat_i, place = atlas(group, label)
        sel = np.isin(TRI_MAT, group)
        T = tris[sel]; TM = TRI_MAT[sel]
        # a vertex can only live in one tile: duplicate it per material
        corner_v = T.reshape(-1); corner_m = np.repeat(TM, 3)
        keyv = corner_v.astype(np.int64) * 64 + corner_m
        uniq, local = np.unique(keyv, return_inverse=True)
        vs = (uniq // 64).astype(np.int64); vm = (uniq % 64).astype(np.int64)
        uv = UV[vs].copy()
        for mi, (ox, oy, sx, sy) in place.items():
            s = vm == mi
            uv[s] = np.clip(uv[s], 0.002, 0.998) * (sx, sy) + (ox, oy)
        I = local.reshape(-1).astype(np.uint32)
        pr = {'attributes': {'POSITION': w.add(P[vs].astype(np.float32), 'VEC3', target=34962, minmax=True),
                             'NORMAL': w.add(N[vs].astype(np.float32), 'VEC3', target=34962),
                             'TEXCOORD_0': w.add(uv.astype(np.float32), 'VEC2', target=34962),
                             'JOINTS_0': w.add(J4[vs], 'VEC4', target=34962),
                             'WEIGHTS_0': w.add(W4[vs].astype(np.float32), 'VEC4', target=34962)},
              'indices': w.add(I, 'SCALAR', target=34963), 'material': mat_i}
        if sel_head and morphs is not None:
            pr['targets'] = [{'POSITION': w.add(morphs[k][vs].astype(np.float32), 'VEC3', minmax=True)}
                             for k in range(len(morph_names))]
        return pr, len(vs), len(T)

    body = prim_for(False, 'Body')
    head = prim_for(True, 'Head')
    j['meshes'][body_mesh] = {'name': f'{name}_Body', 'primitives': [body[0]]}
    if head_mesh is None:
        head_mesh = len(j['meshes']); j['meshes'].append({})
        hn = len(j['nodes']); j['nodes'].append({'name': f'{name}_Head', 'mesh': head_mesh, 'skin': 0})
        j['nodes'][j['scenes'][0]['nodes'][0]].setdefault('children', []).append(hn)
    j['meshes'][head_mesh] = {'name': f'{name}_Head', 'primitives': [head[0]]}
    if morphs is not None:
        j['meshes'][head_mesh]['extras'] = {'targetNames': morph_names}
        j['meshes'][head_mesh]['weights'] = [0.0] * len(morph_names)
    j['asset'] = {'version': '2.0', 'generator': 'SPECIAL OPS build_rocketbox_cast.py (Microsoft Rocketbox, MIT)'}
    w.save(path)
    nv, ntri = body[1] + head[1], body[2] + head[2]
    print(f'CAST_OK {char} <- {avatar}: {nv} verts, {ntri} tris, {len(j["materials"])} materials, '
          f'{os.path.getsize(path) // 1024} KiB, height {P[:, 1].max():.2f} m')


INSIGNIA = {}  # filled per avatar after inspecting the textures: {avatar: {mat_substr: [(x0, y0, x1, y1), ...]}}


def paint_out_insignia(rgb, avatar, mat_low):
    """Cover national flags with plain cloth: saturated red/blue blobs (nothing else on the kit is
    that colour) are found automatically; extra rectangles (UV 0..1) can be listed in INSIGNIA."""
    from scipy import ndimage
    if not any(k in mat_low for k in ('head', 'hair', 'opacity')):
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
