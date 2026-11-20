# SPDX-License-Identifier: Apache-2.0
"""Generate the SPECIAL OPS first-person viewmodel art: two original fictional game weapons and
the player's gloved hands. All geometry is procedural and original (see docs/ASSET_PROVENANCE.md).

    python3 tools/props/build_weapons.py --out game/assets

Writes <out>/models/weapons/*.glb. Each weapon is split into separately animated parts so the
viewmodel script (scripts/weapons.luau) can move the charge cell and slide during reloads:

  pc7_body.glb    "PC-7 Lantern" pulse carbine: shell, shroud, emitter coils, sight
  pc7_cell.glb    its removable charge cell
  sp2_body.glb    "SP-2 Wren" pulse sidearm frame
  sp2_slide.glb   its top shroud (kicks back on each shot)
  sp2_cell.glb    its charge cell
  hand_r.glb      right glove + sleeve (grip hand)
  hand_l.glb      left glove + sleeve (support hand)
  pulse_bolt.glb  emissive bolt used for the tracer and muzzle bloom
  stun_target.glb pop-up training target for the range
  lr4_body.glb    "LR-4 Heron" long pulse emitter with a two-step scope; lr4_cell.glb its cell
  *_world.glb     storage/world variants (parts merged, resting on their side)
  ../props/field_kit.glb, ../props/cell_pack.glb  non-weapon field equipment

The weapons are game objects only: they fire invented "stun pulses" with invented values, have
no real-world mechanism and do not resemble a specific real firearm.

Local frame (all parts): metres, +Y up, the muzzle points along -Z, origin at the grip hand.
"""
from __future__ import annotations
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'characters'))
from build_forest import Model as _Model, hexc  # noqa: E402
import meshkit as mk  # noqa: E402

SHELL = hexc('#3a4046')
SHELL_DARK = hexc('#22262a')
TRIM = hexc('#6d7378')
ACCENT = hexc('#c48a2c')   # SPECIAL OPS amber accent shared with the field device
GLOW = (0.35, 0.9, 1.0)
GLOVE = hexc('#3b352d')
GLOVE_DARK = hexc('#25221e')
SLEEVE = hexc('#4f5a3a')
SLEEVE_CUFF = hexc('#3c4630')


class Model(_Model):
    """Model that also records its parts so world (storage) variants can be assembled."""
    def __init__(self, name):
        super().__init__(name); self.parts = []
    def solid(self, mesh, mat):
        self.parts.append((mesh, self.j['materials'][mat]))
        return super().solid(mesh, mat)


def world_model(name, models, rot=None, offset=(0, 0, 0)):
    """Merge viewmodel parts into one world prop (rotated to its resting pose)."""
    out = _Model(name)
    tris = 0
    R = np.eye(3) if rot is None else rot
    for src in models:
        for mesh, mat in src.parts:
            mi = out.material(mat['name'] + '_w', None, mat['pbrMetallicRoughness']['roughnessFactor'],
                              metal=mat['pbrMetallicRoughness']['metallicFactor'],
                              emissive=mat.get('emissiveFactor'),
                              strength=mat.get('extensions', {}).get('KHR_materials_emissive_strength', {}).get('emissiveStrength', 1.0))
            P, N, C, T, I, UV = mesh.arrays()
            P = P @ R.T + np.asarray(offset, np.float32); N = N @ R.T
            tris += out.prim(P, N, C, I, UV, mi)
    return out, tris


def zloft(z0, z1, prof, x=0.0, y=0.0, segs=18, caps=True):
    return mk.loft((x, y, z0), (x, y, z1), prof, segs, hint=(0, 1, 0), caps=caps)


def carbine():
    m = Model('pc7_body')
    shell = m.material('pc7_Shell', None, 0.42, metal=0.35)
    grip = m.material('pc7_Grip', None, 0.85)
    glow = m.material('pc7_Glow', None, 0.3, emissive=GLOW, strength=3.0)
    a, g, e = mk.Mesh(), mk.Mesh(), mk.Mesh()
    # receiver: long rounded body sitting above the hand, with a sloped front
    a.add(mk.rounded_box((0, 0.045, -0.06), (0.03, 0.04, 0.17), 0.3), SHELL)
    a.add(mk.rounded_box((0, 0.012, -0.03), (0.026, 0.022, 0.13), 0.35), SHELL_DARK)
    a.add(mk.rounded_box((0, 0.05, -0.245), (0.027, 0.032, 0.035), 0.5), SHELL)
    # side panels with an amber stripe
    for sx in (-1, 1):
        a.add(mk.rounded_box((sx * 0.0305, 0.05, -0.08), (0.002, 0.018, 0.09), 0.3), TRIM)
        a.add(mk.rounded_box((sx * 0.031, 0.03, -0.16), (0.0015, 0.004, 0.04), 0.3), ACCENT)
    # top optic rail and a compact enclosed sight
    a.add(mk.rounded_box((0, 0.09, -0.07), (0.011, 0.007, 0.13), 0.25), SHELL_DARK)
    a.add(zloft(-0.03, -0.1, [(0, 0.012, 0.012), (0.15, 0.0145, 0.0145), (0.85, 0.0145, 0.0145), (1, 0.0125, 0.0125)], 0, 0.113, caps=False), SHELL_DARK)
    a.add(mk.rounded_box((0, 0.098, -0.065), (0.009, 0.005, 0.025), 0.3), SHELL_DARK)
    # emitter shroud: a tapered tube ahead of the receiver, vented by three glowing coils
    a.add(zloft(-0.27, -0.5, [(0, 0.026, 0.026), (0.6, 0.023, 0.023), (0.92, 0.024, 0.024), (1, 0.02, 0.02)], 0, 0.045), SHELL_DARK)
    for i, z in enumerate((-0.31, -0.36, -0.41)):
        e.add(zloft(z, z - 0.012, [(0, 0.0275, 0.0275), (1, 0.0275, 0.0275)], 0, 0.045), (1, 1, 1))
    e.add(zloft(-0.498, -0.503, [(0, 0.014, 0.014), (1, 0.014, 0.014)], 0, 0.045), (1, 1, 1))  # emitter face
    e.add(mk.ellipsoid((0, 0.1135, -0.101), (0.0035, 0.0035, 0.0015)), (1, 1, 1))  # sight dot (visible ADS)
    # stock: short skeletal shape behind the hand
    a.add(mk.rounded_box((0, 0.045, 0.14), (0.022, 0.03, 0.06), 0.4), SHELL)
    a.add(mk.rounded_box((0, 0.02, 0.215), (0.024, 0.055, 0.018), 0.45), SHELL_DARK)
    # pistol grip and trigger guard
    g.add(mk.capsule((0, 0.005, 0.005), (0, -0.085, 0.03), 0.019, 0.017, squash=0.75, hint=(1, 0, 0)), SHELL_DARK)
    a.add(mk.rounded_box((0, -0.012, -0.035), (0.006, 0.004, 0.03), 0.4), SHELL_DARK)
    # forward grip under the shroud
    g.add(mk.capsule((0, 0.0, -0.215), (0, -0.07, -0.205), 0.016, 0.015, hint=(1, 0, 0)), SHELL_DARK)
    tris = m.solid(a, shell) + m.solid(g, grip) + m.solid(e, glow)
    return m, tris


