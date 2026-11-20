# SPDX-License-Identifier: Apache-2.0
"""Photoscanned dressing for the Kestrel Station interiors (called by build_facility.py).

The procedural kit (desks, benches, shelves, bunks, the breaker wall, the archive rows) stays as
the room layout; this pass adds the things that make a real building read as lived in and
maintained: fire safety kit and CCTV on the walls, cable runs and risers, ducts under the slab,
desk clutter, carts and boxes left mid-job, the comms room where Venn is kept, the Source Vault's
paperwork and the review room's workstations. Models: models/interior/ph/*.glb from
tools/assets/build_interior_props.py (Poly Haven, CC0); bounds in tools/levels/interior_props.json.

Placement rules (the squad and contractors still need their aisles):
  * floor props stand against a wall (`wall()`), never inside a door opening (+0.9 m margin);
  * free-standing props only where the room plan leaves space (explicit coordinates);
  * small clutter and wall fittings have no collider; furniture gets its bounding box.
Conventions: x east, z south; a prop's front is its local +Z, so yaw 0 faces south.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from vscene import transform, collider, body

HERE = Path(__file__).resolve().parent
PH = 'models/interior/ph/'
B = json.loads((HERE / 'interior_props.json').read_text()) if (HERE / 'interior_props.json').exists() else {}
T = 0.15          # half wall thickness (build_facility.build_shell, T = 0.3)
NO_COLLIDE = {'extinguisher', 'fire_alarm', 'cctv', 'wall_lamp',
              'power_box', 'security_light', 'wall_clock', 'binder',
              'clipboard', 'notepads', 'laptop', 'crt_monitor', 'desk_lamp', 'stationery', 'radio_set',
              'medical_box', 'microscope', 'chemistry_set', 'multimeter', 'circuit_board',
              'searchlight', 'wet_floor_sign', 'cardboard_box', 'jerrycan', 'cement_bag',
              'stool', 'propane_tank'}
COUNT = {'props': 0, 'tris': 0, 'skipped': 0}


def size(model):
    b = B[model]
    return [b['max'][i] - b['min'][i] for i in range(3)]


def put(sc, name, model, x, z, yaw=0.0, y=0.0, collide=None, parent=None):
    if model not in B:
        print(f'dress: {model} not built, skipped')
        return None
    root = sc.prop('Dress ' + name, PH + model + '.glb', (x, y, z), yaw, parent=parent, shadows=model not in NO_COLLIDE)
    if collide is None:
        collide = model not in NO_COLLIDE
    if collide:
        b = B[model]
        c = [(b['min'][i] + b['max'][i]) / 2 for i in range(3)]
        h = [max(0.05, b['max'][i] - b['min'][i]) for i in range(3)]
        sc.add(f'{name} Col', {'Transform': transform(tuple(c)), 'Collider': collider('box', tuple(h)),
                               'RigidBody': body('static')}, root)
    COUNT['props'] += 1
    COUNT['tris'] += B[model].get('tris', 0)
    return root


# walls: side -> (inward normal x, z, yaw facing into the room)
SIDES = {'n': (0, 1, 0.0), 's': (0, -1, 180.0), 'w': (1, 0, 90.0), 'e': (-1, 0, -90.0)}


def blocked(lv, r, side, t, half):
    """True if the wall `side` of room r has an opening within `half` (+0.9 m) of position t."""
    line, axis = {'n': (r.z0, 'x'), 's': (r.z1, 'x'), 'w': (r.x0, 'z'), 'e': (r.x1, 'z')}[side]
    for o in lv.openings:
        if o['axis'] == axis and abs(o['at'] - line) < 1e-6:
            if o['a'] - 0.9 - half < t < o['b'] + 0.9 + half:
                return True
    return False


def wall(sc, lv, r, side, t, model, name, y=0.0, gap=0.02, collide=None, flush=False):
    """Stand (or mount, with y) `model` against wall `side` of room r at position t along it (x for
    n/s walls, z for e/w). `flush`: the model's pivot is its back face (wall fittings)."""
    if model not in B:
        print(f'dress: {model} not built, skipped')
        return None
    nx, nz, yaw = SIDES[side]
    w, _, d = size(model)
    if blocked(lv, r, side, t, w / 2):
        COUNT['skipped'] += 1
        return None
    off = T + gap + (0 if flush else d / 2)
    if side in ('n', 's'):
        x, z = t, (r.z0 if side == 'n' else r.z1) + nz * off
    else:
        x, z = (r.x0 if side == 'w' else r.x1) + nx * off, t
    return put(sc, name, model, x, z, yaw, y, collide)


