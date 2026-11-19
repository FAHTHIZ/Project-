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


BASE = dict(build=1.0, hat=False, backpack=False, vest=False, headgear=None, hair_style='short', beard=False,
            pack=None, armband=None, mask=False, iris='#3a2c22', morphs=True, shoulders=1.0, brow_tilt=6)

def C(**kw):
    d = dict(BASE); d.update(kw)
    for k in ('skin', 'hair', 'jacket', 'jacket2', 'pants', 'boots', 'gloves', 'gear', 'accent'):
        d[k] = srgb(d[k])
    return d


EXPLORER = C(name="Explorer", skin='#c99a7c', hair='#2b211b', jacket='#4f5a3a', jacket2='#3c4630', pants='#34373b',
             boots='#4a3526', gloves='#6b5a45', gear='#2a2d30', accent='#c48a2c', backpack=True)
RANGER = C(name="Ranger", skin='#a8775a', hair='#8d8a86', jacket='#a99a74', jacket2='#2f4a35', pants='#5a4733',
           boots='#2e2520', gloves='#a8775a', gear='#2f4a35', accent='#c9b25a', build=1.06, hat=True, vest=True,
           headgear='hat', iris='#3d5560')
# The squad. Shared Mosswood unit palette (olive/stone) with a personal accent colour each.
ANCHOR = C(name="Anchor", skin='#8a5a3f', hair='#1d1814', jacket='#55603f', jacket2='#3b4430', pants='#3f4236',
           boots='#3a2b20', gloves='#2c2a26', gear='#2a2d2a', accent='#d0a040', build=1.08, vest='plate',
           headgear='cap', hair_style='buzz', beard=True, pack='backpack', iris='#2a2018', brow_tilt=2)
PATCH = C(name="Patch", skin='#e0b493', hair='#7a3b22', jacket='#5d6a55', jacket2='#45503f', pants='#3b3f3c',
          boots='#40322a', gloves='#d8d8d0', gear='#33383a', accent='#3fb7a4', build=0.93, shoulders=0.92,
          vest='plate', hair_style='bun', pack='medic', armband='#3fb7a4', iris='#4a6a3a', brow_tilt=8)
ECHO = C(name="Echo", skin='#c48e6a', hair='#0f0f12', jacket='#4a5446', jacket2='#30382f', pants='#2f332f',
         boots='#262420', gloves='#262624', gear='#24282a', accent='#8fb3d8', build=0.95, shoulders=0.95,
         vest=False, headgear='hood', hair_style='short', pack=None, iris='#2c2420', brow_tilt=10)
TALLY = C(name="Tally", skin='#f0c8a8', hair='#c8a060', jacket='#606a48', jacket2='#454d36', pants='#44473b',
          boots='#3e3026', gloves='#3a3530', gear='#2e3230', accent='#e07a3a', build=1.12, vest='plate',
          headgear='headset', hair_style='short', beard=False, pack='radio', iris='#4a6880', brow_tilt=4)
# Brick (story bible rev 2): the breacher. Heaviest build, helmet, short beard, rust accent.
BRICK = C(name="Brick", skin='#5e3c2a', hair='#141110', jacket='#525c3e', jacket2='#394130', pants='#3c3f34',
          boots='#2e241c', gloves='#24221f', gear='#282b28', accent='#b4502e', build=1.2, shoulders=1.1,
          vest='plate', headgear='helmet', hair_style='buzz', beard=True, pack='backpack', iris='#231a14', brow_tilt=1)
# Greyline contractors: grey/charcoal with safety-orange visor; faces covered, no facial morphs.
GREYLINE_A = C(name="Greyline", skin='#b08a70', hair='#202020', jacket='#5c6064', jacket2='#3a3d41', pants='#2f3236',
               boots='#1e1f21', gloves='#1e1f21', gear='#26282b', accent='#ff7a1a', vest='plate', headgear='helmet',
               mask=True, morphs=False, hair_style='buzz')
GREYLINE_B = C(name="GreylineB", skin='#7a5440', hair='#202020', jacket='#4c5054', jacket2='#2e3134', pants='#3a3d41',
               boots='#1e1f21', gloves='#1e1f21', gear='#26282b', accent='#ff7a1a', build=1.1, vest='plate',
               headgear='helmet', mask=True, morphs=False, pack='backpack', hair_style='buzz')
