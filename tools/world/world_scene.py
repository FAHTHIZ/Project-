# SPDX-License-Identifier: Apache-2.0
"""Kestrel Valley scene builder (called by worldgen.py). See docs/world/KESTREL_VALLEY.md.

Writes game/scenes/world/kestrel.vscene (all props in place), then runs `victus world` to move
props into 64 m streaming cells, then derives the viewpoint test scenes from the streamed scene
(same cells, different player start + Autotest plan)."""
from __future__ import annotations

import copy
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np

import worldmap as M
import terrain_gen as T
import worldgen as WG

import vscene as V
from vscene import Scene, transform, collider, body, mesh_renderer, script, meta_uuid, quat_euler
import common
import rig
import vehicle

ROOT = WG.ROOT
GAME = ROOT / 'game'
SCENE_REL = 'scenes/world/kestrel.vscene'
WORLD_OUT = 'worlds/kestrel'

ENV = 'models/env/'

# Viewpoints for the world evidence plans: name -> (x, z, yaw of the body, look target x, y, z)
VIEWS = {
    'world_trailhead': dict(pos=(-50, 296), look=(-20, None, 250)),
    'world_forest':    dict(pos=(30, 176), look=(48, None, 150)),
    'world_creek':     dict(pos=(4, 207), look=(40, None, 204)),
    'world_relay':     dict(pos=(-30, 34), look=(-42, None, 16)),
    'world_ravine':    dict(pos=(-24, -26), look=(4, None, -96)),
    'world_saddle':    dict(pos=(0, -190), look=(30, 72, -380)),
    'world_vista':     dict(pos=(-42, 20), look=(40, 60, -260)),
}


def ground(H, x, z):
    return float(T.sample_grid(H, [x], [z])[0])


def add_terrain(sc, H):
    tex = {k: meta_uuid(f'textures/terrain/{k}.png') for k in ('forest', 'rock', 'path', 'meadow')}
    terr = sc.add('Kestrel Terrain', {
        'Transform': transform((0, 0, 0)),
        'Terrain': {
            'data': meta_uuid(WG.TERRAIN_REL), 'size': [M.SIZE, M.HEIGHT, M.SIZE],
            # tiling = repeats across the whole terrain: forest floor 4 m, rock 6 m, path 3 m, meadow 4 m
            'layer0_texture': tex['forest'], 'layer0_tint': [1, 1, 1, 1], 'layer0_tiling': M.SIZE / 4.0,
            'layer1_texture': tex['rock'], 'layer1_tint': [1, 1, 1, 1], 'layer1_tiling': M.SIZE / 6.0,
            'layer2_texture': tex['path'], 'layer2_tint': [1, 1, 1, 1], 'layer2_tiling': M.SIZE / 3.0,
            'layer3_texture': tex['meadow'], 'layer3_tint': [1, 1, 1, 1], 'layer3_tiling': M.SIZE / 4.0,
            'roughness': 0.92, 'cast_shadows': True, 'collision': True, 'friction': 0.9,
            'collision_layer': 0, 'collision_mask': 65535,
        },
        'Tags': {'tags': 'Ground Terrain'},
    })
    # Ground cover scatter: GPU-instanced, culled per chunk and by draw distance. The splat layer
    # gates density (ferns on forest floor, grass on meadow and path verges, shrubs on both).
    def foliage(name, rel, layer, density, smin, smax, dist, seed, max_slope=32, min_w=0.35, offset=-0.03,
                shadows=False, align=0.6, maxi=400000):
        f = sc.add(name, {
            'Foliage': {'layer': layer, 'min_weight': min_w, 'density': density, 'min_scale': smin,
                        'max_scale': smax, 'align_to_normal': align, 'random_yaw': True, 'max_slope': max_slope,
                        'min_height': 0.0, 'max_height': 1.0, 'offset': offset, 'draw_distance': dist,
                        'seed': seed, 'max_instances': maxi},
            'MeshRenderer': mesh_renderer(mesh=meta_uuid(rel), mesh_index=0, shadows=shadows, roughness=0.85),
        }, terr)
        return f
    foliage('Ferns A', ENV + 'fern_a.glb', 0, 0.16, 0.8, 1.35, 45, 11)
    foliage('Ferns B', ENV + 'fern_b.glb', 0, 0.12, 0.8, 1.3, 45, 12)
    foliage('Ferns Hero', ENV + 'fern_hero.glb', 0, 0.012, 0.8, 1.2, 60, 13, min_w=0.6)
    foliage('Grass A', ENV + 'grass_a.glb', 3, 0.9, 0.8, 1.5, 38, 21, max_slope=38, min_w=0.3, align=0.8)
    foliage('Grass B', ENV + 'grass_b.glb', 3, 0.7, 0.8, 1.4, 32, 22, max_slope=38, min_w=0.3, align=0.8)
    foliage('Grass Verge', ENV + 'grass_a.glb', 0, 0.12, 0.7, 1.2, 30, 23, min_w=0.15)
    foliage('Shrubs A', ENV + 'shrub_a.glb', 0, 0.022, 0.8, 1.4, 90, 31, min_w=0.5, shadows=True, align=0.2)
    foliage('Shrubs B', ENV + 'shrub_b.glb', 3, 0.006, 0.7, 1.2, 110, 32, min_w=0.5, shadows=True, align=0.2)
    return terr


