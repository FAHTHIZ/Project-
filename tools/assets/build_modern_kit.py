# SPDX-License-Identifier: Apache-2.0
"""Dress the SPECIAL OPS cast in modern combat kit.

    BLENDER=/path/to/blender python3 tools/assets/build_modern_kit.py [sops_anchor ...]

The Rocketbox cast (tools/assets/build_rocketbox_cast.py + build_mocap_clips.py) wore 2000s-era
ACU-pattern fatigues, patrol caps and a vest from a police avatar: the playtest verdict was that
they "look like the 1990s". This pass keeps everything that made the cast work: each character's
skeleton, rest pose, every animation clip, and the Rocketbox head with its 11 facial morphs (lip
sync, blinks and expressions). It replaces everything below the collar with a modern kit body: a
plate carrier with magazine/utility pouches and cummerbund, combat shirt and trousers with knee
pads, gloves and boots. It also puts a high-cut ballistic helmet with an NVG shroud on the soldiers'
heads, removing each Rocketbox patrol cap and the scalp beneath the helmet.

Source body: "Soldier" by Grab3D, CC0 1.0 (AI-assisted model; https://grab3d.com/models/characters/soldier/,
rigged variant https://grab3d.com/dl/soldier-rigged/soldier-rigged.glb), cached in .cache/gear.
tools/assets/blender_gear.py decimates it from 279k to ~18k triangles and bakes the full-resolution
geometry and its normal map into a tangent-space normal map for the phone.

Fit: for every game joint J, a per-bone affine map A_J takes the source bone (joint -> child joint)
onto the character's rest bone (minimal rotation, length ratio along the bone, girth factor across
it). Vertices are blended through these maps with the source skin weights (merged onto the 21
joints), which puts the kit into the character's own rest pose and proportions, so the existing
inverse bind matrices and clips apply unchanged.

Colour: the source's mottled woodland camo is re-coloured texel by texel. High-frequency camo
cloth is mapped through a four-colour palette (luminance bands), and smooth webbing/plate-carrier
nylon is dyed to one gear colour (ranger green, coyote, black), so each operator reads as a
current-issue unit: Multicam-style uniforms with ranger-green or coyote carriers for Halyard, and
all-black contractor kit for Greyline.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageFilter
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'characters'))
from gltf_util import read_glb, accessor, Writer, node_globals, add_image  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
CHARS = os.path.join(ROOT, 'game', 'assets', 'models', 'characters')
GEAR = os.path.join(ROOT, '.cache', 'gear')
BLENDER = os.environ.get('BLENDER', 'blender')
SRC_GLB = os.path.join(GEAR, 'soldier-rigged.glb')
SRC_URL = 'https://grab3d.com/dl/soldier-rigged/soldier-rigged.glb'
RATIO = float(os.environ.get('KIT_RATIO', '0.08'))

JOINTS = ["Hips", "Spine", "Chest", "Neck", "Head", "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
          "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R", "UpperLeg.L", "LowerLeg.L", "Foot.L", "Toe.L",
          "UpperLeg.R", "LowerLeg.R", "Foot.R", "Toe.R"]
JI = {n: i for i, n in enumerate(JOINTS)}
SRC = {'Hips': 'Hips', 'Spine': 'Spine02', 'Chest': 'Spine01', 'Neck': 'neck', 'Head': 'Head'}
for s, d in (('Left', 'L'), ('Right', 'R')):
    SRC.update({f'Shoulder.{d}': f'{s}Shoulder', f'UpperArm.{d}': f'{s}Arm', f'LowerArm.{d}': f'{s}ForeArm',
                f'Hand.{d}': f'{s}Hand', f'UpperLeg.{d}': f'{s}UpLeg', f'LowerLeg.{d}': f'{s}Leg',
                f'Foot.{d}': f'{s}Foot', f'Toe.{d}': f'{s}ToeBase'})
CHILD = {'Hips': 'Spine', 'Spine': 'Chest', 'Chest': 'Neck', 'Neck': 'Head'}
for d in 'LR':
    CHILD.update({f'Shoulder.{d}': f'UpperArm.{d}', f'UpperArm.{d}': f'LowerArm.{d}', f'LowerArm.{d}': f'Hand.{d}',
                  f'UpperLeg.{d}': f'LowerLeg.{d}', f'LowerLeg.{d}': f'Foot.{d}', f'Foot.{d}': f'Toe.{d}'})
LEAF_FROM = {'Head': 'Neck', 'Hand.L': 'LowerArm.L', 'Hand.R': 'LowerArm.R', 'Toe.L': 'Foot.L', 'Toe.R': 'Foot.R'}

# palettes, sRGB hex. camo: four luminance bands, darkest first.
MULTICAM = ('#3b3627', '#58593a', '#7f6d4c', '#a1906a')
MULTICAM_GREEN = ('#2c3024', '#4b5236', '#6b6a4a', '#8e8762')
BLACK = ('#16171a', '#222326', '#2c2d31', '#38393d')
CHARCOAL = ('#1f2124', '#2e3034', '#3c3e42', '#4a4c50')
RANGER_GREEN = '#4b4f3a'
COYOTE = '#7a6648'
GEAR_BLACK = '#202124'
GEAR_GREY = '#33353a'

# character -> kit
KIT = {
    'sops_anchor': {'camo': MULTICAM, 'gear': RANGER_GREEN, 'helmet': 'gear'},
    'sops_brick': {'camo': MULTICAM, 'gear': COYOTE, 'helmet': 'camo', 'girth': 1.06},
    'sops_tally': {'camo': MULTICAM_GREEN, 'gear': RANGER_GREEN, 'helmet': 'gear'},
    'sops_patch': {'camo': MULTICAM, 'gear': COYOTE, 'helmet': 'gear', 'girth': 0.9, 'armband': '#2f9283'},
    'sops_echo': {'camo': MULTICAM_GREEN, 'gear': RANGER_GREEN, 'helmet': 'camo', 'girth': 0.9},
    # Greyline: the Rocketbox helmet was part of the replaced body mesh, so they get the same shell
    # in black over their balaclava; the orange goggles (head mesh) then sit on its front
    'sops_greyline_a': {'camo': BLACK, 'gear': GEAR_BLACK, 'helmet': 'gear', 'girth': 1.02},
    'sops_greyline_b': {'camo': CHARCOAL, 'gear': GEAR_GREY, 'helmet': 'gear', 'girth': 1.02},
}


def hexrgb(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


# --- source kit --------------------------------------------------------------------------------
def load_kit():
    npz = os.path.join(GEAR, f'kit_{RATIO}.npz'); nrm = os.path.join(GEAR, f'kit_{RATIO}_normal.png')
    if not os.path.exists(SRC_GLB):
        os.makedirs(GEAR, exist_ok=True)
        import urllib.request
        urllib.request.urlretrieve(SRC_URL, SRC_GLB)
    if not (os.path.exists(npz) and os.path.exists(nrm)):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump({'glb': SRC_GLB, 'out': npz, 'ratio': RATIO, 'bake': nrm, 'bake_size': 2048}, f)
        r = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', os.path.join(HERE, 'blender_gear.py'), '--', f.name],
                           capture_output=True, text=True)
        os.unlink(f.name)
        if 'KIT_OK' not in r.stdout:
            sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:]); raise SystemExit('kit bake failed')
    D = np.load(npz, allow_pickle=False)
    lv, luv, ln = D['loop_v'], D['loop_uv'], D['loop_n']
    key = np.c_[lv, np.round(luv * 8192), np.round(ln * 64)]
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    V = lv[first]
    kit = {'P': D['base'][V].astype(np.float64), 'N': ln[first].astype(np.float64), 'UV': luv[first].astype(np.float64),
           'W': D['weights'][V].astype(np.float64), 'T': inv[D['tri_loops']], 'jpos': json.loads(str(D['jpos']))}
    kit['N'] /= np.linalg.norm(kit['N'], axis=1, keepdims=True) + 1e-9
    j, b = read_glb(SRC_GLB)
    maps = {}
    for im in j['images']:
        bv = j['bufferViews'][im['bufferView']]; o = bv.get('byteOffset', 0)
        maps[im['name']] = Image.open(io.BytesIO(bytes(b[o:o + bv['byteLength']]))).convert('RGB')
    kit['color'] = np.asarray(next(v for k, v in maps.items() if 'basecolor' in k)).astype(np.float32) / 255
    kit['mr'] = np.asarray(next(v for k, v in maps.items() if 'rough' in k)).astype(np.float32) / 255
    kit['normal'] = np.asarray(Image.open(nrm).convert('RGB')).astype(np.float32) / 255
    # selected-to-active rays that hit the wrong layer (fingers, overlapping pouch flaps) bake
    # normals tilted far past anything the cloth has: fade those back to flat
    n = kit['normal'] * 2 - 1
    bad = np.clip((0.55 - n[..., 2]) / 0.25, 0, 1)
    bad = np.asarray(Image.fromarray((bad * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255
    kit['normal'] = kit['normal'] * (1 - bad[..., None]) + np.array([0.5, 0.5, 1.0], np.float32) * bad[..., None]
    print(f'  normal bake: {float((bad > 0.5).mean()) * 100:.1f}% texels flattened')
    # The source atlas packs ~1000 small UV islands on a near-black background. Decimation lets
    # some low-poly triangles straddle island borders, which would sample that background as black
    # flecks: fill every texel outside the full-resolution mesh's islands from its neighbours.
    cover = uv_coverage(j, b, kit['color'].shape[0])
    kit['color'] = pushpull(kit['color'], cover)
    kit['mr'] = pushpull(kit['mr'], cover)
    return kit


def uv_coverage(j, b, size):
    from PIL import ImageDraw
    m = Image.new('L', (size, size), 0); dr = ImageDraw.Draw(m)
    for mesh in j['meshes']:
        for pr in mesh['primitives']:
            uv = accessor(j, b, pr['attributes']['TEXCOORD_0']) * size
            I = accessor(j, b, pr['indices']).reshape(-1, 3)
            for tri in uv[I]:
                dr.polygon([tuple(x) for x in tri], fill=255)
    m = m.filter(ImageFilter.MinFilter(3))   # islands' anti-aliased rims blend into the background
    return np.asarray(m) > 127


def pushpull(img, mask):
    """Fill texels outside `mask` with a smooth extension of the texels inside (pull-push)."""
    levels = []; c = img * mask[..., None]; w = mask.astype(np.float32)
    while c.shape[0] > 4:
        levels.append((c, w))
        H, W = c.shape[:2]
        c = c.reshape(H // 2, 2, W // 2, 2, -1).sum((1, 3)); w = w.reshape(H // 2, 2, W // 2, 2).sum((1, 3))
    fill = c / np.maximum(w[..., None], 1e-6)
    for c, w in reversed(levels):
        up = np.repeat(np.repeat(fill, 2, 0), 2, 1)
        own = c / np.maximum(w[..., None], 1e-6)
        a = np.clip(w, 0, 1)[..., None]
        fill = own * a + up * (1 - a)
    return np.where(mask[..., None], img, fill).astype(np.float32)


def sample(img, uv):
    H, W = img.shape[:2]
    x = np.clip((uv[:, 0] * W).astype(int), 0, W - 1); y = np.clip((uv[:, 1] * H).astype(int), 0, H - 1)
    return img[y, x]


def classes(color):
    """Per-texel masks: skin, camo cloth (high-frequency mottling) and the rest (webbing, nylon,
    plastic, boots, gloves)."""
    r, g, b = color[..., 0], color[..., 1], color[..., 2]
    skin = (r > g + 0.06) & (r > b + 0.09) & (r > 0.25)
    lum = color @ np.array([0.3, 0.59, 0.11], np.float32)
    L = Image.fromarray((lum * 255).astype(np.uint8))
    mean = np.asarray(L.filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    sq = np.asarray(Image.fromarray((np.clip(lum * lum, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    std = np.sqrt(np.maximum(sq - mean * mean, 0))
    camo = (std > 0.045) & ~skin
    camo = np.asarray(Image.fromarray((camo * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255
    return skin, camo, lum


def recolor(kit, spec):
    color = kit['color']
    skin, camo, lum = classes(color)
    # camo: luminance bands -> palette, keeping fine shading inside each band
    pal = np.array([hexrgb(h) for h in spec['camo']])
    edges = np.quantile(lum[camo > 0.5], [0.25, 0.5, 0.75]) if (camo > 0.5).any() else [0.2, 0.3, 0.4]
    band = np.digitize(lum, edges)
    bm = np.zeros(lum.shape + (3,), np.float32)
    for k in range(4):
        sel = band == k
        bm[sel] = pal[k]
    bm = np.asarray(Image.fromarray((bm * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255
    local = np.asarray(Image.fromarray((lum * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
    shade = np.clip(lum / np.maximum(local, 1e-3), 0.7, 1.3)[..., None]
    camo_rgb = np.clip(bm * shade, 0, 1)
    # gear: one dye, the source's luminance carries stitching, MOLLE and shading
    gt = hexrgb(spec['gear'])
    ref = float(np.median(lum[(camo < 0.2) & ~skin])) if ((camo < 0.2) & ~skin).any() else 0.3
    gear_rgb = np.clip(gt[None, None, :] * (lum / max(ref, 1e-3))[..., None] * 0.95, 0, 1)
    dark = lum < 0.09    # rubber, plastic buckles, boot soles stay as they are (desaturated)
    gear_rgb[dark] = np.repeat(lum[dark][:, None], 3, 1) * 0.9 + gt * 0.04
    out = camo_rgb * camo[..., None] + gear_rgb * (1 - camo[..., None])
    out[skin] = color[skin]
    return out


# --- geometry ----------------------------------------------------------------------------------
def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(a @ b)
    if c < -0.9999:
        return -np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def bone_maps(src_pos, dst_pos, girth):
    """A_J (3x3) and t_J per joint: x' = A_J x + t_J."""
    A = np.zeros((len(JOINTS), 3, 3)); t = np.zeros((len(JOINTS), 3))
    for n in JOINTS:
        if n in CHILD:
            ds = src_pos[CHILD[n]] - src_pos[n]; dd = dst_pos[CHILD[n]] - dst_pos[n]
            R = rot_between(ds, dd); u = ds / np.linalg.norm(ds)
            k = np.linalg.norm(dd) / np.linalg.norm(ds)
            gg = girth.get(n, girth.get('*', 1.0))
            S = gg * np.eye(3) + (k - gg) * np.outer(u, u)
            A[JI[n]] = R @ S
        for n2 in []: pass
    for n, p in LEAF_FROM.items():
        A[JI[n]] = A[JI[p]] if n != 'Head' else np.eye(3) * 1.0
        if n.startswith(('Hand', 'Toe')):   # keep gloves and boot toes rigid: rotation only
            U, _, Vt = np.linalg.svd(A[JI[p]]); A[JI[n]] = U @ Vt
    for n in JOINTS:
        t[JI[n]] = dst_pos[n] - A[JI[n]] @ src_pos[n]
    return A, t


