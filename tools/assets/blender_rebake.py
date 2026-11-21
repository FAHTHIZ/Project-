# SPDX-License-Identifier: Apache-2.0
"""Hero texture re-bake for the procedural weapons (tools/props/build_weapons.py + retexture.py).

    blender -b --factory-startup --python tools/assets/blender_rebake.py -- <src_dir> <out_dir> [names...]

Imports each GLB, joins it, and runs blender_bake.bake_hero with presets derived from the material
names: the existing (vertex colour x retexture scan) base colour is baked as albedo, then AO grime,
edge wear, a CC0 scan normal and bevel-rounded edges are added, and every non-emissive, non-glass
part merges into one textured material. Writes <out_dir>/<name>.glb.
"""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_bake as bk  # noqa: E402

# view-model parts are hero assets (big on screen); world copies and cells are small
SIZES = {'kv5_body': 1024, 'br9_body': 1024, 'mr6_body': 1024, 'lr4_body': 1024, 'sp2_body': 512,
         'sp2_slide': 512, 'br9_pump': 512, 'kv5_world': 512, 'br9_world': 512, 'mr6_world': 512,
         'lr4_world': 512, 'sp2_world': 512,
         # PC-7 modern carbine body from tools/assets/blender_carbine.py
         'pc7_body': 1024, 'pc7_cell': 512, 'pc7_world': 512}
DEFAULT_NAMES = list(SIZES) + ['kv5_cell', 'br9_cell', 'mr6_cell', 'lr4_cell', 'sp2_cell']
KEEP = ('Glow', 'Dot', 'Glass', 'Lens', 'Sight', 'Mark')


def preset(mname, bsdf):
    """Material role from its name (<weapon>[cell|pump]_<Role>[_w])."""
    role = mname.split('_')[1] if '_' in mname else mname
    cell = 'cell_' in mname
    rough = 0.5
    metal = 0.0
    if bsdf is not None:
        # the importer links textures to these sockets; the glTF factors are on the material
        pass
    if role == 'Metal':
        return dict(scan='Metal032', tile=0.3, contrast=0.2, nor=0.4, color=None, rough=0.36, metal=0.85, wear=0.6)
    if role == 'MetalDark':   # phosphated barrel and muzzle device
        return dict(scan='Metal032', tile=0.3, contrast=0.25, nor=0.4, color=None, rough=0.44, metal=0.8, wear=0.45)
    if role == 'Frame':       # hard-anodised aluminium receiver and handguard: wear shows bright metal
        return dict(scan='Metal032', tile=0.35, contrast=0.12, nor=0.3, color=None, rough=0.5, metal=0.55, wear=0.6)
    if role in ('Grip', 'Pad'):
        return dict(scan='Rubber004', tile=0.1, contrast=0.3, nor=0.9, color=None, rough=0.85, metal=0.0, wear=0.08)
    if role == 'Slide' or cell:
        return dict(scan='PaintedMetal004', tile=0.4, contrast=0.15, nor=0.4, color=None, rough=0.48, metal=0.3,
                    wear=0.65, paint=True)
    # Shell / Frame / pump shell: polymer
    return dict(scan='Plastic006', tile=0.22, contrast=0.25, nor=0.5, color=None, rough=0.62 if role != 'Frame' else 0.68,
                metal=0.0, wear=0.5)


def rebake(src, out, name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(src, name + '.glb'))
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    if len(obs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    presets, keep = {}, set()
    for s in ob.material_slots:
        m = s.material
        if any(k in m.name for k in KEEP):
            keep.add(m.name)
        else:
            presets[m.name] = preset(m.name, m.node_tree.nodes.get('Principled BSDF'))
    tris_before = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    bk.bake_hero(ob, SIZES.get(name, 256), presets, keep, name, os.environ.get('REBAKE_DEBUG'))
    # the vertex colours are baked into the albedo now; the engine would multiply them in again
    for a in list(ob.data.color_attributes):
        ob.data.color_attributes.remove(a)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, name + '.glb'), export_format='GLB', use_selection=True,
                              export_tangents=True, export_yup=True, export_apply=True)
    print('REBAKE_OK', name, tris_before, sorted(keep))


argv = sys.argv[sys.argv.index('--') + 1:]
src, out = argv[0], argv[1]
names = argv[2:] or DEFAULT_NAMES
os.makedirs(out, exist_ok=True)
for n in names:
    rebake(src, out, n)
