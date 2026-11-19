# SPDX-License-Identifier: Apache-2.0
"""Build the SPECIAL OPS human characters on the VICTUS Vanguard skeleton.

    python3 tools/characters/build_humans.py --rig <victus>/engine/project/data/characters/victus_vanguard_02.glb \
        --out game/assets/models/characters

The Vanguard GLB is only read for its rig: the 21 joint nodes, inverse bind matrices and the seven
VICTUS clips (Idle, Walk, Run, Jump, Fall, Land, Interact). The robot mesh and materials are
discarded. New geometry is generated here procedurally and rigidly skinned (one joint per vertex),
the same technique the Vanguard family uses, so `vanguard_locomotion.vanim` drives the humans
unchanged. Extra clips (Stumble, GetUp, Scan, Talk, Wave, Inspect) are authored below as key
poses in model-space axes.

The head is its own skinned mesh with two morph targets, `Blink` and `JawOpen`, for dialogue.
Outputs are original SPECIAL OPS assets (Apache-2.0, see docs/ASSET_PROVENANCE.md).
"""
from __future__ import annotations
import argparse, copy, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from gltf_util import read_glb, accessor, Writer, node_globals, qmul, qconj, qaxis, qnorm, qrot  # noqa: E402
import meshkit as mk  # noqa: E402

JOINT_NAMES = ["Hips", "Spine", "Chest", "Neck", "Head", "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
               "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R", "UpperLeg.L", "LowerLeg.L", "Foot.L", "Toe.L",
               "UpperLeg.R", "LowerLeg.R", "Foot.R", "Toe.R"]
J = {n: i for i, n in enumerate(JOINT_NAMES)}


def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]


EXPLORER = dict(
    name="Explorer", skin=srgb('#c99a7c'), hair=srgb('#2b211b'), jacket=srgb('#4f5a3a'), jacket2=srgb('#3c4630'),
    pants=srgb('#34373b'), boots=srgb('#4a3526'), gloves=srgb('#6b5a45'), gear=srgb('#2a2d30'), accent=srgb('#c48a2c'),
    build=1.0, hat=False, backpack=True, vest=False)
RANGER = dict(
    name="Ranger", skin=srgb('#a8775a'), hair=srgb('#8d8a86'), jacket=srgb('#a99a74'), jacket2=srgb('#2f4a35'),
    pants=srgb('#5a4733'), boots=srgb('#2e2520'), gloves=srgb('#a8775a'), gear=srgb('#2f4a35'), accent=srgb('#c9b25a'),
    build=1.06, hat=True, backpack=False, vest=True)


