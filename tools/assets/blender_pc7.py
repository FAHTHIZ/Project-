# SPDX-License-Identifier: Apache-2.0
"""Blender worker: hard-surface "PC-7 Lantern" pulse carbine (original, fictional design).

    blender -b --factory-startup --python tools/assets/blender_pc7.py -- <out_dir>

Writes pc7_body.glb, pc7_cell.glb and pc7_world.glb. Same layout as the procedural original in
tools/props/build_weapons.py (glTF frame: metres, +Y up, muzzle along -Z at z = -0.5, origin at
the grip hand; the cell sits at z ~ -0.105 below the receiver) so the viewmodel script, reload
animation and muzzle effects need no change. What is new is the construction: extruded side
profiles with real chamfers (bevel modifier, harden normals + weighted normals), vent slots cut
through the shroud, a toothed top rail, panel seams, screws and a hooded sight, i.e. the edge
highlights and small-scale breakup that make a viewmodel read as a manufactured object.

Blender axes: X right, Y forward (= glTF -Z), Z up (= glTF +Y).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

OUT = sys.argv[sys.argv.index('--') + 1]


def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c]


MATS = {}


def mat(name, color, rough, metal=0.0, emit=None, strength=1.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = strength
    MATS[name] = m
    return m


def finish(ob, bevel, segs=2, angle=35):
    if bevel > 0:
        md = ob.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = segs
        md.limit_method = 'ANGLE'; md.angle_limit = math.radians(angle); md.harden_normals = True
        md.miter_outer = 'MITER_ARC'
    ob.modifiers.new('wn', 'WEIGHTED_NORMAL').keep_sharp = True
    for p in ob.data.polygons: p.use_smooth = True
    return ob


def new_obj(name, bm, material):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob


def prism(name, prof, half_w, material, bevel=0.004, x=0.0, segs=2, angle=35):
    """Extrude a side profile [(y, z), ...] (counter-clockwise seen from +X) across +-half_w."""
    bm = bmesh.new()
    vs = [bm.verts.new((x - half_w, y, z)) for y, z in prof]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    bmesh.ops.translate(bm, vec=(2 * half_w, 0, 0), verts=[v for v in r['geom'] if isinstance(v, bmesh.types.BMVert)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return finish(new_obj(name, bm, material), bevel, segs, angle)


def box(name, c, h, material, bevel=0.003, segs=2):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((c[0] + v.co.x * 2 * h[0], c[1] + v.co.y * 2 * h[1], c[2] + v.co.z * 2 * h[2]))
    return finish(new_obj(name, bm, material), bevel, segs)


def cyl(name, p0, p1, r0, material, r1=None, verts=24, bevel=0.002, segs=2, cap=True):
    r1 = r0 if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1); d = p1 - p0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=verts, radius1=r0, radius2=r1, depth=d.length)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4(), verts=bm.verts)
    return finish(new_obj(name, bm, material), bevel, segs)


def cut(target, cutters):
    for c in cutters:
        md = target.modifiers.new('cut', 'BOOLEAN'); md.object = c; md.operation = 'DIFFERENCE'; md.solver = 'EXACT'
        c.hide_set(True); c.hide_render = True
    # boolean before bevel so the slots get chamfered too
    while target.modifiers[0].type != 'BOOLEAN':
        bpy.context.view_layer.objects.active = target
        bpy.ops.object.modifier_move_to_index(modifier=target.modifiers[0].name, index=len(target.modifiers) - 1)
    return target


def apply_all(obs):
    for ob in obs:
        bpy.context.view_layer.objects.active = ob
        for md in list(ob.modifiers):
            bpy.ops.object.modifier_apply(modifier=md.name)


SHELL = srgb('#3a4046'); DARK = srgb('#22262a'); TRIM = srgb('#6d7378'); ACCENT = srgb('#c48a2c')
GLOW = (0.35, 0.9, 1.0)
M_SHELL = mat('pc7_Shell', SHELL, 0.42, 0.1)
M_DARK = mat('pc7_ShellDark', DARK, 0.5, 0.1)
M_METAL = mat('pc7_Metal', srgb('#4a4e52'), 0.32, 0.9)
M_GRIP = mat('pc7_Grip', DARK, 0.85)
M_TRIM = mat('pc7_Trim', TRIM, 0.38, 0.6)
M_ACC = mat('pc7_Accent', ACCENT, 0.45, 0.0)
M_GLOW = mat('pc7_Glow', (1, 1, 1), 0.3, emit=GLOW, strength=3.0)
M_LENS = mat('pc7_Lens', srgb('#0d1418'), 0.05, 0.6)
M_CSHELL = mat('pc7cell_Shell', TRIM, 0.5, 0.2)
M_CGLOW = mat('pc7cell_Glow', (1, 1, 1), 0.3, emit=GLOW, strength=2.5)

body, cell = [], []
ZC = 0.045  # bore height (glTF y)

# --- receiver: one extruded profile with a sloped nose and a magwell step ---------------------
rec = prism('receiver', [(-0.12, 0.004), (-0.04, 0.0), (0.03, -0.012), (0.135, -0.012), (0.17, 0.004),
                         (0.255, 0.012), (0.285, 0.03), (0.285, 0.066), (0.262, 0.082), (-0.10, 0.084),
                         (-0.12, 0.074)], 0.029, M_SHELL, bevel=0.0035, segs=3)
seams = [box(f'seam{i}', (s * 0.0295, y, 0.04), (0.0012, 0.0008, 0.05), M_SHELL, bevel=0)
         for i, (s, y) in enumerate([(sx, yy) for sx in (-1, 1) for yy in (-0.02, 0.2)])]
seams += [box(f'seamh{s}', (s * 0.0295, 0.09, 0.062), (0.0012, 0.11, 0.0008), M_SHELL, bevel=0) for s in (-1, 1)]
cut(rec, seams); body.append(rec)
# lower receiver / trigger housing (darker polymer)
body.append(prism('lower', [(-0.11, 0.006), (-0.11, -0.006), (0.03, -0.016), (0.13, -0.016), (0.13, 0.006)],
                  0.0255, M_DARK, bevel=0.003))
# side panels with the amber stripe, screws
for sx in (-1, 1):
    body.append(box(f'panel{sx}', (sx * 0.0305, 0.08, 0.05), (0.0018, 0.09, 0.017), M_TRIM, bevel=0.0012))
    body.append(box(f'stripe{sx}', (sx * 0.031, 0.16, 0.03), (0.0015, 0.04, 0.004), M_ACC, bevel=0.0008))
    for y, z in ((0.0, 0.062), (0.16, 0.062), (0.0, 0.038), (0.16, 0.038)):
        body.append(cyl(f'screw{sx}{y}{z}', (sx * 0.031, y, z), (sx * 0.0335, y, z), 0.0026, M_METAL, verts=10, bevel=0.0006, segs=1))
# ejection-style vent block on the right
vent = box('ventblk', (0.0285, -0.06, 0.058), (0.003, 0.03, 0.012), M_DARK, bevel=0.001)
cut(vent, [box(f'vs{i}', (0.032, -0.08 + i * 0.01, 0.058), (0.003, 0.0025, 0.008), M_DARK, bevel=0) for i in range(5)])
body.append(vent)

# --- top rail with teeth, hooded optic ------------------------------------------------------
rail = box('rail', (0, 0.07, 0.0905), (0.0105, 0.13, 0.0055), M_METAL, bevel=0.0012)
cut(rail, [box(f'rt{i}', (0, -0.05 + i * 0.0105, 0.095), (0.012, 0.0028, 0.0025), M_METAL, bevel=0) for i in range(23)])
body.append(rail)
body.append(cyl('optic', (0, 0.025, 0.113), (0, 0.105, 0.113), 0.0148, M_DARK, verts=28, bevel=0.0015))
body.append(cyl('optic_hood', (0, 0.095, 0.113), (0, 0.112, 0.113), 0.0162, M_DARK, verts=28, bevel=0.001))
body.append(cyl('optic_lens', (0, 0.111, 0.113), (0, 0.1125, 0.113), 0.0128, M_LENS, verts=28, bevel=0))
body.append(cyl('optic_lens_r', (0, 0.0235, 0.113), (0, 0.025, 0.113), 0.0118, M_LENS, verts=28, bevel=0))
body.append(box('optic_mount', (0, 0.065, 0.1), (0.009, 0.022, 0.006), M_METAL, bevel=0.001))
for y in (0.045, 0.085):
    body.append(cyl(f'opt_knob{y}', (0.014, y, 0.113), (0.02, y, 0.113), 0.004, M_METAL, verts=12, bevel=0.0008, segs=1))
body.append(cyl('sight_dot', (0, 0.1005, 0.1135), (0, 0.1015, 0.1135), 0.0032, M_GLOW, verts=12, bevel=0))

# --- emitter shroud: tapered tube with vent slots, glowing coils inside ----------------------
shroud = cyl('shroud', (0, 0.27, ZC), (0, 0.49, ZC), 0.026, M_DARK, r1=0.023, verts=32, bevel=0.0015)
slots = []
for i in range(5):
    for a in (0, 60, 120, 180, 240, 300):
        ra = math.radians(a); y = 0.30 + i * 0.035
        s = box(f'sl{i}_{a}', (math.cos(ra) * 0.025, y, ZC + math.sin(ra) * 0.025), (0.006, 0.011, 0.006), M_DARK, bevel=0)
        s.rotation_euler = (0, -ra, 0); slots.append(s)
cut(shroud, slots); body.append(shroud)
body.append(cyl('shroud_inner', (0, 0.28, ZC), (0, 0.488, ZC), 0.0185, M_METAL, verts=20, bevel=0, cap=True))
for i, y in enumerate((0.31, 0.36, 0.41)):
    body.append(cyl(f'coil{i}', (0, y, ZC), (0, y + 0.012, ZC), 0.0215, M_GLOW, verts=24, bevel=0))
body.append(cyl('collar', (0, 0.262, ZC), (0, 0.285, ZC), 0.0285, M_METAL, verts=32, bevel=0.0018))
mz = cyl('muzzle', (0, 0.478, ZC), (0, 0.503, ZC), 0.0275, M_METAL, r1=0.026, verts=32, bevel=0.0018)
cut(mz, [cyl('mzbore', (0, 0.495, ZC), (0, 0.51, ZC), 0.016, M_METAL, verts=24, bevel=0)])
body.append(mz)
body.append(cyl('emitter_face', (0, 0.496, ZC), (0, 0.4985, ZC), 0.0155, M_GLOW, verts=24, bevel=0))

# --- stock: skeletal profile with a lightening cut, rubber butt pad --------------------------
stock = prism('stock', [(-0.12, 0.07), (-0.12, 0.012), (-0.2, -0.03), (-0.232, -0.036), (-0.232, 0.084),
                        (-0.2, 0.084), (-0.13, 0.078)], 0.021, M_SHELL, bevel=0.003, segs=3)
cut(stock, [prism('stock_hole', [(-0.145, 0.06), (-0.145, 0.03), (-0.205, 0.0), (-0.205, 0.06)], 0.03, M_SHELL, bevel=0.0)])
body.append(stock)
body.append(prism('buttpad', [(-0.232, -0.04), (-0.248, -0.038), (-0.248, 0.086), (-0.232, 0.088)], 0.0235, M_GRIP, bevel=0.004, segs=3))

# --- pistol grip, trigger guard, trigger, foregrip ------------------------------------------
grip = prism('grip', [(0.016, -0.004), (-0.022, -0.004), (-0.046, -0.088), (-0.01, -0.094), (0.004, -0.06)],
             0.0165, M_GRIP, bevel=0.0065, segs=3, angle=25)
body.append(grip)
guard = prism('guard', [(0.07, -0.01), (0.07, -0.036), (0.0, -0.036), (0.0, -0.028), (0.062, -0.028), (0.062, -0.01)],
              0.0045, M_DARK, bevel=0.0012)
body.append(guard)
body.append(prism('trigger', [(0.041, -0.012), (0.046, -0.012), (0.04, -0.026), (0.035, -0.025)], 0.0028, M_METAL, bevel=0.0008))
fg = cyl('foregrip', (0, 0.215, -0.005), (0, 0.205, -0.075), 0.0155, M_GRIP, r1=0.0145, verts=20, bevel=0.003)
body.append(fg)
body.append(cyl('fg_cap', (0, 0.205, -0.075), (0, 0.204, -0.082), 0.0165, M_DARK, verts=20, bevel=0.002))
body.append(box('fg_mount', (0, 0.215, 0.006), (0.012, 0.024, 0.01), M_METAL, bevel=0.0012))

# --- removable charge cell (separate part) ---------------------------------------------------
c = box('cell', (0, 0.105, -0.04), (0.017, 0.028, 0.045), M_CSHELL, bevel=0.003, segs=3)
cut(c, [box(f'cg{i}', (0, 0.105, -0.06 + i * 0.012), (0.02, 0.0285, 0.0012), M_CSHELL, bevel=0) for i in range(3)])
cell.append(c)
cell.append(box('cell_base', (0, 0.105, -0.085), (0.019, 0.03, 0.007), M_DARK, bevel=0.0025, segs=3))
for sx in (-1, 1):
    cell.append(box(f'cell_glow{sx}', (sx * 0.0172, 0.105, -0.04), (0.0012, 0.006, 0.03), M_CGLOW, bevel=0.0005))

apply_all(body + cell)
for ob in list(bpy.context.scene.objects):
    if ob.hide_get():
        bpy.data.objects.remove(ob)


def export(obs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True, export_texcoords=True, export_normals=True,
                              export_materials='EXPORT', export_extras=False, export_lights=False, export_cameras=False)


def joined(obs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.join(); ob = bpy.context.active_object; ob.name = name
    return ob


b = joined(body, 'pc7_body'); export([b], 'pc7_body')
cc = joined(cell, 'pc7_cell'); export([cc], 'pc7_cell')
# world variant: both parts merged, laid on the left side (glTF rot_z(90), then x += 0.035)
w = b.copy(); w.data = b.data.copy(); bpy.context.collection.objects.link(w)
wc = cc.copy(); wc.data = cc.data.copy(); bpy.context.collection.objects.link(wc)
w = joined([w, wc], 'pc7_world')
w.data.transform(Matrix(((0, 0, -1, 0.035), (0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 0, 1))))
for mm in w.data.materials:
    pass
export([w], 'pc7_world')
tris = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in (b, cc, w)}
print('PC7_OK', tris)
