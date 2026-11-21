# SPDX-License-Identifier: Apache-2.0
"""Kestrel Valley chapter scenes: the streamed world plus the cast, mission director, music and
mission markers for each chapter that starts in the valley.

    python3 tools/world/chapters.py          (after tools/world/worldgen.py all)

Writes scenes/prologue.vscene, scenes/op01_forest.vscene, scenes/op02_perimeter.vscene and
scenes/op03_approach.vscene (the paths lib/campaign.luau loads). All four are the same world;
`chapter` on the Mission entity says where play starts, and the cast includes only what is still
ahead from there (contractors already dealt with in an earlier chapter are not placed again).
"""
from __future__ import annotations
import copy, json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'scenes'))

import worldmap as M  # noqa: E402
import worldgen as WG  # noqa: E402
import world_scene as WS  # noqa: E402
import actors  # noqa: E402
import night  # noqa: E402
import cinematics  # noqa: E402
from vscene import Scene, transform, script  # noqa: E402

GAME = WS.GAME
ORDER = ['prologue', 'op01', 'op02', 'op03', 'epilogue']
SCENES = {'prologue': 'scenes/prologue.vscene', 'op01': 'scenes/op01_forest.vscene',
          'op02': 'scenes/op02_perimeter.vscene', 'op03': 'scenes/op03_approach.vscene',
          'epilogue': 'scenes/epilogue.vscene'}
MUSIC = {'prologue': 'forest', 'op01': 'forest', 'op02': 'perimeter', 'op03': 'perimeter', 'epilogue': 'forest'}


def mule_rear(dx=0.0, dz=0.0):
    """World point behind the parked Mule's hatch (it waits at mule_park, nose 150 deg), offset
    in world metres. The epilogue gathers everyone at the tailgate."""
    m = P('mule_park')
    r = math.radians(150.0)
    return (m[0] + 2.9 * math.sin(r) + dx, m[2] + 2.9 * math.cos(r) + dz)

# Greyline groups: chapter, then (name, x, z, yaw, variant, extra props). y comes from the ground
# (tower guards stand on the tower decks).
GROUPS = {
    'patrol': ('op01', [('Greyline Patrol 1', 26, 82, 200, 0, dict(patrol='26,82;4,62;-14,50;4,62', voice='greyline1')),
                        ('Greyline Patrol 2', 22, 85, 200, 1, dict(patrol='22,85;0,65;-18,53;0,65', voice='greyline2'))]),
    # Op01 search line: three contractors walking a line through the woods east -> west across the
    # trail below the cabin, ~10 m apart, rail lights on. Woken by the director at the footbridge.
    'line': ('op01', [('Greyline Line 1', 112, 162, -90, 0, dict(patrol='112,162;-48,162', voice='greyline1', dormant=True)),
                      ('Greyline Line 2', 116, 172, -90, 1, dict(patrol='116,172;-44,172', voice='greyline2', dormant=True)),
                      ('Greyline Line 3', 120, 182, -90, 0, dict(patrol='120,182;-40,182', dormant=True))]),
    'ambush': ('op01', [('Greyline Ambush 1', -20, -100, 0, 0, dict(voice='greyline1')),
                        ('Greyline Ambush 2', 18, -98, 10, 1, dict(voice='greyline2')),
                        ('Greyline Ambush 3', -8, -114, 0, 1, dict()),
                        ('Greyline Ambush 4', 9, -120, -10, 0, dict())]),
    'towers': ('op02', [('Greyline Tower 0', 'tower_0', None, 0, 0, dict(voice='greyline1')),
                        ('Greyline Tower 1', 'tower_1', None, 0, 1, dict()),
                        ('Greyline Tower 2', 'tower_2', None, 0, 0, dict(voice='greyline2'))]),
    'gate': ('op02', [('Greyline Gate 1', 44, -348, 0, 1, dict(patrol='44,-348;54,-348')),
                      ('Greyline Gate 2', 55, -352, 20, 0, dict())]),
    'reinf': ('op02', [('Greyline Reinforcement 1', 26, -380, 0, 0, dict(voice='greyline2')),
                       ('Greyline Reinforcement 2', 30, -384, 0, 1, dict()),
                       ('Greyline Reinforcement 3', 34, -380, 0, 0, dict())]),
    'yard': ('op03', [('Greyline Yard 1', 10, -372, 0, 0, dict(patrol='10,-372;-20,-372;-20,-404;10,-404', voice='greyline1')),
                      ('Greyline Yard 2', 50, -398, 90, 1, dict(patrol='50,-398;50,-372')),
                      ('Greyline Yard 3', -30, -380, 180, 0, dict()),
                      ('Greyline Yard 4', -60, -380, 90, 1, dict(patrol='-60,-380;-60,-410;-30,-414')),
                      ('Greyline Yard 5', 12, -424, 180, 0, dict(voice='greyline2'))]),
}