def body_mesh(cfg, G):
    """Everything except the head. Returns meshkit.Mesh with joint tags."""
    m = mk.Mesh(); b = cfg['build']
    pos = {n: G[n] for n in JOINT_NAMES}
    jk, pn, bt, gl = cfg['jacket'], cfg['pants'], cfg['boots'], cfg['gloves']
    # pelvis / belt
    m.add(mk.rounded_box((0, 0.94, 0), (0.165 * b, 0.085, 0.112 * b), 0.45), pn, J['Hips'])
    m.add(mk.loft((0, 0.985, 0), (0, 1.03, 0), [(0, 0.172 * b, 0.12 * b), (1, 0.172 * b, 0.12 * b)], 20), cfg['gear'], J['Hips'])
    m.add(mk.rounded_box((0, 1.005, 0.122 * b), (0.03, 0.022, 0.008), 0.3), cfg['accent'], J['Hips'])  # buckle
    # torso
    m.add(mk.rounded_box((0, 1.11, 0.0), (0.168 * b, 0.105, 0.118 * b), 0.5), jk, J['Spine'])
    m.add(mk.rounded_box((0, 1.30, 0.0), (0.188 * b, 0.155, 0.125 * b), 0.5), jk, J['Chest'])
    # jacket hem flare and zipper line
    m.add(mk.loft((0, 1.02, 0), (0, 1.06, 0), [(0, 0.176 * b, 0.126 * b), (1, 0.17 * b, 0.12 * b)], 20), cfg['jacket2'], J['Spine'])
    m.add(mk.rounded_box((0, 1.24, 0.122 * b), (0.006, 0.19, 0.006), 0.3), cfg['jacket2'], J['Chest'])
    if cfg['vest']:
        m.add(mk.rounded_box((0, 1.27, 0.0), (0.198 * b, 0.14, 0.133 * b), 0.55), cfg['jacket2'], J['Chest'])
        m.add(mk.rounded_box((0.09, 1.34, 0.136 * b), (0.03, 0.025, 0.006), 0.3), cfg['accent'], J['Chest'])  # badge
    else:
        for sx in (-1, 1):  # chest pockets
            m.add(mk.rounded_box((sx * 0.085, 1.31, 0.124 * b), (0.05, 0.045, 0.008), 0.3), cfg['jacket2'], J['Chest'])
    # collar
    m.add(mk.loft((0, 1.42, -0.005), (0, 1.48, -0.005), [(0, 0.085, 0.075), (1, 0.07, 0.065)], 16), cfg['jacket2'], J['Chest'])
    if cfg['backpack']:
        m.add(mk.rounded_box((0, 1.25, -0.19 * b), (0.135, 0.17, 0.07), 0.55), cfg['gear'], J['Chest'])
        m.add(mk.rounded_box((0, 1.16, -0.255 * b), (0.11, 0.06, 0.02), 0.4), cfg['jacket2'], J['Chest'])
        for sx in (-1, 1):  # straps
            m.add(mk.rounded_box((sx * 0.095, 1.33, 0.11 * b), (0.02, 0.12, 0.012), 0.3), cfg['gear'], J['Chest'])
    # neck
    m.add(mk.capsule((0, 1.43, 0), (0, 1.53, 0.005), 0.047, 0.045), cfg['skin'], J['Neck'])
    for side in ('L', 'R'):
        s = 1 if side == 'L' else -1
        ua, la = pos['UpperArm.' + side], pos['LowerArm.' + side]
        d2 = (pos['Hand.' + side] - la); d2 /= np.linalg.norm(d2)
        m.add(mk.ellipsoid((s * 0.165 * b, 1.385, 0), (0.078 * b, 0.07, 0.083 * b)), jk, J['Shoulder.' + side])
        m.add(mk.capsule(ua, la, 0.054 * b, 0.046 * b), jk, J['UpperArm.' + side])
        m.add(mk.capsule(la, pos['Hand.' + side] - d2 * 0.03, 0.045 * b, 0.038 * b), jk, J['LowerArm.' + side])
        m.add(mk.loft(pos['Hand.' + side] - d2 * 0.05, pos['Hand.' + side] - d2 * 0.005,
                      [(0, 0.043 * b, 0.043 * b), (1, 0.041 * b, 0.041 * b)], 14), cfg['jacket2'], J['LowerArm.' + side])
        hb = pos['Hand.' + side]
        m.add(mk.capsule(hb + d2 * 0.005, hb + d2 * 0.11, 0.036, 0.03, squash=0.62, hint=(0, 0, 1)), gl, J['Hand.' + side])
        m.add(mk.capsule(hb + d2 * 0.03 + np.array([0, 0, 0.03]), hb + d2 * 0.075 + np.array([0, 0, 0.045]), 0.014, 0.012),
              gl, J['Hand.' + side])  # thumb
        ul, ll, ft, to = pos['UpperLeg.' + side], pos['LowerLeg.' + side], pos['Foot.' + side], pos['Toe.' + side]
        m.add(mk.capsule(ul + np.array([0, 0.02, 0]), ll, 0.078 * b, 0.058 * b), pn, J['UpperLeg.' + side])
        m.add(mk.capsule(ll, ft + np.array([0, 0.12, 0]), 0.057 * b, 0.047 * b), pn, J['LowerLeg.' + side])
        m.add(mk.capsule(ft + np.array([0, 0.2, -0.005]), ft + np.array([0, 0.03, 0]), 0.053, 0.055), bt, J['LowerLeg.' + side])
        m.add(mk.rounded_box((ft[0], 0.055, 0.03), (0.056, 0.05, 0.095), 0.4), bt, J['Foot.' + side])
        m.add(mk.rounded_box((to[0], 0.042, 0.16), (0.052, 0.038, 0.05), 0.5), bt, J['Toe.' + side])
        m.add(mk.rounded_box((ft[0], 0.012, 0.06), (0.06, 0.012, 0.14), 0.25), cfg['gear'], J['Foot.' + side])  # sole
    return m


