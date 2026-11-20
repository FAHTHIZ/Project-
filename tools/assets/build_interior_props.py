# SPDX-License-Identifier: Apache-2.0
"""Photoscanned CC0 dressing for the Kestrel Station interiors (Operations 04-07).

    BLENDER=/path/to/blender python3 tools/assets/build_interior_props.py [names...]

Downloads each Poly Haven model at 1k (tools/assets/polyhaven.py, cached in .cache/polyhaven),
decimates it to a per-prop triangle budget, shrinks its textures and writes
game/assets/models/interior/ph/<name>.glb. Bounds (game axes, metres) go to
tools/levels/interior_props.json, which tools/levels/build_facility.py reads for colliders and
wall placement. Budgets assume the Hot 10S class GPU (Mali-G52): furniture 1.5-3k triangles,
wall fittings and desk clutter 300-900, textures 512 px (256 for small clutter).
Every source is CC0 1.0 (https://polyhaven.com/license); see docs/ASSET_PROVENANCE.md.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import polyhaven as ph  # noqa: E402

ROOT = ph.ROOT
OUT = os.path.join(ROOT, 'game', 'assets', 'models', 'interior', 'ph')
BOUNDS = os.path.join(ROOT, 'tools', 'levels', 'interior_props.json')
BLENDER = os.environ.get('BLENDER', 'blender')
WORKER = os.path.join(os.path.dirname(__file__), 'blender_interior.py')

# name: (poly haven id, triangle budget, texture px, extra job keys)
JOBS = {
    # furniture
    'office_desk': ('metal_office_desk', 2400, 512, {}),
    'drawer_cabinet': ('drawer_cabinet', 2000, 512, {}),
    'metal_rack': ('worn_metal_rack', 1800, 512, {}),
    'wood_cabinet': ('painted_wooden_cabinet', 1500, 512, {}),
    'record_cabinet': ('vintage_cabinet_01', 3000, 512, {}),
    'chalkboard': ('standing_chalkboard_01', 1200, 512, {}),
    'projector_screen': ('projector_screen', 1200, 512, {}),
    'stool': ('metal_stool_01', 800, 256, {}),
    # storage and industrial
    'trash_can': ('metal_trash_can', 900, 256, {'objects': ['metal_trash_can$', 'metal_trash_can_lid', 'metal_trash_can_handle_']}),
    'cardboard_box': ('cardboard_box_01', 300, 256, {}),
    'military_crate': ('old_military_crate', 900, 512, {'objects': ['old_military_crate_a', 'old_military_crate_lid_a', 'old_military_crate_loop_a', 'old_military_crate_latch_a', 'old_military_crate_cloth_a']}),
    'long_crate': ('wooden_military_crate', 1200, 512, {}),
    'storage_cart': ('industrial_storage_cart', 2000, 512, {}),
    'tool_cart': ('tool_cart', 2200, 512, {}),
    'tool_chest': ('metal_tool_chest', 900, 256, {}),
    'barrel': ('Barrel_01', 900, 512, {}),
    'propane_tank': ('propane_tank', 700, 256, {}),
    'generator': ('portable_generator', 2200, 512, {}),
    'compressor': ('old_military_compressor', 3000, 512, {}),
    'hand_truck': ('hand_truck', 1200, 256, {}),
    'ladder': ('ladder_sectioned_01', 1200, 256, {}),
    'plastic_container': ('industrial_pastic_container', 800, 256, {}),
    'jerrycan': ('plastic_jerrycan', 600, 256, {}),
    'cement_bag': ('cement_bag', 300, 256, {}),
    'wet_floor_sign': ('WetFloorSign_01', 228, 256, {}),
    # wall and ceiling fittings
    'extinguisher': ('korean_fire_extinguisher_01', 900, 256, {}),
    'fire_alarm': ('fire_alarm', 300, 256, {'pivot': 'back'}),
    'cctv': ('security_camera_01', 1200, 256, {'pivot': 'back'}),
    'wall_lamp': ('industrial_wall_lamp', 700, 256, {'pivot': 'back'}),
    'power_box': ('power_box_01', 700, 256, {'pivot': 'back'}),
    'utility_box': ('utility_box_01', 900, 512, {'pivot': 'back'}),
    'security_light': ('security_light', 700, 256, {'pivot': 'back'}),
    'wall_clock': ('wall_clock', 500, 256, {'pivot': 'back'}),
    # desk clutter and evidence
    'binder': ('binder_notebook', 400, 256, {'objects': ['binder_notebook_closed']}),
    'clipboard': ('clipboard', 300, 256, {}),
    'notepads': ('office_notepads', 300, 256, {'objects': ['office_notepads_a4_stack']}),
    'laptop': ('classic_laptop', 1200, 512, {}),
    'crt_monitor': ('Television_01', 900, 512, {}),
    'desk_lamp': ('desk_lamp_arm_01', 900, 256, {}),
    'stationery': ('stationery_supplies', 400, 256, {'objects': ['stationery_supplies_pencilcup']}),
    'radio_set': ('vintage_radio_transceiver', 1600, 512, {}),
    'medical_box': ('medical_box', 500, 256, {}),
    'microscope': ('industrial_microscope', 1000, 256, {}),
    'chemistry_set': ('chemistry_set', 1200, 256, {}),
    'multimeter': ('retro_multimeter', 500, 256, {}),
    'circuit_board': ('circuit_board', 600, 256, {}),
    'searchlight': ('portable_searchlight', 700, 256, {}),
    'potted_plant': ('potted_plant_01', 1800, 512, {}),
}


def build(name: str) -> dict:
    asset, tris, tex, extra = JOBS[name]
    job = dict(src=ph.model(asset, '1k'), out=os.path.join(OUT, name + '.glb'), tris=tris, tex_size=tex, **extra)
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(job, f)
    r = subprocess.run([BLENDER, '-b', '--factory-startup', '-P', WORKER, '--', f.name],
                       capture_output=True, text=True)
    os.unlink(f.name)
    ok = [l for l in r.stdout.splitlines() if l.startswith('PROP_OK')]
    bl = [l for l in r.stdout.splitlines() if l.startswith('BOUNDS ')]
    if r.returncode != 0 or not ok or not bl:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit(f'{name}: blender failed')
    b = json.loads(bl[-1][7:])
    b['tris'] = int(ok[-1].split()[2])
    b['source'] = asset
    print(f'{name:18s} {asset:32s} {b["tris"]:5d} tris  '
          f'{[round(b["max"][i] - b["min"][i], 2) for i in range(3)]} m')
    return b


def main() -> int:
    names = sys.argv[1:] or list(JOBS)
    data = json.load(open(BOUNDS)) if os.path.exists(BOUNDS) else {}
    for n in names:
        data[n] = build(n)
    with open(BOUNDS, 'w') as f:
        json.dump(dict(sorted(data.items())), f, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main())