def P(name):
    return WS.POINTS[name]


def flat_yaw(a, b):
    """Player/vehicle yaw (forward = -Z at 0) from a toward b."""
    return math.degrees(math.atan2(-(b[0] - a[0]), -(b[2] - a[2])))


def char_yaw(a, b):
    """Character yaw (model faces +Z) from a toward b."""
    return math.degrees(math.atan2(b[0] - a[0], b[2] - a[2]))


def add_music(sc, chapter, H):
    area = MUSIC[chapter]
    root = sc.add('Music', {'Transform': transform(),
                            'Script': script('scripts/music.luau', zones=';'.join([
                                f"{P('poi_camp')[0]:.0f},{P('poi_camp')[2]:.0f},70,audio/ambient/camp.wav",
                            ]))})

    def src(name, clip, bus, vol, loop=True, stream=True):
        sc.add(name, {'Transform': transform(), 'AudioSource': {
            'clip': clip, 'bus': bus, 'volume': vol, 'pitch': 1.0, 'loop': loop, 'play_on_start': False,
            'stream': stream, 'spatial': False, 'priority': 250, 'occlusion': False}}, root)
    src('Explore', f'audio/music/{area}_explore.ogg', 'music', 0.55)
    src('Tension', f'audio/music/{area}_tension.ogg', 'music', 0.0)
    src('Cue', '', 'music', 0.8, loop=False)
    # dawn: the storm has passed and the birds are back (the night beds are rain)
    src('Bed', 'audio/ambient/forest_day.wav' if chapter == 'epilogue' else 'audio/ambient/forest.wav', 'ambient', 0.6,
        stream=False)


def add_creek_audio(sc, H, masks):
    cr = masks['splines']['creek']
    for i, (x, z, _) in enumerate(WS.along(cr, 45.0, 10.0)):
        sc.add(f'Creek Sound {i}', {'Transform': transform((x, WS.ground(H, x, z) + 0.4, z)), 'AudioSource': {
            'clip': 'audio/ambient/creek.wav', 'bus': 'ambient', 'volume': 0.8, 'pitch': 0.9 + 0.04 * (i % 5),
            'loop': True, 'play_on_start': True, 'stream': False, 'spatial': True, 'attenuation': 'inverse',
            'min_distance': 3.0, 'max_distance': 32.0, 'rolloff': 1.0, 'priority': 90, 'occlusion': False}})


def add_markers(sc):
    """Invisible interaction points the director registers (fp_player's cone fallback finds them)."""
    for name, key, tags in (('Mark Board', 'mule_camp', ''), ('Mark Relay Cell', 'relay_bay', 'Relay Scannable'),
                            ('Mark Booth Panel', 'booth_panel', ''), ('Mark Office Desk', 'office_desk', ''),
                            ('Mark Facility Panel', 'facility_panel', ''),
                            # evidence in the gate booth and the site office (Op02/Op03 story beats)
                            ('Mark Booth Records', ('booth_panel', -1.1, 0.0, 0.7), ''),
                            ('Mark Field Recorder', ('booth_panel', 0.9, -0.4, -0.9), ''),
                            ('Mark Site Manifest', ('office_desk', 0.8, 0.0, 0.0), '')):
        if isinstance(key, tuple):
            b = P(key[0])
            key = (b[0] + key[1], b[1] + key[2], b[2] + key[3])
        else:
            key = P(key)
        comps = {'Transform': transform(key)}
        if tags:
            comps['Tags'] = {'tags': tags}
        sc.add(name, comps)