def head_mesh(cfg):
    """Head with face features. Returns (Mesh, blink_delta, jaw_delta)."""
    m = mk.Mesh(); hj = J['Head']
    skin, hair = cfg['skin'], cfg['hair']
    hc = np.array([0, 1.615, 0.012])
    parts = []
    def add(part, col, kind=''):
        start = m.n; m.add(part, col, hj); parts.append((kind, start, m.n))
    add(mk.ellipsoid(hc, (0.094, 0.116, 0.106), 22, 16), skin, 'skull')
    add(mk.ellipsoid(hc + [0, -0.072, 0.03], (0.066, 0.046, 0.068), 16, 10), skin, 'jaw')  # jaw/chin volume
    # hair
    add(mk.ellipsoid(hc + [0, 0.036, -0.022], (0.1, 0.1, 0.104), 22, 14), hair, 'hair')
    add(mk.ellipsoid(hc + [0, -0.01, -0.03], (0.097, 0.09, 0.085), 18, 12), hair, 'hair')
    for sx in (-1, 1):
        add(mk.ellipsoid(hc + [sx * 0.093, -0.01, -0.005], (0.014, 0.026, 0.018), 10, 8), skin, 'ear')
    add(mk.ellipsoid(hc + [0, -0.012, 0.112], (0.015, 0.027, 0.018), 10, 8), skin, 'nose')
    eye_y = hc[1] + 0.012
    white = [0.85, 0.83, 0.8]; iris = srgb('#3a2c22') if cfg['name'] == 'Explorer' else srgb('#3d5560')
    for sx in (-1, 1):
        ec = np.array([sx * 0.036, eye_y, 0.1])
        add(mk.ellipsoid(ec, (0.017, 0.012, 0.012), 12, 8), white, 'eye')
        add(mk.ellipsoid(ec + [0, 0, 0.0095], (0.0082, 0.0082, 0.004), 10, 6), iris, 'iris')
        add(mk.rounded_box(ec + [0, 0.026, 0.006], (0.021, 0.0045, 0.006), 0.4, rot=mk.rot_z(-sx * 6)), hair, 'brow')
        add(mk.ellipsoid(ec + [0, 0.0135, 0.0005], (0.0198, 0.0062, 0.0146), 12, 8), skin, 'lid')
    add(mk.ellipsoid(hc + [0, -0.052, 0.1], (0.024, 0.0045, 0.011), 12, 6), srgb('#5a2a28'), 'mouth')
    add(mk.ellipsoid(hc + [0, -0.045, 0.104], (0.025, 0.0042, 0.008), 12, 6), srgb('#9a6058'), 'lip')
    if cfg['hat']:
        hp = hc + [0, 0.07, -0.005]
        add(mk.loft(hp + [0, -0.01, 0], hp + [0, 0.005, 0], [(0, 0.19, 0.2), (1, 0.18, 0.19)], 28), cfg['jacket2'], 'hat')
        add(mk.loft(hp, hp + [0, 0.09, 0], [(0, 0.104, 0.112), (0.8, 0.098, 0.104), (1, 0.06, 0.07)], 24), cfg['jacket2'], 'hat')
        add(mk.loft(hp + [0, 0.012, 0], hp + [0, 0.03, 0], [(0, 0.106, 0.114), (1, 0.105, 0.113)], 24), cfg['accent'], 'hat')
    P, N, C, T, I, UV = m.arrays()
    blink = np.zeros_like(P); jaw = np.zeros_like(P)
    for kind, s, e in parts:
        if kind == 'lid':
            # move the lid down and slightly forward to cover the eye
            c = P[s:e].mean(0)
            blink[s:e, 1] = (P[s:e, 1] - c[1]) * 1.25 - 0.0125; blink[s:e, 2] = 0.0015
        if kind in ('mouth',):
            c = P[s:e].mean(0); jaw[s:e, 1] = (P[s:e, 1] - c[1]) * 2.2 - 0.004
        if kind in ('jaw',):
            w = np.clip((hc[1] - 0.04 - P[s:e, 1]) / 0.06, 0, 1) * np.clip(P[s:e, 2] / 0.06, 0, 1)
            jaw[s:e, 1] = -0.012 * w
        if kind == 'skull':
            w = np.clip((hc[1] - 0.06 - P[s:e, 1]) / 0.05, 0, 1) * np.clip((P[s:e, 2] - 0.02) / 0.07, 0, 1)
            jaw[s:e, 1] = -0.011 * w
    return (P, N, C, T, I, UV), blink.astype(np.float32), jaw.astype(np.float32)


