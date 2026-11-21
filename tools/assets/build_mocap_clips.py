# SPDX-License-Identifier: Apache-2.0
"""Bake Microsoft Rocketbox motion capture (MIT) into the SPECIAL OPS cast.

    BLENDER=/path/to/blender python3 tools/assets/build_mocap_clips.py [sops_anchor ...]

The cast (tools/assets/build_rocketbox_cast.py) are Rocketbox avatars re-weighted onto the game's
21-joint rig, so Rocketbox's own captures fit them exactly: for every character this tool samples
the clips below on that character's Rocketbox avatar (tools/assets/blender_mocap.py) and writes
them into game/assets/models/characters/<char>.glb as glTF animations, replacing clips of the same
name. Clips the captures do not cover (Kneel, Surrender, Halt, Point, Beckon, Lift, Reach, Scan,
Inspect, Stumble, GetUp, Jump/Fall/Land, crouch gaits) keep their authored versions.

Joint rotations: R_sops(t) = R_biped(t) R_biped_rest^-1 R_sops_rest (world space, per joint), with
the Biped rest taken in the pose the mesh was baked in. Hips translation follows the capture's
pelvis, scaled to the character; locomotion cycles are made in place (their forward travel is
removed, so the game's character controller moves the body). Loops are cross-faded over their
last 0.4 s, and keys are reduced to within 0.0015 (quaternion) / 2 mm of the 30 fps samples.

Male captures (m_*) drive the male cast, female captures (f_*) Patch and Echo.
Sources: https://github.com/microsoft/Microsoft-Rocketbox (Assets/Animations, MIT); cached in
.cache/rocketbox/anims (fetch with --fetch).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'characters'))
from gltf_util import read_glb, accessor, node_globals  # noqa: E402
from build_rocketbox_cast import CAST, JOINTS, qmat, RB, CHARS, BLENDER  # noqa: E402

ANIMS = os.path.join(RB, 'anims')
RAW = 'https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets/Animations/'
FEMALE = {'sops_patch', 'sops_echo'}

# game clip -> (capture stem, kind). kind: loop (seamless, in place), once (in place),
# keep (pelvis travel kept: sit/stand, crouch in/out)
CLIPS = {
    'Idle': ('idle_neutral_01', 'loop'),
    'IdleB': ('idle_neutral_02', 'loop'),
    'IdleC': ('idle_neutral_03', 'loop'),
    'IdleLook': ('idle_look_around_01', 'loop'),
    'IdleShift': ('idle_waiting_01', 'loop'),
    'IdleStretch': ('idle_stretch_arms_01', 'once'),
    'IdleScratch': ('idle_scratch_head_01', 'once'),
    'Walk': ('walk_neutral_01', 'loop'),
    'WalkFast': ('walk_fast_01', 'loop'),
    'WalkSlow': ('walk_slow_01', 'loop'),
    'Run': ('run_neutral_01', 'loop'),
    'RunSlow': ('run_slow_01', 'loop'),
    'RunFast': ('run_fast_01', 'loop'),
    'Talk': ('gestic_talk_neutral_01', 'loop'),
    'TalkB': ('gestic_talk_neutral_02', 'loop'),
    'TalkC': ('gestic_talk_neutral_03', 'loop'),
    'TalkCalm': ('gestic_talk_relaxed_01', 'loop'),
    'TalkFirm': ('gestic_talk_cool', 'loop'),
    'TalkExcited': ('gestic_talk_excited_01', 'loop'),
    'TalkNervous': ('gestic_talk_nervous_01', 'loop'),
    'Listen': ('gestic_listen_neutral_01', 'loop'),
    'ListenB': ('gestic_listen_neutral_02', 'loop'),
    'Nod': ('gestic_listen_accept_01', 'once'),
    'NodB': ('gestic_listen_accept_02', 'once'),
    'Deny': ('gestic_listen_deny_01', 'once'),
    'Present': ('gestic_presentation_right_01', 'once'),
    'PresentL': ('gestic_presentation_left_01', 'once'),
    'Shrug': ('gestic_shrug_01', 'once'),
    'Think': ('gestic_thoughtful_01', 'once'),
    'Laugh': ('gestic_laugh_low', 'once'),
    'CrouchIdle': ('crouch_idle', 'loop'),
    'CrouchDown': ('crouch_in', 'keep'),
    'CrouchUp': ('crouch_out', 'keep'),
    'Sit': ('sit_chair_idle_neutral_01', 'keep'),
    'SitLook': ('sit_chair_idle_look_around', 'keep'),
    'SitStand': ('sit_stand_up_chair_01', 'keep'),
    'SitDown': ('sit_down_chair_01', 'keep'),
    'Wave': ('wave_01', 'once'),
    'Radio': ('headphones_idle', 'loop'),
    'Phone': ('cell_phone_talk_01', 'loop'),
    'Docs': ('documents_idle', 'loop'),
    'DocsCheck': ('documents_check', 'once'),
    'Lean': ('work_table', 'loop'),
    'Knock': ('knock_door', 'once'),
    'ListenDoor': ('listen_door', 'once'),
}
# Per-character takes: each operator idles and talks with their own capture, so a squad standing
# together never moves in step and each keeps an animation identity (docs/CHARACTERS_ANIMATION_AUDIO.md).
IDENTITY = {
    'sops_anchor': {},                                                          # composed, still
    'sops_brick': {'Idle': 'idle_neutral_04', 'Talk': 'gestic_talk_relaxed_01'},   # heavy, unhurried
    'sops_tally': {'Idle': 'idle_neutral_05', 'Talk': 'gestic_talk_excited_01'},   # fidgety
    'sops_patch': {'Idle': 'idle_neutral_02', 'Talk': 'gestic_talk_neutral_02'},
    'sops_echo': {'Idle': 'idle_neutral_03', 'Talk': 'gestic_talk_relaxed_01'},    # economical
    'sops_ranger': {'Idle': 'idle_breathe_01', 'Talk': 'gestic_talk_cool'},
    'sops_explorer': {'Idle': 'idle_neutral_03', 'Talk': 'gestic_talk_nervous_01'},
    'sops_greyline_a': {'Idle': 'idle_neutral_02'},
    'sops_greyline_b': {'Idle': 'idle_neutral_03'},
}
FPS = 30.0
XFADE = 0.4


def fetch(names):
    os.makedirs(ANIMS, exist_ok=True)
    for f in names:
        p = os.path.join(ANIMS, f)
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            continue
        for folder in ('all_animations_max_motextr_static', 'all_animations_max_motextr_xy',
                       'all_animations_max_motextr_xyz'):
            try:
                data = urllib.request.urlopen(RAW + folder + '/' + f).read()
            except Exception:
                continue
            open(p, 'wb').write(data)
            break


def capture_file(char, stem):
    g = 'f' if char in FEMALE else 'm'
    p = os.path.join(ANIMS, f'{g}_{stem}.max.fbx')
    if not os.path.exists(p) and g == 'f':          # fall back to the male take
        p = os.path.join(ANIMS, f'm_{stem}.max.fbx')
    return p if os.path.exists(p) else None


def mat_to_quat(m):
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s, (m[1, 0] - m[0, 1]) / s]
    q = np.array(q)
    return q / np.linalg.norm(q)


def slerp(a, b, t):
    d = float(np.dot(a, b))
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        r = a + (b - a) * t
        return r / np.linalg.norm(r)
    th = np.arccos(d)
    return (np.sin((1 - t) * th) * a + np.sin(t * th) * b) / np.sin(th)


def reduce_keys(times, vals, tol):
    """Greedy keyframe reduction: keep a key wherever linear interpolation from the last kept key
    to the next candidate strays more than `tol` from any sample in between."""
    n = len(times)
    if n <= 2:
        return np.arange(n)
    keep = [0]
    i = 0
    while i < n - 1:
        j = i + 2
        while j < n:
            seg_t = (times[i + 1:j] - times[i]) / (times[j] - times[i])
            interp = vals[i] + (vals[j] - vals[i]) * seg_t[:, None]
            if np.abs(interp - vals[i + 1:j]).max() > tol:
                break
            j += 1
        keep.append(j - 1)
        i = j - 1
    return np.array(keep)


def sample(char, avatar, joints, clips):
    fbx = os.path.join(RB, avatar, f'{avatar}_facial.fbx')
    out = os.path.join(tempfile.gettempdir(), f'mocap_{char}.npz')
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'avatar': fbx, 'joints': joints, 'clips': clips, 'out': out}, f)
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', os.path.join(HERE, 'blender_mocap.py'),
                        '--', f.name], capture_output=True, text=True)
    os.unlink(f.name)
    if 'MOCAP_OK' not in r.stdout:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f'mocap sampling failed: {char}')
    return np.load(out)


def compact(j, binc):
    """Rebuild the binary chunk with only the buffer views still referenced (after clips were
    replaced, their old keys are unreferenced)."""
    used_acc = set()
    for m in j.get('meshes', []):
        for p in m['primitives']:
            used_acc.update(p['attributes'].values())
            if 'indices' in p:
                used_acc.add(p['indices'])
            for t in p.get('targets', []):
                used_acc.update(t.values())
    for s in j.get('skins', []):
        if 'inverseBindMatrices' in s:
            used_acc.add(s['inverseBindMatrices'])
    for a in j.get('animations', []):
        for s in a['samplers']:
            used_acc.update((s['input'], s['output']))
    acc_map, accs = {}, []
    for i in sorted(used_acc):
        acc_map[i] = len(accs)
        accs.append(dict(j['accessors'][i]))
    used_bv = sorted({a['bufferView'] for a in accs if 'bufferView' in a} |
                     {im['bufferView'] for im in j.get('images', []) if 'bufferView' in im})
    bv_map, bvs, out = {}, [], bytearray()
    for i in used_bv:
        bv = dict(j['bufferViews'][i])
        while len(out) % 4:
            out.append(0)
        o = bv.get('byteOffset', 0)
        data = binc[o:o + bv['byteLength']]
        bv['byteOffset'] = len(out)
        out += data
        bv_map[i] = len(bvs)
        bvs.append(bv)
    for a in accs:
        if 'bufferView' in a:
            a['bufferView'] = bv_map[a['bufferView']]
    for im in j.get('images', []):
        if 'bufferView' in im:
            im['bufferView'] = bv_map[im['bufferView']]
    for m in j.get('meshes', []):
        for p in m['primitives']:
            p['attributes'] = {k: acc_map[v] for k, v in p['attributes'].items()}
            if 'indices' in p:
                p['indices'] = acc_map[p['indices']]
            if 'targets' in p:
                p['targets'] = [{k: acc_map[v] for k, v in t.items()} for t in p['targets']]
    for s in j.get('skins', []):
        if 'inverseBindMatrices' in s:
            s['inverseBindMatrices'] = acc_map[s['inverseBindMatrices']]
    for a in j.get('animations', []):
        for s in a['samplers']:
            s['input'], s['output'] = acc_map[s['input']], acc_map[s['output']]
    j['accessors'], j['bufferViews'] = accs, bvs
    return out


def save_glb(path, j, binc):
    import struct
    while len(binc) % 4:
        binc.append(0)
    j['buffers'] = [{'byteLength': len(binc)}]
    js = json.dumps(j, separators=(',', ':')).encode()
    while len(js) % 4:
        js += b' '
    out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binc))
    out += struct.pack('<II', len(js), 0x4E4F534A) + js
    out += struct.pack('<II', len(binc), 0x004E4942) + bytes(binc)
    open(path, 'wb').write(out)


def add_acc(j, binc, arr, typ, minmax=False):
    arr = np.ascontiguousarray(arr, np.float32)
    while len(binc) % 4:
        binc.append(0)
    j['bufferViews'].append({'buffer': 0, 'byteOffset': len(binc), 'byteLength': arr.nbytes})
    binc += arr.tobytes()
    a = {'bufferView': len(j['bufferViews']) - 1, 'componentType': 5126, 'count': int(arr.shape[0]), 'type': typ}
    if minmax:
        a['min'] = [float(x) for x in np.atleast_1d(arr.min(axis=0))]
        a['max'] = [float(x) for x in np.atleast_1d(arr.max(axis=0))]
    j['accessors'].append(a)
    return len(j['accessors']) - 1


def build(char):
    avatar = CAST[char][0]
    path = os.path.join(CHARS, char + '.glb')
    j, binc = read_glb(path)
    skin = j['skins'][0]
    jn = {j['nodes'][i]['name']: i for i in skin['joints']}
    g, parent = node_globals(j)
    rest_pos = {n: [float(x) for x in g[jn[n]][0]] for n in JOINTS}
    Rrest = {n: qmat(g[jn[n]][1]) for n in JOINTS}
    hip_parent = parent.get(jn['Hips'])
    Rhp = qmat(g[hip_parent][1]) if hip_parent is not None else np.eye(3)
    Thp = np.array(g[hip_parent][0]) if hip_parent is not None else np.zeros(3)

    ident = IDENTITY.get(char, {})
    clips = [(name, capture_file(char, ident.get(name, stem))) for name, (stem, _) in CLIPS.items()]
    missing = [n for n, p in clips if not p]
    clips = [(n, p) for n, p in clips if p]
    D = sample(char, avatar, rest_pos, clips)
    Rb_rest = D['rest']                       # (21, 3, 3)
    hips_rest = np.array(rest_pos['Hips'])
    scale = hips_rest[1] / max(float(D['rest_hips'][1]), 1e-3)

    names = {a['name']: k for k, a in enumerate(j.get('animations', []))}
    report = []
    for name, _ in clips:
        kind = CLIPS[name][1]
        Rb = D[f'{name}.R'].astype(np.float64)    # (F, 21, 3, 3)
        P = D[f'{name}.P'].astype(np.float64)     # (F, 3)
        F = len(Rb)
        # world rotations of the sops joints
        Rw = np.einsum('fjab,jcb,jcd->fjad', Rb, Rb_rest, np.array([Rrest[n] for n in JOINTS]))
        # hips position: capture pelvis, scaled; in-place clips lose their horizontal travel
        hp = P * scale
        hp[:, 1] += hips_rest[1] - float(D['rest_hips'][1]) * scale
        travel = hp[-1, [0, 2]] - hp[0, [0, 2]]
        speed = float(np.linalg.norm(travel)) / max((F - 1) / FPS, 1e-3)
        if kind in ('loop', 'once'):
            u = np.linspace(0, 1, F)[:, None]
            hp[:, [0, 2]] -= hp[0, [0, 2]] + travel[None, :] * u
            hp[:, [0, 2]] += hips_rest[[0, 2]]
        else:
            hp[:, [0, 2]] += hips_rest[[0, 2]] - hp[0, [0, 2]]
        # local rotations
        idx = {n: k for k, n in enumerate(JOINTS)}
        local_q = np.zeros((F, len(JOINTS), 4))
        for f in range(F):
            for k, n in enumerate(JOINTS):
                p = parent.get(jn[n])
                pn = j['nodes'][p]['name'] if p is not None else None
                PR = Rw[f, idx[pn]] if pn in idx else Rhp
                local_q[f, k] = mat_to_quat(PR.T @ Rw[f, k])
        hips_local = (Rhp.T @ (hp - Thp).T).T
        # hemisphere continuity
        for f in range(1, F):
            for k in range(len(JOINTS)):
                if np.dot(local_q[f, k], local_q[f - 1, k]) < 0:
                    local_q[f, k] *= -1
        if kind == 'loop':
            n = min(int(XFADE * FPS), F // 3)
            for i in range(n):
                t = (i + 1) / (n + 1)
                f = F - n + i
                for k in range(len(JOINTS)):
                    local_q[f, k] = slerp(local_q[f, k], local_q[0, k], t)
                hips_local[f] = hips_local[f] * (1 - t) + hips_local[0] * t
            local_q[-1] = local_q[0]
            hips_local[-1] = hips_local[0]
        times = np.arange(F) / FPS
        # write (replace a clip of the same name)
        channels, samplers = [], []
        for k, n in enumerate(JOINTS):
            keep = reduce_keys(times, local_q[:, k], 0.0015)
            ti = add_acc(j, binc, times[keep], 'SCALAR', minmax=True)
            to = add_acc(j, binc, local_q[keep, k], 'VEC4')
            samplers.append({'input': ti, 'output': to, 'interpolation': 'LINEAR'})
            channels.append({'sampler': len(samplers) - 1, 'target': {'node': jn[n], 'path': 'rotation'}})
        keep = reduce_keys(times, hips_local, 0.002)
        ti = add_acc(j, binc, times[keep], 'SCALAR', minmax=True)
        to = add_acc(j, binc, hips_local[keep], 'VEC3')
        samplers.append({'input': ti, 'output': to, 'interpolation': 'LINEAR'})
        channels.append({'sampler': len(samplers) - 1, 'target': {'node': jn['Hips'], 'path': 'translation'}})
        anim = {'name': name, 'channels': channels, 'samplers': samplers,
                'extras': {'source': f'Microsoft Rocketbox {os.path.basename(dict(clips)[name])} (MIT)',
                           'capture_speed': round(speed, 3)}}
        if name in names:
            j['animations'][names[name]] = anim
        else:
            j.setdefault('animations', []).append(anim)
            names[name] = len(j['animations']) - 1
        report.append(f'{name} {F / FPS:.2f}s {speed:.2f}m/s')
    binc = compact(j, binc)
    j['asset']['generator'] = j['asset'].get('generator', '').split(' + ')[0] + ' + build_mocap_clips.py (Rocketbox mocap, MIT)'
    save_glb(path, j, binc)
    print(char, os.path.getsize(path), 'bytes;', len(report), 'clips;', 'missing', missing)
    print('  ' + '; '.join(report))


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if '--fetch' in sys.argv:
        stems = {stem for stem, _ in CLIPS.values()} | {v for m in IDENTITY.values() for v in m.values()}
        fetch([f'{g}_{stem}.max.fbx' for stem in stems for g in 'mf'])
    for c in (args or [c for c in CAST]):
        build(c)
