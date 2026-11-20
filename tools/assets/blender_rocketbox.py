# SPDX-License-Identifier: Apache-2.0
"""Blender worker: bake a Microsoft Rocketbox avatar (MIT) onto the SPECIAL OPS 21-joint rig.

    blender -b --factory-startup --python tools/assets/blender_rocketbox.py -- job.json

job.json: {"fbx": path, "out": path.npz, "joints": {sops joint: [x, y, z] glTF rest position},
           "drop_materials": [substr, ...]}

1. Import the *_facial.fbx (Biped skeleton, 52 ARKit + 15 viseme blendshapes).
2. Pose its bones so every limb segment points along the matching segment of the target rest
   pose (A-pose, facing glTF +Z). The game's clips are authored as absolute joint rotations on
   that rest pose, so the mesh must be in it; the joint *positions* follow the avatar's own
   proportions and are written back to the skeleton by the caller.
3. Evaluate the posed mesh with no blendshape and once per game morph (each a mix of ARKit
   shapes), and write positions, split normals, UVs, material ids, 4-joint skin weights
   (Biped groups merged onto the 21 joints) and morph deltas in glTF axes to an .npz.
"""
import json
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))

JOINTS = ["Hips", "Spine", "Chest", "Neck", "Head", "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
          "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R", "UpperLeg.L", "LowerLeg.L", "Foot.L", "Toe.L",
          "UpperLeg.R", "LowerLeg.R", "Foot.R", "Toe.R"]
# sops joint -> Biped bone whose head is that joint
HEAD_OF = {"Hips": "Bip01 Pelvis", "Spine": "Bip01 Spine", "Chest": "Bip01 Spine2", "Neck": "Bip01 Neck",
           "Head": "Bip01 Head"}
for s, b in (("L", "L"), ("R", "R")):
    HEAD_OF.update({f"Shoulder.{s}": f"Bip01 {b} Clavicle", f"UpperArm.{s}": f"Bip01 {b} UpperArm",
                    f"LowerArm.{s}": f"Bip01 {b} Forearm", f"Hand.{s}": f"Bip01 {b} Hand",
                    f"UpperLeg.{s}": f"Bip01 {b} Thigh", f"LowerLeg.{s}": f"Bip01 {b} Calf",
                    f"Foot.{s}": f"Bip01 {b} Foot", f"Toe.{s}": f"Bip01 {b} Toe0"})
# segments to align: (biped bone to rotate, sops from-joint, sops to-joint, biped to-bone)
ALIGN = [("Bip01 Spine", "Spine", "Chest", "Bip01 Spine2"), ("Bip01 Spine2", "Chest", "Neck", "Bip01 Neck"),
         ("Bip01 Neck", "Neck", "Head", "Bip01 Head")]
for s in "LR":
    ALIGN += [(f"Bip01 {s} Clavicle", f"Shoulder.{s}", f"UpperArm.{s}", f"Bip01 {s} UpperArm"),
              (f"Bip01 {s} UpperArm", f"UpperArm.{s}", f"LowerArm.{s}", f"Bip01 {s} Forearm"),
              (f"Bip01 {s} Forearm", f"LowerArm.{s}", f"Hand.{s}", f"Bip01 {s} Hand"),
              (f"Bip01 {s} Thigh", f"UpperLeg.{s}", f"LowerLeg.{s}", f"Bip01 {s} Calf"),
              (f"Bip01 {s} Calf", f"LowerLeg.{s}", f"Foot.{s}", f"Bip01 {s} Foot"),
              (f"Bip01 {s} Foot", f"Foot.{s}", f"Toe.{s}", f"Bip01 {s} Toe0")]


def group_joint(name):
    """Biped vertex group -> sops joint."""
    n = name.replace("Bip01 ", "")
    for s in "LR":
        if n.startswith(f"{s} "):
            r = n[2:]
            if r.startswith("Finger") or r == "Hand": return f"Hand.{s}"
            return {"Clavicle": f"Shoulder.{s}", "UpperArm": f"UpperArm.{s}", "Forearm": f"LowerArm.{s}",
                    "Thigh": f"UpperLeg.{s}", "Calf": f"LowerLeg.{s}", "Foot": f"Foot.{s}",
                    "Toe0": f"Toe.{s}"}.get(r.split(" ")[0])
    if n in ("Pelvis", "Bip01"): return "Hips"
    if n in ("Spine", "Spine1"): return "Spine"
    if n == "Spine2": return "Chest"
    if n == "Neck": return "Neck"
    return "Head"  # head and every facial bone