# ------------------------------------------------------------------------------------------------
# Clip authoring: key poses as model-space axis rotations at each joint.

def axis_sign(jn, ax):
    """Authoring convention -> model-space rotation sign.

    Key poses are written so that +X means 'forward' for every joint: the torso and head pitch
    forward, a thigh or upper arm swings forward, elbows use -X to flex (forearm forward) and knees
    use -X to flex (shin back) so both read as 'bend'. +Z on an arm joint raises the arm sideways
    away from the body on the left and toward the body on the right; arms_down uses this. Limbs
    that hang downward need the X sign flipped, and right-side Z is mirrored by the model.
    """
    base = jn.split('.')[0]
    sgn = 1
    if ax == X and base in ('UpperArm', 'Hand', 'UpperLeg', 'LowerLeg'):
        sgn = -1
    if ax == Z and base in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand'):
        sgn = -1
    return sgn


def make_clip(name, keys, rest_local, rest_global, joint_nodes, hips_rest_t, fps=30, loop=False):
    """keys: list of (time, {joint: [(axis, deg), ...]}, hips_offset(xyz)).

    Each joint's delta is a rotation about model-space axes at that joint's rest orientation, so
    the result reads the same regardless of Blender bone roll. Between keys rotations are slerped
    with smoothstep easing.
    """
    times = np.arange(0, keys[-1][0] + 1e-6, 1 / fps)
    def pose_at(k):
        out = {}
        for jn in JOINT_NAMES:
            q = np.array([0, 0, 0, 1.0])
            for ax, deg in k[1].get(jn, []):
                q = qmul(qaxis(ax, deg * axis_sign(jn, ax)), q)
            out[jn] = q
        return out, np.array(k[2] if len(k) > 2 else (0, 0, 0), float)
    poses = [pose_at(k) for k in keys]
    rot = {jn: [] for jn in JOINT_NAMES}; hips_t = []
    for t in times:
        i = max(0, min(len(keys) - 2, int(np.searchsorted([k[0] for k in keys], t, side='right')) - 1))
        t0, t1 = keys[i][0], keys[i + 1][0]
        u = 0 if t1 == t0 else np.clip((t - t0) / (t1 - t0), 0, 1); u = u * u * (3 - 2 * u)
        for jn in JOINT_NAMES:
            qa, qb = poses[i][0][jn], poses[i + 1][0][jn]
            if np.dot(qa, qb) < 0: qb = -qb
            d = qnorm(qa * (1 - u) + qb * u)  # nlerp is fine for these small deltas
            gr = rest_global[jn]
            local_delta = qmul(qmul(qconj(gr), d), gr)
            rot[jn].append(qnorm(qmul(rest_local[jn], local_delta)))
        hips_t.append(hips_rest_t + poses[i][1] * (1 - u) + poses[i + 1][1] * u)
    return name, times.astype(np.float32), {k: np.array(v, np.float32) for k, v in rot.items()}, np.array(hips_t, np.float32)


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def authored_clips():
    """Key poses. +X rotation pitches a joint forward (toward +Z), +Y turns it to its left."""
    arms_down = {'UpperArm.L': [(Z, 28)], 'UpperArm.R': [(Z, -28)]}  # relax A-pose toward the body
    def merge(*ds):
        out = {}
        for d in ds:
            for k, v in d.items(): out.setdefault(k, []).extend(v)
        return out
    relaxed = merge(arms_down, {'LowerArm.L': [(X, -12)], 'LowerArm.R': [(X, -12)]})
    clips = []
    # Stumble: catch a foot, pitch forward, throw the arms out, drop to one knee (ends low).
    clips.append(("Stumble", [
        (0.0, relaxed, (0, 0, 0)),
        (0.18, merge(relaxed, {'Spine': [(X, 18)], 'Chest': [(X, 14)], 'UpperLeg.R': [(X, -30)], 'LowerLeg.R': [(X, 40)],
                               'UpperLeg.L': [(X, 22)], 'UpperArm.L': [(X, 50)], 'UpperArm.R': [(X, 45)], 'Head': [(X, -12)]}), (0, -0.03, 0.08)),
        (0.45, merge(relaxed, {'Spine': [(X, 30)], 'Chest': [(X, 18)], 'UpperLeg.L': [(X, 70)], 'LowerLeg.L': [(X, -95)],
                               'UpperLeg.R': [(X, -15)], 'LowerLeg.R': [(X, -100)], 'Foot.R': [(X, 50)],
                               'UpperArm.L': [(X, 60), (Z, 10)], 'UpperArm.R': [(X, 60), (Z, -10)],
                               'LowerArm.L': [(X, -30)], 'LowerArm.R': [(X, -30)], 'Head': [(X, -20)]}), (0, -0.36, 0.22)),
        (0.9, merge(relaxed, {'Spine': [(X, 22)], 'Chest': [(X, 10)], 'UpperLeg.L': [(X, 75)], 'LowerLeg.L': [(X, -100)], 'Foot.L': [(X, 20)],
                              'UpperLeg.R': [(X, -10)], 'LowerLeg.R': [(X, -105)], 'Foot.R': [(X, 55)],
                              'UpperArm.L': [(X, 25)], 'UpperArm.R': [(X, 40)], 'LowerArm.R': [(X, -40)], 'Head': [(X, -8)]}), (0, -0.4, 0.2)),
    ]))
    low = clips[-1][1][-1]
    clips.append(("GetUp", [
        (0.0, low[1], low[2]),
        (0.45, merge(relaxed, {'Spine': [(X, 26)], 'Chest': [(X, 8)], 'UpperLeg.L': [(X, 55)], 'LowerLeg.L': [(X, -70)],
                               'UpperLeg.R': [(X, 20)], 'LowerLeg.R': [(X, -50)], 'Foot.R': [(X, 15)],
                               'UpperArm.L': [(X, 10)], 'UpperArm.R': [(X, 15)]}), (0, -0.22, 0.12)),
        (0.9, merge(relaxed, {'Spine': [(X, 6)], 'Head': [(X, 4), (Y, 10)]}), (0, -0.02, 0.02)),
        (1.2, relaxed, (0, 0, 0)),
    ]))
    scan_pose = merge(relaxed, {'UpperArm.R': [(Z, 28), (X, 70)], 'LowerArm.R': [(X, 25)], 'Hand.R': [(X, -10)],
                                'UpperArm.L': [(X, 15)], 'Chest': [(Y, 8)], 'Head': [(X, 6)]})
    clips.append(("Scan", [
        (0.0, scan_pose, (0, 0, 0)),
        (0.6, merge(scan_pose, {'Chest': [(Y, -16)], 'Head': [(Y, -14)]}), (0, 0, 0)),
        (1.2, merge(scan_pose, {'Chest': [(Y, 14)], 'Head': [(Y, 12)]}), (0, 0, 0)),
        (1.6, scan_pose, (0, 0, 0)),
    ]))
    clips.append(("Talk", [
        (0.0, relaxed, (0, 0, 0)),
        (0.7, merge(relaxed, {'UpperArm.R': [(X, 30)], 'LowerArm.R': [(X, -50)], 'Head': [(X, 6), (Y, 6)], 'Chest': [(Y, 5)]}), (0, 0, 0)),
        (1.5, merge(relaxed, {'UpperArm.R': [(X, 20)], 'LowerArm.R': [(X, -40)], 'Hand.R': [(Z, -20)], 'Head': [(X, -3), (Y, -4)]}), (0, 0, 0)),
        (2.3, merge(relaxed, {'UpperArm.L': [(X, 25)], 'LowerArm.L': [(X, -45)], 'Head': [(X, 4), (Y, -8)], 'Chest': [(Y, -4)]}), (0, 0, 0)),
        (3.0, relaxed, (0, 0, 0)),
    ]))
    wave_up = merge(relaxed, {'UpperArm.R': [(Z, 90), (X, 20)], 'LowerArm.R': [(X, -10), (Z, 40)]})
    clips.append(("Wave", [
        (0.0, relaxed, (0, 0, 0)),
        (0.35, wave_up, (0, 0, 0)),
        (0.6, merge(wave_up, {'LowerArm.R': [(Z, -35)]}), (0, 0, 0)),
        (0.85, wave_up, (0, 0, 0)),
        (1.1, merge(wave_up, {'LowerArm.R': [(Z, -35)]}), (0, 0, 0)),
        (1.5, relaxed, (0, 0, 0)),
    ]))
    crouch = merge(relaxed, {'Spine': [(X, 25)], 'Chest': [(X, 15)], 'Head': [(X, 15)], 'UpperLeg.L': [(X, 60)], 'LowerLeg.L': [(X, -85)],
                             'Foot.L': [(X, 25)], 'UpperLeg.R': [(X, 40)], 'LowerLeg.R': [(X, -90)], 'Foot.R': [(X, 48)],
                             'UpperArm.R': [(X, 45)], 'LowerArm.R': [(X, -30)], 'UpperArm.L': [(X, 20)]})
    clips.append(("Inspect", [
        (0.0, relaxed, (0, 0, 0)),
        (0.5, crouch, (0, -0.3, 0.05)),
        (1.4, merge(crouch, {'Head': [(Y, 12)], 'Hand.R': [(X, 15)]}), (0, -0.3, 0.05)),
        (2.0, relaxed, (0, 0, 0)),
    ]))
    return clips