def safety(sc, lv, r, n, side='s', at=None):
    """Extinguisher with the fire alarm above it, near a room's entrance wall."""
    span = (r.x0, r.x1) if side in ('n', 's') else (r.z0, r.z1)
    t = at if at is not None else span[0] + 1.0
    if wall(sc, lv, r, side, t, 'extinguisher', f'{n} Extinguisher', y=0.0):
        wall(sc, lv, r, side, t, 'fire_alarm', f'{n} Fire Alarm', y=1.45, flush=True)


def cctv(sc, r, n, corner='ne'):
    """A camera high in a corner, looking across the room."""
    x = r.x1 - 0.35 if 'e' in corner else r.x0 + 0.35
    z = r.z0 + 0.35 if 'n' in corner else r.z1 - 0.35
    yaw = math.degrees(math.atan2(r.c[0] - x, r.c[1] - z))
    put(sc, f'{n} CCTV', 'cctv', x, z, yaw, y=r.h - 0.45, collide=False)


def runs(sc, lv, r, n, side, every=5.0, model='cable_run', y=None):
    """Service fittings along a wall every few metres (skipping openings).

    'cable_run' walls get electrical boxes (power box, then a utility cabinet), 'pipe_riser' walls get
    utility cabinets at floor level. The Poly Haven modular pipe/cable/duct kits are single short pieces,
    so the long runs stay with the procedural kit pipes in build_facility.
    """
    span = (r.x0, r.x1) if side in ('n', 's') else (r.z0, r.z1)
    t = span[0] + every / 2
    i = 0
    while t < span[1] - 0.6:
        m = 'utility_box' if (model == 'pipe_riser' or i % 2) else 'power_box'
        hy = 0.0 if m == 'utility_box' else 1.45
        wall(sc, lv, r, side, t, m, f'{n} {m} {i}', y=hy, flush=True)
        t += every
        i += 1


def on(sc, name, model, x, z, top, yaw=0.0):
    """Clutter on a work surface whose top is at height `top`."""
    return put(sc, name, model, x, z, yaw, y=top, collide=False)


DESK_TOP = 0.76        # kit desk (build_facility.k_desk)
PH_DESK_TOP = 0.79     # metal_office_desk
BENCH_TOP = 0.92       # kit lab bench


