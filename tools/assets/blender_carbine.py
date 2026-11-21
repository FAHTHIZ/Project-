# SPDX-License-Identifier: Apache-2.0
"""Blender worker: modern carbine body for the PC-7 Lantern from the Vinish "Assault Rifle" model.

    blender -b --factory-startup --python tools/assets/blender_carbine.py -- <src.glb> <out_dir>

Source: https://models.vinish.dev/weapons/assault-rifle.glb (vinish.dev, CC BY 4.0; generic design,
no real make or markings): flat top rail, slotted handguard, muzzle device, adjustable stock, red
dot, separate magazine and charging handle, real size (0.88 m).

The PC-7 stays the game's fictional stun-pulse carbine (the magazine is its pulse cell); only its
look changes from the old procedural block. Writes pc7_body.glb (receiver, barrel, furniture,
optic, charging handle), pc7_cell.glb (magazine) and pc7_world.glb (everything, for pickups and
squad carry) in the PC-7 frame used by weapons.luau and the rigs: metres, glTF +Y up, muzzle
along -Z, origin at the right (grip) hand. Materials are renamed to the roles
blender_rebake.py understands, which then bakes AO, edge wear and CC0 scan detail into them.
Prints FRAME lines with the offsets the scripts need (muzzle, sight height, magazine well,
handguard grip point).

Blender axes: X right, Y forward (= glTF -Z), Z up (= glTF +Y).
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)

ROLE = {'Gun_Steel': 'Metal', 'Gun_Dark': 'MetalDark', 'Anodized_Black': 'Frame', 'Polymer_Black': 'Shell',
        'Polymer_Tan': 'ShellTan', 'Rubber': 'Grip', 'Lens': 'Lens', 'Dot_Red': 'Dot'}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=SRC)
obs = {o.name: o for o in bpy.context.scene.objects if o.type == 'MESH'}
for o in obs.values():   # bake node transforms into the meshes
    o.data.transform(o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    o.parent = None

# the source muzzle points along Blender -Y: turn it to +Y (the PC-7's forward)
turn = Matrix.Rotation(math.pi, 4, 'Z')
for o in obs.values():
    o.data.transform(turn)


def verts(o, mat=None, pred=None):
    out = []
    for p in o.data.polygons:
        if mat and o.material_slots[p.material_index].material.name != mat:
            continue
        for vi in p.vertices:
            v = o.data.vertices[vi].co
            if pred is None or pred(v):
                out.append(v.copy())
    return out


rifle = obs['Rifle']
barrel = verts(rifle, 'Gun_Dark') + verts(rifle, 'Gun_Steel')
muzzle_y = max(v.y for v in barrel)
front = [v for v in barrel if v.y > muzzle_y - 0.03]
bore_z = sum(v.z for v in front) / len(front)
dot = verts(rifle, 'Dot_Red')
sight_z = sum(v.z for v in dot) / len(dot)
# pistol grip: tan polymer below the receiver, behind the magazine well
grip = verts(rifle, 'Polymer_Tan', lambda v: v.z < 0.125 and v.y < 0.0)   # below the stock's toe
grip_y = sum(v.y for v in grip) / len(grip)
# the hand origin sits 4.5 cm under the bore at the grip, as on the old PC-7
origin = Vector((0.0, grip_y, bore_z - 0.045))
shift = Matrix.Translation(-origin)
for o in obs.values():
    o.data.transform(shift)

# collapse the adjustable stock 7 cm (how it is run with plate carriers; full length it fills the
# lower corner of the first-person view): tan furniture and the butt pad behind the receiver
COLLAPSE = float(os.environ.get('PC7_STOCK_COLLAPSE', '0.07'))
# move the stock rigidly: the tan/rubber mesh islands that lie wholly behind the pistol grip
# (a per-vertex cut kinks faces that straddle it; the buffer tube stays put inside the stock)
furn = [p for p in rifle.data.polygons
        if ROLE.get(rifle.material_slots[p.material_index].material.name.split('.')[0]) in ('ShellTan', 'Grip')]
parent = {}
def find(a):
    while parent.setdefault(a, a) != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
for p in furn:
    vs = list(p.vertices)
    for v in vs[1:]:
        parent[find(v)] = find(vs[0])
islands = {}
for p in furn:
    islands.setdefault(find(p.vertices[0]), set()).update(p.vertices)
stock_v = set()
for vs in islands.values():
    if max(rifle.data.vertices[v].co.y for v in vs) < -0.08:
        stock_v |= vs
print('FRAME islands', len(islands))
for vi in stock_v:
    rifle.data.vertices[vi].co.y += COLLAPSE
tan_all = verts(rifle, 'Polymer_Tan')
print('FRAME stock_moved', len(stock_v), 'tan y range', round(min(v.y for v in tan_all), 3), round(max(v.y for v in tan_all), 3))
# furniture colour: black stock and grip (a tan stock right under the camera, lit by the weapon
# light, reads as a big flat block in first person); the magazine keeps its tan polymer
if os.environ.get('PC7_FURNITURE', 'black') == 'black':
    blk = next(i for i, s in enumerate(rifle.material_slots) if s.material.name.split('.')[0] == 'Polymer_Black') \
        if any(s.material.name.split('.')[0] == 'Polymer_Black' for s in rifle.material_slots) else None
    if blk is None:
        src_m = next(s.material for s in obs['Magazine'].material_slots if s.material.name.split('.')[0] == 'Polymer_Black')
        rifle.data.materials.append(src_m); blk = len(rifle.material_slots) - 1
    for p in rifle.data.polygons:
        if rifle.material_slots[p.material_index].material.name.split('.')[0] == 'Polymer_Tan':
            p.material_index = blk
# the source optic's lens is an opaque disc: aiming down sights saw a dark circle. Drop it so the
# tube is open (as a real red dot reads at arm's length) and the red dot floats in it
import bmesh  # noqa: E402
bm = bmesh.new(); bm.from_mesh(rifle.data)
lens_i = [i for i, s in enumerate(rifle.material_slots) if s.material.name.split('.')[0] == 'Lens']
gone = [f for f in bm.faces if f.material_index in lens_i]
bmesh.ops.delete(bm, geom=gone, context='FACES')
bm.to_mesh(rifle.data); bm.free()
print('FRAME lens_faces_removed', len(gone))
mag = obs['Magazine']
mv = verts(mag)
guard = verts(rifle, 'Anodized_Black', lambda v: v.z < -0.01 and v.y > 0.12)
guard_bottom = min(v.z for v in guard) if guard else -0.03
# glTF frame values (x, y, -z <- Blender x, z, y)
print('FRAME muzzle', 0.0, round(bore_z - origin.z, 4), round(-(muzzle_y - origin.y), 4))
print('FRAME sight_height', round(sight_z - origin.z, 4))
print('FRAME cell_box', [round(min(v.x for v in mv), 3), round(min(v.z for v in mv), 3), round(-max(v.y for v in mv), 3)],
      [round(max(v.x for v in mv), 3), round(max(v.z for v in mv), 3), round(-min(v.y for v in mv), 3)])
print('FRAME guard_bottom', round(guard_bottom, 4))

for o in obs.values():
    for s in o.material_slots:
        m = s.material
        if m and not m.name.startswith('pc7'):
            base = m.name.split('.')[0]
            m.name = ('pc7mag_' if o is mag else 'pc7_') + ROLE.get(base, base)
# magazine materials are copies so the body and the cell bake into their own textures
for s in mag.material_slots:
    if s.material and not s.material.name.startswith('pc7mag_'):
        c = s.material.copy(); c.name = 'pc7mag_' + s.material.name.split('_', 1)[1]; s.material = c


def shade(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))


def export(name, objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + '.glb'), export_format='GLB', use_selection=True,
                              export_yup=True, export_apply=True)
    print('CARBINE_OK', name, sum(len(p.vertices) - 2 for o in objs for p in o.data.polygons))


for o in obs.values():
    shade(o)
export('pc7_body', [rifle, obs['Charging_Handle']])
export('pc7_cell', [mag])
export('pc7_world', [rifle, obs['Charging_Handle'], mag])