def tree_collider(t):
    d = WG.TREES[t['type']]
    return collider('capsule', radius=d['trunk'], height=3.2, offset=(0, 1.6, 0))


def add_vegetation(sc, H, masks, cover, trees):
    n = 0
    for i, t in enumerate(trees):
        if t['region'] != 'inner':
            continue
        d = WG.TREES[t['type']]
        sc.prop(f'Tree {i}', d['rel'], (t['x'], t['y'], t['z']), t['yaw'], t['scale'], col=tree_collider(t),
                tags='Tree')
        n += 1
    for i, r in enumerate(WG.place_rocks(H, masks, cover)):
        rot = quat_euler(r['tilt'], r['yaw'], r['tilt'] * 0.6)
        sc.prop(f'Rock {i}', ENV + r['type'] + '.glb', (r['x'], r['y'], r['z']), rot=rot, scale=r['scale'],
                col=collider('sphere', radius=0.55, offset=(0, 0.25, 0)) if r['scale'] > 1.0 else None, tags='Rock')
    for i, w in enumerate(WG.place_deadwood(H, masks, cover)):
        c = collider('box', (4.2, 0.6, 0.6), offset=(0, 0.3, 0)) if w['type'] == 'log_a' else \
            collider('cylinder', radius=0.42, height=0.55, offset=(0, 0.27, 0))
        sc.prop(f'Deadwood {i}', ENV + w['type'] + '.glb', (w['x'], w['y'], w['z']), w['yaw'], w['scale'], col=c)
    return n


def add_canopy(sc):
    """Canopy proxies stay resident (the root holds a Script, which keeps the subtree out of the
    streamed cells). Near blocks are tagged with their streaming cell; canopy.luau hides a near
    block while that cell's detailed trees are loaded, so a tree is never drawn twice."""
    root = sc.add('Canopy', {'Script': script('scripts/world/canopy.luau', cell_size=WG.CELL)})
    blocks = json.loads((WG.ASSETS / WG.CANOPY_DIR / 'canopy_blocks.json').read_text())
    for b in blocks:
        tags = f"Canopy CanopyNear Cell_{b['i']}_{b['j']}" if b['kind'] == 'near' else 'Canopy CanopyFar'
        sc.prop(f"Canopy {b['kind']} {b['i']} {b['j']}", f"{WG.CANOPY_DIR}/{b['file']}", (b['x'], 0, b['z']),
                parent=root, shadows=False, tags=tags)
    return root


def along(spline, every, start=0.0):
    """(x, z, heading deg) at fixed arc-length steps."""
    out = []
    s = spline.s
    for d in np.arange(start, s[-1], every):
        i = int(np.searchsorted(s, d))
        i = min(max(i, 1), len(s) - 1)
        p0, p1 = spline.p[i - 1], spline.p[i]
        hd = math.degrees(math.atan2(p1[0] - p0[0], p1[1] - p0[1]))
        out.append((float(p1[0]), float(p1[1]), hd))
    return out