def build(cfg, rig_path, out_path):
    j, binc = read_glb(rig_path)
    G, parent = node_globals(j)
    name_to_node = {n['name']: i for i, n in enumerate(j['nodes'])}
    joints = j['skins'][0]['joints']
    assert [j['nodes'][i]['name'] for i in joints] == JOINT_NAMES, "unexpected Vanguard joint order"
    gpos = {n: G[name_to_node[n]][0] for n in JOINT_NAMES}
    grot = {n: G[name_to_node[n]][1] for n in JOINT_NAMES}
    rlocal = {n: np.array(j['nodes'][name_to_node[n]].get('rotation', [0, 0, 0, 1]), float) for n in JOINT_NAMES}
    hips_rest_t = np.array(j['nodes'][name_to_node['Hips']].get('translation'), float)
    ibm = accessor(j, binc, j['skins'][0]['inverseBindMatrices']).astype(np.float32)
    old_anims = []
    for a in j['animations']:
        chans = []
        for c in a['channels']:
            s = a['samplers'][c['sampler']]
            chans.append((c['target']['node'], c['target']['path'], accessor(j, binc, s['input']).astype(np.float32),
                          accessor(j, binc, s['output']).astype(np.float32), s.get('interpolation', 'LINEAR')))
        old_anims.append((a['name'], chans))

    out = copy.deepcopy({k: v for k, v in j.items() if k not in ('accessors', 'bufferViews', 'buffers', 'animations', 'meshes', 'materials')})
    out['asset'] = {'version': '2.0', 'generator': 'SPECIAL OPS build_humans.py'}
    out.pop('extensionsUsed', None)
    w = Writer(out)
    out['materials'] = [
        {'name': cfg['name'] + '_Cloth', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.82}},
        {'name': cfg['name'] + '_Skin', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0.0, 'roughnessFactor': 0.55}},
    ]
    body = body_mesh(cfg, gpos)
    (hP, hN, hC, hT, hI, hUV), blink, jaw = head_mesh(cfg)

    def prim(P, N, C, T, I, mat, targets=None):
        jn = np.zeros((len(P), 4), np.uint8); jn[:, 0] = T.astype(np.uint8)
        wt = np.zeros((len(P), 4), np.float32); wt[:, 0] = 1
        attrs = {'POSITION': w.add(P, 'VEC3', 34962, True), 'NORMAL': w.add(N, 'VEC3', 34962),
                 'COLOR_0': w.add(C, 'VEC4', 34962), 'JOINTS_0': w.add(jn, 'VEC4', 34962), 'WEIGHTS_0': w.add(wt, 'VEC4', 34962)}
        p = {'attributes': attrs, 'indices': w.add(I, 'SCALAR', 34963), 'material': mat}
        if targets:
            p['targets'] = [{'POSITION': w.add(t, 'VEC3', 34962, True)} for t in targets]
        return p
    bP, bN, bC, bT, bI, _ = body.arrays()
    out['meshes'] = [
        {'name': cfg['name'] + '_Body', 'primitives': [prim(bP, bN, bC, bT, bI, 0)]},
        {'name': cfg['name'] + '_Head', 'primitives': [prim(hP, hN, hC, hT, hI, 1, [blink, jaw])],
         'weights': [0.0, 0.0], 'extras': {'targetNames': ['Blink', 'JawOpen']}},
    ]
    ibm_acc = w.add(ibm.reshape(-1, 16), 'MAT4')
    out['skins'][0]['inverseBindMatrices'] = ibm_acc
    out['skins'][0]['name'] = cfg['name'] + '_Rig'
    # rename the mesh node, add the head node, rename the root
    for i, n in enumerate(out['nodes']):
        if 'mesh' in n:
            n['name'] = cfg['name'] + '_Body'; body_node = i
        if n['name'] == 'Vanguard':
            n['name'] = cfg['name']; root = i
    out['nodes'].append({'name': cfg['name'] + '_Head', 'mesh': 1, 'skin': 0})
    out['nodes'][root]['children'].insert(1, len(out['nodes']) - 1)

    anims = []
    for name, chans in old_anims:
        samplers, channels = [], []
        for node, path, inp, outp, interp in chans:
            samplers.append({'input': w.add(inp, 'SCALAR', None, True), 'output': w.add(outp, {3: 'VEC3', 4: 'VEC4'}[outp.shape[1]]),
                             'interpolation': interp})
            channels.append({'sampler': len(samplers) - 1, 'target': {'node': node, 'path': path}})
        anims.append({'name': name, 'samplers': samplers, 'channels': channels})
    for name, keys in authored_clips():
        _, times, rot, hips_t = make_clip(name, keys, rlocal, grot, None, hips_rest_t)
        samplers, channels = [], []
        ti = w.add(times, 'SCALAR', None, True)
        for jn in JOINT_NAMES:
            samplers.append({'input': ti, 'output': w.add(rot[jn], 'VEC4'), 'interpolation': 'LINEAR'})
            channels.append({'sampler': len(samplers) - 1, 'target': {'node': name_to_node[jn], 'path': 'rotation'}})
        samplers.append({'input': ti, 'output': w.add(hips_t, 'VEC3'), 'interpolation': 'LINEAR'})
        channels.append({'sampler': len(samplers) - 1, 'target': {'node': name_to_node['Hips'], 'path': 'translation'}})
        anims.append({'name': name, 'samplers': samplers, 'channels': channels})
    out['animations'] = anims
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    w.save(out_path)
    tris = (len(bI) + len(hI)) // 3
    print(f"{out_path}: {len(bP) + len(hP)} vertices, {tris} triangles, clips: {[a['name'] for a in anims]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    build(EXPLORER, a.rig, os.path.join(a.out, 'sops_explorer.glb'))
    build(RANGER, a.rig, os.path.join(a.out, 'sops_ranger.glb'))


if __name__ == '__main__':
    main()
