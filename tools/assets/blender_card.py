# SPDX-License-Identifier: Apache-2.0
"""Blender worker: bake a foliage card (unlit albedo + alpha) from a photoscanned plant.

    blender -b --factory-startup --python tools/assets/blender_card.py -- job.json

job = {"src": ".gltf", "objects": [names] (optional), "out": "card.png", "size": [w, h],
       "center": [x, y, z] (Blender Z-up world), "view": [dx, dy, dz] (camera looks along this),
       "up": [ux, uy, uz], "width": ortho width m, "depth": slab thickness m,
       "info": true (print bounds only)}

Workbench, flat lighting, texture colour: the card stores the scan's albedo, the engine lights it.
"""
import json
import sys

import bpy
from mathutils import Vector, Matrix

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=job['src'])
objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
if job.get('objects'):
    for o in objs:
        if o.name not in job['objects']:
            bpy.data.objects.remove(o, do_unlink=True)
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']

if job.get('info'):
    for o in objs:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        lo = [min(v[i] for v in bb) for i in range(3)]; hi = [max(v[i] for v in bb) for i in range(3)]
        print('CARD_INFO', o.name, [round(x, 3) for x in lo], [round(x, 3) for x in hi], len(o.data.polygons),
              [m.name for m in o.data.materials])
    sys.exit(0)

# alpha-clip every material so leaf silhouettes come from the scan's alpha
for m in bpy.data.materials:
    try:
        m.blend_method = 'CLIP'
    except Exception:
        pass
    m.alpha_threshold = 0.5

sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'FLAT'
sh.color_type = 'TEXTURE'
sh.show_backface_culling = False
sh.show_object_outline = False
sh.show_cavity = False
sh.show_shadows = False
sc.render.film_transparent = True
sc.render.resolution_x, sc.render.resolution_y = job['size']
sc.render.resolution_percentage = 100
sc.render.filter_size = 1.0
sc.display.render_aa = '16'
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGBA'

cam_data = bpy.data.cameras.new('card')
cam_data.type = 'ORTHO'
cam_data.ortho_scale = job['width']
cam = bpy.data.objects.new('card', cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
view = Vector(job['view']).normalized()
up = Vector(job.get('up', [0, 0, 1]))
right = view.cross(up).normalized()
up = right.cross(view).normalized()
center = Vector(job['center'])
depth = job.get('depth', 2.0)
pos = center - view * (depth * 0.5 + 0.01)
rot = Matrix((right, up, -view)).transposed()
cam.matrix_world = Matrix.Translation(pos) @ rot.to_4x4()
cam_data.clip_start = 0.01
cam_data.clip_end = depth + 0.01
sc.render.filepath = job['out']
bpy.ops.render.render(write_still=True)
print('CARD_OK', job['out'])
