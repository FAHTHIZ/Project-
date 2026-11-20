# SPDX-License-Identifier: Apache-2.0
"""First-person hands (hand_r.glb / hand_l.glb).

    BLENDER=/path/to/blender python3 tools/assets/build_vm_arms.py              # MakeHuman (CC0), default
    BLENDER=/path/to/blender python3 tools/assets/build_vm_arms.py --rocketbox  # legacy Rocketbox source

Default: tools/assets/blender_mh_hand.py poses the MakeHuman CC0 base mesh hand (five modelled
fingers, three phalanges each) around the grip; flat glove/sleeve materials get scanned leather
and fabric from retexture.py. Legacy:

tools/assets/blender_vm_arm.py poses the avatar's right forearm, gloved hand and fingers around
a vertical grip at the origin (the contract the viewmodel rig uses); this script writes the two
primitives the scenes expect (0 = glove, 1 = sleeve) with the avatar's own scanned textures,
re-dyed to the Halyard olive. The left hand is the exact mirror.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'characters'))
from gltf_util import Writer  # noqa: E402
import build_rocketbox_cast as cast  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, 'game', 'assets', 'models', 'weapons')
AVATAR = 'Military_Male_04'
UNIFORM = '#55603f'
GLOVE = '#3a3c34'


def bake(job):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(job, f)
    r = subprocess.run([cast.BLENDER, '-b', '--factory-startup', '--python', os.path.join(HERE, 'blender_vm_arm.py'),
                        '--', f.name], capture_output=True, text=True)
    os.unlink(f.name)
    if 'VM_OK' not in r.stdout:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:]); raise SystemExit('vm arm bake failed')
    print(next(l for l in r.stdout.splitlines() if l.startswith('VM_OK')))
    return np.load(job['out'])


def textures(D):
    folder = os.path.join(cast.RB, AVATAR)
    mats = [str(m) for m in D['mats']]
    used = np.unique(D['tri_mat'])
    if len(used) != 1:
        print('  note: hand uses materials', [mats[i] for i in used])
    mname = mats[int(np.bincount(D['tri_mat']).argmax())]
    col, _ = cast.load_img(cast.find_tex(folder, mname, '_color'), 1024)
    rgb = col[..., :3]
    # sleeves to the unit olive; the gloves (already darker) to a near-black olive drab
    from PIL import ImageDraw, ImageFilter
    H = rgb.shape[0]
    mimg = Image.new('L', (H, H), 0); dr = ImageDraw.Draw(mimg)
    for t in D['tri_loops'][D['tri_part'] == 0]:
        dr.polygon([tuple(D['UV'][k] * H) for k in t], fill=255)
    mask = np.asarray(mimg.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32)[..., None] / 255
    rgb = cast.dye(rgb, UNIFORM) * (1 - mask) + cast.dye(rgb, GLOVE, protect_bright=False) * mask
    nor, _ = cast.load_img(cast.find_tex(folder, mname, 'normal'), 1024)
    sp, _ = cast.load_img(cast.find_tex(folder, mname, 'specular'), 1024)
    rough = np.clip(0.92 - sp[..., :3].mean(-1) * 0.6, 0.3, 1.0)
    return mname, rgb, nor[..., :3], rough


def write(D, tex, side, path):
    P, N, UV, LV, TL, TP = D['P'].astype(np.float64), D['N'], D['UV'], D['LV'], D['tri_loops'], D['tri_part']
    if side == 'l':
        P = P * (-1, 1, 1); N = N * (-1, 1, 1); TL = TL[:, ::-1]
    j = {'asset': {'version': '2.0', 'generator': 'SPECIAL OPS build_vm_arms.py (Microsoft Rocketbox, MIT)'},
         'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': f'hand_{side}', 'mesh': 0}],
         'materials': [], 'meshes': [{'name': f'hand_{side}', 'primitives': []}]}
    w = Writer(j)
    mname, rgb, nor, rough = tex
    t_col = cast.add_tex(w, rgb, f'hand_{side}_color')
    t_nor = cast.add_tex(w, nor, f'hand_{side}_normal')
    t_mr = cast.add_tex(w, np.dstack([np.ones_like(rough), rough, np.zeros_like(rough)]), f'hand_{side}_mr')
    for pid, label in ((0, 'Glove'), (1, 'Sleeve')):
        j['materials'].append({'name': f'hand{side}_{label}', 'normalTexture': {'index': t_nor},
                               'pbrMetallicRoughness': {'baseColorTexture': {'index': t_col},
                                                        'metallicRoughnessTexture': {'index': t_mr},
                                                        'metallicFactor': 0.0, 'roughnessFactor': 1.0}})
        T = TL[TP == pid]
        loops, local = np.unique(T.reshape(-1), return_inverse=True)
        pos = P[LV[loops]].astype(np.float32)
        j['meshes'][0]['primitives'].append({
            'attributes': {'POSITION': w.add(pos, 'VEC3', target=34962, minmax=True),
                           'NORMAL': w.add(N[loops].astype(np.float32), 'VEC3', target=34962),
                           'TEXCOORD_0': w.add(UV[loops].astype(np.float32), 'VEC2', target=34962)},
            'indices': w.add(local.reshape(-1).astype(np.uint32), 'SCALAR', target=34963),
            'material': pid})
    w.save(path)
    print(f'VM_ARM {os.path.basename(path)}: {len(TL)} tris, {os.path.getsize(path) // 1024} KiB, '
          f'bounds {P[LV[TL.reshape(-1)]].min(0).round(3)} {P[LV[TL.reshape(-1)]].max(0).round(3)}')


MH_DIR = os.environ.get('MAKEHUMAN_DATA', os.path.join(tempfile.gettempdir(), 'mh'))
MH_URL = 'https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/'
MH_FILES = {'base.obj': '3dobjs/base.obj', 'default.mhskel': 'rigs/default.mhskel',
            'default_weights.mhw': 'rigs/default_weights.mhw'}


def fetch_mh():
    import urllib.request
    os.makedirs(MH_DIR, exist_ok=True)
    for f, rel in MH_FILES.items():
        if not os.path.exists(os.path.join(MH_DIR, f)):
            urllib.request.urlretrieve(MH_URL + rel, os.path.join(MH_DIR, f))


def write_mh(D, side, path):
    """MakeHuman source: flat leather glove + olive sleeve; retexture.py adds the scanned surfaces."""
    P, N, LV, TL, TP = D['P'].astype(np.float64), D['N'], D['LV'], D['tri_loops'], D['tri_part']
    if side == 'l':
        P = P * (-1, 1, 1); N = N * (-1, 1, 1); TL = TL[:, ::-1]
    j = {'asset': {'version': '2.0', 'generator': 'SPECIAL OPS build_vm_arms.py (MakeHuman base mesh, CC0)'},
         'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': f'hand_{side}', 'mesh': 0}],
         'materials': [], 'meshes': [{'name': f'hand_{side}', 'primitives': []}]}
    w = Writer(j)
    looks = {0: ('Glove', [0.052, 0.050, 0.044, 1], 0.62), 1: ('Sleeve', [0.115, 0.125, 0.078, 1], 0.9)}
    for pid in (0, 1):
        label, col, rough = looks[pid]
        j['materials'].append({'name': f'hand{side}_{label}',
                               'pbrMetallicRoughness': {'baseColorFactor': col, 'metallicFactor': 0.0,
                                                        'roughnessFactor': rough}})
        T = TL[TP == pid]
        loops, local = np.unique(T.reshape(-1), return_inverse=True)
        # weld by vertex so normals stay smooth across UV seams
        vid, vlocal = np.unique(LV[loops], return_inverse=True)
        idx = vlocal[local.reshape(-1)]
        j['meshes'][0]['primitives'].append({
            'attributes': {'POSITION': w.add(P[vid].astype(np.float32), 'VEC3', target=34962, minmax=True),
                           'NORMAL': w.add(_vnorm(N, LV, loops, vid, vlocal), 'VEC3', target=34962)},
            'indices': w.add(idx.astype(np.uint32), 'SCALAR', target=34963),
            'material': pid})
    w.save(path)
    print(f'VM_ARM {os.path.basename(path)}: {len(TL)} tris, {os.path.getsize(path) // 1024} KiB')


def _vnorm(N, LV, loops, vid, vlocal):
    acc = np.zeros((len(vid), 3))
    np.add.at(acc, vlocal, N[loops])
    return (acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-9)).astype(np.float32)


def bake_mh(name, **opts):
    out = os.path.join(tempfile.gettempdir(), f'vm_mh_{name}.npz')
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'mh': MH_DIR, 'out': out, **opts}, f)
    r = subprocess.run([cast.BLENDER, '-b', '--factory-startup', '--python', os.path.join(HERE, 'blender_mh_hand.py'),
                        '--', f.name], capture_output=True, text=True)
    os.unlink(f.name)
    if 'VM_OK' not in r.stdout:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:]); raise SystemExit('MakeHuman hand bake failed')
    print(name, next(l for l in r.stdout.splitlines() if l.startswith('VM_OK')))
    return np.load(out)


def main_mh():
    fetch_mh()
    import retexture
    # firing hand: index finger forward on the trigger; support hand: full wrap (mirrored)
    for side, D in (('r', bake_mh('r', trigger=[16, 48, 22])), ('l', bake_mh('l'))):
        p = os.path.join(OUT, f'hand_{side}.glb')
        write_mh(D, side, p)
        retexture.retexture(p)


def main():
    if '--rocketbox' not in sys.argv:
        return main_mh()
    job = {'fbx': os.path.join(cast.RB, AVATAR, f'{AVATAR}_facial.fbx'), 'out': os.path.join(tempfile.gettempdir(), 'vm_arm.npz')}
    D = bake(job)
    tex = textures(D)
    for side in 'rl':
        write(D, tex, side, os.path.join(OUT, f'hand_{side}.glb'))


if __name__ == '__main__':
    main()