def add_routes(sc, H, masks):
    trail = masks['splines']['trail']
    best = None
    for i, (x, z, hd) in enumerate(along(trail, 34.0, 20.0)):
        d = math.hypot(x - 40.0, z - 166.0)
        if best is None or d < best[0]:
            best = (d, x, z)
        # marker post at the trail edge, alternating sides
        side = 1 if i % 2 else -1
        ox = math.cos(math.radians(hd)) * side * 1.6
        oz = -math.sin(math.radians(hd)) * side * 1.6
        sc.prop(f'Trail Marker {i}', ENV + 'trail_marker.glb', (x + ox, ground(H, x + ox, z + oz) - 0.05, z + oz),
                hd, 1.0, col=collider('box', (0.14, 1.2, 0.14), offset=(0, 0.6, 0)))
    # the post Echo notices (first marker past the footbridge, arrows scratched off)
    POINTS['trail_marker'] = (best[1], ground(H, best[1], best[2]), best[2])
    s0 = trail.p[int(np.searchsorted(trail.s, 6.0))]
    POINTS['trail_start'] = (float(s0[0]), ground(H, float(s0[0]), float(s0[1])), float(s0[1]))
    end = trail.p[-1]
    POINTS['fence_approach'] = (float(end[0]), ground(H, float(end[0]), float(end[1])), float(end[1]))
    # trailhead sign beside the turnout, facing the parking area
    tx, tz = M.TRAIL[0]
    sc.prop('Trailhead Sign', ENV + 'trail_sign.glb', (tx + 2.5, ground(H, tx + 2.5, tz + 2.0), tz + 2.0), 200.0,
            1.0, col=collider('box', (1.3, 1.5, 0.15), offset=(0, 0.75, 0)), tags='Sign')
    # Footbridge over the creek where the trail crosses (timber deck on two stringers)
    (bx, bz), _ = M.FOOTBRIDGE
    i = int(trail.tree.query([bx, bz])[1])
    p0, p1 = trail.p[max(0, i - 3)], trail.p[min(len(trail.p) - 1, i + 3)]
    hd = math.degrees(math.atan2(p1[0] - p0[0], p1[1] - p0[1]))
    bank = max(ground(H, *trail.p[max(0, i - 8)]), ground(H, *trail.p[min(len(trail.p) - 1, i + 8)]))
    deck_y = bank + 0.15
    br = sc.add('Footbridge', {'Transform': transform((bx, deck_y, bz), yaw=hd), 'Tags': {'tags': 'Bridge'}})
    wood = (0.36, 0.27, 0.18)
    sc.box('Footbridge Deck', (0, 0, 0), (1.6, 0.12, 9.0), wood, parent=br, roughness=0.9)
    for sx in (-0.7, 0.7):
        sc.box(f'Footbridge Stringer {sx}', (sx, -0.2, 0), (0.18, 0.3, 9.4), (0.28, 0.2, 0.14), parent=br,
               collide=False)
        for k, zz in enumerate((-4.2, -1.4, 1.4, 4.2)):
            sc.box(f'Footbridge Post {sx} {k}', (sx * 1.05, 0.5, zz), (0.1, 1.0, 0.1), wood, parent=br)
        sc.box(f'Footbridge Rail {sx}', (sx * 1.05, 0.95, 0), (0.08, 0.08, 9.0), wood, parent=br, collide=False)
    return br