def skin_through(P, N, W, A, t):
    X = np.einsum('jab,vb->vja', A, P) + t[None]
    P2 = np.einsum('vj,vja->va', W, X)
    AinvT = np.linalg.inv(A).transpose(0, 2, 1)
    N2 = np.einsum('vj,vja->va', W, np.einsum('jab,vb->vja', AinvT, N))
    N2 /= np.linalg.norm(N2, axis=1, keepdims=True) + 1e-9
    return P2, N2


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def img_bytes(j, b, tex_index):
    im = j['images'][j['textures'][tex_index]['source']]
    bv = j['bufferViews'][im['bufferView']]; o = bv.get('byteOffset', 0)
    return Image.open(io.BytesIO(bytes(b[o:o + bv['byteLength']])))


def enc(arr, size=None, png=False):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')
    if size and im.size[0] != size:
        im = im.resize((size, size), Image.LANCZOS)
    bio = io.BytesIO()
    if png:
        im.save(bio, 'PNG', optimize=True); return bio.getvalue(), 'image/png'
    im.save(bio, 'JPEG', quality=90, subsampling=0); return bio.getvalue(), 'image/jpeg'


def add_tex(w, arr, name, size=None, png=False):
    data, mime = enc(arr, size, png)
    t = add_image(w, data, name)
    w.j['images'][-1]['mimeType'] = mime
    return t


