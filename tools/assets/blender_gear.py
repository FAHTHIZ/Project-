# SPDX-License-Identifier: Apache-2.0
"""Blender stage of tools/assets/build_modern_kit.py: prepare the modern combat-kit body.

    blender -b --factory-startup --python tools/assets/blender_gear.py -- job.json

job.json: {"glb": soldier-rigged.glb, "out": kit.npz, "ratio": 0.065, "bake": normal.png | null,
           "bake_size": 2048}

Imports the rigged soldier in its bind (rest) pose, decimates a copy for the phone and, when
asked, bakes the full-resolution mesh *and* its own normal map into a tangent-space normal map on
the decimated copy's UVs (Decimate keeps the source UV layout, so the colour and roughness maps
still apply unchanged). Writes positions/normals/UVs/triangles in glTF space (Y up, +Z forward),
skin weights merged onto the game's 21 joints and the source rig's joint positions.
"""
import json
import sys

import bpy
import numpy as np

JOINTS = ["Hips", "Spine", "Chest", "Neck", "Head", "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
          "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R", "UpperLeg.L", "LowerLeg.L", "Foot.L", "Toe.L",
          "UpperLeg.R", "LowerLeg.R", "Foot.R", "Toe.R"]
# source rig (Hips > Spine02 > Spine01 > Spine > neck > Head) -> game rig
MAP = {'Hips': 'Hips', 'Spine02': 'Spine', 'Spine01': 'Chest', 'Spine': 'Chest', 'neck': 'Neck',
       'Head': 'Head', 'head_end': 'Head', 'headfront': 'Head'}
for s, d in (('Left', 'L'), ('Right', 'R')):
    MAP.update({f'{s}Shoulder': f'Shoulder.{d}', f'{s}Arm': f'UpperArm.{d}', f'{s}ForeArm': f'LowerArm.{d}',
                f'{s}Hand': f'Hand.{d}', f'{s}UpLeg': f'UpperLeg.{d}', f'{s}Leg': f'LowerLeg.{d}',
                f'{s}Foot': f'Foot.{d}', f'{s}ToeBase': f'Toe.{d}'})


def to_gltf(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], -v[..., 1]], -1)


def main():
    job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=job['glb'])
    arm = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    arm.data.pose_position = 'REST'
    arm.animation_data_clear()
    hi = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
    bpy.context.view_layer.update()

    # joint positions (rest heads) in glTF space
    jpos = {}
    for b in arm.data.bones:
        jpos[b.name] = to_gltf(arm.matrix_world @ b.head_local).tolist()
        jpos[b.name + '__tail'] = to_gltf(arm.matrix_world @ b.tail_local).tolist()

    lo = hi.copy(); lo.data = hi.data.copy(); lo.name = 'kit_lo'
    bpy.context.scene.collection.objects.link(lo)
    for m in list(lo.modifiers):
        lo.modifiers.remove(m)
    dec = lo.modifiers.new('dec', 'DECIMATE'); dec.ratio = job.get('ratio', 0.065)
    dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = lo
    bpy.ops.object.select_all(action='DESELECT'); lo.select_set(True)
    bpy.ops.object.modifier_apply(modifier='dec')
    tri = lo.modifiers.new('tri', 'TRIANGULATE')
    bpy.ops.object.modifier_apply(modifier='tri')
    # decimation turns the source's dense split normals into faceted slivers: shade the low mesh
    # smooth (no custom normals, no sharp edges) and let the baked normal map carry the detail
    with bpy.context.temp_override(object=lo, active_object=lo, selected_objects=[lo]):
        if lo.data.has_custom_normals:
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for e in lo.data.edges:
        e.use_edge_sharp = False
    lo.data.shade_smooth()
    print('KIT_TRIS', len(lo.data.polygons))

    if job.get('bake'):
        sc = bpy.context.scene
        sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
        size = job.get('bake_size', 2048)
        img = bpy.data.images.new('kit_normal', size, size, float_buffer=False)
        img.colorspace_settings.name = 'Non-Color'
        # the low copy shares the source material: give it its own so the bake target node is
        # not also present on the high mesh
        mat = lo.data.materials[0].copy(); lo.data.materials[0] = mat
        n = mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img
        mat.node_tree.nodes.active = n
        bpy.ops.object.select_all(action='DESELECT')
        hi.select_set(True); lo.select_set(True); bpy.context.view_layer.objects.active = lo
        sc.render.bake.use_selected_to_active = True
        sc.render.bake.cage_extrusion = job.get('extrusion', 0.02)
        sc.render.bake.max_ray_distance = job.get('extrusion', 0.02) * 2.5
        sc.render.bake.margin = 6
        bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
        img.filepath_raw = job['bake']; img.file_format = 'PNG'; img.save()
        print('KIT_BAKED', job['bake'])

    me = lo.data
    me.calc_loop_triangles()
    nv = len(me.vertices)
    co = np.empty(nv * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    M = np.array(lo.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    nl = len(me.loops)
    lv = np.empty(nl, np.int64); me.loops.foreach_get('vertex_index', lv)
    ln = np.empty(nl * 3); me.corner_normals.foreach_get('vector', ln); ln = ln.reshape(-1, 3)   # Blender >= 4.1
    ln = ln @ M[:3, :3].T
    uv = np.empty(nl * 2); me.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    uv[:, 1] = 1 - uv[:, 1]
    tl = np.array([t.loops[:] for t in me.loop_triangles], np.int64)

    gi = {g.index: g.name for g in lo.vertex_groups}
    W = np.zeros((nv, len(JOINTS)), np.float32)
    for v in me.vertices:
        for g in v.groups:
            d = MAP.get(gi[g.group])
            if d: W[v.index, JOINTS.index(d)] += g.weight
    W /= np.maximum(W.sum(1, keepdims=True), 1e-6)
    np.savez(job['out'], loop_v=lv, loop_uv=uv.astype(np.float32), loop_n=to_gltf(ln).astype(np.float32),
             tri_loops=tl, base=to_gltf(co).astype(np.float32), weights=W,
             jpos=json.dumps(jpos))
    print('KIT_OK', nv, len(tl))


main()