MORPHS = {
    "Blink": {"AK_09_EyeBlinkLeft": 1, "AK_10_EyeBlinkRight": 1},
    "JawOpen": {"AK_25_JawOpen": 0.85, "AA_VI_10_aa": 0.35},
    "Smile": {"AK_44_MouthSmileLeft": 1, "AK_45_MouthSmileRight": 1, "AK_07_CheekSquintLeft": 0.4, "AK_08_CheekSquintRight": 0.4},
    "Frown": {"AK_30_MouthFrownLeft": 1, "AK_31_MouthFrownRight": 1},
    "BrowUp": {"AK_03_BrowInnerUp": 1, "AK_04_BrowOuterUpLeft": 0.8, "AK_05_BrowOuterUpRight": 0.8},
    "BrowDown": {"AK_01_BrowDownLeft": 1, "AK_02_BrowDownRight": 1},
    "MouthO": {"AA_VI_13_O": 1.0, "AK_32_MouthFunnel": 0.3},
    "LookL": {"AK_15_EyeLookOutLeft": 1, "AK_14_EyeLookInRight": 1},
    "LookR": {"AK_13_EyeLookInLeft": 1, "AK_16_EyeLookOutRight": 1},
    "LookUp": {"AK_17_EyeLookUpLeft": 1, "AK_18_EyeLookUpRight": 1},
    "LookDown": {"AK_11_EyeLookDownLeft": 1, "AK_12_EyeLookDownRight": 1},
}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=job["fbx"], automatic_bone_orientation=False)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
body = max(meshes, key=lambda o: len(o.data.vertices))


def g2b(v):  # glTF -> Blender world
    return Vector((v[0], -v[2], v[1]))


def b2g(v):
    return np.array([v[0], v[2], -v[1]], np.float64)


bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="POSE")
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"


def whead(name):
    return arm.matrix_world @ arm.pose.bones[name].head


# Facing: the target faces glTF +Z (Blender -Y); the left side is +X in both.
if whead("Bip01 L Clavicle").x < whead("Bip01 R Clavicle").x:
    arm.rotation_euler.z += np.pi
    bpy.context.view_layer.update()

T = {k: g2b(v) for k, v in job["joints"].items()}
Aw = arm.matrix_world.to_3x3().normalized()
for _ in range(2):  # second pass fixes small coupling between parents and children
    for bone, a, b, child in ALIGN:
        bpy.context.view_layer.update()
        pb = arm.pose.bones[bone]
        cur = (whead(child) - whead(bone)).normalized()
        want = (T[b] - T[a]).normalized()
        q = cur.rotation_difference(want)
        Rarm = Aw.inverted() @ q.to_matrix() @ Aw
        h = pb.head.copy()
        pb.matrix = Matrix.Translation(h) @ Rarm.to_4x4() @ Matrix.Translation(-h) @ pb.matrix
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode="OBJECT")

# joint rest positions of the posed avatar (glTF axes)
jpos = {j: b2g(whead(HEAD_OF[j])) for j in JOINTS}
# put the feet on the ground (y = 0 at the lowest vertex) like the original rig
keys = body.data.shape_keys.key_blocks if body.data.shape_keys else None
for k in (keys or []):
    k.value = 0.0


def evaluate():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    M = body.matrix_world
    P = np.array([b2g(M @ v.co) for v in me.vertices])
    me.calc_loop_triangles() if hasattr(me, "calc_loop_triangles") else None
    nrm = np.array([b2g(M.to_3x3() @ Vector(l.vector)) for l in me.corner_normals]) if hasattr(me, "corner_normals") else \
        np.array([b2g(M.to_3x3() @ l.normal) for l in me.loops])
    ev.to_mesh_clear()
    return P, nrm


base, loop_n = evaluate()
dg = bpy.context.evaluated_depsgraph_get()
me = body.evaluated_get(dg).to_mesh()
me.calc_loop_triangles()
tri_loops = np.array([t.loops[:] for t in me.loop_triangles], np.int64)
tri_mat = np.array([t.material_index for t in me.loop_triangles], np.int64)
loop_v = np.array([l.vertex_index for l in me.loops], np.int64)
uvl = me.uv_layers.active.data
loop_uv = np.array([[d.uv[0], 1.0 - d.uv[1]] for d in uvl], np.float32)
body.evaluated_get(dg).to_mesh_clear()

morph = {}
for name, mix in MORPHS.items():
    if not keys: break
    for k in keys: k.value = 0.0
    for kn, w in mix.items():
        if kn in keys: keys[kn].value = w
    P, _ = evaluate()
    morph[name] = (P - base).astype(np.float32)
for k in (keys or []): k.value = 0.0

# skin weights onto the 21 joints
gidx = {g.index: group_joint(g.name) for g in body.vertex_groups}
W = np.zeros((len(body.data.vertices), len(JOINTS)), np.float32)
for v in body.data.vertices:
    for g in v.groups:
        j = gidx.get(g.group)
        if j: W[v.index, JOINTS.index(j)] += g.weight
mats = [m.name if m else "" for m in body.data.materials]
imgs = {}
for m in body.data.materials:
    if m and m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                imgs.setdefault(m.name, []).append(bpy.path.abspath(n.image.filepath))
lift = -float(base[:, 1].min())
for j in jpos: jpos[j][1] += lift
base[:, 1] += lift
np.savez_compressed(job["out"], base=base.astype(np.float32), loop_n=loop_n.astype(np.float32), loop_v=loop_v,
                    loop_uv=loop_uv, tri_loops=tri_loops, tri_mat=tri_mat, weights=W,
                    jpos=np.array([jpos[j] for j in JOINTS], np.float32),
                    morph_names=np.array(list(morph)), morphs=np.array([morph[k] for k in morph]) if morph else np.zeros((0,)),
                    mats=np.array(mats), imgs=json.dumps(imgs))
print("RB_OK", len(base), len(tri_loops), mats, {k: float(np.abs(v).max()) for k, v in morph.items()})