# --- build -------------------------------------------------------------------------------------
def build(char, kit):
    spec = KIT[char]
    path = os.path.join(CHARS, char + '.glb')
    j, binc = read_glb(path)
    skin = j['skins'][0]
    jn = {j['nodes'][i]['name']: i for i in skin['joints']}
    g, _ = node_globals(j)
    dst = {n: np.array(g[jn[n]][0], np.float64) for n in JOINTS}
    src = {n: np.array(kit['jpos'][SRC[n]], np.float64) for n in JOINTS}
    girth = {'*': spec.get('girth', 1.0)}
    A, t = bone_maps(src, dst, girth)

    T = kit['T']; W = kit['W']
    dom_v = W.argmax(1)
    tri_dom = np.array([np.bincount(r, minlength=len(JOINTS)).argmax() for r in dom_v[T]])
    skin_m, _, _ = classes(kit['color'])
    uv_c = kit['UV'][T].mean(1)
    tri_skin = sample(skin_m.astype(np.float32)[..., None], uv_c)[:, 0] > 0.5
    head_like = np.isin(tri_dom, [JI['Head'], JI['Neck']])
    # helmet: head-weighted, not skin, above the source's eyes
    src_head = src['Head']
    brow_y = float(kit['jpos']['headfront'][1]) + 0.035
    yc = kit['P'][T].mean(1)[:, 1]
    helmet_tri = (tri_dom == JI['Head']) & ~tri_skin & (yc > brow_y)
    body_tri = ~head_like | ((tri_dom == JI['Neck']) & ~tri_skin & (yc < src['Neck'][1] + 0.02))

    P2, N2 = skin_through(kit['P'], kit['N'], W, A, t)
    # soles on the ground plane like the rest pose's (the source boots sit lower on its ankles)
    sole = float(P2[:, 1].min())
    if sole < 0:
        P2[:, 1] -= sole * np.clip(1 - (P2[:, 1] - sole) / (0.16 - sole), 0, 1)

    # existing head primitive
    hm = next(k for k, m in enumerate(j['meshes']) if m['name'].endswith('_Head'))
    bm = next(k for k, m in enumerate(j['meshes']) if m['name'].endswith('_Body'))
    hp = j['meshes'][hm]['primitives'][0]
    # the head's full triangle list comes from the pre-kit copy, so re-running this tool on its own
    # output starts from the same cap and scalp (clips and skeleton are always the current file's)
    pre = os.path.join(GEAR, '_pre', char + '.glb')
    if not os.path.exists(pre):
        os.makedirs(os.path.dirname(pre), exist_ok=True); open(pre, 'wb').write(open(path, 'rb').read())
    jp_, bp_ = read_glb(pre)
    php = next(m for m in jp_['meshes'] if m['name'].endswith('_Head'))['primitives'][0]
    HP = accessor(j, binc, hp['attributes']['POSITION']).astype(np.float64)
    HUV = accessor(j, binc, hp['attributes']['TEXCOORD_0']).astype(np.float64)
    HI = accessor(jp_, bp_, php['indices']).reshape(-1, 3).astype(np.int64)
    hcol = np.asarray(img_bytes(jp_, bp_, jp_['materials'][php['material']]['pbrMetallicRoughness']['baseColorTexture']['index']).convert('RGB')).astype(np.float32) / 255

    keep_head = np.ones(len(HI), bool)
    head_recolor = None
    head_targets_pre = [{k: accessor(j, binc, v) for k, v in tg.items()} for tg in hp.get('targets', [])]
    helmet = None
    if spec.get('helmet') is not None:
        # 1) the Rocketbox patrol cap: camouflage-coloured texels in the head map
        hc = sample(hcol, HUV[HI].mean(1))
        hh = np.asarray(Image.fromarray((np.clip(hc[None], 0, 1) * 255).astype(np.uint8)).convert('HSV'))[0].astype(np.float32) / 255
        r_, g_, b_ = hc[:, 0], hc[:, 1], hc[:, 2]
        capish = (g_ >= r_ - 0.015) & (hh[:, 1] < 0.45) & (hh[:, 2] > 0.18)
        hy = HP[HI].mean(1)[:, 1]
        cap = capish & (hy > dst['Head'][1] + 0.03)
        # 2) fit the helmet shell to this head. Eye level comes from the eyeball vertices (the
        #    LookL/LookR morphs move only those); the shell is scaled by skull width (ear to ear,
        #    skin only, so hair volume does not inflate it) and lowered until its front brim sits
        #    just above the brow.
        names = j['meshes'][hm].get('extras', {}).get('targetNames', [])
        eye_v = np.zeros(len(HP), bool)
        for k, nm in enumerate(names):
            if nm in ('LookL', 'LookR'):
                eye_v |= np.linalg.norm(head_targets_pre[k]['POSITION'], axis=1) > 1e-4
        eye_y = float(HP[eye_v, 1].mean()) if eye_v.any() else float(dst['Head'][1] + 0.085)
        eye_z = float(HP[eye_v, 2].max()) if eye_v.any() else float(HP[:, 2].max() - 0.02)
        # the cap's visor is a flap in front of the forehead: no skull behind it, so it can go
        hcen = HP[HI].mean(1)
        visor = ((hcen[:, 2] > eye_z + 0.025) & (hcen[:, 1] > eye_y - 0.004)) | \
                (cap & (hcen[:, 2] > eye_z + 0.01) & (hcen[:, 1] > eye_y - 0.006))
        keep_head &= ~visor
        print(f'  visor tris {int(visor.sum())}')
        hv_idx = np.unique(T[helmet_tri])
        Hsrc = kit['P'][hv_idx]
        src_skin_head = kit['P'][np.unique(T[(tri_dom == JI['Head']) & tri_skin])]
        band = np.abs(src_skin_head[:, 1] - (brow_y + 0.007)) < 0.012   # source eye line, ears included
        src_w = np.ptp(src_skin_head[band, 0]) if band.sum() > 10 else 0.15
        hv_all = HP[np.unique(HI[keep_head])]
        rb_band = hv_all[np.abs(hv_all[:, 1] - eye_y) < 0.025]
        rb_w = np.ptp(rb_band[:, 0])
        s = float(np.clip(rb_w / src_w * 1.12, 0.88, 1.2))
        hc = 0.5 * (Hsrc.min(0) + Hsrc.max(0))
        Hc = Hsrc - hc
        front = Hc[:, 2] > 0.25 * np.ptp(Hc[:, 2])
        brim_rel = float(Hc[front, 1].min()) if front.any() else float(Hc[:, 1].min())
        rb_c = np.array([float(np.median(rb_band[:, 0])), 0.0,
                         0.5 * (hv_all[hv_all[:, 1] > eye_y + 0.04, 2].min() + hv_all[hv_all[:, 1] > eye_y + 0.04, 2].max())])
        rb_c[1] = eye_y + spec.get('brim', 0.036) - s * brim_rel
        # seat the shell on the forehead: its front face ~2 cm (shell + pads) ahead of the skin
        Hpos_fit = rb_c + s * Hc
        by = float(Hpos_fit[front, 1].min()) if front.any() else float(Hpos_fit[:, 1].min())
        # smallest shift that keeps the shell's front clear of the forehead over the brim band
        need = []
        for hh in np.arange(by + 0.006, by + 0.06, 0.006):
            fh = hv_all[(np.abs(hv_all[:, 1] - hh) < 0.004) & (np.abs(hv_all[:, 0]) < 0.035)]
            hf = Hpos_fit[(np.abs(Hpos_fit[:, 1] - hh) < 0.005) & (np.abs(Hpos_fit[:, 0]) < 0.035)]
            if len(fh) and len(hf) and hf[:, 2].max() > 0.02:   # heights where the shell's front exists
                need.append(float(fh[:, 2].max()) + spec.get('shell_gap', 0.012) - float(hf[:, 2].max()))
        if need:
            dz = float(np.clip(max(need), -0.05, 0.02))
            rb_c[2] += dz; Hpos_fit[:, 2] += dz
            print(f'  helmet seated {dz * 100:+.1f} cm')
        helmet = {'src_idx': hv_idx, 'pos': Hpos_fit, 'scale': s}
        print(f'  helmet scale {s:.3f} (skull {rb_w:.3f} m / {src_w:.3f} m), eye y {eye_y:.3f}, cap tris {int(cap.sum())}')
        # 3) drop scalp/hair inside the shell (directions it covers, above the brow)
        Hd = s * Hc
        dirs = Hd / np.linalg.norm(Hd, axis=1, keepdims=True); rad = np.linalg.norm(Hd, axis=1)
        tree = cKDTree(dirs)
        hcent = HP[HI].mean(1) - rb_c
        hd = hcent / (np.linalg.norm(hcent, axis=1, keepdims=True) + 1e-9)
        dd, ii = tree.query(hd, k=16)
        inner_t = np.where(dd < 0.08, rad[ii], np.inf).min(1)
        # only triangles the shell fully encloses: every corner inside it and above the brim
        cv = HP[HI] - rb_c
        cd = cv / (np.linalg.norm(cv, axis=2, keepdims=True) + 1e-9)
        dd, ii = tree.query(cd.reshape(-1, 3), k=16)
        inner_c = np.where(dd < 0.08, rad[ii], np.inf).min(1).reshape(-1, 3)
        brim_y = float(rb_c[1] + s * brim_rel)
        covered = ((np.linalg.norm(cv, axis=2) < inner_c + 0.004) & (HP[HI][..., 1] > brim_y + 0.012)).all(1)
        keep_head &= ~covered
        # the rest of the cap (painted on the skull) shows under the brim: repaint it as hair
        cap_left = cap & keep_head
        head_recolor = (HUV[HI[cap_left]], spec.get('hair', '#17130f'))
        print(f'  scalp tris under the helmet {int(covered.sum())}')

    # --- assemble the body primitive (kit body + helmet, one material) -------------------------
    bsel = body_tri | (helmet_tri if helmet is not None else np.zeros_like(body_tri))
    BT = T[bsel]
    used = np.unique(BT); remap = -np.ones(len(P2), np.int64); remap[used] = np.arange(len(used))
    BP = P2[used].copy(); BN = N2[used]; BUV = kit['UV'][used]; BW = W[used].copy()
    if helmet is not None:
        hmask = np.isin(used, helmet['src_idx']) & np.isin(used, np.unique(T[helmet_tri])) & ~np.isin(used, np.unique(T[body_tri]))
        pos_of = dict(zip(helmet['src_idx'].tolist(), range(len(helmet['src_idx']))))
        rows = np.array([pos_of[u] for u in used[hmask]])
        BP[hmask] = helmet['pos'][rows]
        BW[hmask] = 0; BW[hmask, JI['Head']] = 1
    order = np.argsort(-BW, axis=1)[:, :4]
    J4 = order.astype(np.uint16); W4 = np.take_along_axis(BW, order, 1)
    W4 /= np.maximum(W4.sum(1, keepdims=True), 1e-6)

    # gather animations before rewriting the binary
    anims = []
    for a in j.get('animations', []):
        samplers = [(accessor(j, binc, s['input']).copy(), accessor(j, binc, s['output']).copy(),
                     j['accessors'][s['output']]['type']) for s in a['samplers']]
        anims.append((a, samplers))
    ibm = accessor(j, binc, skin['inverseBindMatrices']).copy()
    head_attr = {k: accessor(j, binc, v).copy() for k, v in hp['attributes'].items()}
    head_targets = [{k: accessor(j, binc, v).copy() for k, v in tg.items()} for tg in hp.get('targets', [])]
    head_mat = j['materials'][hp['material']]
    head_maps = {}
    pre_mat = jp_['materials'][php['material']]
    for key, ref in (('color', head_mat['pbrMetallicRoughness'].get('baseColorTexture')),
                     ('mr', head_mat['pbrMetallicRoughness'].get('metallicRoughnessTexture')),
                     ('normal', head_mat.get('normalTexture'))):
        if ref:   # maps from the pre-kit copy: the cap repaint below must not stack on re-runs
            pref = {'color': pre_mat['pbrMetallicRoughness'].get('baseColorTexture'),
                    'mr': pre_mat['pbrMetallicRoughness'].get('metallicRoughnessTexture'),
                    'normal': pre_mat.get('normalTexture')}[key]
            im = jp_['images'][jp_['textures'][pref['index']]['source']]
            bv = jp_['bufferViews'][im['bufferView']]; o = bv.get('byteOffset', 0)
            head_maps[key] = (bytes(bp_[o:o + bv['byteLength']]), im.get('mimeType', 'image/png'))
    name = j['meshes'][bm]['name'][:-5]

    w = Writer(j)
    j.pop('images', None); j.pop('textures', None); j.pop('samplers', None)
    j['materials'] = []
    skin['inverseBindMatrices'] = w.add(ibm.astype(np.float32), 'MAT4')
    for a, samplers in anims:
        for si, (inp, out, typ) in enumerate(samplers):
            s_ = a['samplers'][si]
            s_['input'] = w.add(inp.astype(np.float32), 'SCALAR', minmax=True)
            s_['output'] = w.add(out.astype(np.float32), typ)

    # body material
    col = recolor(kit, spec)
    if spec.get('armband'):
        col = paint_armband(col, kit, BT, remap, BP, BUV, BW, dst, hexrgb(spec['armband']))
    if spec.get('helmet') == 'gear' and helmet is not None:
        pass   # the dye in recolor already covers helmet cover nylon; camo helmets keep the band map
    mr = kit['mr']
    MR = np.dstack([np.ones_like(mr[..., 1]), np.clip(mr[..., 1] * 1.05, 0.35, 1.0), mr[..., 2] * 0.0])
    bmat = {'name': f'{name}_Kit',
            'pbrMetallicRoughness': {'baseColorTexture': {'index': add_tex(w, col, f'{name}_kit_color')},
                                     'metallicRoughnessTexture': {'index': add_tex(w, MR, f'{name}_kit_mr', 1024)},
                                     'metallicFactor': 0.0, 'roughnessFactor': 1.0},
            'normalTexture': {'index': add_tex(w, kit['normal'], f'{name}_kit_normal', png=False), 'scale': float(os.environ.get('KIT_NSCALE', '1.0'))}}
    j['materials'].append(bmat)
    if head_recolor is not None and len(head_recolor[0]):
        from PIL import ImageDraw
        cimg = Image.open(io.BytesIO(head_maps['color'][0])).convert('RGB')
        Wc, Hc_ = cimg.size
        m = Image.new('L', cimg.size, 0); dr = ImageDraw.Draw(m)
        for tri in head_recolor[0]:
            dr.polygon([(float(u * Wc), float(v * Hc_)) for u, v in tri], fill=255)
        m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))
        arr = np.asarray(cimg).astype(np.float32) / 255
        lum = arr @ np.array([0.3, 0.59, 0.11], np.float32)
        hair = hexrgb(head_recolor[1])[None, None, :] * (0.7 + 0.6 * lum[..., None])
        a = (np.asarray(m).astype(np.float32) / 255)[..., None]
        arr = arr * (1 - a) + np.clip(hair, 0, 1) * a
        bio = io.BytesIO(); Image.fromarray((arr * 255 + 0.5).astype(np.uint8)).save(bio, 'JPEG', quality=92)
        head_maps['color'] = (bio.getvalue(), 'image/jpeg')
    hmat = json.loads(json.dumps(head_mat))
    for key, ref in (('color', hmat['pbrMetallicRoughness'].get('baseColorTexture')),
                     ('mr', hmat['pbrMetallicRoughness'].get('metallicRoughnessTexture')),
                     ('normal', hmat.get('normalTexture'))):
        if ref:
            data, mime = head_maps[key]
            ref['index'] = add_image(w, data, f'{name}_head_{key}'); w.j['images'][-1]['mimeType'] = mime
    j['materials'].append(hmat)

    I = remap[BT].reshape(-1).astype(np.uint32)
    j['meshes'][bm] = {'name': f'{name}_Body', 'primitives': [{
        'attributes': {'POSITION': w.add(BP.astype(np.float32), 'VEC3', target=34962, minmax=True),
                       'NORMAL': w.add(BN.astype(np.float32), 'VEC3', target=34962),
                       'TEXCOORD_0': w.add(BUV.astype(np.float32), 'VEC2', target=34962),
                       'JOINTS_0': w.add(J4, 'VEC4', target=34962),
                       'WEIGHTS_0': w.add(W4.astype(np.float32), 'VEC4', target=34962)},
        'indices': w.add(I, 'SCALAR', target=34963), 'material': 0}]}
    hpr = {'attributes': {}, 'material': 1}
    for k, v in head_attr.items():
        typ = {1: 'SCALAR', 2: 'VEC2', 3: 'VEC3', 4: 'VEC4'}[v.shape[1] if v.ndim == 2 else 1]
        hpr['attributes'][k] = w.add(v, typ, target=34962, minmax=(k == 'POSITION'))
    hpr['indices'] = w.add(HI[keep_head].reshape(-1).astype(np.uint32), 'SCALAR', target=34963)
    if head_targets:
        hpr['targets'] = [{k: w.add(v.astype(np.float32), 'VEC3', minmax=True) for k, v in tg.items()} for tg in head_targets]
    j['meshes'][hm]['primitives'] = [hpr]
    gen = j['asset'].get('generator', '')
    if 'build_modern_kit' not in gen:
        gen += ' + build_modern_kit.py (Grab3D Soldier, CC0)'
    j['asset']['generator'] = gen
    w.save(path)
    print(f'KIT_OK {char}: body {len(BP)} verts {len(BT)} tris, head {int(keep_head.sum())}/{len(HI)} tris, '
          f'{os.path.getsize(path) // 1024} KiB')