def carbine_cell():
    m = Model('pc7_cell')
    shell = m.material('pc7cell_Shell', None, 0.5, metal=0.2)
    glow = m.material('pc7cell_Glow', None, 0.3, emissive=GLOW, strength=2.5)
    a, e = mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, -0.04, -0.105), (0.017, 0.045, 0.028), 0.35), TRIM)
    a.add(mk.rounded_box((0, -0.085, -0.105), (0.019, 0.007, 0.03), 0.4), SHELL_DARK)
    for sx in (-1, 1):
        e.add(mk.rounded_box((sx * 0.0172, -0.04, -0.105), (0.0012, 0.03, 0.006), 0.3), (1, 1, 1))
    return m, m.solid(a, shell) + m.solid(e, glow)


def sidearm():
    m = Model('sp2_body')
    shell = m.material('sp2_Frame', None, 0.6, metal=0.15)
    glow = m.material('sp2_Glow', None, 0.3, emissive=(1.0, 0.7, 0.3), strength=2.5)
    a, e = mk.Mesh(), mk.Mesh()
    # frame and an angled grip
    a.add(mk.rounded_box((0, 0.01, -0.06), (0.016, 0.014, 0.085), 0.4), SHELL_DARK)
    a.add(mk.capsule((0, 0.0, 0.0), (0, -0.085, 0.022), 0.017, 0.016, squash=0.68, hint=(1, 0, 0)), SHELL_DARK)
    a.add(mk.rounded_box((0, -0.018, -0.03), (0.005, 0.004, 0.025), 0.4), SHELL)
    for sx in (-1, 1):
        a.add(mk.rounded_box((sx * 0.0165, 0.012, -0.1), (0.0015, 0.004, 0.03), 0.3), ACCENT)
    e.add(mk.rounded_box((0, 0.012, -0.146), (0.007, 0.004, 0.0015), 0.4), (1, 1, 1))  # emitter
    return m, m.solid(a, shell) + m.solid(e, glow)


def sidearm_slide():
    m = Model('sp2_slide')
    shell = m.material('sp2_Slide', None, 0.38, metal=0.45)
    glow = m.material('sp2_Sight', None, 0.3, emissive=(1.0, 0.7, 0.3), strength=3.0)
    a, e = mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, 0.04, -0.07), (0.015, 0.016, 0.09), 0.3), SHELL)
    for i in range(5):
        a.add(mk.rounded_box((0, 0.042, 0.0 - i * 0.006), (0.0155, 0.012, 0.0012), 0.2), SHELL_DARK)
    a.add(mk.rounded_box((0, 0.058, -0.152), (0.003, 0.004, 0.003), 0.3), SHELL_DARK)
    e.add(mk.ellipsoid((0, 0.062, -0.152), (0.0022, 0.0022, 0.0015)), (1, 1, 1))
    for sx in (-1, 1):
        e.add(mk.ellipsoid((sx * 0.007, 0.06, 0.012), (0.0018, 0.0018, 0.0012)), (1, 1, 1))
    return m, m.solid(a, shell) + m.solid(e, glow)


WARM = (1.0, 0.72, 0.32)


