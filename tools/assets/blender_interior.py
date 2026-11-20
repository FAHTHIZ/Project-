# SPDX-License-Identifier: Apache-2.0
"""Blender worker: one photoscanned Poly Haven prop -> a mobile-budget interior GLB.

Run by tools/assets/build_interior_props.py, never directly:
    blender -b --factory-startup -P tools/assets/blender_interior.py -- job.json

Unlike blender_prop.py (forest scatter, one material per primitive), interior props keep their
source materials (a desk keeps its steel and its laminate). Job keys:
    src        source .gltf
    out        output .glb
    objects    optional list of object-name prefixes to keep (a trailing '$' means an exact name)
    tris       triangle budget for the whole prop (collapse decimation, per object, proportional)
    tex_size   largest texture edge (px)
    scale      uniform scale (Poly Haven models are real-world size; default 1)
    fit        optional {"axis": "height"|"length"|"width", "size": metres}
    yaw        degrees about the vertical axis, applied before the pivot
    pivot      "base" (footprint centre at y = 0, default) | "back" (base, and the back face at
               z = 0 so wall-mounted props sit flush) | "top" (hang from y = 0)
Prints PROP_OK <out> <tris> and a BOUNDS json line (game axes, metres) for the level builder.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=job['src'])

want = job.get('objects')
objs = []
for o in list(bpy.data.objects):
    if o.type == 'MESH' and (not want or any((o.name == w[:-1] or o.name.startswith(w[:-1] + '.')) if w.endswith('$')
                                             else o.name.startswith(w) for w in want)):
        objs.append(o)
for o in list(bpy.data.objects):
    if o not in objs:
        if o.type != 'MESH':
            for c in o.children:
                mw = c.matrix_world.copy()
                c.parent = None
                c.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)
if not objs:
    raise SystemExit('no mesh objects matched')
for o in objs:
    mw = o.matrix_world.copy()
    o.parent = None
    o.data = o.data.copy()
    o.data.transform(mw)
    o.matrix_world = Matrix.Identity(4)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


total = sum(tris(o) for o in objs)
budget = job.get('tris')
if budget and total > budget:
    ratio = max(budget / total, 0.004)
    for o in objs:
        m = o.modifiers.new('dec', 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = ratio
        m.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)

bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
if len(objs) > 1:
    bpy.ops.object.join()
root = bpy.context.view_layer.objects.active
root.name = os.path.splitext(os.path.basename(job['out']))[0]

# blender Z up; game Y up (x' = x, y' = z, z' = -y)
root.data.transform(Matrix.Rotation(math.radians(job.get('yaw', 0.0)), 4, 'Z'))


def bounds():
    mn = Vector((1e9, 1e9, 1e9))
    mx = -mn
    for v in root.data.vertices:
        mn = Vector(map(min, mn, v.co))
        mx = Vector(map(max, mx, v.co))
    return mn, mx


mn, mx = bounds()
k = job.get('scale', 1.0)
fit = job.get('fit')
if fit:
    dims = {'height': mx.z - mn.z, 'length': mx.x - mn.x, 'width': mx.y - mn.y}
    k = fit['size'] / max(dims[fit['axis']], 1e-6)
pivot = job.get('pivot', 'base')
c = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
if pivot == 'back':
    c.y = mx.y          # game +Z (out of the wall) is blender -Y: the back face is blender max Y
elif pivot == 'top':
    c.z = mx.z
root.data.transform(Matrix.Scale(k, 4) @ Matrix.Translation(-c))
root.data.update()

size = job.get('tex_size', 512)
for img in bpy.data.images:
    if img.size[0] > size or img.size[1] > size:
        s = size / max(img.size[0], img.size[1])
        img.scale(max(1, int(img.size[0] * s)), max(1, int(img.size[1] * s)))
for m in root.data.materials:
    if m:
        m.use_backface_culling = True

os.makedirs(os.path.dirname(job['out']), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=job['out'], export_format='GLB', use_selection=False, export_yup=True,
                          export_apply=True, export_image_format='AUTO', export_jpeg_quality=86,
                          export_texcoords=True, export_normals=True, export_tangents=False,
                          export_materials='EXPORT', export_animations=False, export_skins=False,
                          export_morph=False, export_cameras=False, export_lights=False)
mn, mx = bounds()
# game axes: x = x, y = blender z, z = -blender y
print('BOUNDS ' + json.dumps({'min': [mn.x, mn.z, -mx.y], 'max': [mx.x, mx.z, -mn.y]}))
print('PROP_OK', job['out'], tris(root), len(root.data.materials))
