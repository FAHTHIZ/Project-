# SPDX-License-Identifier: Apache-2.0
"""Generate the Halyard Team squad transport: the HT-4 "Mule", an original boxy four-door
utility vehicle with a rear cargo hatch. All geometry is procedural and original (see
docs/ASSET_PROVENANCE.md); it is not modelled on a specific real vehicle.

    python3 tools/props/build_vehicle.py --out game/assets

Writes <out>/models/vehicle/*.glb, each part with its pivot where it moves:

  mule_body.glb        chassis, cabin shell (pillars, roof, hood, bumpers), lights, interior
                       (dash, steering wheel, two front seats, rear bench), cargo bay, roof rack
  mule_glass.glb       fixed glass: windscreen, rear quarter windows (alpha material override)
  mule_door_fl/fr/rl/rr.glb  doors; origin on the hinge line (front edge), door extends to +Z
  mule_door_glass.glb  door window (shared by all four doors)
  mule_hatch.glb       rear hatch; origin on the roof hinge, hangs down (-Y), opens about X
  mule_hatch_glass.glb hatch window
  mule_wheel.glb       tyre + rim; origin at the hub, axle along X
  mule_steering.glb    steering wheel; origin at the column, turns about its local Z

Vehicle frame: metres, +Y up, the front points along -Z, origin on the ground at the centre of
the wheelbase. Key dimensions are exported in VEHICLE (used by tools/scenes and the scripts).
"""
from __future__ import annotations
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'characters'))
from build_forest import Model, hexc  # noqa: E402
import meshkit as mk  # noqa: E402

PAINT = hexc('#4d5648')       # muted field olive
PAINT_DARK = hexc('#3a4136')
CLAD = hexc('#26292a')        # black plastic cladding / bumpers
TRIM = hexc('#5c6166')
INTERIOR = hexc('#2e3134')
SEAT = hexc('#3b3a36')
SEAT_SIDE = hexc('#2b2a27')
FLOOR = hexc('#1f2122')
RUBBER = hexc('#1b1c1d')
RIM = hexc('#6a6e70')
ACCENT = hexc('#c48a2c')      # Halyard amber
GLASS = (0.16, 0.2, 0.22)

VEHICLE = {
    'wheel_radius': 0.40, 'wheel_x': 0.84, 'front_axle_z': -1.55, 'rear_axle_z': 1.45,
    'doors': {  # hinge position (x, y, z) in the vehicle frame; open sign for yaw
        'fl': {'hinge': [-0.965, 0.0, -1.02], 'sign': -1, 'len': 0.96},
        'fr': {'hinge': [0.965, 0.0, -1.02], 'sign': 1, 'len': 0.96},
        'rl': {'hinge': [-0.965, 0.0, -0.02], 'sign': -1, 'len': 0.94},
        'rr': {'hinge': [0.965, 0.0, -0.02], 'sign': 1, 'len': 0.94},
    },
    'hatch_hinge': [0.0, 1.9 + 0.12, 2.36],  # 0.12 = ROOF_LIFT
    'seats': {  # hip point (x, y, z) and the door each seat exits through
        'driver': {'pos': [-0.44, 0.98, -0.36], 'door': 'fl'},
        'front_right': {'pos': [0.44, 0.98, -0.36], 'door': 'fr'},
        'rear_left': {'pos': [-0.5, 0.98, 0.62], 'door': 'rl'},
        'rear_middle': {'pos': [0.0, 0.98, 0.62], 'door': 'rr'},
        'rear_right': {'pos': [0.5, 0.98, 0.62], 'door': 'rr'},
    },
    'cargo_floor_y': 0.74, 'cargo_z': [1.12, 2.3],
    'steering': [-0.44, 1.26, -0.78],
}


ROOF_LIFT = 0.12   # extra cabin headroom: a seated operator in a helmet needs ~0.95 m hip-to-headliner
LIFT_Y = 1.75      # everything at or above this line (roof, rails, pillar tops, window headers) moves up