def marksman():
    """"LR-4 Heron" long pulse emitter: slim receiver, long vented shroud, two-step scope."""
    m = Model('lr4_body')
    shell = m.material('lr4_Shell', None, 0.5, metal=0.3)
    grip = m.material('lr4_Grip', None, 0.85)
    glass = m.material('lr4_Lens', None, 0.08, metal=0.6)
    glow = m.material('lr4_Glow', None, 0.3, emissive=WARM, strength=2.6)
    a, g, l, e = mk.Mesh(), mk.Mesh(), mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, 0.045, -0.09), (0.027, 0.036, 0.2), 0.3), SHELL)
    a.add(mk.rounded_box((0, 0.012, -0.06), (0.024, 0.02, 0.15), 0.35), SHELL_DARK)
    for sx in (-1, 1):
        a.add(mk.rounded_box((sx * 0.0275, 0.05, -0.12), (0.002, 0.016, 0.12), 0.3), TRIM)
        a.add(mk.rounded_box((sx * 0.028, 0.026, -0.2), (0.0015, 0.004, 0.05), 0.3), ACCENT)
    # long shroud with vent rings, tapering to a narrow emitter
    a.add(zloft(-0.29, -0.74, [(0, 0.022, 0.022), (0.5, 0.019, 0.019), (0.9, 0.017, 0.017), (1, 0.014, 0.014)], 0, 0.045), SHELL_DARK)
    for z in (-0.36, -0.44, -0.52, -0.6):
        a.add(zloft(z, z - 0.018, [(0, 0.0235, 0.0235), (1, 0.0235, 0.0235)], 0, 0.045), TRIM)
    e.add(zloft(-0.738, -0.744, [(0, 0.011, 0.011), (1, 0.011, 0.011)], 0, 0.045), (1, 1, 1))
    for z in (-0.4, -0.48, -0.56):
        e.add(zloft(z, z - 0.006, [(0, 0.0205, 0.0205), (1, 0.0205, 0.0205)], 0, 0.045), (1, 1, 1))
    # scope: mounts, main tube, objective bell and eyepiece (centre line y = 0.1175)
    for z in (-0.07, -0.19):
        a.add(mk.rounded_box((0, 0.092, z), (0.012, 0.014, 0.012), 0.3), SHELL_DARK)
    a.add(zloft(0.0, -0.27, [(0, 0.025, 0.025), (0.12, 0.021, 0.021), (0.25, 0.019, 0.019), (0.7, 0.019, 0.019),
                             (0.85, 0.027, 0.027), (1, 0.029, 0.029)], 0, 0.1175, segs=20, caps=False), SHELL_DARK)
    a.add(zloft(-0.12, -0.15, [(0, 0.024, 0.024), (1, 0.024, 0.024)], 0, 0.1175, segs=16), SHELL)  # zoom ring
    a.add(mk.rounded_box((0.026, 0.1175, -0.135), (0.008, 0.009, 0.01), 0.4), ACCENT)            # zoom knob
    l.add(zloft(-0.266, -0.27, [(0, 0.026, 0.026), (1, 0.026, 0.026)], 0, 0.1175, segs=20), (0.2, 0.3, 0.32))
    l.add(zloft(0.0, 0.004, [(0, 0.021, 0.021), (1, 0.021, 0.021)], 0, 0.1175, segs=20), (0.08, 0.1, 0.1))
    # stock with cheek rest and butt pad
    a.add(mk.rounded_box((0, 0.05, 0.16), (0.02, 0.026, 0.07), 0.4), SHELL)
    a.add(mk.rounded_box((0, 0.082, 0.17), (0.018, 0.01, 0.06), 0.5), SHELL_DARK)
    a.add(mk.rounded_box((0, 0.02, 0.25), (0.022, 0.06, 0.02), 0.45), SHELL_DARK)
    a.add(mk.rounded_box((0, -0.01, 0.19), (0.012, 0.018, 0.05), 0.4), SHELL)
    # pistol grip, trigger guard, folded bipod legs under the shroud
    g.add(mk.capsule((0, 0.005, 0.005), (0, -0.085, 0.03), 0.019, 0.017, squash=0.75, hint=(1, 0, 0)), SHELL_DARK)
    a.add(mk.rounded_box((0, -0.012, -0.035), (0.006, 0.004, 0.03), 0.4), SHELL_DARK)
    for sx in (-1, 1):
        a.add(mk.capsule((sx * 0.012, 0.018, -0.31), (sx * 0.012, 0.02, -0.5), 0.0055, 0.005, segs=6, rings=1), SHELL_DARK)
    tris = m.solid(a, shell) + m.solid(g, grip) + m.solid(l, glass) + m.solid(e, glow)
    return m, tris


def marksman_cell():
    m = Model('lr4_cell')
    shell = m.material('lr4cell_Shell', None, 0.5, metal=0.2)
    glow = m.material('lr4cell_Glow', None, 0.3, emissive=WARM, strength=2.2)
    a, e = mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, -0.035, -0.11), (0.016, 0.038, 0.034), 0.35), TRIM)
    a.add(mk.rounded_box((0, -0.075, -0.11), (0.018, 0.007, 0.036), 0.4), SHELL_DARK)
    for sx in (-1, 1):
        e.add(mk.rounded_box((sx * 0.0162, -0.035, -0.11), (0.0012, 0.024, 0.005), 0.3), (1, 1, 1))
    return m, m.solid(a, shell) + m.solid(e, glow)


def field_kit():
    """FK-1 field kit: a soft-sided pouch with a hard lid and a white cross-free amber band."""
    m = Model('field_kit')
    cloth = m.material('kit_Cloth', None, 0.92)
    hard = m.material('kit_Shell', None, 0.55, metal=0.1)
    a, h = mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, 0.07, 0), (0.15, 0.07, 0.1), 0.5), hexc('#4a5a3e'))
    a.add(mk.rounded_box((0, 0.07, 0.101), (0.12, 0.05, 0.004), 0.4), hexc('#3c4a33'))
    h.add(mk.rounded_box((0, 0.142, 0), (0.152, 0.012, 0.102), 0.35), hexc('#2d3134'))
    h.add(mk.rounded_box((0, 0.1, 0.1035), (0.045, 0.018, 0.003), 0.3), ACCENT)
    for sx in (-1, 1):
        h.add(mk.capsule((sx * 0.08, 0.155, -0.05), (sx * 0.08, 0.155, 0.05), 0.006, 0.006, segs=6, rings=1), hexc('#1d1f20'))
    return m, m.solid(a, cloth) + m.solid(h, hard)


def cell_pack():
    """Spare charge cells in a webbing sleeve: three cells standing in a row."""
    m = Model('cell_pack')
    web = m.material('pack_Web', None, 0.95)
    shell = m.material('pack_Cell', None, 0.5, metal=0.2)
    glow = m.material('pack_Glow', None, 0.3, emissive=GLOW, strength=1.6)
    a, c, e = mk.Mesh(), mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, 0.045, 0), (0.075, 0.045, 0.03), 0.4), hexc('#3a3f33'))
    for i, x in enumerate((-0.045, 0.0, 0.045)):
        c.add(mk.rounded_box((x, 0.1, 0), (0.019, 0.03, 0.026), 0.35), TRIM)
        e.add(mk.rounded_box((x, 0.115, 0.0265), (0.008, 0.012, 0.001), 0.3), (1, 1, 1))
    return m, m.solid(a, web) + m.solid(c, shell) + m.solid(e, glow)


def sidearm_cell():
    m = Model('sp2_cell')
    shell = m.material('sp2cell_Shell', None, 0.5, metal=0.2)
    a = mk.Mesh()
    a.add(mk.rounded_box((0, -0.05, 0.012), (0.012, 0.035, 0.016), 0.35), TRIM)
    a.add(mk.rounded_box((0, -0.089, 0.014), (0.0145, 0.005, 0.019), 0.4), SHELL_DARK)
    return m, m.solid(a, shell)


