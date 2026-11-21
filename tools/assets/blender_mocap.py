# SPDX-License-Identifier: Apache-2.0
"""Blender worker: sample Microsoft Rocketbox motion capture (MIT) for the SPECIAL OPS rig.

    blender -b --factory-startup --python tools/assets/blender_mocap.py -- job.json

job.json: {"avatar": <avatar>_facial.fbx, "joints": {sops joint: glTF rest position},
           "clips": [[name, fbx], ...], "out": path.npz}

1. Import the avatar and pose it exactly as tools/assets/blender_rocketbox.py does when it bakes
   the mesh (rb_rig.align), and record the world rotation of every Biped bone that drives a sops
   joint in that pose (the rig's rest pose seen from the Biped).
2. For every clip: import the capture, face it forward and record the same bones' world rotations
   and the pelvis position on every frame (30 fps).
The caller (tools/assets/build_mocap_clips.py) turns these into sops joint rotations:
R_sops(t) = R_biped(t) R_biped_rest^-1 R_sops_rest, which deforms the baked mesh the way the
Biped skin would deform under the capture.
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rb_rig import JOINTS, ROT_OF, HEAD_OF, b2g, face_forward, align, world_rot_g  # noqa: E402

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False)
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    face_forward(bpy, arm)
    return arm


arm = load(job["avatar"])
align(bpy, arm, job["joints"])
rest = np.array([world_rot_g(arm, ROT_OF[j]) for j in JOINTS])
rest_hips = b2g(arm.matrix_world @ arm.pose.bones[HEAD_OF["Hips"]].head)
out = {"rest": rest, "rest_hips": rest_hips}
for name, fbx in job["clips"]:
    arm = load(fbx)
    act = arm.animation_data.action
    f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    sc = bpy.context.scene
    R, P = [], []
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        R.append([world_rot_g(arm, ROT_OF[j]) for j in JOINTS])
        P.append(b2g(arm.matrix_world @ arm.pose.bones[HEAD_OF["Hips"]].head))
    out[f"{name}.R"] = np.array(R, np.float32)
    out[f"{name}.P"] = np.array(P, np.float32)
    print("CLIP", name, f1 - f0 + 1, "frames")
np.savez_compressed(job["out"], **out)
print("MOCAP_OK", len(job["clips"]))