def lift(*meshes):
    """Raise the roof line: vertices at or above LIFT_Y move up ROOF_LIFT, stretching pillars and glass."""
    for me in meshes:
        for P in me.P:
            P[:, 1] = np.where(P[:, 1] >= LIFT_Y - 1e-6, P[:, 1] + ROOF_LIFT, P[:, 1])


def hatch_stretch(*meshes):
    """The hatch hangs from the lifted hinge to the unchanged loading lip: stretch it along -Y."""
    k = (1.16 + ROOF_LIFT) / 1.16
    for me in meshes:
        for P in me.P:
            P[:, 1] = P[:, 1] * k


def hexa(c):
    """Flat-shaded hexahedron from 8 corners (two quads: c[0..3] then c[4..7], same winding)."""
    c = np.asarray(c, float)
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    cen = c.mean(axis=0)
    P, N, I = [], [], []
    for f in faces:
        q = c[list(f)]
        n = np.cross(q[1] - q[0], q[2] - q[0])
        if np.linalg.norm(n) < 1e-9:
            n = np.cross(q[2] - q[0], q[3] - q[0])
        ln = np.linalg.norm(n)
        if ln < 1e-9:
            continue
        n /= ln
        if np.dot(n, q.mean(axis=0) - cen) < 0:
            n = -n
        b = len(P)
        P.extend(q); N.extend([n] * 4)
        I += [b, b + 1, b + 2, b, b + 2, b + 3]
    return np.array(P), np.array(N), np.array(I, dtype=np.uint32)