def hand(side):
    """A gloved hand in a grip pose with a sleeved forearm reaching back out of frame.

    Right hand: palm around the pistol grip at the origin, forearm toward +Z, down and right.
    Left hand: the support grip; the palm faces +X and wraps a vertical post at the origin,
    forearm toward +Z, down and left. Both are authored for a camera at about (-0.15, 0.17, 0.4).
    """
    s = 1 if side == 'r' else -1
    m = Model('hand_' + side)
    glove = m.material(f'hand{side}_Glove', None, 0.82)
    cloth = m.material(f'hand{side}_Sleeve', None, 0.92)
    g, c = mk.Mesh(), mk.Mesh()
    # palm block around a vertical grip (grip axis is -Y, slight rake)
    g.add(mk.rounded_box((s * 0.018, -0.03, 0.012), (0.012, 0.038, 0.03), 0.45, rot=mk.rot_x(-12)), GLOVE)
    g.add(mk.rounded_box((s * 0.02, -0.03, 0.03), (0.016, 0.042, 0.022), 0.5, rot=mk.rot_x(-12)), GLOVE)
    # four fingers wrapping around the far side of the grip
    for i in range(4):
        y = -0.008 - i * 0.021
        z = 0.006 + i * 0.004
        p0 = np.array([s * 0.024, y, z + 0.012])
        p1 = np.array([-s * 0.006, y - 0.002, z - 0.022])
        p2 = np.array([-s * 0.022, y - 0.004, z + 0.002])
        g.add(mk.capsule(p0, p1, 0.0085, 0.0078), GLOVE)
        g.add(mk.capsule(p1, p2, 0.0078, 0.007), GLOVE_DARK if i == 0 else GLOVE)
    # thumb along the near side
    g.add(mk.capsule((s * 0.026, 0.004, 0.03), (-s * 0.008, 0.016, -0.004), 0.0095, 0.008), GLOVE)
    # knuckle pad
    g.add(mk.rounded_box((s * 0.03, -0.035, 0.02), (0.004, 0.034, 0.012), 0.5, rot=mk.rot_x(-12)), GLOVE_DARK)
    # wrist, cuff and forearm sleeve reaching out of frame
    wrist = np.array([s * 0.028, -0.05, 0.065])
    elbow = np.array([s * 0.13, -0.24, 0.42])
    g.add(mk.capsule((s * 0.022, -0.035, 0.045), wrist, 0.024, 0.024), GLOVE)
    c.add(mk.capsule(wrist + (elbow - wrist) * 0.02, elbow, 0.032, 0.045), SLEEVE)
    c.add(mk.loft(wrist - (elbow - wrist) * 0.01, wrist + (elbow - wrist) * 0.09,
                  [(0, 0.034, 0.034), (0.5, 0.036, 0.036), (1, 0.035, 0.035)], 16), SLEEVE_CUFF)
    # a fabric fold and a strap on the sleeve
    c.add(mk.loft(wrist + (elbow - wrist) * 0.3, wrist + (elbow - wrist) * 0.34,
                  [(0, 0.039, 0.039), (1, 0.039, 0.039)], 16), SLEEVE_CUFF)
    return m, m.solid(g, glove) + m.solid(c, cloth)


def pulse_bolt():
    m = Model('pulse_bolt')
    glow = m.material('bolt_Glow', None, 0.2, emissive=GLOW, strength=6.0)
    a = mk.Mesh()
    a.add(mk.capsule((0, 0, 0.0), (0, 0, -1.0), 0.012, 0.004, segs=8, rings=2), (0.7, 0.95, 1.0))
    return m, m.solid(a, glow)


def stun_target():
    """Range target on a post: a plate silhouette with an amber bullseye (y up, faces +Z)."""
    m = Model('stun_target')
    plate = m.material('target_Plate', None, 0.7, metal=0.1)
    mark = m.material('target_Mark', None, 0.5, emissive=(1.0, 0.55, 0.15), strength=1.2)
    a, e = mk.Mesh(), mk.Mesh()
    a.add(mk.capsule((0, 0, 0), (0, 0.9, 0), 0.03, 0.03), SHELL_DARK)
    a.add(mk.rounded_box((0, 1.25, 0), (0.22, 0.34, 0.015), 0.25), hexc('#c9c3b4'))
    a.add(mk.ellipsoid((0, 1.72, 0), (0.12, 0.13, 0.016)), hexc('#c9c3b4'))
    e.add(mk.loft((0, 1.33, 0.012), (0, 1.33, 0.02), [(0, 0.07, 0.07), (1, 0.07, 0.07)], 20, hint=(0, 1, 0)), (1, 1, 1))
    return m, m.solid(a, plate) + m.solid(e, mark)


# ---- Halyard kit additions (story bible rev 2, section 1A weapons table) -----------------------
# Same family as the PC-7: dark polymer shells, machined grey metal, amber unit stripe and a
# cyan (Lamplight) or warm (contractor-era) emitter glow. Picatinny-style rails are modelled as
# rows of small teeth, because at viewmodel distance the rhythm of a rail is what reads as real.
METAL = hexc('#4a4f53')
POLY = hexc('#2b2f32')
TAN = hexc('#6b604c')       # flat-dark-earth furniture on the Ram
RED = (1.0, 0.18, 0.12)


def rail(mesh, z0, z1, y, w=0.0105, col=SHELL_DARK, pitch=0.0105, x=0.0, axis='top'):
    """A toothed accessory rail from z0 to z1 (z0 > z1, toward the muzzle) at height y."""
    if axis == 'top':
        mesh.add(mk.rounded_box((x, y, (z0 + z1) / 2), (w, 0.0035, abs(z0 - z1) / 2), 0.2), col)
        z = z0 - pitch / 2
        while z > z1 + pitch / 2:
            mesh.add(mk.rounded_box((x, y + 0.0045, z), (w * 0.95, 0.0016, pitch * 0.28), 0.15, segs=2), col)
            z -= pitch
    else:  # side rail, x is the face position (sign gives the side)
        sx = 1 if x > 0 else -1
        mesh.add(mk.rounded_box((x, y, (z0 + z1) / 2), (0.0035, w * 0.8, abs(z0 - z1) / 2), 0.2), col)
        z = z0 - pitch / 2
        while z > z1 + pitch / 2:
            mesh.add(mk.rounded_box((x + sx * 0.0045, y, z), (0.0016, w * 0.75, pitch * 0.28), 0.15, segs=2), col)
            z -= pitch