def add_creek(sc, H, masks):
    """Step-pool creek: one flat Water volume per pool (terrain_gen.step_pools) and a riffle of
    stones across each step. Pools stream with their cells; the tier keeps the nearest 4-16."""
    pools = masks['creek_pools']
    rng = np.random.default_rng(7301)
    half = M.CREEK_WIDTH / 2 + 1.6
    for i, p in enumerate(pools):
        if not p.get('wet', True):
            continue
        cx, cz = 0.5 * (p['wx0'] + p['x1']), 0.5 * (p['z0'] + p['z1'])
        sx, sz = p['x1'] - p['wx0'], (p['z1'] - p['z0']) + 2 * half
        sc.add(f'Creek Pool {i}', {
            'Transform': transform((cx, p['level'], cz)),
            'Water': {'size': [sx, sz], 'shallow_color': [0.42, 0.46, 0.36, 1], 'deep_color': [0.05, 0.08, 0.06, 1],
                      'clarity': 1.4, 'wave_height': 0.012, 'wavelength': 0.7, 'wave_direction': 180.0,
                      'steepness': 0.25, 'wave_speed': 1.0, 'foam': 0.04, 'refraction': 0.03, 'roughness': 0.06,
                      'resolution': 24, 'current': [-0.45, 0.0]},
            'Tags': {'tags': 'Water Creek'},
        })
        # riffle: stones across the step at the downstream edge of this pool
        if i > 0:
            creek = masks['splines']['creek']
            k = int(np.argmin(np.abs(creek.p[:, 0] - (p['x0'] + 2.0))))
            bx, bz = creek.p[k]
            for j in range(4):
                ox = rng.uniform(-0.8, 0.4)
                oz = rng.uniform(-1.6, 1.6)
                sc.prop(f'Riffle Stone {i} {j}', ENV + ['rock_a', 'rock_b', 'rock_c'][j % 3] + '.glb',
                        (bx + ox, p['level'] - 0.18, bz + oz), float(rng.uniform(0, 360)), float(rng.uniform(0.45, 0.8)))
    return len(pools)


def add_trailhead(sc, H):
    p = M.POIS['trailhead']
    x, z = p['x'] + 4, p['z'] + 4
    y = ground(H, x, z)
    road = WG.ROOT  # noqa: F841 (documentation: Mule parks along the turnout facing the trail)
    vehicle.add_vehicle(sc, 'Mule', (x, y + 0.02, z), 150.0, cargo=['marksman', 'field_kit', 'cell_pack', 'cell_pack'])
    POINTS['mule_park'] = (x, y + 0.02, z)
    return (x, y, z)


STRUCT = 'models/structures/'
_LAYOUT = None


def struct_layout():
    global _LAYOUT
    if _LAYOUT is None:
        _LAYOUT = json.loads((ROOT / 'tools' / 'props' / 'structures_layout.json').read_text())
    return _LAYOUT


def place(sc, name, model, x, z, yaw, H=None, y=None, sink=0.05, tags=None, extra=None):
    """Structure prop from tools/props/build_structures.py with its static box colliders as
    children (the layout lists centre, half extents and yaw in the model frame)."""
    if y is None:
        # rest on the lowest ground under the footprint corners so nothing floats
        lay = struct_layout()[model]
        hs = [ground(H, x, z)]
        for c in lay['colliders'][:6]:
            hs.append(ground(H, x + c['c'][0] * math.cos(math.radians(yaw)) + c['c'][2] * math.sin(math.radians(yaw)),
                             z - c['c'][0] * math.sin(math.radians(yaw)) + c['c'][2] * math.cos(math.radians(yaw))))
        y = min(hs) - sink
    root = sc.prop(name, STRUCT + model + '.glb', (x, y, z), yaw, tags=tags, extra=extra)
    PLACED[name] = (model, x, y, z, yaw)
    for k, c in enumerate(struct_layout()[model]['colliders']):
        sc.add(f'{name} Collider {k}', {'Transform': transform(tuple(c['c']), yaw=c['yaw']),
                                        'Collider': collider('box', tuple(2 * v for v in c['h'])),
                                        'RigidBody': body('static')}, root)
    return root, y


def anchor_world(model, key, x, y, z, yaw):
    """World position and yaw of a layout anchor for a structure placed at (x, y, z, yaw)."""
    a = struct_layout()[model]['anchors'][key]
    px, py, pz = a['p']
    r = math.radians(yaw)
    return (x + px * math.cos(r) + pz * math.sin(r), y + py, z - px * math.sin(r) + pz * math.cos(r)), yaw + a['yaw']