def paint_armband(col, kit, BT, remap, BP, BUV, BW, dst, rgb):
    """Teal medic armband: texels of left-sleeve triangles 30-55 % down the upper arm."""
    from PIL import ImageDraw
    H, Wd = col.shape[:2]
    m = Image.new('L', (Wd, H), 0); dr = ImageDraw.Draw(m)
    a, b = dst['UpperArm.L'], dst['LowerArm.L']; ax = b - a; L2 = float(ax @ ax)
    for tri in BT:
        loc = remap[tri]
        if BW[loc, JI['UpperArm.L']].mean() < 0.6: continue
        tt = float(((BP[loc].mean(0) - a) @ ax) / L2)
        if not 0.3 < tt < 0.55: continue
        dr.polygon([(float(BUV[k, 0] * Wd), float(BUV[k, 1] * H)) for k in loc], fill=255)
    mask = np.asarray(m.filter(ImageFilter.GaussianBlur(1))).astype(np.float32) / 255
    skin, camo, lum = classes(kit['color'])
    band = np.clip(rgb[None, None, :] * (0.7 + 0.6 * lum[..., None]), 0, 1)
    sel = (mask * (camo > 0.3))[..., None]
    return col * (1 - sel) + band * sel


def main(argv):
    kit = load_kit()
    for c in (argv or list(KIT)):
        build(c, kit)


if __name__ == '__main__':
    main(sys.argv[1:])