def add_cast(sc, chapter, H):
    start = ORDER.index(chapter)
    # squad
    if chapter == 'prologue':
        # 02:40: the squad is already aboard the Mule at the staging camp, engine idling (the
        # Arrival cinematic opens on the valley, then cuts to them pulling out)
        mc = P('mule_camp')
        seats = {'Anchor': 'driver', 'Patch': 'front_right', 'Echo': 'rear_left', 'Tally': 'rear_right'}
        for i, (who, seat) in enumerate(seats.items()):
            x, z = mc[0] + 3.0 + i, mc[2] + 3.0
            actors.add_operator(sc, who, (x, WS.ground(H, x, z) + 0.05, z), 0.0, order='hold', ride='Mule', seat=seat)
        # Brick went ahead to clear the washout; he waits at the trailhead beside the cut tree
        b = P('trail_start')
        x, z = b[0] + 2.6, b[2] - 2.2
        actors.add_operator(sc, 'Brick', (x, WS.ground(H, x, z) + 0.05, z), char_yaw((x, 0, z), P('mule_park')),
                            order='hold')
    elif chapter == 'epilogue':
        # 05:52, the lay-by: everyone out of the facility and back at the Mule. Brick has Venn
        # at the tailgate, Patch beside them; Hollis came down the trail to see them off.
        look = P('trail_start')
        for who, dx, dz in (('Anchor', -1.6, -1.9), ('Patch', 1.0, -2.5), ('Echo', -2.7, -0.7),
                            ('Tally', 2.5, -1.6), ('Brick', 1.3, -0.4)):
            x, z = mule_rear(dx, dz)
            actors.add_operator(sc, who, (x, WS.ground(H, x, z) + 0.05, z), char_yaw((x, 0, z), look), order='hold')
        x, z = mule_rear(0.1, -0.9)
        actors.add_npc(sc, 'Venn', 'models/characters/sops_explorer.glb', (x, WS.ground(H, x, z) + 0.05, z),
                       char_yaw((x, 0, z), look), who='venn')
        x, z = mule_rear(-3.8, -4.2)
        actors.add_npc(sc, 'Hollis', 'models/characters/sops_ranger.glb', (x, WS.ground(H, x, z) + 0.05, z),
                       char_yaw((x, 0, z), look), who='hollis')
    else:
        base = {'op01': P('trail_start'), 'op02': P('poi_saddle'), 'op03': (P('gate')[0], 0, P('gate')[2] - 14)}[chapter]
        for i, who in enumerate(('Anchor', 'Patch', 'Echo', 'Tally', 'Brick')):
            x, z = base[0] + (i - 2.0) * 1.6, base[2] + 2.5 + (i % 2)
            actors.add_operator(sc, who, (x, WS.ground(H, x, z) + 0.05, z), 180.0)
    # Hollis waits on his porch, watching the trail
    if start <= ORDER.index('op01') and chapter != 'epilogue':
        h = P('cabin_porch')
        actors.add_npc(sc, 'Hollis', 'models/characters/sops_ranger.glb', (h[0], h[1] + 0.05, h[2]), -90.0,
                       who='hollis')
    # contractors still ahead
    for group, (ch, members) in GROUPS.items():
        if ORDER.index(ch) < start or chapter == 'epilogue':
            continue
        for name, x, z, yaw, variant, extra in members:
            if isinstance(x, str):
                px, py, pz = P(x)
                pos = (px, py + 0.1, pz)
            else:
                pos = (x, WS.ground(H, x, z) + 0.05, z)
            actors.add_enemy(sc, name, pos, yaw, variant=variant, group=group, **extra)