def box(lo, hi):
    x0, y0, z0 = lo; x1, y1, z1 = hi
    return hexa([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                 (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])


def rbox(center, half, r=0.18):
    return mk.rounded_box(center, half, r, segs=3)


def side_profile(x0, x1, pts_yz):
    """Prism along X from a convex YZ outline given as 4 points (y, z)."""
    q = [(x0, y, z) for y, z in pts_yz] + [(x1, y, z) for y, z in pts_yz]
    return hexa(q)


def body():
    m = Model('mule_body')
    paint = m.material('mule_Paint', None, 0.48, metal=0.25)
    clad = m.material('mule_Clad', None, 0.8)
    inner = m.material('mule_Interior', None, 0.85)
    seat = m.material('mule_Seat', None, 0.92)
    lamp = m.material('mule_Lamp', None, 0.2, emissive=(1.0, 0.95, 0.85), strength=2.0)
    tail = m.material('mule_Tail', None, 0.3, emissive=(0.9, 0.08, 0.04), strength=1.4)
    a, cl, it, st, lm, tl = (mk.Mesh() for _ in range(6))
    W = 0.97
    # lower tub: sills under the doors, front and rear quarter panels around the wheel arches
    a.add(box((-W, 0.40, -1.02), (-W + 0.07, 0.56, 0.95)), PAINT_DARK)
    a.add(box((W - 0.07, 0.40, -1.02), (W, 0.56, 0.95)), PAINT_DARK)
    for sx in (-1, 1):
        x0, x1 = (sx * W, sx * (W - 0.08)) if sx < 0 else (sx * (W - 0.08), sx * W)
        lo, hi = min(x0, x1), max(x0, x1)
        # front quarter (ahead of the front door) with an arch cut-out implied by two blocks
        a.add(box((lo, 0.82, -2.38), (hi, 1.12, -1.02)), PAINT)
        a.add(box((lo, 0.45, -2.38), (hi, 0.82, -2.0)), PAINT)
        a.add(box((lo, 0.45, -1.1), (hi, 0.82, -1.02)), PAINT)
        # rear quarter (behind the rear door, round the cargo bay)
        a.add(box((lo, 0.82, 0.95), (hi, 1.2, 2.38)), PAINT)
        a.add(box((lo, 0.45, 0.95), (hi, 0.82, 1.02)), PAINT)
        a.add(box((lo, 0.45, 1.9), (hi, 0.82, 2.38)), PAINT)
        # wheel-arch flares (black cladding)
        for zc in (VEHICLE['front_axle_z'], VEHICLE['rear_axle_z']):
            cl.add(mk.loft((sx * (W + 0.01), 0.40, zc), (sx * (W - 0.12), 0.40, zc),
                           [(0, 0.5, 0.5), (1, 0.5, 0.5)], 16, hint=(0, 1, 0), caps=False), CLAD)
        # pillars: A (slanted), B, C, D
        a.add(hexa([(lo, 1.14, -1.06), (hi, 1.14, -1.06), (hi, 1.14, -0.98), (lo, 1.14, -0.98),
                    (lo, 1.86, -0.46), (hi, 1.86, -0.46), (hi, 1.86, -0.38), (lo, 1.86, -0.38)]), PAINT)
        a.add(box((lo, 0.56, -0.06), (hi, 1.88, 0.02)), PAINT_DARK)
        a.add(box((lo, 1.2, 0.95), (hi, 1.88, 1.1)), PAINT)
        a.add(box((lo, 1.2, 2.26), (hi, 1.88, 2.38)), PAINT)
        a.add(box((lo, 1.2, 1.1), (hi, 1.26, 2.26)), PAINT)      # rear quarter window sill
        a.add(box((lo, 1.8, 1.1), (hi, 1.88, 2.26)), PAINT)      # rear quarter window header
        # roof side rails
        a.add(box((lo, 1.8, -0.46), (hi, 1.9, 0.95)), PAINT)
        # door-line seals visible when the doors open
        it.add(box((sx * (W - 0.09) - 0.005, 0.56, -1.0), (sx * (W - 0.09) + 0.005, 0.6, 0.94)), FLOOR)
    # roof with a shallow crown and a rack
    a.add(hexa([(-W, 1.88, -0.46), (W, 1.88, -0.46), (W, 1.88, 2.38), (-W, 1.88, 2.38),
                (-W + 0.06, 1.95, -0.4), (W - 0.06, 1.95, -0.4), (W - 0.06, 1.95, 2.34), (-W + 0.06, 1.95, 2.34)]), PAINT)
    for z in (0.1, 1.0, 1.9):
        cl.add(box((-0.86, 1.95, z - 0.025), (0.86, 2.0, z + 0.025)), CLAD)
    for sx in (-1, 1):
        cl.add(box((sx * 0.86 - 0.03, 1.95, -0.2), (sx * 0.86 + 0.03, 2.03, 2.2)), CLAD)
    # hood and nose
    a.add(hexa([(-W, 1.0, -2.38), (W, 1.0, -2.38), (W, 1.12, -1.06), (-W, 1.12, -1.06),
                (-W + 0.04, 1.06, -2.38), (W - 0.04, 1.06, -2.38), (W - 0.04, 1.16, -1.06), (-W + 0.04, 1.16, -1.06)]), PAINT)
    a.add(box((-W, 0.56, -2.42), (W, 1.02, -2.32)), PAINT_DARK)               # front face
    for i in range(5):                                                         # grille slats
        cl.add(box((-0.42, 0.66 + i * 0.06, -2.445), (0.42, 0.69 + i * 0.06, -2.41)), CLAD)
    cl.add(box((-1.0, 0.38, -2.55), (1.0, 0.6, -2.38)), CLAD)                  # front bumper
    cl.add(box((-1.0, 0.38, 2.38), (1.0, 0.64, 2.52)), CLAD)                   # rear bumper / step
    cl.add(box((-0.9, 0.36, -2.3), (0.9, 0.44, 2.3)), CLAD)                    # underbody
    cl.add(box((-0.92, 0.42, -1.02), (-W + 0.07, 0.5, 0.95)), CLAD)            # side steps
    cl.add(box((W - 0.07, 0.42, -1.02), (0.92, 0.5, 0.95)), CLAD)
    cl.add(box((-1.12, 0.42, -0.9), (-W, 0.46, 0.9)), CLAD)
    cl.add(box((W, 0.42, -0.9), (1.12, 0.46, 0.9)), CLAD)
    # rear face round the hatch opening
    for sx in (-1, 1):
        a.add(box((min(sx * W, sx * 0.84), 0.56, 2.32), (max(sx * W, sx * 0.84), 1.9, 2.4)), PAINT)
    a.add(box((-0.84, 0.56, 2.32), (0.84, 0.74, 2.4)), PAINT)                 # loading lip
    # lamps
    for sx in (-1, 1):
        lm.add(rbox((sx * 0.72, 0.93, -2.425), (0.16, 0.055, 0.015), 0.3), (1, 1, 1))
        tl.add(rbox((sx * 0.905, 1.42, 2.405), (0.045, 0.2, 0.012), 0.3), (1, 1, 1))
        cl.add(rbox((sx * 1.04, 1.32, -1.0), (0.07, 0.06, 0.03), 0.3), CLAD)   # mirrors
        cl.add(box((sx * 0.98 - 0.02, 1.3, -1.02), (sx * 0.98 + 0.02, 1.34, -0.98)), CLAD)
    # amber unit stripe and number plate blank
    for sx in (-1, 1):
        a.add(box((min(sx * W, sx * (W + 0.004)), 0.98, 1.2), (max(sx * W, sx * (W + 0.004)), 1.02, 2.3)), ACCENT)
    cl.add(box((-0.22, 0.44, 2.52), (0.22, 0.56, 2.53)), hexc('#d8d3c4'))
    # interior: floor, firewall, dash, seats, divider, cargo bay
    it.add(box((-0.9, 0.5, -1.0), (0.9, 0.56, 1.12)), FLOOR)
    it.add(box((-0.9, 0.56, -1.06), (0.9, 1.0, -0.98)), INTERIOR)             # firewall
    it.add(hexa([(-0.9, 1.0, -1.02), (0.9, 1.0, -1.02), (0.9, 1.0, -0.72), (-0.9, 1.0, -0.72),
                 (-0.9, 1.2, -1.04), (0.9, 1.2, -1.04), (0.9, 1.22, -0.86), (-0.9, 1.22, -0.86)]), INTERIOR)  # dash
    it.add(box((-0.16, 0.56, -0.95), (0.16, 0.86, -0.1)), INTERIOR)           # centre console
    it.add(box((-0.9, 1.86, -0.44), (0.9, 1.88, 2.3)), hexc('#55575a'))        # headliner
    for sx in (-1, 1):                                                         # door-card colour inside the quarter panels
        it.add(box((sx * 0.9 - 0.01, 0.56, 1.1), (sx * 0.9 + 0.01, 1.2, 2.3)), INTERIOR)
    for x in (-0.44, 0.44):                                                    # front seats
        st.add(rbox((x, 0.9, -0.38), (0.24, 0.07, 0.25), 0.4), SEAT)
        st.add(rbox((x, 1.3, -0.13), (0.24, 0.34, 0.07), 0.4), SEAT)
        st.add(rbox((x, 1.72, -0.12), (0.13, 0.08, 0.06), 0.5), SEAT_SIDE)
        st.add(box((x - 0.18, 0.56, -0.56), (x + 0.18, 0.83, -0.2)), SEAT_SIDE)
    st.add(rbox((0, 0.9, 0.62), (0.8, 0.07, 0.25), 0.3), SEAT)                 # rear bench
    st.add(rbox((0, 1.3, 0.92), (0.8, 0.34, 0.07), 0.3), SEAT)
    for x in (-0.5, 0.0, 0.5):
        st.add(rbox((x, 1.72, 0.93), (0.12, 0.07, 0.05), 0.5), SEAT_SIDE)
    st.add(box((-0.8, 0.56, 0.4), (0.8, 0.83, 0.86)), SEAT_SIDE)
    it.add(box((-0.9, 0.56, 1.0), (0.9, 1.32, 1.1)), INTERIOR)                # bench back / divider
    it.add(box((-0.9, 0.56, 1.1), (0.9, VEHICLE['cargo_floor_y'], 2.32)), INTERIOR)
    it.add(box((-0.84, VEHICLE['cargo_floor_y'], 1.12), (0.84, VEHICLE['cargo_floor_y'] + 0.012, 2.3)), FLOOR)
    for z in (1.4, 1.8, 2.15):                                                 # load rails
        it.add(box((-0.8, VEHICLE['cargo_floor_y'] + 0.012, z - 0.012), (0.8, VEHICLE['cargo_floor_y'] + 0.03, z + 0.012)), TRIM)
    for sx in (-1, 1):                                                         # wheel tubs inside the bay
        it.add(rbox((sx * 0.74, VEHICLE['cargo_floor_y'] + 0.1, VEHICLE['rear_axle_z']), (0.12, 0.1, 0.36), 0.4), INTERIOR)
    lift(a, cl, it)
    tris = (m.solid(a, paint) + m.solid(cl, clad) + m.solid(it, inner) + m.solid(st, seat) +
            m.solid(lm, lamp) + m.solid(tl, tail))
    return m, tris


def glass_mat(m, name):
    return m.material(name, None, 0.06, metal=0.0, color=(GLASS[0], GLASS[1], GLASS[2], 0.38), double=True)


def glass():
    m = Model('mule_glass')
    g = glass_mat(m, 'mule_Glass')
    a = mk.Mesh()
    a.add(hexa([(-0.9, 1.15, -1.02), (0.9, 1.15, -1.02), (0.9, 1.15, -1.0), (-0.9, 1.15, -1.0),
                (-0.9, 1.84, -0.43), (0.9, 1.84, -0.43), (0.9, 1.84, -0.41), (-0.9, 1.84, -0.41)]), GLASS)
    for sx in (-1, 1):
        x = sx * 0.955
        a.add(box((x - 0.006, 1.26, 1.1), (x + 0.006, 1.8, 2.26)), GLASS)
    lift(a)
    return m, m.solid(a, g)


def door(side, front):
    """Door in hinge space: hinge line at x=0,z=0; the panel runs to +Z, outer skin at x=0."""
    name = f"mule_door_{side}"
    m = Model(name)
    paint = m.material(name + '_Paint', None, 0.48, metal=0.25)
    inner = m.material(name + '_Card', None, 0.85)
    clad = m.material(name + '_Clad', None, 0.8)
    a, it, cl = mk.Mesh(), mk.Mesh(), mk.Mesh()
    L = 0.96 if front else 0.94
    s = -1 if side == 'l' else 1          # outward x
    xo, xi = 0.0, -s * 0.07               # outer skin and the inner door card plane
    lo, hi = min(xo, xi), max(xo, xi)
    a.add(box((lo, 0.5, 0.0), (hi, 1.18, L)), PAINT)                          # lower panel
    a.add(box((lo + (0.03 if s < 0 else 0), 1.18, 0.0), (hi - (0.0 if s < 0 else 0.03), 1.8, 0.05)), PAINT)
    a.add(box((lo + (0.03 if s < 0 else 0), 1.18, L - 0.05), (hi - (0.0 if s < 0 else 0.03), 1.8, L)), PAINT)
    a.add(box((lo + (0.03 if s < 0 else 0), 1.76, 0.0), (hi - (0.0 if s < 0 else 0.03), 1.82, L)), PAINT)
    if front:  # mirror-side front edge follows the A pillar: shorten the upper frame
        a.add(box((lo + (0.03 if s < 0 else 0), 1.18, 0.05), (hi - (0.0 if s < 0 else 0.03), 1.4, 0.16)), PAINT)
    it.add(box((min(xi, xi - s * 0.012), 0.55, 0.04), (max(xi, xi - s * 0.012), 1.16, L - 0.04)), INTERIOR)
    it.add(rbox((xi - s * 0.04, 0.98, L * 0.55), (0.03, 0.03, L * 0.3), 0.4), INTERIOR)  # armrest
    cl.add(rbox((s * 0.008, 1.06, L - 0.16), (0.008, 0.016, 0.07), 0.4), CLAD)            # handle
    cl.add(box((lo, 0.5, 0.0), (hi, 0.6, L)), CLAD)                                       # lower cladding
    lift(a, it, cl)
    return m, m.solid(a, paint) + m.solid(it, inner) + m.solid(cl, clad)


def door_glass():
    m = Model('mule_door_glass')
    g = glass_mat(m, 'mule_DoorGlass')
    a = mk.Mesh()
    a.add(box((-0.006, 1.18, 0.05), (0.006, 1.76, 0.89)), GLASS)
    lift(a)
    return m, m.solid(a, g)


def hatch():
    """Rear hatch in hinge space: hinge at the origin, hangs to -Y, outer skin toward +Z."""
    m = Model('mule_hatch')
    paint = m.material('mule_hatch_Paint', None, 0.48, metal=0.25)
    inner = m.material('mule_hatch_Card', None, 0.85)
    clad = m.material('mule_hatch_Clad', None, 0.8)
    a, it, cl = mk.Mesh(), mk.Mesh(), mk.Mesh()
    # frame round the window, lower panel to the loading lip
    a.add(box((-0.84, -1.16, -0.02), (0.84, -0.62, 0.05)), PAINT)
    a.add(box((-0.84, -0.62, -0.02), (-0.74, 0.0, 0.05)), PAINT)
    a.add(box((0.74, -0.62, -0.02), (0.84, 0.0, 0.05)), PAINT)
    a.add(box((-0.84, -0.08, -0.02), (0.84, 0.0, 0.05)), PAINT)
    it.add(box((-0.8, -1.12, -0.05), (0.8, -0.64, -0.02)), INTERIOR)
    cl.add(rbox((0, -0.72, 0.058), (0.12, 0.018, 0.01), 0.4), CLAD)           # handle
    cl.add(box((-0.12, -0.83, 0.05), (0.12, -0.75, 0.056)), hexc('#d8d3c4'))
    cl.add(box((-0.84, -1.16, 0.05), (0.84, -1.1, 0.06)), CLAD)
    hatch_stretch(a, it, cl)
    return m, m.solid(a, paint) + m.solid(it, inner) + m.solid(cl, clad)


def hatch_glass():
    m = Model('mule_hatch_glass')
    g = glass_mat(m, 'mule_HatchGlass')
    a = mk.Mesh()
    a.add(box((-0.74, -0.62, 0.008), (0.74, -0.08, 0.02)), GLASS)
    hatch_stretch(a)
    return m, m.solid(a, g)


def wheel():
    m = Model('mule_wheel')
    rub = m.material('mule_Tyre', None, 0.95)
    rim = m.material('mule_Rim', None, 0.5, metal=0.5)
    t, r = mk.Mesh(), mk.Mesh()
    R, Wd = VEHICLE['wheel_radius'], 0.27
    prof = [(0.0, R * 0.68, R * 0.68), (0.06, R * 0.9, R * 0.9), (0.2, R, R), (0.8, R, R), (0.94, R * 0.9, R * 0.9),
            (1.0, R * 0.68, R * 0.68)]
    t.add(mk.loft((-Wd / 2, 0, 0), (Wd / 2, 0, 0), prof, 28, hint=(0, 1, 0), caps=False), RUBBER)
    # tread blocks so the spin reads
    for i in range(18):
        ang = 2 * np.pi * i / 18
        c = np.array([0, np.cos(ang) * (R + 0.004), np.sin(ang) * (R + 0.004)])
        rot = mk.rot_x(-np.degrees(ang))
        t.add(mk.rounded_box(c, (Wd * 0.42, 0.012, 0.03), 0.2, segs=2, rot=rot), RUBBER)
    for sx in (-1, 1):
        x = sx * (Wd / 2 - 0.035)
        r.add(mk.loft((x, 0, 0), (x + sx * 0.03, 0, 0), [(0, R * 0.66, R * 0.66), (1, R * 0.6, R * 0.6)], 24, hint=(0, 1, 0)), RIM)
        r.add(mk.loft((x + sx * 0.03, 0, 0), (x + sx * 0.05, 0, 0), [(0, 0.08, 0.08), (1, 0.06, 0.06)], 12, hint=(0, 1, 0)), TRIM)
        for i in range(6):  # spokes
            ang = 2 * np.pi * i / 6
            d = np.array([0, np.cos(ang), np.sin(ang)])
            r.add(mk.capsule(np.array([x + sx * 0.03, 0, 0]) + d * 0.07, np.array([x + sx * 0.02, 0, 0]) + d * R * 0.6,
                             0.022, 0.018, segs=6, rings=1, hint=(1, 0, 0)), RIM)
    return m, m.solid(t, rub) + m.solid(r, rim)


def steering():
    m = Model('mule_steering')
    mat = m.material('mule_Steering', None, 0.7)
    a = mk.Mesh()
    ring = []
    n = 20
    for i in range(n):
        a0 = 2 * np.pi * i / n; a1 = 2 * np.pi * (i + 1) / n
        p0 = np.array([np.cos(a0) * 0.18, np.sin(a0) * 0.18, 0]); p1 = np.array([np.cos(a1) * 0.18, np.sin(a1) * 0.18, 0])
        a.add(mk.capsule(p0, p1, 0.016, 0.016, segs=6, rings=1), CLAD)
    for ang in (0, 2.3, 3.98):
        d = np.array([np.cos(ang), np.sin(ang), 0])
        a.add(mk.capsule(d * 0.03, d * 0.17, 0.014, 0.012, segs=6, rings=1), CLAD)
    a.add(mk.loft((0, 0, -0.01), (0, 0, 0.03), [(0, 0.05, 0.05), (1, 0.04, 0.04)], 12), CLAD)
    a.add(mk.capsule((0, 0, 0.03), (0, 0, 0.32), 0.025, 0.03, segs=8, rings=1), CLAD)
    return m, m.solid(a, mat)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); a = ap.parse_args()
    d = os.path.join(a.out, 'models', 'vehicle'); os.makedirs(d, exist_ok=True)
    parts = [body(), glass(), door('l', True), door('r', True), door('l', False), door('r', False), door_glass(),
             hatch(), hatch_glass(), wheel(), steering()]
    names = ['mule_body', 'mule_glass', 'mule_door_fl', 'mule_door_fr', 'mule_door_rl', 'mule_door_rr',
             'mule_door_glass', 'mule_hatch', 'mule_hatch_glass', 'mule_wheel', 'mule_steering']
    total = 0
    for (m, tris), nm in zip(parts, names):
        m.name = nm
        p = os.path.join(d, nm + '.glb'); m.save(p)
        total += tris * (4 if nm == 'mule_wheel' else 1)
        print(f"{nm:18s} {tris:6d} tris  {os.path.getsize(p) // 1024:4d} KiB")
    print(f"vehicle total (4 wheels) {total} tris")
    with open(os.path.join(os.path.dirname(__file__), '..', 'scenes', 'vehicle_layout.json'), 'w') as f:
        json.dump(VEHICLE, f, indent=1)


if __name__ == '__main__':
    main()
