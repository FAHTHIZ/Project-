# SPDX-License-Identifier: Apache-2.0
"""Structure gallery test scenes (visual inspection of tools/props/build_structures.py models on
flat ground, without the 1 km world): scenes/tests/gallery_camp.vscene, gallery_site.vscene."""
from __future__ import annotations

from vscene import Scene, GROUND_MATERIAL, transform, script
from common import environment, sun
import rig

S = 'models/structures/'

SETS = {
    'gallery_camp': dict(player=((0, 0, 14), 0.0), items=[
        ('ranger_cabin', (-8, 0, -4), 20.0), ('relay_mast', (6, 0, -6), -30.0), ('camp_tent', (12, 0, 4), -70.0),
        ('camp_table', (4, 0, 6), 10.0), ('supply_crates', (-2, 0, 6), 0.0), ('generator', (8, 0, 9), 0.0),
        ('floodlight', (1, 0, 3), 160.0)]),
    'gallery_site': dict(player=((0, 0, 22), 0.0), items=[
        ('watchtower', (-14, 0, -6), 0.0), ('gate_booth', (-6, 0, 4), 0.0), ('gate_leaf', (-3, 0, 2), 0.0),
        ('warning_sign', (2, 0, 8), 0.0), ('jersey_barrier', (6, 0, 9), 10.0), ('light_pole', (9, 0, 2), 180.0),
        ('site_office', (8, 0, -6), 0.0), ('container', (16, 0, 6), 60.0), ('garage', (-2, 0, -16), 0.0),
        ('facility_portal', (20, 0, -14), 0.0), ('culvert', (-10, 0, 12), 90.0)]),
}


def main():
    for name, d in SETS.items():
        sc = Scene(name)
        environment(sc, 'forest')
        sun(sc, pitch=-35, yaw=-40)
        sc.box('Ground', (0, -0.1, 0), (120, 0.2, 120), (0.5, 0.52, 0.46), material=GROUND_MATERIAL)
        for m, pos, yaw in d['items']:
            sc.prop(m, S + m + '.glb', pos, yaw)
        p, yaw = d['player']
        rig.add_player(sc, p, yaw, with_weapons=False)
        sc.save(f'scenes/tests/{name}.vscene')
        print('wrote', name)


if __name__ == '__main__':
    main()
