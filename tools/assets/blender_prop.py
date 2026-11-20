# SPDX-License-Identifier: Apache-2.0
"""Blender worker: turn photoscanned source meshes into a game-ready, mobile-budget GLB.

Run by tools/assets/build_photoreal_props.py, never directly:
    blender -b --factory-startup -P tools/assets/blender_prop.py -- job.json

A job (JSON) describes one output GLB:
    out          output .glb path
    tex_size     largest texture edge (px)
    groups       list of primitives, in output order; each becomes one mesh/material in the GLB:
                   name       material name in the output
                   parts      [{src, objects:[names], offset:[x,y,z] (game metres, Y up),
                                yaw (deg), scale}]
                   tris       triangle budget for this primitive (collapse decimation)
                   alpha      "mask" | "opaque" | "blend" (default: keep the source)
                   double     double-sided
    fit          {"axis": "height"|"length"|"width", "size": metres} uniform scale fit, measured
                 on the merged result (game axes: height = Y, length = X, width = Z)
    pivot        "base" (default: footprint centre at y = 0) | "center" | "keep"
    sink         metres to push the result below y = 0 (hides scan edges in the ground)

Every source is CC0 (Poly Haven); see docs/ASSET_PROVENANCE.md.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_part(part):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=part['src'])
    new = [o for o in bpy.data.objects if o not in before]
    want = part.get('objects')
    keep = []
    for o in new:
        if o.type == 'MESH' and (not want or o.name in want or any(o.name.startswith(w) for w in want)):
            keep.append(o)
    # bake parents/transforms into the mesh data, drop everything else
    for o in keep:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in new:
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    for o in keep:
        o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    # each part on its own footprint centre and base (sets are laid out side by side)
    mn = Vector((1e9, 1e9, 1e9))
    mx = -mn
    for o in keep:
        for v in o.data.vertices:
            mn = Vector(map(min, mn, v.co))
            mx = Vector(map(max, mx, v.co))
    if keep:
        c = Matrix.Translation(-Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z)))
        for o in keep:
            o.data.transform(c)
    # game (Y up) -> blender (Z up): x' = x, y' = -z, z' = y
    off = part.get('offset', [0, 0, 0])
    yaw = math.radians(part.get('yaw', 0.0))
    s = part.get('scale', 1.0)
    m = Matrix.Translation(Vector((off[0], -off[2], off[1]))) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Scale(s, 4)
    for o in keep:
        o.data.transform(m)
    return keep


def tri_count(objs):
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in objs)


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = name
    o.data.name = name
    return o


def decimate(o, tris):
    have = tri_count([o])
    if not tris or have <= tris:
        return
    mod = o.modifiers.new('dec', 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(tris / have, 0.002)
    mod.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier=mod.name)


def unify_material(o, name, group):
    mats = [m for m in o.data.materials if m]
    if not mats:
        return
    base = mats[0]
    base.name = name
    # one material per primitive: every face uses the first material
    for p in o.data.polygons:
        p.material_index = 0
    while len(o.data.materials) > 1:
        o.data.materials.pop(index=len(o.data.materials) - 1)
    a = group.get('alpha')
    if a == 'mask':
        base.blend_method = 'CLIP'
        base.alpha_threshold = group.get('cutoff', 0.5)
        base.surface_render_method = 'DITHERED'
    elif a == 'opaque':
        base.blend_method = 'OPAQUE'
        bsdf = base.node_tree.nodes.get('Principled BSDF')
        if bsdf and bsdf.inputs['Alpha'].is_linked:
            base.node_tree.links.remove(bsdf.inputs['Alpha'].links[0])
    base.use_backface_culling = not group.get('double', False)


def shrink_images(size):
    for img in bpy.data.images:
        if img.size[0] > size or img.size[1] > size:
            k = size / max(img.size[0], img.size[1])
            img.scale(max(1, int(img.size[0] * k)), max(1, int(img.size[1] * k)))


reset()
prims = []
for gi, g in enumerate(job['groups']):
    objs = []
    for part in g['parts']:
        objs += import_part(part)
    if not objs:
        raise SystemExit(f"group {g['name']}: no source objects matched")
    o = join(objs, f"{g['name']}")
    decimate(o, g.get('tris'))
    unify_material(o, g['name'], g)
    prims.append(o)

# merged bounds (blender axes)
mn = Vector((1e9, 1e9, 1e9))
mx = -mn
for o in prims:
    for v in o.data.vertices:
        mn = Vector(map(min, mn, v.co))
        mx = Vector(map(max, mx, v.co))
fit = job.get('fit')
k = 1.0
if fit:
    dims = {'height': mx.z - mn.z, 'length': mx.x - mn.x, 'width': mx.y - mn.y}
    k = fit['size'] / max(dims[fit['axis']], 1e-6)
pivot = job.get('pivot', 'base')
c = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
if pivot == 'center':
    c.z = (mn.z + mx.z) / 2
elif pivot == 'keep':
    c = Vector((0, 0, 0))
sink = job.get('sink', 0.0)
T = Matrix.Translation(Vector((0, 0, -sink))) @ Matrix.Scale(k, 4) @ Matrix.Translation(-c)
for o in prims:
    o.data.transform(T)
    o.data.update()

shrink_images(job.get('tex_size', 1024))

# one mesh object per primitive, exported in order; glTF exporter writes one mesh per object,
# so join into one object with ordered material slots instead (one mesh, N primitives)
if len(prims) > 1:
    bpy.ops.object.select_all(action='DESELECT')
    for o in prims:
        o.select_set(True)
    bpy.context.view_layer.objects.active = prims[0]
    bpy.ops.object.join()
root = bpy.context.view_layer.objects.active if len(prims) > 1 else prims[0]
root.name = os.path.splitext(os.path.basename(job['out']))[0]
# keep the material order identical to the group order
order = [g['name'] for g in job['groups']]
slots = [s.material.name for s in root.material_slots]
remap = {i: order.index(n) for i, n in enumerate(slots) if n in order}
new_mats = [bpy.data.materials[n] for n in order]
idx = [remap.get(p.material_index, 0) for p in root.data.polygons]
root.data.materials.clear()
for m in new_mats:
    root.data.materials.append(m)
for p, i in zip(root.data.polygons, idx):
    p.material_index = i

os.makedirs(os.path.dirname(job['out']), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=job['out'], export_format='GLB', use_selection=False, export_yup=True,
                          export_apply=True, export_image_format='AUTO', export_jpeg_quality=88,
                          export_texcoords=True, export_normals=True, export_tangents=False,
                          export_materials='EXPORT', export_animations=False, export_skins=False,
                          export_morph=False, export_cameras=False, export_lights=False)
print('PROP_OK', job['out'], tri_count([root]), [m.name for m in root.data.materials])