def hornet():
    """"KV-5 Hornet" compact pulse PDW: short receiver, integral vented shroud, vertical grip,
    folding wire stock and a reflex sight with a red dot (sight line y = 0.103)."""
    m = Model('kv5_body')
    shell = m.material('kv5_Shell', None, 0.45, metal=0.3)
    metal = m.material('kv5_Metal', None, 0.32, metal=0.85)
    grip = m.material('kv5_Grip', None, 0.86)
    glass = m.material('kv5_Glass', None, 0.05, metal=0.3)
    glow = m.material('kv5_Glow', None, 0.3, emissive=GLOW, strength=3.0)
    dot = m.material('kv5_Dot', None, 0.3, emissive=RED, strength=9.0)
    a, mt, g, gl, e, d = mk.Mesh(), mk.Mesh(), mk.Mesh(), mk.Mesh(), mk.Mesh(), mk.Mesh()
    # receiver: upper (metal) over lower (polymer) with a magwell ahead of the grip
    mt.add(mk.rounded_box((0, 0.05, -0.07), (0.026, 0.026, 0.13), 0.25), METAL)
    a.add(mk.rounded_box((0, 0.014, -0.05), (0.024, 0.02, 0.1), 0.35), POLY)
    for sx in (-1, 1):
        a.add(mk.rounded_box((sx * 0.0265, 0.05, -0.05), (0.0015, 0.012, 0.07), 0.3), SHELL_DARK)
        a.add(mk.rounded_box((sx * 0.0255, 0.022, -0.13), (0.0012, 0.003, 0.03), 0.3), ACCENT)
        # ejection-style vent cut and charging handle on the left
    mt.add(mk.rounded_box((-0.031, 0.06, -0.02), (0.006, 0.006, 0.012), 0.4), METAL)
    rail(mt, 0.05, -0.19, 0.078)
    # shroud: short perforated cylinder, 3 cyan coil rings, crown at the muzzle
    mt.add(zloft(-0.2, -0.385, [(0, 0.024, 0.024), (0.8, 0.023, 0.023), (1, 0.021, 0.021)], 0, 0.05, segs=20), SHELL_DARK)
    for z in (-0.235, -0.27, -0.305, -0.34):
        for k in range(8):
            ang = k / 8 * 2 * np.pi
            mt.add(mk.rounded_box((np.cos(ang) * 0.0235, 0.05 + np.sin(ang) * 0.0235, z), (0.003, 0.003, 0.008), 0.4, segs=2), POLY)
    for z in (-0.25, -0.29, -0.33):
        e.add(zloft(z, z - 0.006, [(0, 0.0215, 0.0215), (1, 0.0215, 0.0215)], 0, 0.05), (1, 1, 1))
    e.add(zloft(-0.383, -0.388, [(0, 0.012, 0.012), (1, 0.012, 0.012)], 0, 0.05), (1, 1, 1))
    # handguard with side rails under the shroud, vertical foregrip
    a.add(mk.rounded_box((0, 0.03, -0.17), (0.023, 0.02, 0.05), 0.35), POLY)
    rail(mt, -0.13, -0.21, 0.035, x=0.025, axis='side')
    rail(mt, -0.13, -0.21, 0.035, x=-0.025, axis='side')
    g.add(mk.capsule((0, 0.012, -0.175), (0, -0.07, -0.168), 0.014, 0.013, hint=(1, 0, 0)), POLY)
    # reflex sight: low base and an open rectangular hood (no opaque glass in the eye line), a thin
    # tinted lens rim at the front and a bright dot in the middle of the window on the sight line
    mt.add(mk.rounded_box((0, 0.084, -0.075), (0.013, 0.004, 0.022), 0.3), POLY)
    SL, HZ0, HZ1, WX, WY = 0.103, -0.058, -0.092, 0.0135, 0.0115
    hz, hd = (HZ0 + HZ1) / 2, (HZ0 - HZ1) / 2
    mt.add(mk.rounded_box((0, SL + WY + 0.002, hz), (WX + 0.004, 0.002, hd), 0.3), POLY)
    mt.add(mk.rounded_box((0, SL - WY - 0.0015, hz), (WX + 0.004, 0.0015, hd), 0.3), POLY)
    for sx in (-1, 1):
        mt.add(mk.rounded_box((sx * (WX + 0.002), SL, hz), (0.002, WY + 0.002, hd), 0.3), POLY)
    mt.add(mk.rounded_box((WX + 0.0055, SL + 0.004, hz), (0.0015, 0.003, 0.006), 0.4), METAL)
    for sx in (-1, 1):
        gl.add(mk.rounded_box((sx * (WX - 0.0005), SL, HZ1 + 0.001), (0.0006, WY, 0.0008), 0.2), (0.35, 0.45, 0.4))
    gl.add(mk.rounded_box((0, SL + WY - 0.0005, HZ1 + 0.001), (WX, 0.0006, 0.0008), 0.2), (0.35, 0.45, 0.4))
    d.add(mk.ellipsoid((0, SL, HZ1 + 0.0025), (0.0012, 0.0012, 0.0006)), (1, 1, 1))
    # pistol grip with texture bands, trigger guard
    g.add(mk.capsule((0, 0.004, 0.005), (0, -0.082, 0.03), 0.018, 0.016, squash=0.75, hint=(1, 0, 0)), POLY)
    for k in range(3):
        g.add(mk.rounded_box((0, -0.03 - k * 0.018, 0.022 + k * 0.004), (0.0182, 0.003, 0.012), 0.4), SHELL_DARK)
    a.add(mk.rounded_box((0, -0.012, -0.035), (0.006, 0.004, 0.028), 0.4), POLY)
    # folding wire stock (folded alongside the left of the receiver) and an end-plate
    for y in (0.03, 0.065):
        mt.add(mk.capsule((-0.033, y, 0.06), (-0.033, y, -0.08), 0.0042, 0.0042, segs=6, rings=1), METAL)
    mt.add(mk.rounded_box((-0.033, 0.047, -0.088), (0.005, 0.026, 0.008), 0.3), METAL)
    mt.add(mk.rounded_box((-0.03, 0.047, 0.062), (0.006, 0.026, 0.006), 0.3), METAL)
    a.add(mk.rounded_box((0, 0.038, 0.062), (0.02, 0.02, 0.012), 0.4), POLY)
    tris = (m.solid(a, shell) + m.solid(mt, metal) + m.solid(g, grip) + m.solid(gl, glass) + m.solid(e, glow)
            + m.solid(d, dot))
    return m, tris


