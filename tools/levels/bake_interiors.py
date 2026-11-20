#!/usr/bin/env python3
"""Bakes static lighting (VICTUS lightmaps, ADR-0125) for the Op04-Op07 interiors.

For each chapter this runs `victus bake-lighting --mark-static` on the generated scene, records which
mesh renderers VICTUS marked as Static Lighting in `tools/levels/<key>_static.json`, restores the
scene file and lets `build_facility.py --scenes` write the marks and the Environment's `lightmap`
path into both the chapter and its `tests/story_<key>` copy (same uuids and transforms, so the
bake's fingerprints match).

The bake is indirect only (sky plus bounce of every light); the rooms' lights stay realtime, so
nothing is lit twice. The bounce colour comes from each material's albedo texture mean (VICTUS
ADR-0143).

    export PATH=<engine>/build/rel/bin:$PATH
    python3 tools/levels/bake_interiors.py [op05 ...] [--density 4] [--samples 64]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GAME = ROOT / 'game'
sys.path.insert(0, str(HERE))
from build_facility import SCENE_PATH  # noqa: E402


# Small fittings and clutter take their indirect light from the baked probes instead of atlas space,
# and anything a mission script moves (doors, the lift car, V-01, the tracer rig) stays realtime.
SKIP = re.compile(r'Fitting|Emergency|Extinguisher|Light|Lamp|CCTV|Clock|Fire Alarm|Sign|Plant|Bin\b|Clipboard|'
                  r'Binder|Notes|Monitor|Laptop|Screen|Board|Jerrycan|Wet Floor|Box [AB]|Boxes|Stool|Chair|Door|'
                  r'Lift|V-0|Tracer|power_box|utility_box|Utility Box|Power Box|Clutter|Drawer|Hand Truck|'
                  r'Container|Barrel|Tool Chest|Ladder|Cart')


def marked_uuids(scene_json):
    by_id = {e['uuid']: e for e in scene_json['entities']}
    out = []
    for e in scene_json['entities']:
        mr = e.get('components', {}).get('MeshRenderer')
        if not (mr and mr.get('lightmapped')):
            continue
        names, p = [], e
        while p is not None:
            names.append(p['name'])
            p = by_id.get(p.get('parent'))
        if not any(SKIP.search(n) for n in names):
            out.append(e['uuid'])
    return sorted(out)


def mark(scene_json, ids, lightmap):
    for e in scene_json['entities']:
        c = e.get('components', {})
        if 'Environment' in c:
            c['Environment']['lightmap'] = lightmap
        if 'MeshRenderer' in c:
            c['MeshRenderer']['lightmapped'] = e['uuid'] in ids


# Bounce ("indirect intensity", as Unreal calls it per light) for the bake only. The realtime lights
# keep their values; the bake also gets a light in every ceiling fitting, including the ones that
# carry no realtime light for the mobile light budget, so big rooms do not fall to black between
# lit fittings. The deep levels get more bounce: their rooms read black on a phone otherwise.
INDIRECT = {'op04': 1.0, 'op05': 1.4, 'op06': 2.2, 'op07': 1.0}
FITTING = re.compile(r'^(.*) Light (\d+) Fitting$')


def bake_lights(scene_json, key):
    ents = scene_json['entities']
    lights = {e['name']: e for e in ents if 'Light' in e['components']}
    room_light = {}
    for n, e in lights.items():
        m = re.match(r'^(.*) Light \d+$', n)
        if m:
            room_light.setdefault(m.group(1), e['components']['Light'])
    added = 0
    for e in list(ents):
        m = FITTING.match(e['name'])
        if not m or f'{m.group(1)} Light {m.group(2)}' in lights or m.group(1) not in room_light:
            continue
        x, y, z = e['components']['Transform']['position']
        ents.append({'uuid': f'00000000-0000-4000-8000-{added:012d}', 'name': f'Bake Fill {e["name"]}',
                     'components': {'Transform': {'position': [x, y - 0.33, z], 'rotation': [0, 0, 0, 1],
                                                  'scale': [1, 1, 1]},
                                    'Light': dict(room_light[m.group(1)])}})
        added += 1
    # Scale the room lights; carried lights (the player's weapon light, operators' and contractors'
    # torches, muzzle flashes) move, so they must not leave a baked imprint at their start positions.
    k = INDIRECT[key]
    for e in ents:
        L = e['components'].get('Light')
        if not L:
            continue
        if re.match(r'^(.*) Light \d+$', e['name']) or e['name'].startswith('Bake Fill'):
            L['intensity'] = L['intensity'] * k
        else:
            del e['components']['Light']
    return added


def victus_bake(rel, *args):
    r = subprocess.run(['victus', 'bake-lighting', str(GAME), '--scene', rel, *args], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit(f'{rel}: bake failed: {r.stderr.strip()}')


def main():
    ap = argparse.ArgumentParser()
    # op06 is not baked yet: the lower archive is a 60 x 44 m hall with sparse work lights, and with
    # its fake ambient replaced by the bake it reads near-black even at 2.2x bounce (needs a lighting
    # pass on the room first).
    ap.add_argument('keys', nargs='*', default=['op04', 'op05', 'op07'])
    ap.add_argument('--density', type=float, default=4.0)
    ap.add_argument('--samples', type=int, default=64)
    ap.add_argument('--bounces', type=int, default=3)
    a = ap.parse_args()
    for key in a.keys:
        rel = SCENE_PATH[key]
        path = GAME / rel
        original = path.read_text()
        lm = rel.replace('.vscene', '.vlightmap')
        try:
            # 1. let VICTUS decide what cannot move (a 1-sample throwaway bake), then filter it
            victus_bake(rel, '--mark-static', '--density', '1', '--samples', '1', '--no-probes')
            data = json.loads(path.read_text())
            ids = marked_uuids(data)
            # 2. the real bake with only the kept receivers
            path.write_text(original)
            data = json.loads(original)
            mark(data, set(ids), lm)
            print(key, bake_lights(data, key), 'bake-only fill lights, indirect x', INDIRECT[key])
            path.write_text(json.dumps(data, indent=1) + '\n')
            victus_bake(rel, '--density', str(a.density), '--samples', str(a.samples), '--bounces', str(a.bounces))
        finally:
            path.write_text(original)
        (HERE / f'{key}_static.json').write_text(json.dumps(ids, indent=0) + '\n')
        print(key, len(ids), 'static lighting renderers')
    subprocess.run([sys.executable, str(HERE / 'build_facility.py'), '--scenes'], check=True)


if __name__ == '__main__':
    main()