CAST = [(EXPLORER, 'sops_explorer'), (RANGER, 'sops_ranger'), (ANCHOR, 'sops_anchor'), (PATCH, 'sops_patch'),
        (ECHO, 'sops_echo'), (TALLY, 'sops_tally'), (BRICK, 'sops_brick'), (GREYLINE_A, 'sops_greyline_a'), (GREYLINE_B, 'sops_greyline_b')]


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
    m.add(mk.rounded_box((0, 1.30, 0.0), (0.188 * b * cfg['shoulders'], 0.155, 0.125 * b), 0.5), jk, J['Chest'])
    # jacket hem flare and zipper line
    m.add(mk.loft((0, 1.02, 0), (0, 1.06, 0), [(0, 0.176 * b, 0.126 * b), (1, 0.17 * b, 0.12 * b)], 20), cfg['jacket2'], J['Spine'])
    m.add(mk.rounded_box((0, 1.24, 0.122 * b), (0.006, 0.19, 0.006), 0.3), cfg['jacket2'], J['Chest'])
    if cfg['vest'] == 'plate':
        m.add(mk.rounded_box((0, 1.26, 0.012), (0.2 * b, 0.15, 0.138 * b), 0.42), cfg['gear'], J['Chest'])
        for k, sx in enumerate((-0.1, -0.035, 0.035, 0.1)):  # front pouches
            m.add(mk.rounded_box((sx * b, 1.16, 0.15 * b), (0.03, 0.04, 0.02), 0.35), cfg['jacket2'], J['Chest'])
        m.add(mk.rounded_box((0.11 * b, 1.34, 0.146 * b), (0.028, 0.018, 0.005), 0.3), cfg['accent'], J['Chest'])  # unit patch
    elif cfg['vest']:
        m.add(mk.rounded_box((0, 1.27, 0.0), (0.198 * b, 0.14, 0.133 * b), 0.55), cfg['jacket2'], J['Chest'])
        m.add(mk.rounded_box((0.09, 1.34, 0.136 * b), (0.03, 0.025, 0.006), 0.3), cfg['accent'], J['Chest'])  # badge
    else:
        for sx in (-1, 1):  # chest pockets
            m.add(mk.rounded_box((sx * 0.085, 1.31, 0.124 * b), (0.05, 0.045, 0.008), 0.3), cfg['jacket2'], J['Chest'])
    # collar
    m.add(mk.loft((0, 1.42, -0.005), (0, 1.48, -0.005), [(0, 0.085, 0.075), (1, 0.07, 0.065)], 16), cfg['jacket2'], J['Chest'])
    if cfg['pack'] == 'medic':
        m.add(mk.rounded_box((0, 1.24, -0.175 * b), (0.12, 0.13, 0.06), 0.5), cfg['jacket2'], J['Chest'])
        m.add(mk.rounded_box((0, 1.27, -0.237 * b), (0.035, 0.012, 0.004), 0.2), cfg['accent'], J['Chest'])
        m.add(mk.rounded_box((0, 1.27, -0.237 * b), (0.012, 0.035, 0.004), 0.2), cfg['accent'], J['Chest'])
        m.add(mk.rounded_box((-0.17 * b, 0.93, 0.02), (0.035, 0.06, 0.07), 0.45), cfg['jacket2'], J['Hips'])  # hip satchel
    elif cfg['pack'] == 'radio':
        m.add(mk.rounded_box((0, 1.24, -0.2 * b), (0.14, 0.18, 0.08), 0.35), cfg['gear'], J['Chest'])
        m.add(mk.rounded_box((0.06, 1.33, -0.285 * b), (0.03, 0.03, 0.006), 0.3), cfg['accent'], J['Chest'])
        m.add(mk.capsule((-0.09, 1.38, -0.22 * b), (-0.11, 1.78, -0.25 * b), 0.006, 0.004, segs=6, rings=2), cfg['gear'], J['Chest'])
    elif cfg['pack'] == 'backpack':
        m.add(mk.rounded_box((0, 1.25, -0.19 * b), (0.135, 0.17, 0.07), 0.55), cfg['gear'], J['Chest'])
        m.add(mk.rounded_box((0, 1.16, -0.255 * b), (0.11, 0.06, 0.02), 0.4), cfg['jacket2'], J['Chest'])
    if cfg['armband']:
        ua, la = pos['UpperArm.L'], pos['LowerArm.L']
        m.add(mk.loft(ua + (la - ua) * 0.45, ua + (la - ua) * 0.6, [(0, 0.058 * b, 0.058 * b), (1, 0.056 * b, 0.056 * b)], 14),
              srgb(cfg['armband']), J['UpperArm.L'])
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