def hornet_cell():
    m = Model('kv5_cell')
    shell = m.material('kv5cell_Shell', None, 0.5, metal=0.2)
    glow = m.material('kv5cell_Glow', None, 0.3, emissive=GLOW, strength=2.2)
    a, e = mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, -0.045, -0.095), (0.014, 0.05, 0.022), 0.35, rot=mk.rot_x(8)), TRIM)
    a.add(mk.rounded_box((0, -0.095, -0.1), (0.016, 0.006, 0.024), 0.4), SHELL_DARK)
    for sx in (-1, 1):
        e.add(mk.rounded_box((sx * 0.0142, -0.045, -0.095), (0.0012, 0.032, 0.004), 0.3, rot=mk.rot_x(8)), (1, 1, 1))
    return m, m.solid(a, shell) + m.solid(e, glow)


def ram():
    """"BR-9 Ram" breaching pulse projector: heavy receiver, wide bore with a vented breaching
    crown, magazine tube under the bore, ghost-ring sights (sight line y = 0.094), fixed stock
    with a thick pad. The pump fore-end is its own part (br9_pump.glb)."""
    m = Model('br9_body')
    shell = m.material('br9_Shell', None, 0.55, metal=0.2)
    metal = m.material('br9_Metal', None, 0.35, metal=0.8)
    pad = m.material('br9_Pad', None, 0.95)
    glow = m.material('br9_Glow', None, 0.3, emissive=WARM, strength=3.2)
    a, mt, p, e = mk.Mesh(), mk.Mesh(), mk.Mesh(), mk.Mesh()
    mt.add(mk.rounded_box((0, 0.045, -0.06), (0.03, 0.034, 0.15), 0.22), METAL)
    for sx in (-1, 1):
        mt.add(mk.rounded_box((sx * 0.0305, 0.05, -0.05), (0.0015, 0.016, 0.1), 0.2), SHELL_DARK)
        a.add(mk.rounded_box((sx * 0.031, 0.024, -0.16), (0.0015, 0.004, 0.035), 0.3), ACCENT)
    # bore: wide tube to a crown with breaching teeth
    mt.add(zloft(-0.2, -0.53, [(0, 0.022, 0.022), (1, 0.021, 0.021)], 0, 0.058, segs=20), SHELL_DARK)
    mt.add(zloft(-0.5, -0.56, [(0, 0.027, 0.027), (0.5, 0.029, 0.029), (1, 0.027, 0.027)], 0, 0.058, segs=20), METAL)
    for k in range(6):
        ang = k / 6 * 2 * np.pi + 0.3
        mt.add(mk.rounded_box((np.cos(ang) * 0.025, 0.058 + np.sin(ang) * 0.025, -0.565), (0.006, 0.006, 0.008), 0.3, segs=2), METAL)
        mt.add(mk.rounded_box((np.cos(ang) * 0.0285, 0.058 + np.sin(ang) * 0.0285, -0.53), (0.0025, 0.0025, 0.012), 0.3, segs=2), POLY)
    e.add(zloft(-0.556, -0.56, [(0, 0.017, 0.017), (1, 0.017, 0.017)], 0, 0.058), (1, 1, 1))
    for z in (-0.44, -0.47):
        e.add(zloft(z, z - 0.006, [(0, 0.0222, 0.0222), (1, 0.0222, 0.0222)], 0, 0.058), (1, 1, 1))
    # magazine tube and its cap
    mt.add(zloft(-0.15, -0.5, [(0, 0.014, 0.014), (1, 0.014, 0.014)], 0, 0.016, segs=14), SHELL_DARK)
    mt.add(zloft(-0.5, -0.515, [(0, 0.0155, 0.0155), (1, 0.013, 0.013)], 0, 0.016, segs=14), METAL)
    # barrel clamp and a short side rail for a light
    mt.add(mk.rounded_box((0, 0.037, -0.45), (0.012, 0.028, 0.009), 0.3), METAL)
    rail(mt, -0.42, -0.48, 0.016, x=0.018, axis='side', w=0.008)
    # ghost-ring rear on the receiver, post front on the bore
    mt.add(mk.rounded_box((0, 0.086, 0.04), (0.012, 0.006, 0.01), 0.3), METAL)
    mt.add(zloft(0.045, 0.035, [(0, 0.0075, 0.0075), (1, 0.0075, 0.0075)], 0, 0.094, segs=14, caps=False), METAL)
    mt.add(mk.rounded_box((0, 0.088, -0.51), (0.0022, 0.009, 0.004), 0.3), METAL)
    e.add(mk.ellipsoid((0, 0.0945, -0.51), (0.0016, 0.0016, 0.001)), (1, 1, 1))
    # stock: straight polymer stock with a thick recoil pad
    # (comb kept well under the ghost-ring line so the stock sits below the aimed view)
    a.add(mk.rounded_box((0, 0.024, 0.15), (0.021, 0.03, 0.08), 0.4), TAN)
    a.add(mk.rounded_box((0, 0.0, 0.11), (0.018, 0.02, 0.06), 0.4), TAN)
    p.add(mk.rounded_box((0, 0.012, 0.245), (0.023, 0.048, 0.016), 0.5), hexc('#1c1d1e'))
    # pistol grip, trigger guard
    a.add(mk.capsule((0, 0.004, 0.005), (0, -0.084, 0.03), 0.02, 0.018, squash=0.75, hint=(1, 0, 0)), TAN)
    a.add(mk.rounded_box((0, -0.012, -0.035), (0.007, 0.004, 0.03), 0.4), POLY)
    tris = m.solid(a, shell) + m.solid(mt, metal) + m.solid(p, pad) + m.solid(e, glow)
    return m, tris