# Where the mission scripts find things (written to scripts/world/kestrel_points.luau).
POINTS = {}
# Structures placed by add_structures: name -> (model, x, y, z, yaw), for lights added later.
PLACED = {}


def add_structures(sc, H, masks):
    """Staging camp, Hollis's cabin, the relay knoll, the perimeter fence with gate and towers,
    the compound yard and the facility portal (docs/world/KESTREL_VALLEY.md)."""
    # Prologue staging camp: two tents, briefing table, crates, generator, floodlights
    c = M.POIS['camp']
    cx, cz = c['x'], c['z']
    _, ty = place(sc, 'Camp Tent A', 'camp_tent', cx + 6, cz - 4, -110.0, H)
    place(sc, 'Camp Tent B', 'camp_tent', cx + 7, cz + 5, -70.0, H)
    _, by = place(sc, 'Camp Table', 'camp_table', cx - 1, cz, 75.0, H)
    place(sc, 'Camp Crates', 'supply_crates', cx + 1, cz - 6, 20.0, H)
    place(sc, 'Camp Generator', 'generator', cx + 10, cz + 1, 80.0, H)
    place(sc, 'Camp Flood A', 'floodlight', cx - 5, cz - 4, 60.0, H)
    place(sc, 'Camp Flood B', 'floodlight', cx + 2, cz + 7, 200.0, H)
    POINTS['camp_table'] = (cx - 1, by, cz)
    # where the Mule waits on the ranger road beside the camp (prologue start), nose south
    rd = masks['splines']['road_in']
    k = int(rd.tree.query([cx - 18.0, cz - 4.0])[1])
    mx, mz = float(rd.p[k, 0]), float(rd.p[k, 1])
    POINTS['mule_camp'] = (mx, ground(H, mx, mz) + 0.02, mz)
    # Hollis's cabin on the east side of the trail, porch facing the path (west)
    _, cy = place(sc, 'Ranger Cabin', 'ranger_cabin', 71.0, 122.0, 90.0, H, sink=0.25)
    for key in ('door_out', 'porch', 'inside', 'table', 'lamp'):
        POINTS['cabin_' + key] = anchor_world('ranger_cabin', key, 71.0, cy, 122.0, 90.0)[0]
    lamp = POINTS['cabin_lamp']
    sc.add('Cabin Lamp Light', {'Transform': transform(lamp), 'Light': {
        'type': 'point', 'color': [1.0, 0.72, 0.42], 'intensity': 6.0, 'range': 7.0, 'shadows': False}})
    place(sc, 'Cabin Crates', 'supply_crates', 66.5, 128.5, 10.0, H)
    # Greyline relay on the knoll west of the trail
    _, ry = place(sc, 'Relay Mast', 'relay_mast', -50.0, 14.0, 70.0, H, sink=0.1, tags='Relay Scannable')
    POINTS['relay_bay'] = anchor_world('relay_mast', 'cell_bay', -50.0, ry, 14.0, 70.0)[0]
    POINTS['relay_stand'] = anchor_world('relay_mast', 'stand', -50.0, ry, 14.0, 70.0)[0]
    place(sc, 'Relay Generator', 'generator', -46.5, 10.5, 20.0, H)
    # Perimeter fence along the cleared strip, with a gap for the gate on the service road
    fence = masks['splines']['fence']
    gx, gz = M.POIS['gate']['x'], M.POIS['gate']['z']
    n = 0
    for (x, z, hd) in along(fence, 4.07, 2.0):
        if math.hypot(x - gx, z - gz) < 7.5:
            continue
        sc.prop(f'Fence {n}', ENV + 'fence_panel.glb', (x, ground(H, x, z) - 0.15, z), hd - 90.0,
                col=collider('box', (4.07, 2.45, 0.1), offset=(0, 1.2, 0)))
        n += 1
    # gate: two sliding leaves (closed) across the road, guard booth inside, towers, sign, lights
    gy = ground(H, gx, gz)
    for s, nm in ((-1, 'Gate Leaf West'), (1, 'Gate Leaf East')):
        place(sc, nm, 'gate_leaf', gx + s * 0.05, gz, 0.0 if s > 0 else 180.0, y=gy - 0.02, tags='Gate')
    place(sc, 'Gate Booth', 'gate_booth', gx + 9.0, gz - 7.0, 0.0, H, tags='Booth')
    place(sc, 'Gate Sign', 'warning_sign', gx - 9.0, gz + 3.0, 0.0, H)
    place(sc, 'Gate Barrier A', 'jersey_barrier', gx - 4.5, gz + 6.5, 8.0, H)
    place(sc, 'Gate Barrier B', 'jersey_barrier', gx + 5.0, gz + 7.5, -12.0, H)
    place(sc, 'Gate Light', 'light_pole', gx + 6.5, gz - 1.5, 160.0, H)
    POINTS['gate'] = (gx, gy, gz)
    POINTS['booth_panel'] = anchor_world('gate_booth', 'inside', gx + 9.0, ground(H, gx + 9.0, gz - 7.0), gz - 7.0, 0.0)[0]
    for i, (x, z) in enumerate(((-120.0, -347.0), (140.0, -343.0), (-40.0, -348.0))):
        _, wy = place(sc, f'Watchtower {i}', 'watchtower', x, z, 0.0, H, sink=0.2, tags='Watchtower')
        POINTS[f'tower_{i}'] = anchor_world('watchtower', 'deck', x, wy, z, 0.0)[0]
    for i, x in enumerate(np.arange(-200.0, 210.0, 64.0)):
        z = float(np.interp(x, [p[0] for p in M.FENCE], [p[1] for p in M.FENCE])) + 18.0
        if abs(x - gx) < 20:
            continue
        sc.prop(f'Fence Sign {i}', STRUCT + 'warning_sign.glb', (x, ground(H, x, z - 17.0) - 0.05, z - 17.0), 0.0, 0.6,
                col=collider('box', (1.1, 1.2, 0.08), offset=(0, 0.6, 0)))
    # compound yard on its pad (h = COMPOUND h): office, garage, containers, lights
    cy0 = M.COMPOUND['h']
    _, oy = place(sc, 'Site Office', 'site_office', 30.0, -372.0, 0.0, y=cy0 - 0.05, tags='Office')
    POINTS['office_door'] = anchor_world('site_office', 'door', 30.0, oy, -372.0, 0.0)[0]
    POINTS['office_desk'] = anchor_world('site_office', 'desk', 30.0, oy, -372.0, 0.0)[0]
    place(sc, 'Garage', 'garage', -28.0, -392.0, 0.0, y=cy0 - 0.05, tags='Garage')
    for i, (x, z, yw) in enumerate(((60.0, -392.0, 90.0), (64.0, -392.0, 88.0), (-62.0, -370.0, 15.0),
                                    (-6.0, -414.0, 0.0))):
        place(sc, f'Container {i}', 'container', x, z, yw, y=cy0 - 0.02)
    for i, (x, z) in enumerate(((-6.0, -362.0), (48.0, -404.0), (-44.0, -414.0), (18.0, -430.0))):
        place(sc, f'Yard Light {i}', 'light_pole', x, z, 30.0 * i, y=cy0 - 0.05)
    for i, (x, z, yw) in enumerate(((8.0, -380.0, 90.0), (8.0, -386.5, 90.0), (-14.0, -404.0, 0.0))):
        place(sc, f'Yard Barrier {i}', 'jersey_barrier', x, z, yw, y=cy0 - 0.02)
    # facility portal: frame faces the yard (south), tunnel runs north into the mountain
    fx, fz = M.POIS['facility']['x'], M.POIS['facility']['z']
    _, fy = place(sc, 'Facility Portal', 'facility_portal', fx, fz, 180.0, y=ground(H, fx, fz) - 0.02, tags='Facility')
    POINTS['facility_door'] = anchor_world('facility_portal', 'door', fx, fy, fz, 180.0)[0]
    POINTS['facility_front'] = anchor_world('facility_portal', 'front', fx, fy, fz, 180.0)[0]
    POINTS['facility_panel'] = anchor_world('facility_portal', 'panel', fx, fy, fz, 180.0)[0]
    # culvert where the service road crosses the creek
    rs = masks['splines']['road_sv']
    cr = masks['splines']['creek']
    d = np.hypot(rs.p[:, None, 0] - cr.p[None, :, 0], rs.p[:, None, 1] - cr.p[None, :, 1])
    i, j = np.unravel_index(int(d.argmin()), d.shape)
    if d[i, j] < 6:
        px, pz = float(rs.p[i, 0]), float(rs.p[i, 1])
        p0, p1 = rs.p[max(0, i - 3)], rs.p[min(len(rs.p) - 1, i + 3)]
        hd = math.degrees(math.atan2(p1[0] - p0[0], p1[1] - p0[1]))
        place(sc, 'Road Culvert', 'culvert', px, pz, hd + 90.0, y=ground(H, px, pz) - 1.25)
    for k in ('trailhead', 'cabin', 'relay', 'ravine', 'saddle', 'gate', 'compound', 'facility', 'camp'):
        p = M.POIS[k]
        POINTS.setdefault('poi_' + k, (p['x'], ground(H, p['x'], p['z']), p['z']))
    return n


