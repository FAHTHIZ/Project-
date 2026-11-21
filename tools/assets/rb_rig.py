# SPDX-License-Identifier: Apache-2.0
"""Rocketbox Biped <-> SPECIAL OPS 21-joint rig mapping, shared by the Blender workers
(tools/assets/blender_rocketbox.py bakes the avatar meshes, tools/assets/blender_mocap.py bakes
the Rocketbox motion capture clips). Runs inside Blender (bpy, mathutils)."""
import numpy as np
from mathutils import Matrix, Vector

JOINTS = ["Hips", "Spine", "Chest", "Neck", "Head", "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
          "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R", "UpperLeg.L", "LowerLeg.L", "Foot.L", "Toe.L",
          "UpperLeg.R", "LowerLeg.R", "Foot.R", "Toe.R"]
# sops joint -> Biped bone whose head is that joint
HEAD_OF = {"Hips": "Bip01 Pelvis", "Spine": "Bip01 Spine", "Chest": "Bip01 Spine2", "Neck": "Bip01 Neck",
           "Head": "Bip01 Head"}
for _s in "LR":
    HEAD_OF.update({f"Shoulder.{_s}": f"Bip01 {_s} Clavicle", f"UpperArm.{_s}": f"Bip01 {_s} UpperArm",
                    f"LowerArm.{_s}": f"Bip01 {_s} Forearm", f"Hand.{_s}": f"Bip01 {_s} Hand",
                    f"UpperLeg.{_s}": f"Bip01 {_s} Thigh", f"LowerLeg.{_s}": f"Bip01 {_s} Calf",
                    f"Foot.{_s}": f"Bip01 {_s} Foot", f"Toe.{_s}": f"Bip01 {_s} Toe0"})
# sops joint -> Biped bone whose world rotation drives it in motion capture. The sops Spine covers
# Biped Spine and Spine1 (Spine1 carries most of the mid-back bend in the Rocketbox captures).
ROT_OF = dict(HEAD_OF, Spine="Bip01 Spine1")
# segments to align: (biped bone to rotate, sops from-joint, sops to-joint, biped to-bone)
ALIGN = [("Bip01 Spine", "Spine", "Chest", "Bip01 Spine2"), ("Bip01 Spine2", "Chest", "Neck", "Bip01 Neck"),
         ("Bip01 Neck", "Neck", "Head", "Bip01 Head")]
for _s in "LR":
    ALIGN += [(f"Bip01 {_s} Clavicle", f"Shoulder.{_s}", f"UpperArm.{_s}", f"Bip01 {_s} UpperArm"),
              (f"Bip01 {_s} UpperArm", f"UpperArm.{_s}", f"LowerArm.{_s}", f"Bip01 {_s} Forearm"),
              (f"Bip01 {_s} Forearm", f"LowerArm.{_s}", f"Hand.{_s}", f"Bip01 {_s} Hand"),
              (f"Bip01 {_s} Thigh", f"UpperLeg.{_s}", f"LowerLeg.{_s}", f"Bip01 {_s} Calf"),
              (f"Bip01 {_s} Calf", f"LowerLeg.{_s}", f"Foot.{_s}", f"Bip01 {_s} Foot"),
              (f"Bip01 {_s} Foot", f"Foot.{_s}", f"Toe.{_s}", f"Bip01 {_s} Toe0")]

# Blender world (Z up, character faces -Y) <-> glTF (Y up, faces +Z)
C = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], np.float64)


def g2b(v):
    return Vector((v[0], -v[2], v[1]))


def b2g(v):
    return np.array([v[0], v[2], -v[1]], np.float64)


def face_forward(bpy, arm):
    """Turn the armature so the character faces glTF +Z (Blender -Y): its left (+X) is the L side."""
    def wh(n): return arm.matrix_world @ arm.pose.bones[n].head
    bpy.context.view_layer.update()
    if wh("Bip01 L Clavicle").x < wh("Bip01 R Clavicle").x:
        arm.rotation_euler.z += np.pi
        bpy.context.view_layer.update()


def align(bpy, arm, joints):
    """Pose `arm` (in POSE mode) so every Biped limb segment points along the matching segment of
    the sops rest pose. joints: {sops joint: glTF rest position}."""
    def whead(n): return arm.matrix_world @ arm.pose.bones[n].head
    T = {k: g2b(v) for k, v in joints.items()}
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


def world_rot_g(arm, name):
    """World rotation of a pose bone, as a glTF-axes 3x3 matrix."""
    m = (arm.matrix_world @ arm.pose.bones[name].matrix).to_3x3().normalized()
    R = np.array(m, np.float64)
    return C @ R @ C.T