def ram_pump():
    """The Ram's pump fore-end around the magazine tube (slides back +Z after each shot)."""
    m = Model('br9_pump')
    shell = m.material('br9pump_Shell', None, 0.75, metal=0.1)
    a = mk.Mesh()
    a.add(zloft(-0.22, -0.34, [(0, 0.024, 0.026), (0.1, 0.027, 0.029), (0.9, 0.027, 0.029), (1, 0.024, 0.026)], 0, 0.02, segs=18), TAN)
    for k in range(7):
        z = -0.235 - k * 0.0155
        a.add(zloft(z, z - 0.004, [(0, 0.0285, 0.0305), (1, 0.0285, 0.0305)], 0, 0.02, segs=18), hexc('#5a5140'))
    return m, m.solid(a, shell)


def ram_cell():
    m = Model('br9_cell')
    shell = m.material('br9cell_Shell', None, 0.5, metal=0.2)
    glow = m.material('br9cell_Glow', None, 0.3, emissive=WARM, strength=2.2)
    a, e = mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, -0.03, -0.11), (0.02, 0.03, 0.03), 0.35), TRIM)
    a.add(mk.rounded_box((0, -0.062, -0.11), (0.022, 0.006, 0.032), 0.4), SHELL_DARK)
    for sx in (-1, 1):
        e.add(mk.rounded_box((sx * 0.0202, -0.03, -0.11), (0.0012, 0.018, 0.006), 0.3), (1, 1, 1))
    return m, m.solid(a, shell) + m.solid(e, glow)


def kestrel():
    """"MR-6 Kestrel" designated marksman emitter: free-floated slotted handguard, full-length
    top rail, fixed 4x prism optic (sight line y = 0.116), adjustable stock with a cheek riser."""
    m = Model('mr6_body')
    shell = m.material('mr6_Shell', None, 0.45, metal=0.3)
    metal = m.material('mr6_Metal', None, 0.3, metal=0.85)
    grip = m.material('mr6_Grip', None, 0.86)
    glass = m.material('mr6_Lens', None, 0.05, metal=0.6)
    glow = m.material('mr6_Glow', None, 0.3, emissive=GLOW, strength=2.8)
    a, mt, g, l, e = mk.Mesh(), mk.Mesh(), mk.Mesh(), mk.Mesh(), mk.Mesh()
    mt.add(mk.rounded_box((0, 0.05, -0.06), (0.025, 0.026, 0.15), 0.25), METAL)
    a.add(mk.rounded_box((0, 0.014, -0.04), (0.023, 0.02, 0.12), 0.35), POLY)
    for sx in (-1, 1):
        a.add(mk.rounded_box((sx * 0.0255, 0.026, -0.12), (0.0012, 0.003, 0.04), 0.3), ACCENT)
    # handguard: octagonal-ish tube with slots
    mt.add(zloft(-0.2, -0.56, [(0, 0.027, 0.027), (1, 0.025, 0.025)], 0, 0.045, segs=8), SHELL_DARK)
    for sx in (-1, 1):
        for k in range(6):
            z = -0.25 - k * 0.05
            a.add(mk.rounded_box((sx * 0.0255, 0.045, z), (0.0018, 0.006, 0.015), 0.4, segs=3), POLY)
    rail(mt, 0.08, -0.55, 0.077, w=0.0105)
    # shroud past the handguard with emitter rings
    mt.add(zloft(-0.56, -0.665, [(0, 0.017, 0.017), (0.7, 0.016, 0.016), (1, 0.019, 0.019)], 0, 0.045, segs=18), METAL)
    for z in (-0.585, -0.615):
        e.add(zloft(z, z - 0.005, [(0, 0.0172, 0.0172), (1, 0.0172, 0.0172)], 0, 0.045), (1, 1, 1))
    e.add(zloft(-0.663, -0.667, [(0, 0.011, 0.011), (1, 0.011, 0.011)], 0, 0.045), (1, 1, 1))
    # prism optic: box body, objective and eyepiece bells, turrets, mount
    mt.add(mk.rounded_box((0, 0.088, -0.07), (0.012, 0.007, 0.03), 0.3), POLY)
    a.add(mk.rounded_box((0, 0.116, -0.07), (0.019, 0.02, 0.045), 0.3), POLY)
    a.add(zloft(-0.115, -0.16, [(0, 0.017, 0.017), (1, 0.021, 0.021)], 0, 0.116, segs=18, caps=False), POLY)
    a.add(zloft(-0.025, 0.02, [(0, 0.016, 0.016), (1, 0.018, 0.018)], 0, 0.116, segs=18, caps=False), POLY)
    a.add(mk.rounded_box((0.022, 0.116, -0.07), (0.005, 0.009, 0.009), 0.4), SHELL_DARK)
    a.add(mk.rounded_box((0, 0.139, -0.07), (0.009, 0.005, 0.009), 0.4), SHELL_DARK)
    l.add(zloft(-0.157, -0.16, [(0, 0.02, 0.02), (1, 0.02, 0.02)], 0, 0.116, segs=18), (0.2, 0.28, 0.3))
    l.add(zloft(0.018, 0.02, [(0, 0.017, 0.017), (1, 0.017, 0.017)], 0, 0.116, segs=18), (0.08, 0.1, 0.1))
    # stock: buffer tube, adjustable stock with cheek riser and pad
    mt.add(zloft(0.08, 0.2, [(0, 0.013, 0.013), (1, 0.013, 0.013)], 0, 0.05, segs=14), METAL)
    a.add(mk.rounded_box((0, 0.045, 0.21), (0.021, 0.034, 0.055), 0.4), POLY)
    a.add(mk.rounded_box((0, 0.084, 0.2), (0.015, 0.008, 0.045), 0.5), SHELL_DARK)
    a.add(mk.rounded_box((0, 0.035, 0.268), (0.022, 0.052, 0.01), 0.5), hexc('#1c1d1e'))
    # grip, guard
    g.add(mk.capsule((0, 0.004, 0.005), (0, -0.084, 0.03), 0.018, 0.016, squash=0.75, hint=(1, 0, 0)), POLY)
    a.add(mk.rounded_box((0, -0.012, -0.035), (0.006, 0.004, 0.03), 0.4), POLY)
    tris = m.solid(a, shell) + m.solid(mt, metal) + m.solid(g, grip) + m.solid(l, glass) + m.solid(e, glow)
    return m, tris