def write_points(H, masks):
    trail = masks['splines']['trail']
    lines = ['-- Generated by tools/world/world_scene.py: Kestrel Valley mission points (world metres).',
             'local v = vector.create', 'return {']
    for k, (x, y, z) in sorted(POINTS.items()):
        lines.append(f'    {k} = v({x:.2f}, {y:.2f}, {z:.2f}),')
    # the footpath as a polyline (every 6 m) for squad leads and mission triggers
    pts = along(trail, 6.0)
    lines.append('    trail = {')
    for (x, z, _) in pts:
        lines.append(f'        v({x:.1f}, {ground(H, x, z):.2f}, {z:.1f}),')
    lines.append('    },')
    for name, key in (('road_in', 'road_in'), ('road_service', 'road_sv')):
        sp = masks['splines'][key]
        lines.append(f'    {name} = {{')
        for (x, z, _) in along(sp, 8.0):
            lines.append(f'        v({x:.1f}, {ground(H, x, z):.2f}, {z:.1f}),')
        lines.append('    },')
    lines += ['}', '']
    (GAME / 'assets' / 'scripts' / 'world' / 'kestrel_points.luau').write_text('\n'.join(lines))


def build_main(H, masks, cover, trees):
    sc = Scene('Kestrel Valley')
    common.environment(sc, 'forest', fog_density=0.0035, fog_start=60, fog_end=900, fog_max_opacity=0.75,
                       shadow_distance=60, fog_color=[0.63, 0.69, 0.72, 1], sky_horizon=[0.7, 0.76, 0.79, 1],
                       # under a closed canopy most light is diffuse skylight through gaps plus bounce
                       # from the foliage; the hemisphere ambient carries that, so shaded forest reads
                       # as dim green rather than black (no darkness used to hide the scene)
                       ambient_intensity=0.85, ground=[0.2, 0.22, 0.14, 1])
    common.sun(sc, pitch=-38, yaw=-35, intensity=3.4)
    add_terrain(sc, H)
    add_canopy(sc)
    n_trees = add_vegetation(sc, H, masks, cover, trees)
    add_routes(sc, H, masks)
    add_creek(sc, H, masks)
    add_trailhead(sc, H)
    add_structures(sc, H, masks)
    write_points(H, masks)
    sc.add('Open World', {'Transform': transform(), 'Tags': {'tags': 'OpenWorld'}})
    tx, tz = M.TRAIL[0]
    start = (tx - 3.0, ground(H, tx - 3.0, tz + 3.0) + 0.05, tz + 3.0)
    rig.add_player(sc, start, 20.0, with_weapons=True, far=1500,
                   extra={'StreamingSource': {'radius_scale': 1.0}})
    rig.add_hud(sc)
    sc.save(SCENE_REL)
    return sc, n_trees


