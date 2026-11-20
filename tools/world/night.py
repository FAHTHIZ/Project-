"""Storm night over Kestrel Valley (docs/CAMPAIGN_STORY_BIBLE.md section 1A).

The open-world chapters run 02:40 to 05:30 under an overcast storm: heavy rain, wet ground
with standing water, low fog lying in the creek line and drifting through the forest. There is
no daylight to read the valley by, so every light is a real source with a reason to exist:

  moon          a weak blue key leaking through the cloud deck (shadowed directional)
  lightning     a second directional driven by scripts/world/storm.luau, with thunder
  camp floods   the staging camp's two floodlights on their generator
  camp lantern  the battery lantern on the prologue briefing table
  yard lights   sodium pole lamps over the gate and the compound yard
  searchlights  one per watchtower, sweeping on scripts/world/searchlight.luau
  facility      amber portal lamp over the vault door, guard booth strip light
  people        the player's weapon light (rig.py), squad and contractor rail lights (actors.py),
                the Mule's headlights (vehicle.py)

chapters.py calls apply(doc, sc, chapter) on each chapter scene after copying the world.
"""
from __future__ import annotations
import math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'scenes'))
sys.path.insert(0, str(ROOT / 'tools' / 'world'))
import common  # noqa: E402
import world_scene as WS  # noqa: E402
from vscene import Scene, transform, quat_euler, script  # noqa: E402

# Storm progression by chapter (story times): it peaks over the prologue and Op01, thins over the
# saddle (fog thickens instead), and is easing by the compound; the epilogue is dawn.
WEATHER = {
    'prologue': dict(precipitation_intensity=0.95, precipitation_wind=[2.8, 0.0, 1.4], volumetric_density=0.02),
    'op01': dict(precipitation_intensity=0.9, precipitation_wind=[2.4, 0.0, 1.2], volumetric_density=0.024),
    'op02': dict(precipitation_intensity=0.7, precipitation_wind=[3.2, 0.0, 0.6], volumetric_density=0.03,
                 fog_density=0.022, volumetric_height=95.0),
    'op03': dict(precipitation_intensity=0.6, precipitation_wind=[1.6, 0.0, 0.8], volumetric_density=0.02),
}
SODIUM = (1.0, 0.68, 0.36)
LED = (0.9, 0.94, 1.0)


def environment(chapter):
    """The Environment component for a chapter (night storm, or dawn for the epilogue)."""
    tmp = Scene('env')
    if chapter == 'epilogue':
        common.environment(tmp, 'dawn', shadow_distance=60)
    else:
        common.environment(tmp, 'night_storm', **WEATHER.get(chapter, {}))
    return tmp.entities[0]['components']['Environment']


def moon(chapter):
    if chapter == 'epilogue':
        # low sun behind thinning cloud in the east-north-east, cool and soft
        return {'type': 'directional', 'color': [1.0, 0.84, 0.7, 1], 'intensity': 1.6, 'range': 10, 'shadows': True}
    return {'type': 'directional', 'color': [0.56, 0.66, 0.88, 1], 'intensity': 0.42, 'range': 10, 'shadows': True}


def _spot(sc, name, pos, pitch, yaw, color, intensity, rng, inner, outer, shadows=False, extra=None):
    comps = {'Transform': transform(pos, quat_euler(pitch, yaw, 0)),
             'Light': {'type': 'spot', 'color': list(color) + [1], 'intensity': intensity, 'range': rng,
                       'shadows': shadows, 'inner_angle': inner, 'outer_angle': outer}}
    if extra:
        comps.update(extra)
    return sc.add(name, comps)


def _point(sc, name, pos, color, intensity, rng, shadows=False):
    return sc.add(name, {'Transform': transform(pos), 'Light': {
        'type': 'point', 'color': list(color) + [1], 'intensity': intensity, 'range': rng, 'shadows': shadows}})