def player_start(chapter, H):
    if chapter == 'prologue':
        # beside the Mule; the director seats Rook in the rear middle on the first frame
        mc = P('mule_camp')
        x, z = mc[0] - 2.5, mc[2] + 1.0
        return (x, WS.ground(H, x, z) + 0.05, z), 0.0
    if chapter == 'op01':
        s = P('trail_start')
        nxt = WS.POINTS['trail_marker']
        return (s[0], s[1] + 0.05, s[2]), flat_yaw(s, nxt)
    if chapter == 'op02':
        s = P('poi_saddle')
        return (s[0], s[1] + 0.05, s[2]), flat_yaw(s, P('fence_approach'))
    if chapter == 'epilogue':
        # walking out of the trees on the footpath, 20 m short of the lay-by
        s, nxt = P('trail_start'), WS.POINTS['trail_marker']
        d = math.hypot(nxt[0] - s[0], nxt[2] - s[2])
        x, z = s[0] + (nxt[0] - s[0]) / d * 20.0, s[2] + (nxt[2] - s[2]) / d * 20.0
        return (x, WS.ground(H, x, z) + 0.05, z), flat_yaw((x, 0, z), P('mule_park'))
    g = P('gate')
    x, z = g[0], g[2] - 10
    return (x, WS.ground(H, x, z) + 0.05, z), flat_yaw((x, 0, z), P('poi_compound'))


def build():
    H, masks, cover = WG.load_layout()
    # recompute POINTS without rebuilding the world (same functions world_scene uses)
    tmp = Scene('points')
    WS.add_routes(tmp, H, masks)
    WS.add_trailhead(tmp, H)
    WS.add_structures(tmp, H, masks)
    src = json.loads((GAME / WS.SCENE_REL).read_text())
    actors.USE_NAV = False
    for chapter in ORDER:
        doc = copy.deepcopy(src)
        title = {'prologue': 'Prologue', 'op01': 'Operation 01', 'op02': 'Operation 02', 'op03': 'Operation 03',
                 'epilogue': 'Epilogue'}[chapter]
        doc['name'] = f'{title} - Kestrel Valley'
        pos, yaw = player_start(chapter, H)
        for e in doc['entities']:
            if e['name'] == 'Player':
                e['components']['Transform'] = transform(pos, yaw=yaw)
            if e['name'] == 'Mule' and chapter == 'prologue':
                mc = P('mule_camp')
                road = masks['splines']['road_in']
                k = int(road.tree.query([mc[0], mc[2]])[1])
                ahead = road.p[min(len(road.p) - 1, k + 6)]
                e['components']['Transform'] = transform(mc, yaw=flat_yaw(mc, (ahead[0], 0, ahead[1])))
        sc = Scene(doc['name'])
        night.apply(doc, sc, chapter)
        actors.add_ensemble(sc)
        add_cast(sc, chapter, H)
        if chapter == 'prologue':
            cinematics.add_prologue(doc, WS.POINTS, lambda x, z: WS.ground(H, x, z))
        add_markers(sc)
        add_music(sc, chapter, H)
        add_creek_audio(sc, H, masks)
        sc.add('Mission', {'Transform': transform(), 'Script': script('scripts/missions/kestrel.luau', chapter=chapter)})
        extra = json.loads(sc.to_json()) if hasattr(sc, 'to_json') else None
        ents = extra['entities'] if extra else sc.entities
        doc['entities'].extend(ents)
        out = GAME / SCENES[chapter]
        out.write_text(json.dumps(doc, indent=1) + '\n')
        # the same chapter with the story driver (tools/test/run_autotests.py story_<chapter>)
        test = copy.deepcopy(doc)
        test['entities'].append({'uuid': WS.uid(f'story_{chapter}/autotest') if hasattr(WS, 'uid') else
                                 __import__('vscene').uid(f'story_{chapter}/autotest'), 'name': 'Autotest',
                                 'components': {'Transform': transform(),
                                                'Script': script('scripts/autotest.luau', plan=f'story_{chapter}')}})
        (GAME / f'scenes/tests/story_{chapter}.vscene').write_text(json.dumps(test, indent=1) + '\n')
        if chapter == 'op01':
            # the Op01 search line beat (tests/world_plans.luau op01_line, op01_line_loud)
            for plan in ('op01_line', 'op01_line_loud'):
                t2 = copy.deepcopy(doc)
                t2['entities'].append({'uuid': __import__('vscene').uid(f'{plan}/autotest'), 'name': 'Autotest',
                                       'components': {'Transform': transform(),
                                                      'Script': script('scripts/autotest.luau', plan=plan)}})
                (GAME / f'scenes/tests/{plan}.vscene').write_text(json.dumps(t2, indent=1) + '\n')
        print(chapter, out.relative_to(GAME), len(doc['entities']), 'entities')


if __name__ == '__main__':
    build()
