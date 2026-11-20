# SPDX-License-Identifier: Apache-2.0
"""Blender worker: the squad's battery LED camp lantern (briefing table practical light).

    blender -b --factory-startup -P tools/assets/blender_lantern.py -- game/assets/models/structures/camp_lantern.glb

Modelled from scratch to real dimensions of a common 1000-lumen field lantern: 0.235 m tall,
0.11 m body, matte black ABS base and cap with grip ribs, a ridged frosted polycarbonate
diffuser (the emissive part), rubber foot ring and a fold-down steel wire handle.
No textures: three small PBR factor materials, ~1.5k triangles. Origin at the base centre,
Y up in the exported glTF. Lit by a point light placed by tools/world/night.py.
"""
import math
import sys

import bpy
import bmesh

out = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, color, rough, metal=0.0, emit=None, strength=0.0, transmission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    return m


ABS = mat('Lantern_Shell', (0.018, 0.019, 0.02), 0.62)
RUB = mat('Lantern_Rubber', (0.012, 0.012, 0.012), 0.88)
# warm 3000 K LEDs behind frosted polycarbonate; the light itself is a game point light
LENS = mat('Lantern_Diffuser', (0.86, 0.8, 0.7), 0.35, emit=(1.0, 0.74, 0.46), strength=6.0)
WIRE = mat('Lantern_Wire', (0.55, 0.55, 0.56), 0.4, metal=1.0)


def lathe(name, profile, segs, material, ribs=0, rib_depth=0.0, rib_rows=None):
    """Revolve (r, z) points; optional vertical ribs push alternate columns of rib_rows inwards."""
    bm = bmesh.new()
    rings = []
    for i, (r, z) in enumerate(profile):
        ring = []
        for s in range(segs):
            a = 2 * math.pi * s / segs
            rr = r
            if ribs and rib_rows and i in rib_rows and (s * 2 * ribs // segs) % 2 == 0:
                rr = r - rib_depth
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for s in range(segs):
            bm.faces.new((rings[i][s], rings[i][(s + 1) % segs], rings[i + 1][(s + 1) % segs], rings[i + 1][s]))
    # caps
    if profile[0][0] > 0:
        bm.faces.new(list(reversed(rings[0])))
    if profile[-1][0] > 0:
        bm.faces.new(rings[-1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(material)
    for p in me.polygons:
        p.use_smooth = True
    return ob


H = 0.235
parts = []
# rubber foot ring
parts.append(lathe('Foot', [(0.050, 0.0), (0.056, 0.002), (0.057, 0.008), (0.055, 0.012)], 32, RUB))
# base: battery housing with grip ribs (8 flats) and a switch collar
parts.append(lathe('Base', [(0.053, 0.010), (0.055, 0.016), (0.055, 0.060), (0.054, 0.072), (0.050, 0.078),
                            (0.047, 0.082)], 48, ABS, ribs=12, rib_depth=0.0025, rib_rows={1, 2}))
# diffuser: a slightly barrelled ridged column
dz = [(0.043, 0.082), (0.046, 0.095), (0.047, 0.125), (0.047, 0.165), (0.046, 0.195), (0.043, 0.205)]
parts.append(lathe('Diffuser', dz, 48, LENS, ribs=24, rib_depth=0.0018, rib_rows={1, 2, 3, 4}))
# cap with a domed top
parts.append(lathe('Cap', [(0.046, 0.203), (0.052, 0.208), (0.052, 0.220), (0.044, 0.229), (0.028, 0.234),
                           (0.0, H)], 48, ABS))
# two hinge lugs
for sx in (-1, 1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.006, depth=0.008,
                                        location=(sx * 0.050, 0, 0.222), rotation=(0, math.pi / 2, 0))
    o = bpy.context.object
    o.data.materials.append(ABS)
    parts.append(o)
# wire handle folded down along the cap (a half loop, 3 mm steel)
curve = bpy.data.curves.new('HandleCurve', 'CURVE')
curve.dimensions = '3D'
curve.bevel_depth = 0.0016
curve.bevel_resolution = 2
sp = curve.splines.new('POLY')
pts = []
for k in range(17):
    a = math.pi * k / 16
    # rests on the cap at a 20 degree lean, as a dropped handle does
    x = 0.054 * math.cos(a)
    y = 0.054 * math.sin(a) * math.cos(math.radians(20))
    z = 0.222 + 0.054 * math.sin(a) * math.sin(math.radians(20)) * 0.4
    pts.append((x, -y * 0.25 - 0.004, z + 0.004 * math.sin(a)))
sp.points.add(len(pts) - 1)
for p, c in zip(sp.points, pts):
    p.co = (*c, 1)
ho = bpy.data.objects.new('Handle', curve)
bpy.context.collection.objects.link(ho)
bpy.context.view_layer.objects.active = ho
ho.select_set(True)
bpy.ops.object.convert(target='MESH')
ho = bpy.context.object
ho.data.materials.append(WIRE)
parts.append(ho)

# join by material into one object (four primitives in the glTF)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[1]
bpy.ops.object.join()
ob = bpy.context.object
ob.name = 'camp_lantern'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# soften silhouette edges a little
wn = ob.modifiers.new('wn', 'WEIGHTED_NORMAL')
wn.keep_sharp = True
bpy.ops.object.modifier_apply(modifier='wn')
tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
print('camp_lantern tris', tris)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True, export_yup=True,
                          export_apply=True, export_materials='EXPORT')
