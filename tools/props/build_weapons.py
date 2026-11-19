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

The weapons are game objects only: they fire invented "stun pulses" with invented values, have
no real-world mechanism and do not resemble a specific real firearm.

Local frame (all parts): metres, +Y up, the muzzle points along -Z, origin at the grip hand.
"""
from __future__ import annotations
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'characters'))
from build_forest import Model, hexc  # noqa: E402
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
    for m, tris in [carbine(), carbine_cell(), sidearm(), sidearm_slide(), sidearm_cell(), hand('r'), hand('l'),
                    pulse_bolt(), stun_target()]:
        p = os.path.join(d, m.name + '.glb'); m.save(p)
        print(f"{m.name:14s} {tris:6d} tris  {os.path.getsize(p) // 1024:4d} KiB")


if __name__ == '__main__':
    main()