MORPHS = ['Blink', 'JawOpen', 'Smile', 'Frown', 'BrowUp', 'BrowDown', 'MouthO', 'LookL', 'LookR', 'LookUp', 'LookDown']


def head_mesh(cfg):
    """Head with face features, hair and headgear. Returns (arrays, {morph: delta}) with the
    morph dict empty for characters whose faces are covered (cfg['morphs'] False)."""
    m = mk.Mesh(); hj = J['Head']
    skin, hair = cfg['skin'], cfg['hair']
    hc = np.array([0, 1.615, 0.012])
    parts = []
    def add(part, col, kind=''):
        start = m.n; m.add(part, col, hj); parts.append((kind, start, m.n))
    add(mk.ellipsoid(hc, (0.094, 0.116, 0.106), 22, 16), skin, 'skull')
    add(mk.ellipsoid(hc + [0, -0.072, 0.03], (0.066, 0.046, 0.068), 16, 10), skin, 'jaw')  # jaw/chin volume
    hs = cfg['hair_style']
    if hs == 'buzz':
        add(mk.ellipsoid(hc + [0, 0.022, -0.012], (0.097, 0.1, 0.1), 22, 14), hair, 'hair')
    else:
        add(mk.ellipsoid(hc + [0, 0.036, -0.022], (0.1, 0.1, 0.104), 22, 14), hair, 'hair')
        add(mk.ellipsoid(hc + [0, -0.01, -0.03], (0.097, 0.09, 0.085), 18, 12), hair, 'hair')
    if hs == 'bun':
        add(mk.ellipsoid(hc + [0, 0.05, -0.115], (0.042, 0.04, 0.038), 14, 10), hair, 'hair')
    if cfg['beard']:
        add(mk.ellipsoid(hc + [0, -0.078, 0.038], (0.07, 0.05, 0.07), 18, 10), hair, 'beard')
        add(mk.ellipsoid(hc + [0, -0.034, 0.1], (0.03, 0.007, 0.012), 12, 6), hair, 'moustache')
    for sx in (-1, 1):
        add(mk.ellipsoid(hc + [sx * 0.093, -0.01, -0.005], (0.014, 0.026, 0.018), 10, 8), skin, 'ear')
    add(mk.ellipsoid(hc + [0, -0.012, 0.112], (0.015, 0.027, 0.018), 10, 8), skin, 'nose')
    eye_y = hc[1] + 0.012
    white = [0.85, 0.83, 0.8]; iris = srgb(cfg['iris'])
    for sx in (-1, 1):
        ec = np.array([sx * 0.036, eye_y, 0.1])
        add(mk.ellipsoid(ec, (0.017, 0.012, 0.012), 12, 8), white, 'eye')
        add(mk.ellipsoid(ec + [0, 0, 0.0095], (0.0082, 0.0082, 0.004), 10, 6), iris, 'iris')
        add(mk.rounded_box(ec + [0, 0.026, 0.006], (0.021, 0.0045, 0.006), 0.4, rot=mk.rot_z(-sx * cfg['brow_tilt'])), hair, 'brow')
        add(mk.ellipsoid(ec + [0, 0.0135, 0.0005], (0.0198, 0.0062, 0.0146), 12, 8), skin, 'lid')
    add(mk.ellipsoid(hc + [0, -0.052, 0.1], (0.024, 0.0045, 0.011), 12, 6), srgb('#5a2a28'), 'mouth')
    add(mk.ellipsoid(hc + [0, -0.045, 0.104], (0.025, 0.0042, 0.008), 12, 6), srgb('#9a6058'), 'lip')
    add(mk.ellipsoid(hc + [0, -0.059, 0.102], (0.022, 0.0042, 0.008), 12, 6), srgb('#8a5450'), 'lowlip')
    hg = cfg['headgear']
    if hg == 'hat':
        hp = hc + [0, 0.07, -0.005]
        add(mk.loft(hp + [0, -0.01, 0], hp + [0, 0.005, 0], [(0, 0.19, 0.2), (1, 0.18, 0.19)], 28), cfg['jacket2'], 'hat')
        add(mk.loft(hp, hp + [0, 0.09, 0], [(0, 0.104, 0.112), (0.8, 0.098, 0.104), (1, 0.06, 0.07)], 24), cfg['jacket2'], 'hat')
        add(mk.loft(hp + [0, 0.012, 0], hp + [0, 0.03, 0], [(0, 0.106, 0.114), (1, 0.105, 0.113)], 24), cfg['accent'], 'hat')
    elif hg == 'cap':
        add(mk.ellipsoid(hc + [0, 0.05, -0.008], (0.104, 0.075, 0.112), 22, 10), cfg['jacket2'], 'hat')
        add(mk.rounded_box(hc + [0, 0.046, 0.115], (0.075, 0.006, 0.05), 0.4, rot=mk.rot_x(-8)), cfg['jacket2'], 'hat')
        add(mk.rounded_box(hc + [0.0, 0.085, 0.095], (0.018, 0.012, 0.004), 0.3, rot=mk.rot_x(-30)), cfg['accent'], 'hat')
    elif hg == 'hood':
        add(mk.ellipsoid(hc + [0, 0.016, -0.05], (0.116, 0.134, 0.12), 22, 14), cfg['jacket2'], 'hood')
        add(mk.loft(hc + [0, -0.17, -0.02], hc + [0, -0.1, -0.01], [(0, 0.1, 0.1), (1, 0.095, 0.095)], 18), cfg['jacket2'], 'hood')
    elif hg == 'headset':
        add(mk.loft(hc + [-0.1, 0.0, 0], hc + [0.1, 0.0, 0], [(t, 0.006, 0.012) for t in (0, 1)], 8), cfg['gear'], 'hat')
        band = [hc + [0.098 * np.cos(a), 0.11 * np.sin(a), -0.005] for a in np.linspace(0.15, np.pi - 0.15, 9)]
        for p0, p1 in zip(band[:-1], band[1:]):
            add(mk.capsule(p0, p1, 0.007, 0.007, segs=6, rings=1), cfg['gear'], 'hat')
        for sx in (-1, 1):
            add(mk.loft(hc + [sx * 0.092, -0.01, -0.005], hc + [sx * 0.112, -0.01, -0.005], [(0, 0.028, 0.032), (1, 0.024, 0.028)], 14,
                        hint=(0, 1, 0)), cfg['gear'], 'hat')
        add(mk.capsule(hc + [-0.1, -0.02, 0.02], hc + [-0.035, -0.06, 0.1], 0.004, 0.004, segs=6, rings=1), cfg['gear'], 'hat')
        add(mk.ellipsoid(hc + [-0.03, -0.062, 0.104], (0.009, 0.007, 0.007), 8, 6), cfg['accent'], 'hat')
    elif hg == 'helmet':
        add(mk.ellipsoid(hc + [0, 0.03, -0.006], (0.118, 0.11, 0.126), 22, 12), cfg['jacket2'], 'hat')
        add(mk.loft(hc + [0, -0.012, 0], hc + [0, 0.012, 0], [(0, 0.12, 0.128), (1, 0.121, 0.129)], 26), cfg['gear'], 'hat')
        add(mk.ellipsoid(hc + [0, 0.008, 0.088], (0.09, 0.032, 0.04), 20, 8), cfg['accent'], 'visor')
    if cfg['mask']:
        add(mk.ellipsoid(hc + [0, -0.05, 0.05], (0.096, 0.078, 0.086), 20, 10), cfg['gear'], 'mask')
    P, N, Cc, T, I, UV = m.arrays()
    if not cfg['morphs']:
        return (P, N, Cc, T, I, UV), {}
    D = {k: np.zeros_like(P) for k in MORPHS}
    mouth_c = hc + [0, -0.052, 0.1]
    for kind, s, e in parts:
        Q = P[s:e]; c = Q.mean(0)
        if kind == 'lid':
            D['Blink'][s:e, 1] = (Q[:, 1] - c[1]) * 1.25 - 0.0125; D['Blink'][s:e, 2] = 0.0015
            D['LookUp'][s:e, 1] = 0.0025; D['LookDown'][s:e, 1] = -0.004
            D['BrowUp'][s:e, 1] = 0.002; D['BrowDown'][s:e, 1] = -0.0025
            D['Smile'][s:e, 1] = -0.0015
        if kind in ('mouth', 'lip', 'lowlip'):
            d = np.clip((Q[:, 0] - mouth_c[0]) / 0.025, -1.2, 1.2)
            up = {'mouth': 0, 'lip': 1, 'lowlip': -1}[kind]
            D['JawOpen'][s:e, 1] = ((Q[:, 1] - c[1]) * 2.2 - 0.004) if kind == 'mouth' else (-0.0105 if up < 0 else 0.0015)
            D['Smile'][s:e, 1] = 0.0055 * d * d - 0.0008 * (up < 0)
            D['Smile'][s:e, 0] = 0.0035 * d
            D['Frown'][s:e, 1] = -0.0045 * d * d + 0.0008 * (up > 0)
            D['MouthO'][s:e, 0] = -0.4 * (Q[:, 0] - mouth_c[0])
            D['MouthO'][s:e, 1] = ((Q[:, 1] - c[1]) * 1.6 - 0.002) if kind == 'mouth' else (0.002 * up - 0.004 * (up < 0))
            D['MouthO'][s:e, 2] = 0.004
        if kind in ('jaw', 'beard'):
            w = np.clip((hc[1] - 0.04 - Q[:, 1]) / 0.06, 0, 1) * np.clip(Q[:, 2] / 0.06, 0, 1)
            D['JawOpen'][s:e, 1] = -0.012 * w; D['MouthO'][s:e, 1] = -0.006 * w
        if kind == 'skull':
            w = np.clip((hc[1] - 0.06 - Q[:, 1]) / 0.05, 0, 1) * np.clip((Q[:, 2] - 0.02) / 0.07, 0, 1)
            D['JawOpen'][s:e, 1] = -0.011 * w; D['MouthO'][s:e, 1] = -0.005 * w
            ch = np.exp(-(((np.abs(Q[:, 0]) - 0.055) / 0.02) ** 2 + ((Q[:, 1] - (hc[1] - 0.03)) / 0.02) ** 2)) * (Q[:, 2] > 0.05)
            D['Smile'][s:e, 1] = 0.003 * ch  # cheeks lift
        if kind == 'brow':
            inner = np.clip(1 - (np.abs(Q[:, 0]) - 0.02) / 0.03, 0, 1)
            D['BrowUp'][s:e, 1] = 0.006 + 0.002 * inner
            D['BrowDown'][s:e, 1] = -0.0025 - 0.003 * inner
            D['BrowDown'][s:e, 0] = -np.sign(Q[:, 0]) * 0.002 * inner
            D['Frown'][s:e, 1] = -0.0015 - 0.002 * inner
        if kind == 'moustache':
            D['Smile'][s:e, 1] = 0.002; D['MouthO'][s:e, 0] = -0.3 * (Q[:, 0] - mouth_c[0])
        if kind == 'iris':
            D['LookL'][s:e, 0] = 0.0065; D['LookR'][s:e, 0] = -0.0065
            D['LookL'][s:e, 2] = D['LookR'][s:e, 2] = -0.0018
            D['LookUp'][s:e, 1] = 0.0042; D['LookDown'][s:e, 1] = -0.0042
            D['LookUp'][s:e, 2] = D['LookDown'][s:e, 2] = -0.001
    return (P, N, Cc, T, I, UV), {k: v.astype(np.float32) for k, v in D.items()}


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
    kneel = merge(relaxed, {'Spine': [(X, 8)], 'Chest': [(X, 4)], 'UpperLeg.L': [(X, 86)], 'LowerLeg.L': [(X, -86)],
                            'UpperLeg.R': [(X, 8)], 'LowerLeg.R': [(X, -96)], 'Foot.R': [(X, 45)], 'Head': [(X, -6)]})
    clips.append(("Kneel", [(0.0, kneel, (0, -0.42, 0.02)), (1.0, merge(kneel, {'Chest': [(X, 2)]}), (0, -0.425, 0.02)),
                            (2.0, kneel, (0, -0.42, 0.02))]))
    hands_up = merge({'Spine': [(X, 2)], 'UpperLeg.L': [(X, 8)], 'LowerLeg.L': [(X, -96)], 'Foot.L': [(X, 45)],
                      'UpperLeg.R': [(X, 8)], 'LowerLeg.R': [(X, -96)], 'Foot.R': [(X, 45)],
                      'UpperArm.L': [(Z, -38)], 'UpperArm.R': [(Z, 38)], 'LowerArm.L': [(Z, -95)], 'LowerArm.R': [(Z, 95)],
                      'Head': [(X, 14)]})
    clips.append(("Surrender", [(0.0, relaxed, (0, 0, 0)), (0.35, merge(relaxed, {'Spine': [(X, 20)], 'UpperLeg.L': [(X, 40)],
                  'LowerLeg.L': [(X, -60)], 'UpperLeg.R': [(X, 30)], 'LowerLeg.R': [(X, -70)]}), (0, -0.2, 0.05)),
                  (0.8, hands_up, (0, -0.44, -0.02)), (1.8, merge(hands_up, {'Head': [(X, 8), (Y, 10)]}), (0, -0.445, -0.02)),
                  (2.8, hands_up, (0, -0.44, -0.02))]))
    halt = merge(relaxed, {'UpperArm.L': [(Z, -40)], 'LowerArm.L': [(Z, -100)], 'Head': [(Y, 6)]})
    clips.append(("Halt", [(0.0, relaxed, (0, 0, 0)), (0.25, halt, (0, 0, 0)), (1.2, halt, (0, 0, 0)), (1.5, relaxed, (0, 0, 0))]))
    point = merge(relaxed, {'UpperArm.L': [(Z, 28), (X, 85)], 'LowerArm.L': [(X, -8)], 'Chest': [(Y, -6)]})
    clips.append(("Point", [(0.0, relaxed, (0, 0, 0)), (0.3, point, (0, 0, 0)), (1.3, point, (0, 0, 0)), (1.6, relaxed, (0, 0, 0))]))
    beckon = merge(relaxed, {'UpperArm.L': [(Z, 10), (X, 55)], 'LowerArm.L': [(X, -60)]})
    clips.append(("Beckon", [(0.0, relaxed, (0, 0, 0)), (0.25, beckon, (0, 0, 0)),
                             (0.5, merge(beckon, {'LowerArm.L': [(X, -50)]}), (0, 0, 0)), (0.75, beckon, (0, 0, 0)),
                             (1.0, merge(beckon, {'LowerArm.L': [(X, -50)]}), (0, 0, 0)), (1.3, relaxed, (0, 0, 0))]))
    # Seated (vehicle bench): thighs level, shins vertical, forearms resting on the thighs. Hips drop
    # 0.46 m and sit slightly back so the knees land above the feet.
    sit = merge(relaxed, {'Spine': [(X, -4)], 'UpperLeg.L': [(X, 86), (Z, 4)], 'UpperLeg.R': [(X, 86), (Z, -4)],
                          'LowerLeg.L': [(X, -84)], 'LowerLeg.R': [(X, -84)], 'Foot.L': [(X, 4)], 'Foot.R': [(X, 4)],
                          'UpperArm.L': [(X, 38)], 'UpperArm.R': [(X, 38)], 'LowerArm.L': [(X, -46)],
                          'LowerArm.R': [(X, -46)], 'Head': [(X, 2)]})
    SIT_T = (0, -0.46, -0.06)
    clips.append(("Sit", [(0.0, sit, SIT_T), (1.6, merge(sit, {'Chest': [(X, 2)], 'Head': [(Y, 4)]}), SIT_T),
                          (3.2, sit, SIT_T)]))
    # Standing up out of a seat: lean forward over the feet, push off the thighs, rise.
    lean = merge(relaxed, {'Spine': [(X, 30)], 'Chest': [(X, 12)], 'Head': [(X, -14)],
                           'UpperLeg.L': [(X, 80)], 'UpperLeg.R': [(X, 80)], 'LowerLeg.L': [(X, -90)],
                           'LowerLeg.R': [(X, -90)], 'Foot.L': [(X, 12)], 'Foot.R': [(X, 12)],
                           'UpperArm.L': [(X, 34)], 'UpperArm.R': [(X, 34)], 'LowerArm.L': [(X, -30)],
                           'LowerArm.R': [(X, -30)]})
    rise = merge(relaxed, {'Spine': [(X, 14)], 'Chest': [(X, 6)], 'Head': [(X, -6)],
                           'UpperLeg.L': [(X, 36)], 'UpperLeg.R': [(X, 30)], 'LowerLeg.L': [(X, -46)],
                           'LowerLeg.R': [(X, -40)], 'Foot.L': [(X, 10)], 'Foot.R': [(X, 10)]})
    clips.append(("SitStand", [(0.0, sit, SIT_T), (0.35, lean, (0, -0.42, 0.04)), (0.75, rise, (0, -0.16, 0.04)),
                               (1.15, relaxed, (0, 0, 0))]))
    # Lifting a hatch overhead with both hands, then letting the struts take it.
    lift_lo = merge(relaxed, {'Spine': [(X, 10)], 'UpperArm.L': [(X, 70), (Z, -10)], 'UpperArm.R': [(X, 70), (Z, 10)],
                              'LowerArm.L': [(X, -30)], 'LowerArm.R': [(X, -30)], 'Head': [(X, 6)]})
    lift_hi = merge(relaxed, {'Spine': [(X, -6)], 'UpperArm.L': [(X, 150), (Z, -12)], 'UpperArm.R': [(X, 150), (Z, 12)],
                              'LowerArm.L': [(X, -18)], 'LowerArm.R': [(X, -18)], 'Head': [(X, -18)]})
    clips.append(("Lift", [(0.0, relaxed, (0, 0, 0)), (0.35, lift_lo, (0, -0.04, 0.02)), (0.85, lift_hi, (0, 0.02, 0)),
                           (1.15, lift_hi, (0, 0.02, 0)), (1.6, relaxed, (0, 0, 0))]))
    # Reaching into a cargo bay at hip height and lifting an item out.
    reach = merge(relaxed, {'Spine': [(X, 28)], 'Chest': [(X, 10)], 'UpperArm.R': [(X, 62), (Z, 6)],
                            'LowerArm.R': [(X, -20)], 'UpperArm.L': [(X, 40)], 'LowerArm.L': [(X, -35)],
                            'UpperLeg.L': [(X, 14)], 'UpperLeg.R': [(X, 14)], 'LowerLeg.L': [(X, -16)],
                            'LowerLeg.R': [(X, -16)]})
    clips.append(("Reach", [(0.0, relaxed, (0, 0, 0)), (0.45, reach, (0, -0.06, 0.03)), (0.8, reach, (0, -0.06, 0.03)),
                            (1.3, merge(relaxed, {'UpperArm.R': [(X, 30)], 'LowerArm.R': [(X, -60)]}), (0, 0, 0)),
                            (1.6, relaxed, (0, 0, 0))]))
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
    (hP, hN, hC, hT, hI, hUV), morphs = head_mesh(cfg)

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
        {'name': cfg['name'] + '_Head', 'primitives': [prim(hP, hN, hC, hT, hI, 1, [morphs[k] for k in MORPHS] if morphs else None)]},
    ]
    if morphs:
        out_head = out['meshes'][1]
        out_head['weights'] = [0.0] * len(MORPHS); out_head['extras'] = {'targetNames': list(MORPHS)}
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
    ap.add_argument('--only', default='')
    a = ap.parse_args()
    only = set(a.only.split(',')) if a.only else None
    for cfg, fn in CAST:
        if only and fn not in only: continue
        build(cfg, a.rig, os.path.join(a.out, fn + '.glb'))


if __name__ == '__main__':
    main()
