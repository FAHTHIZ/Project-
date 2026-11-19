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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    d = os.path.join(a.out, 'models', 'weapons'); os.makedirs(d, exist_ok=True)
    pr = os.path.join(a.out, 'models', 'props'); os.makedirs(pr, exist_ok=True)
    built = [carbine(), carbine_cell(), sidearm(), sidearm_slide(), sidearm_cell(), marksman(), marksman_cell(),
             hand('r'), hand('l'), pulse_bolt(), stun_target()]
    by = {m.name: m for m, _ in built}
    # Storage / world variants: the same parts merged and laid on their left side, origin at the
    # bottom centre of the resting pose (lib/storage.luau places them on cargo anchors).
    side = mk.rot_z(90)
    worlds = [world_model('pc7_world', [by['pc7_body'], by['pc7_cell']], side, (0.035, 0, 0.0)),
              world_model('sp2_world', [by['sp2_body'], by['sp2_slide'], by['sp2_cell']], side, (0.025, 0, 0.06)),
              world_model('lr4_world', [by['lr4_body'], by['lr4_cell']], side, (0.035, 0, 0.12))]
    for m, tris in built + worlds:
        p = os.path.join(d, m.name + '.glb'); m.save(p)
        print(f"{m.name:14s} {tris:6d} tris  {os.path.getsize(p) // 1024:4d} KiB")
    for m, tris in [field_kit(), cell_pack()]:
        p = os.path.join(pr, m.name + '.glb'); m.save(p)
        print(f"{m.name:14s} {tris:6d} tris  {os.path.getsize(p) // 1024:4d} KiB")


if __name__ == '__main__':
    main()