def stream():
    env = dict(os.environ)
    env['PATH'] = str(Path.home() / '.local/bin') + ':' + env['PATH']
    out = GAME / WORLD_OUT
    if out.exists():
        import shutil
        shutil.rmtree(out)
    subprocess.check_call(['victus', 'world', 'game', '--scene', SCENE_REL, '--out', WORLD_OUT, '--cell-size', '64'],
                          cwd=str(ROOT), env=env)


def _lua(v):
    if isinstance(v, dict):
        return '{ ' + ', '.join(f'{k} = {_lua(x)}' for k, x in v.items()) + ' }'
    if isinstance(v, (list, tuple)):
        return '{ ' + ', '.join(_lua(x) for x in v) + ' }'
    if isinstance(v, float):
        return f'{v:.2f}'
    return str(v)


def derive_views(H, masks, trees):
    src = json.loads((GAME / SCENE_REL).read_text())
    inner = np.array([(t['x'], t['z']) for t in trees if t['region'] == 'inner'])
    data = {}
    views = dict(VIEWS)
    views['world_trail_walk'] = None
    for name, v in views.items():
        if v is None:
            doc = copy.deepcopy(src)
            doc['name'] = f'Test {name}'
            doc['entities'].append({'uuid': V.uid(f'{name}/Autotest'), 'name': 'Autotest', 'components': {
                'Transform': transform(), 'Script': script('scripts/autotest.luau', plan=name)}})
            (GAME / 'scenes' / 'tests' / f'{name}.vscene').write_text(json.dumps(doc, indent=1) + '\n')
            continue
        doc = copy.deepcopy(src)
        doc['name'] = f'Test {name}'
        x, z = v['pos']
        if v.get('snap', True):
            # Viewpoints stand on the trail centreline when they are near it: the tree scatter keeps
            # only the tread clear, so a point 2 m off the line can sit against a trunk.
            tp = masks['splines']['trail'].p
            dd = np.hypot(tp[:, 0] - x, tp[:, 1] - z)
            k = int(dd.argmin())
            if dd[k] < 8.0:
                x, z = float(tp[k, 0]), float(tp[k, 1])
        lx, ly, lz = v['look']
        y = ground(H, x, z)
        if ly is None:
            ly = ground(H, lx, lz) + 1.6
        yaw = math.degrees(math.atan2(-(lx - x), -(lz - z)))
        for e in doc['entities']:
            if e['name'] == 'Player':
                e['components']['Transform'] = transform((x, y + 0.05, z), yaw=yaw)
        doc['entities'].append({'uuid': V.uid(f'{name}/Autotest'), 'name': 'Autotest', 'components': {
            'Transform': transform(), 'Script': script('scripts/autotest.luau', plan=name)}})
        p = GAME / 'scenes' / 'tests' / f'{name}.vscene'
        p.write_text(json.dumps(doc, indent=1) + '\n')
        n60 = int((np.hypot(inner[:, 0] - x, inner[:, 1] - z) < 58).sum())
        data[name] = dict(pos=[float(x), y, float(z)], look=[float(lx), float(ly), float(lz)], trees60=n60)
    trail = masks['splines']['trail']
    probe = trail.p[int(np.searchsorted(trail.s, 45.0))]
    blocks = len(json.loads((WG.ASSETS / WG.CANOPY_DIR / 'canopy_blocks.json').read_text()))
    lua = ['-- Generated by tools/world/world_scene.py: Kestrel Valley viewpoints for world_plans.luau.',
           'return {', f'    canopy_blocks = {blocks},', f'    trail_probe = {_lua([float(probe[0]), float(probe[1])])},',
           '    views = {']
    for k, d in data.items():
        lua.append(f'        {k} = {_lua(d)},')
    lua += ['    },', '}', '']
    (GAME / 'assets' / 'scripts' / 'tests' / 'world_views.luau').write_text('\n'.join(lua))


def build():
    H, masks, cover = WG.load_layout()
    trees = WG.place_trees(H, masks, cover)
    sc, n = build_main(H, masks, cover, trees)
    print('scene entities', len(sc.entities), 'detailed trees', n)
    stream()
    derive_views(H, masks, trees)