def add_lights(sc, chapter):
    P = WS.PLACED
    for name, (model, x, y, z, yaw) in sorted(P.items()):
        if model == 'floodlight':
            p, _ = WS.anchor_world('floodlight', 'lens', x, y, z, yaw)
            # the camp's floods are the one large shadowed source (tents and crates throw shade)
            _spot(sc, name + ' Beam', p, -22.0, yaw, LED, 60.0, 38.0, 22.0, 48.0, shadows=name.endswith('A'))
        elif model == 'light_pole':
            p, _ = WS.anchor_world('light_pole', 'lamp', x, y, z, yaw)
            _spot(sc, name + ' Lamp', p, -82.0, yaw, SODIUM, 55.0, 24.0, 38.0, 62.0)
        elif model == 'watchtower':
            p, hd = WS.anchor_world('watchtower', 'deck', x, y, z, yaw)
            # mounted on the rail, facing the approach (south, +Z)
            pos = (p[0], p[1] + 1.55, p[2] + 1.7)
            i = int(name.split()[-1])
            _spot(sc, name + ' Searchlight', pos, -9.0, 180.0, LED, 140.0, 90.0, 4.0, 9.0,
                  extra={'Script': script('scripts/world/searchlight.luau', arc=38.0 + 6 * i, period=13.0 + 3 * i,
                                          phase=0.3 * i, pitch=-9.0 - 2 * i, yaw=180.0)})
        elif model == 'facility_portal':
            p, _ = WS.anchor_world('facility_portal', 'front', x, y, z, yaw)
            # amber work lamp above the vault door; Op03's last walk ends under it
            _point(sc, 'Portal Lamp', (p[0], p[1] + 5.2, p[2] + 0.8), (1.0, 0.62, 0.3), 26.0, 16.0)
        elif model == 'gate_booth':
            p, _ = WS.anchor_world('gate_booth', 'inside', x, y, z, yaw)
            _point(sc, 'Booth Strip Light', (p[0], p[1] + 2.0, p[2]), (0.86, 0.95, 1.0), 5.0, 6.0)
        elif model == 'site_office':
            p, _ = WS.anchor_world('site_office', 'desk', x, y, z, yaw)
            _point(sc, 'Office Desk Lamp', (p[0], p[1] + 1.1, p[2]), (1.0, 0.8, 0.55), 4.0, 6.0)
        elif model == 'camp_table' and chapter == 'prologue':
            # Lamplight's battery lantern on the briefing table (tools/assets/blender_lantern.py),
            # warm 3000 K: it is what lights the squad's faces over the map. The squad
            # packs it before Op01, so it only exists in the prologue.
            r = math.radians(yaw)
            lx, lz = 0.62, 0.18
            p = (x + lx * math.cos(r) + lz * math.sin(r), y + 0.76, z - lx * math.sin(r) + lz * math.cos(r))
            sc.prop('Camp Lantern', WS.STRUCT + 'camp_lantern.glb', p, yaw + 20.0, shadows=False)
            # shadowed and at 6: unshadowed at 10 it shone through the table top and burned the
            # grass under it white (campaign tour, 2026-11)
            _point(sc, 'Camp Lantern Light', (p[0], p[1] + 0.15, p[2]), (1.0, 0.76, 0.5), 6.0, 9.0, shadows=True)
        elif model == 'ph_generator' and name.startswith('Camp'):
            # the generator's status lamp, a small green point that blinks in the rain
            _point(sc, 'Camp Generator Lamp', (x, y + 0.7, z), (0.4, 1.0, 0.5), 1.5, 3.0)


def add_storm(sc, chapter):
    if chapter == 'epilogue':
        return
    root = sc.add('Storm', {'Transform': transform(), 'Script': script(
        'scripts/world/storm.luau', min_gap=24.0 if chapter in ('prologue', 'op01') else 40.0,
        max_gap=60.0 if chapter in ('prologue', 'op01') else 110.0, first=7.0 if chapter == 'prologue' else 25.0)})
    sc.add('Lightning', {'Transform': transform((0, 50, 0), quat_euler(-62, 150, 0)), 'Light': {
        'type': 'directional', 'color': [0.78, 0.84, 1.0, 1], 'intensity': 0.0, 'range': 10, 'shadows': False}}, root)


def apply(doc, sc, chapter):
    """Swap the world's daylight Environment/Sun for the chapter's night and add the lights."""
    for e in doc['entities']:
        c = e['components']
        if 'Environment' in c:
            c['Environment'] = environment(chapter)
        if e['name'] == 'Sun' and 'Light' in c:
            e['name'] = 'Moon' if chapter != 'epilogue' else 'Sun'
            c['Light'] = moon(chapter)
            pitch, yaw = (-55.0, 125.0) if chapter != 'epilogue' else (-9.0, 70.0)
            c['Transform'] = transform((0, 30, 0), quat_euler(pitch, yaw, 0))
    # The world scene's player and Mule predate the night pass; give them their lights here
    # when the world has not been regenerated since (rig.py / vehicle.py add them on regen).
    names = {e['name']: e['uuid'] for e in doc['entities']}
    if 'Weapon Light' not in names and 'Main Camera' in names:
        sc.add('Weapon Light', {'Transform': transform((0.16, -0.16, -0.25), quat_euler(-1.5, -1.0, 0)), 'Light': {
            'type': 'spot', 'color': [0.92, 0.95, 1.0, 1], 'intensity': 18.0, 'range': 34.0, 'shadows': True,
            'inner_angle': 9.0, 'outer_angle': 24.0}}, names['Main Camera'])
    if 'Mule Headlight L' not in names and 'Mule Chassis' in names:
        for sx, nm in ((-1, 'Headlight L'), (1, 'Headlight R')):
            sc.add(f'Mule {nm}', {'Transform': transform((sx * 0.72, 0.93, -2.47), quat_euler(-5, 0, 0)), 'Light': {
                'type': 'spot', 'color': [1.0, 0.95, 0.86, 1], 'intensity': 30.0, 'range': 45.0, 'shadows': False,
                'inner_angle': 16.0, 'outer_angle': 34.0}}, names['Mule Chassis'])
    add_lights(sc, chapter)
    add_storm(sc, chapter)