def kestrel_cell():
    m = Model('mr6_cell')
    shell = m.material('mr6cell_Shell', None, 0.5, metal=0.2)
    glow = m.material('mr6cell_Glow', None, 0.3, emissive=GLOW, strength=2.2)
    a, e = mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, -0.04, -0.1), (0.015, 0.045, 0.03), 0.35, rot=mk.rot_x(6)), TRIM)
    a.add(mk.rounded_box((0, -0.085, -0.104), (0.017, 0.006, 0.032), 0.4), SHELL_DARK)
    for sx in (-1, 1):
        e.add(mk.rounded_box((sx * 0.0152, -0.04, -0.1), (0.0012, 0.028, 0.005), 0.3, rot=mk.rot_x(6)), (1, 1, 1))
    return m, m.solid(a, shell) + m.solid(e, glow)


def arms_case():
    """Open hard-shell arms case for the staging camp: grey shell, dark foam bed with three long
    cut-outs and two short ones, lid propped open behind with the unit's amber stripe. Origin at
    the base centre on the ground; long axis of the cut-outs along Z. Foam top at y = 0.13."""
    m = Model('arms_case')
    shell = m.material('case_Shell', None, 0.55, metal=0.1)
    foam = m.material('case_Foam', None, 0.98)
    metal = m.material('case_Metal', None, 0.35, metal=0.8)
    a, f, mt = mk.Mesh(), mk.Mesh(), mk.Mesh()
    a.add(mk.rounded_box((0, 0.07, 0), (0.47, 0.07, 0.6), 0.15), hexc('#3d4247'))
    for x in (-0.47, 0.47):
        for z in (-0.4, 0.0, 0.4):
            a.add(mk.rounded_box((x * 1.01, 0.07, z), (0.012, 0.06, 0.05), 0.3, segs=3), hexc('#2a2e31'))
    f.add(mk.rounded_box((0, 0.125, 0), (0.44, 0.008, 0.57), 0.1, segs=3), hexc('#17191a'))
    for x in (-0.28, 0.0, 0.28):
        f.add(mk.rounded_box((x, 0.131, -0.05), (0.07, 0.002, 0.5), 0.1, segs=2), hexc('#0e0f10'))
    # lid, opened past vertical and leaning back on its stay
    lid = mk.rot_x(-12)
    a.add(mk.rounded_box((0, 0.66, 0.66), (0.47, 0.56, 0.05), 0.15, rot=lid), hexc('#3d4247'))
    f.add(mk.rounded_box((0, 0.66, 0.6), (0.44, 0.53, 0.01), 0.1, segs=3, rot=lid), hexc('#17191a'))
    a.add(mk.rounded_box((0, 0.66, 0.715), (0.47, 0.03, 0.002), 0.2, segs=2, rot=lid), ACCENT)
    for x in (-0.36, 0.36):
        mt.add(mk.rounded_box((x, 0.15, 0.6), (0.04, 0.02, 0.02), 0.3, segs=3), hexc('#6a6f73'))
        mt.add(mk.rounded_box((x, 0.08, -0.61), (0.05, 0.03, 0.012), 0.3, segs=3), hexc('#6a6f73'))
    return m, m.solid(a, shell) + m.solid(f, foam) + m.solid(mt, metal)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    d = os.path.join(a.out, 'models', 'weapons'); os.makedirs(d, exist_ok=True)
    pr = os.path.join(a.out, 'models', 'props'); os.makedirs(pr, exist_ok=True)
    built = [carbine(), carbine_cell(), sidearm(), sidearm_slide(), sidearm_cell(), marksman(), marksman_cell(),
             hand('r'), hand('l'), pulse_bolt(), stun_target(),
             hornet(), hornet_cell(), ram(), ram_pump(), ram_cell(), kestrel(), kestrel_cell()]
    by = {m.name: m for m, _ in built}
    # Storage / world variants: the same parts merged and laid on their left side, origin at the
    # bottom centre of the resting pose (lib/storage.luau places them on cargo anchors).
    side = mk.rot_z(90)
    worlds = [world_model('pc7_world', [by['pc7_body'], by['pc7_cell']], side, (0.035, 0, 0.0)),
              world_model('sp2_world', [by['sp2_body'], by['sp2_slide'], by['sp2_cell']], side, (0.025, 0, 0.06)),
              world_model('lr4_world', [by['lr4_body'], by['lr4_cell']], side, (0.035, 0, 0.12)),
              world_model('kv5_world', [by['kv5_body'], by['kv5_cell']], side, (0.035, 0, 0.0)),
              world_model('br9_world', [by['br9_body'], by['br9_pump'], by['br9_cell']], side, (0.035, 0, 0.1)),
              world_model('mr6_world', [by['mr6_body'], by['mr6_cell']], side, (0.035, 0, 0.12))]
    for m, tris in built + worlds:
        p = os.path.join(d, m.name + '.glb'); m.save(p)
        print(f"{m.name:14s} {tris:6d} tris  {os.path.getsize(p) // 1024:4d} KiB")
    for m, tris in [field_kit(), cell_pack(), arms_case()]:
        p = os.path.join(pr, m.name + '.glb'); m.save(p)
        print(f"{m.name:14s} {tris:6d} tris  {os.path.getsize(p) // 1024:4d} KiB")


if __name__ == '__main__':
    main()