def dress(sc, lv):
    rr = lv.room
    k = lv.key
    for v in COUNT:
        COUNT[v] = 0
    if k == 'op04':
        r = rr['Tunnel']
        runs(sc, lv, r, 'Tunnel W', 'w', 5.0, 'cable_run')
        runs(sc, lv, r, 'Tunnel E', 'e', 7.0, 'pipe_riser', y=0.0)
        wall(sc, lv, r, 'e', 33.0, 'utility_box', 'Tunnel Utility Box', y=0.9, flush=True)
        wall(sc, lv, r, 'w', 41.5, 'security_light', 'Tunnel Security Light', y=2.9, flush=True)
        wall(sc, lv, r, 'w', 36.0, 'hand_truck', 'Tunnel Hand Truck')
        wall(sc, lv, r, 'e', 39.0, 'cardboard_box', 'Tunnel Box A')
        wall(sc, lv, r, 'e', 39.6, 'cardboard_box', 'Tunnel Box B')
        put(sc, 'Tunnel Wet Floor', 'wet_floor_sign', -1.6, 32.5, 20.0)
        cctv(sc, r, 'Tunnel', 'ne')
        r = rr['Reception']
        wall(sc, lv, r, 'n', -7.8, 'potted_plant', 'Reception Plant A')
        wall(sc, lv, r, 'n', 7.8, 'potted_plant', 'Reception Plant B')
        wall(sc, lv, r, 'w', 24.0, 'wall_clock', 'Reception Clock', y=2.3, flush=True)
        wall(sc, lv, r, 'w', 21.0, 'drawer_cabinet', 'Reception Cabinet')
        wall(sc, lv, r, 'e', 23.5, 'trash_can', 'Reception Bin')
        safety(sc, lv, r, 'Reception', 's', at=-7.5)
        on(sc, 'Reception Monitor', 'crt_monitor', -3.2, 23.15, 1.14, 180.0)
        on(sc, 'Reception Clipboard', 'clipboard', -5.0, 23.1, 1.14, 160.0)
        cctv(sc, r, 'Reception', 'nw')
        r = rr['Corridor A']
        safety(sc, lv, r, 'Corridor A', 'w', at=14.5)
        wall(sc, lv, r, 'e', 4.0, 'trash_can', 'Corridor A Bin')
        r = rr['Offices']
        for i, x in enumerate((-18.4, -17.2, -16.0, -12.6, -11.4)):
            wall(sc, lv, r, 'n', x, 'drawer_cabinet', f'Offices Cabinet {i}')
        wall(sc, lv, r, 's', -16.0, 'chalkboard', 'Offices Board')
        wall(sc, lv, r, 's', -7.0, 'wood_cabinet', 'Offices Supply Cabinet')
        wall(sc, lv, r, 'w', 13.5, 'wall_clock', 'Offices Clock', y=2.2, flush=True)
        wall(sc, lv, r, 'w', 4.0, 'trash_can', 'Offices Bin')
        safety(sc, lv, r, 'Offices', 'e', at=13.5)
        # desk clutter: the room was working this week (story bible, Op04)
        clutter = ('binder', 'notepads', 'clipboard', 'stationery', 'desk_lamp', 'binder', 'notepads', 'clipboard')
        n = 0
        for row, z in enumerate((5.0, 9.0, 13.0)):
            for col, x in enumerate((-17.0, -13.0, -9.0, -5.5)):
                if row == 1 and col == 3:
                    continue
                a = clutter[(row * 4 + col) % len(clutter)]
                b = clutter[(row * 4 + col + 3) % len(clutter)]
                on(sc, f'Desk Clutter {n}a', a, x - 0.55, z + 0.12, DESK_TOP, 8.0 * ((n % 3) - 1))
                if (row + col) % 2 == 0:
                    on(sc, f'Desk Clutter {n}b', b, x + 0.5, z + 0.1, DESK_TOP, 175.0 + 6.0 * (n % 4))
                n += 1
        put(sc, 'Offices Boxes A', 'cardboard_box', -3.0, 15.2, 12.0)
        put(sc, 'Offices Boxes B', 'cardboard_box', -3.0, 15.2, -8.0, y=size('cardboard_box')[1] if 'cardboard_box' in B else 0.34)
        cctv(sc, r, 'Offices', 'nw')
        r = rr['Corridor B']
        for i, x in enumerate((-20.0, 8.0)):
            safety(sc, lv, r, f'Corridor B {i}', 'n', at=x)
        wall(sc, lv, r, 's', -18.0, 'trash_can', 'Corridor B Bin')
        wall(sc, lv, r, 's', 19.0, 'tool_cart', 'Corridor B Cart')
        cctv(sc, r, 'Corridor B', 'nw')
        cctv(sc, r, 'Corridor B East', 'se')
        for name, x0 in (('Lab West', -22), ('Lab East', 4)):
            r = rr[name]
            for i, z in enumerate((-19.0, -14.5, -10.0)):
                bx = x0 + 9
                kit = (('microscope', 'multimeter'), ('chemistry_set', 'circuit_board'), ('microscope', 'binder'))[i]
                on(sc, f'{name} Bench {i} A', kit[0], bx - 0.9, z - 0.1, BENCH_TOP, 180.0)
                on(sc, f'{name} Bench {i} B', kit[1], bx + 0.8, z - 0.15, BENCH_TOP, 170.0)
                put(sc, f'{name} Stool {i}', 'stool', bx - 0.3, z - 0.8, 15.0 * i)
            wall(sc, lv, r, 'e', -18.0, 'drawer_cabinet', f'{name} Cabinet A')
            wall(sc, lv, r, 'e', -16.8, 'drawer_cabinet', f'{name} Cabinet B')
            wall(sc, lv, r, 'w', -9.0, 'metal_rack', f'{name} Rack')
            safety(sc, lv, r, name, 'n', at=x0 + 2.0)
            wall(sc, lv, r, 'n', x0 + 14.0, 'trash_can', f'{name} Bin')
            cctv(sc, r, name, 'se')
        r = rr['Switch Room']
        runs(sc, lv, r, 'Switch E', 'e', 3.0, 'cable_run')
        wall(sc, lv, r, 'w', -8.0, 'power_box', 'Switch Power Box A', y=1.3, flush=True)
        wall(sc, lv, r, 'w', -6.6, 'power_box', 'Switch Power Box B', y=1.3, flush=True)
        wall(sc, lv, r, 'w', -1.0, 'utility_box', 'Switch Utility Box', y=0.6, flush=True)
        wall(sc, lv, r, 'e', -6.0, 'tool_chest', 'Switch Tool Chest')
        wall(sc, lv, r, 'e', -2.5, 'ladder', 'Switch Ladder', gap=0.15)
        put(sc, 'Switch Generator', 'generator', 30.6, -0.6, -90.0)
        safety(sc, lv, r, 'Switch', 's', at=25.0)
        r = rr['Corridor C']
        safety(sc, lv, r, 'Corridor C', 'e', at=-10.0)
        runs(sc, lv, r, 'Corridor C', 'w', 6.0, 'cable_run')
        r = rr['Lift Lobby']
        wall(sc, lv, r, 'w', -36.0, 'hand_truck', 'Lobby Hand Truck')
        wall(sc, lv, r, 'e', -38.0, 'plastic_container', 'Lobby Container')
        wall(sc, lv, r, 'e', -35.0, 'jerrycan', 'Lobby Jerrycan')
        put(sc, 'Lobby Wet Floor', 'wet_floor_sign', 3.2, -33.5, -30.0)
        cctv(sc, r, 'Lobby', 'se')
    if k == 'op05':
        r = rr['Lift Shaft']
        runs(sc, lv, r, 'Shaft', 'e', 3.5, 'cable_run')
        r = rr['Antechamber']
        for i, (x, z, yy) in enumerate(((-6.6, 26.5, 90.0), (-6.6, 24.6, 90.0), (6.4, 17.0, -90.0))):
            put(sc, f'Ante Crate {i}', 'military_crate', x, z, yy)
        put(sc, 'Ante Crate Top', 'military_crate', -6.6, 25.5, 85.0, y=size('military_crate')[1] if 'military_crate' in B else 0.36)
        wall(sc, lv, r, 'e', 27.0, 'propane_tank', 'Ante Propane A')
        wall(sc, lv, r, 'e', 26.4, 'propane_tank', 'Ante Propane B')
        wall(sc, lv, r, 'w', 18.0, 'security_light', 'Ante Light W', y=3.4, flush=True)
        wall(sc, lv, r, 'e', 20.0, 'security_light', 'Ante Light E', y=3.4, flush=True)
        safety(sc, lv, r, 'Ante', 's', at=-7.0)
        cctv(sc, r, 'Ante', 'ne')
        r = rr['Bunker Hall']
        runs(sc, lv, r, 'Hall W', 'w', 6.0, 'cable_run')
        runs(sc, lv, r, 'Hall E', 'e', 8.0, 'pipe_riser', y=0.0)
        put(sc, 'Hall Compressor', 'compressor', 11.8, -6.0, -90.0)
        put(sc, 'Hall Generator', 'generator', -12.4, 5.5, 90.0)
        for i, (x, z) in enumerate(((-12.6, -3.4), (-12.6, -4.2), (-11.9, -3.8))):
            put(sc, f'Hall Barrel {i}', 'barrel', x, z, 30.0 * i)
        put(sc, 'Hall Long Crate A', 'long_crate', 4.0, -14.8, 0.0)
        put(sc, 'Hall Long Crate B', 'long_crate', 4.0, -14.8, 4.0, y=size('long_crate')[1] if 'long_crate' in B else 0.42)
        put(sc, 'Hall Cart', 'storage_cart', -9.0, 12.6, 0.0)
        put(sc, 'Hall Searchlight', 'searchlight', -9.0, 12.6, 30.0, y=1.38, collide=False)
        safety(sc, lv, r, 'Hall', 's', at=-12.0)
        cctv(sc, r, 'Hall', 'nw')
        cctv(sc, r, 'Hall SE', 'se')
        r = rr['Dormitory']
        for i, z in enumerate((-4.5, 1.5, 4.5)):
            put(sc, f'Dorm Stool {i}', 'stool', -26.6, z, 20.0 * i)
        wall(sc, lv, r, 'n', -17.0, 'metal_rack', 'Dorm Rack')
        wall(sc, lv, r, 's', -17.0, 'trash_can', 'Dorm Bin')
        put(sc, 'Dorm Medical Box', 'medical_box', -15.2, -7.1, 10.0)
        wall(sc, lv, r, 'e', 6.5, 'wall_lamp', 'Dorm Lamp', y=2.2, flush=True)
        cctv(sc, r, 'Dorm', 'sw')
        r = rr['Stores']
        # the comms room corner where Venn is kept with Brick (story bible, Op05)
        put(sc, 'Comms Desk', 'office_desk', 27.6, -2.0, -90.0)
        on(sc, 'Comms Radio', 'radio_set', 27.6, -1.6, PH_DESK_TOP, -90.0)
        on(sc, 'Comms Laptop', 'laptop', 27.5, -2.7, PH_DESK_TOP, -100.0)
        on(sc, 'Comms Medical', 'medical_box', 27.7, -2.4, PH_DESK_TOP, -80.0)
        put(sc, 'Comms Stool', 'stool', 26.4, -2.0, 0.0)
        wall(sc, lv, r, 'e', 3.0, 'metal_rack', 'Stores Rack A')
        wall(sc, lv, r, 'e', -9.0, 'metal_rack', 'Stores Rack B')
        wall(sc, lv, r, 'n', 26.0, 'plastic_container', 'Stores Container A')
        wall(sc, lv, r, 'n', 27.0, 'plastic_container', 'Stores Container B')
        wall(sc, lv, r, 'n', 28.2, 'jerrycan', 'Stores Jerrycan')
        wall(sc, lv, r, 's', 26.0, 'cement_bag', 'Stores Cement A')
        wall(sc, lv, r, 's', 27.0, 'cement_bag', 'Stores Cement B')
        wall(sc, lv, r, 'e', 0.2, 'power_box', 'Stores Power Box', y=1.3, flush=True)
        cctv(sc, r, 'Stores', 'ne')
        r = rr['Stairwell']
        runs(sc, lv, r, 'Stairwell', 'w', 4.0, 'cable_run')
        safety(sc, lv, r, 'Stairwell', 'e', at=-18.0)
    if k == 'op06':
        r = rr['Stair Foot']
        safety(sc, lv, r, 'Stair Foot', 'w', at=40.0)
        runs(sc, lv, r, 'Stair Foot', 'e', 3.0, 'cable_run')
        r = rr['Archive']
        runs(sc, lv, r, 'Archive W', 'w', 7.0, 'cable_run')
        for i, z in enumerate((30.0, 18.0, 6.0, -6.0)):
            wall(sc, lv, r, 'e', z, 'record_cabinet', f'Archive Cabinet {i}')
        for i, x in enumerate((-22.0, -14.0, 14.0, 22.0)):
            wall(sc, lv, r, 'n', x, 'drawer_cabinet', f'Archive Drawer {i}')
        # work left mid-task at the row ends: ladders, carts and boxes
        for i, (x, z, yy) in enumerate(((-18.0, 29.3, 0.0), (10.0, 17.3, 0.0), (-6.0, 5.3, 0.0))):
            put(sc, f'Archive Ladder {i}', 'ladder', x, z, yy)
        for i, (x, z) in enumerate(((-1.6, 18.0), (1.6, 6.0))):
            put(sc, f'Archive Cart {i}', 'storage_cart', x, z, 90.0)
        for i, (x, z) in enumerate(((-26.0, 31.6), (-25.5, 31.6), (26.0, -8.0), (25.4, -8.2), (6.0, 31.6))):
            put(sc, f'Archive Box {i}', 'cardboard_box', x, z, 25.0 * i)
        wall(sc, lv, r, 's', -20.0, 'wall_clock', 'Archive Clock', y=3.4, flush=True)
        safety(sc, lv, r, 'Archive', 's', at=-26.0)
        safety(sc, lv, r, 'Archive E', 's', at=26.0)
        cctv(sc, r, 'Archive', 'nw')
        cctv(sc, r, 'Archive SE', 'se')
        r = rr['Pump Room']
        runs(sc, lv, r, 'Pump W', 'w', 4.0, 'pipe_riser', y=0.0)
        wall(sc, lv, r, 'n', -36.0, 'tool_chest', 'Pump Tool Chest')
        for i, x in enumerate((-42.5, -41.8)):
            wall(sc, lv, r, 's', x, 'barrel', f'Pump Barrel {i}')
        wall(sc, lv, r, 's', -34.0, 'jerrycan', 'Pump Jerrycan')
        put(sc, 'Pump Wet Floor', 'wet_floor_sign', -35.5, 10.0, 60.0)
        wall(sc, lv, r, 'n', -40.0, 'utility_box', 'Pump Utility Box', y=0.8, flush=True)
        r = rr['Manager Office']
        # the Source Vault: originals, the audit trail and the contract (story bible, Op06)
        wall(sc, lv, r, 'e', 12.0, 'record_cabinet', 'Vault Cabinet')
        wall(sc, lv, r, 'n', 33.0, 'drawer_cabinet', 'Vault Drawer A')
        wall(sc, lv, r, 'n', 34.2, 'drawer_cabinet', 'Vault Drawer B')
        on(sc, 'Vault Binder A', 'binder', 35.6, 13.25, DESK_TOP, 5.0)
        on(sc, 'Vault Binder B', 'binder', 35.6, 13.25, DESK_TOP + 0.03, -7.0)
        on(sc, 'Vault Clipboard', 'clipboard', 36.4, 13.1, DESK_TOP, 170.0)
        on(sc, 'Vault Lamp', 'desk_lamp', 36.6, 13.3, DESK_TOP, 200.0)
        wall(sc, lv, r, 'w', 20.0, 'wall_clock', 'Vault Clock', y=2.2, flush=True)
        cctv(sc, r, 'Vault', 'se')
        r = rr['North Corridor']
        runs(sc, lv, r, 'North', 'e', 4.0, 'cable_run')
        safety(sc, lv, r, 'North', 'w', at=-14.0)
        r = rr['Chamber Antechamber']
        wall(sc, lv, r, 's', -10.0, 'potted_plant', 'Ante Plant A')
        wall(sc, lv, r, 's', 10.0, 'potted_plant', 'Ante Plant B')
        wall(sc, lv, r, 'w', -37.0, 'projector_screen', 'Ante Screen')
        safety(sc, lv, r, 'Ante', 'e', at=-33.0)
        cctv(sc, r, 'Ante', 'nw')
    if k == 'op07':
        r = rr['Chamber Antechamber']
        wall(sc, lv, r, 's', -4.5, 'potted_plant', 'Ante Plant')
        safety(sc, lv, r, 'Ante', 'w', at=20.0)
        r = rr['Trial Chamber']
        # the review room's workstations along the east wall (story bible, Op07: workstations,
        # an old chair and the inert V-01 dummy; nothing moves, nothing speaks)
        for i, z in enumerate((-9.0, -5.0, -1.0)):
            d = wall(sc, lv, r, 'e', z, 'office_desk', f'Workstation {i}')
            if d:
                x = r.x1 - T - 0.02 - size('office_desk')[2] / 2
                on(sc, f'Workstation {i} Monitor', 'crt_monitor', x + 0.15, z - 0.4, PH_DESK_TOP, -90.0)
                on(sc, f'Workstation {i} Notes', ('notepads', 'binder', 'clipboard')[i], x - 0.15, z + 0.45, PH_DESK_TOP, -80.0)
                put(sc, f'Workstation {i} Stool', 'stool', x - 0.95, z, 10.0 * i)
        on(sc, 'Observation Laptop', 'laptop', 7.4, 8.05, DESK_TOP, 180.0)
        on(sc, 'Observation Lamp', 'desk_lamp', 8.6, 8.15, DESK_TOP, 200.0)
        wall(sc, lv, r, 'w', 4.0, 'chalkboard', 'Review Board')
        wall(sc, lv, r, 'n', 6.0, 'projector_screen', 'Review Screen')
        wall(sc, lv, r, 'w', -12.0, 'wall_clock', 'Review Clock', y=3.2, flush=True)
        wall(sc, lv, r, 's', -9.0, 'cardboard_box', 'Review Box A')
        wall(sc, lv, r, 's', -8.4, 'cardboard_box', 'Review Box B')
        wall(sc, lv, r, 'n', -9.0, 'potted_plant', 'Review Plant')
        safety(sc, lv, r, 'Review', 's', at=-10.0)
        for c in ('nw', 'ne', 'sw', 'se'):
            cctv(sc, r, f'Review {c.upper()}', c)
    print(f'dress {k}: {COUNT["props"]} props, {COUNT["tris"]} triangles, {COUNT["skipped"]} skipped at openings')
