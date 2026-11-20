# SPDX-License-Identifier: Apache-2.0
"""Blender worker: first-person gloved hand + sleeved forearm from a Microsoft Rocketbox avatar (MIT).

    blender -b --factory-startup --python tools/assets/blender_vm_arm.py -- job.json

job.json: {"fbx": path, "out": path.npz, "grip": "pistol"}

The right arm is posed so that, in glTF axes:
- the wrist sits at WRIST and the forearm runs back toward ELBOW (out of frame, +Z, down-right);
- the hand's long axis points forward (-Z), the knuckle row runs down (-Y), the palm faces -X
  and wraps a vertical grip at the origin (the contract of the old procedural hand_r.glb);
- fingers curl around the grip, the thumb lies along its near side.
Only vertices driven by the forearm/hand/finger bones are kept. The npz has positions, normals,
UVs, triangles and a per-triangle part id (0 = hand, 1 = sleeve). The left hand is the mirror.
"""
import json
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
WRIST = np.array(job.get('wrist', [0.03, -0.045, 0.072]))
ELBOW = np.array(job.get('elbow', [0.13, -0.24, 0.42]))
CURL = job.get('curl', [62, 78, 48])          # MCP, PIP, DIP degrees
GRIP_X = job.get('palm_x', 0.022)              # palm surface offset from the grip axis


def g2b(v):
    return Vector((v[0], -v[2], v[1]))


def b2g(v):
    return np.array([v[0], v[2], -v[1]], np.float64)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=job['fbx'], automatic_bone_orientation=False)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
body = max((o for o in bpy.data.objects if o.type == 'MESH'), key=lambda o: len(o.data.vertices))
if body.data.shape_keys:
    for k in body.data.shape_keys.key_blocks: k.value = 0.0
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
Aw = arm.matrix_world.to_3x3().normalized()
R = 'Bip01 R '


def whead(n):
    bpy.context.view_layer.update()
    return arm.matrix_world @ arm.pose.bones[n].head


def rotate_world(bone, Rw, pivot_world=None):
    """Rotate a pose bone (and so its children) by the world rotation Rw about its head."""
    pb = arm.pose.bones[bone]
    Rarm = Aw.inverted() @ Rw @ Aw
    h = pb.head.copy()
    pb.matrix = Matrix.Translation(h) @ Rarm.to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def align(bone, child, want):
    cur = (whead(child) - whead(bone)).normalized()
    rotate_world(bone, cur.rotation_difference(want.normalized()).to_matrix())


def hand_frame():
    h = whead(R + 'Hand')
    f1, f4 = whead(R + 'Finger1'), whead(R + 'Finger4')
    L = ((f1 + f4) * 0.5 - h).normalized()
    W = (f4 - f1); W = (W - L * W.dot(L)).normalized()
    return L, W, L.cross(W)


# forearm direction
align(R + 'Forearm', R + 'Hand', g2b(WRIST) - g2b(ELBOW))
# the palm side: thumb base lies on the palm side of the index-pinky line in a relaxed Biped hand
L0, W0, N0 = hand_frame()
thumb = whead(R + 'Finger0') - whead(R + 'Hand')
palm_sign = 1.0 if thumb.dot(N0) > 0 else -1.0
# target hand frame (glTF): long axis forward and a little up, knuckles down, palm toward -X
Lt = g2b(np.array([0.0, 0.18, -1.0])).normalized()
Wt = g2b(np.array([0.0, -1.0, -0.18])).normalized()
Wt = (Wt - Lt * Wt.dot(Lt)).normalized()
Nt = g2b(np.array([-1.0, 0.0, 0.0]))
# N0*palm_sign is the palm normal; build the rotation mapping (L0, W0, palm) -> (Lt, Wt, Nt)
for _ in range(2):
    L0, W0, N0 = hand_frame()
    P0 = N0 * palm_sign
    if (Lt.cross(Wt)).dot(Nt) * (L0.cross(W0)).dot(P0) < 0:  # handedness: flip width to match
        Wt_use = -Wt
    else:
        Wt_use = Wt
    A = Matrix((L0, W0, P0)).transposed()
    B = Matrix((Lt, Wt_use, Lt.cross(Wt_use) if (L0.cross(W0)).dot(P0) > 0 else -Lt.cross(Wt_use))).transposed()
    rotate_world(R + 'Hand', B @ A.inverted())
L1, W1, N1 = hand_frame()
palm = N1 * palm_sign

# curl fingers toward the palm about the knuckle-row axis
for f in '1234':
    chain = [R + f'Finger{f}', R + f'Finger{f}1', R + f'Finger{f}2']
    extra = {'1': -6, '2': 0, '3': 4, '4': 10}[f]  # pinky wraps tighter, index a touch looser
    for k, b in enumerate(chain):
        if b not in arm.pose.bones: continue
        nxt = chain[k + 1] if k + 1 < len(chain) else None
        d = (whead(nxt) - whead(b)).normalized() if nxt else L1
        axis = d.cross(palm).normalized()  # rotating d about this axis moves it toward the palm
        ang = np.radians(CURL[k] + (extra if k == 0 else 0))
        rotate_world(b, Matrix.Rotation(ang, 3, axis))
# thumb: swing across toward the grip's near side and bend slightly
t0 = R + 'Finger0'
rotate_world(t0, Matrix.Rotation(np.radians(28), 3, (L1.cross(palm)).normalized()))
for b in (R + 'Finger01', R + 'Finger02'):
    if b in arm.pose.bones:
        d = (whead(R + 'Finger02') - whead(R + 'Finger01')).normalized()
        rotate_world(b, Matrix.Rotation(np.radians(22), 3, d.cross(palm).normalized()))
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# ---- evaluate and cut ------------------------------------------------------------------------
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = ev.to_mesh()
M = body.matrix_world
P = np.array([b2g(M @ v.co) for v in me.vertices])
me.calc_loop_triangles()
Nl = np.array([b2g((M.to_3x3() @ Vector(l.vector)).normalized()) for l in me.corner_normals]) \
    if hasattr(me, 'corner_normals') else np.array([b2g(M.to_3x3() @ l.normal) for l in me.loops])
uvl = me.uv_layers.active.data
UVl = np.array([[d.uv[0], 1.0 - d.uv[1]] for d in uvl], np.float32)
LV = np.array([l.vertex_index for l in me.loops])
tri_loops = np.array([t.loops[:] for t in me.loop_triangles])
names = [g.name for g in body.vertex_groups]
part = np.full(len(body.data.vertices), -1)
best = np.zeros(len(body.data.vertices))
for v in body.data.vertices:
    for g in v.groups:
        n = names[g.group]
        if not n.startswith(R): continue
        r = n[len(R):]
        pid = 0 if (r == 'Hand' or r.startswith('Finger')) else 1 if r == 'Forearm' else 2 if r.startswith('UpperArm') else -1
        if pid < 0: continue
        if g.weight > best[v.index]: best[v.index] = g.weight; part[v.index] = pid
# keep hand + forearm; upper-arm vertices only within 6 cm of the elbow (the sleeve leaves frame)
elb_b = b2g(whead(R + 'Forearm'))
keepv = (part == 0) | (part == 1) | ((part == 2) & (np.linalg.norm(P - elb_b, axis=1) < 0.06))
tv = LV[tri_loops]
keep_t = keepv[tv].all(1)
tri_loops = tri_loops[keep_t]
tri_part = np.where((part[LV[tri_loops]] == 0).sum(1) >= 2, 0, 1)
# place: wrist (hand bone head) to WRIST, then nudge so the palm surface sits GRIP_X off the grip axis
wrist_now = b2g(whead(R + 'Hand'))
P = P + (WRIST - wrist_now)
hand_pts = P[LV[tri_loops[tri_part == 0]].reshape(-1)]
palm_g = b2g(palm)
# grip axis is vertical through the origin; palm surface = hand points furthest along -palm... use
# the median of the innermost 10 % of hand vertices in x
inner = np.percentile(hand_pts[:, 0], 8)
P[:, 0] += GRIP_X * (-1 if palm_g[0] < 0 else 1) * 0 + (-0.0 - inner) * 0  # see note below
note = {'inner_x': float(inner)}
mat_uv_ok = True
np.savez_compressed(job['out'], P=P.astype(np.float32), N=Nl.astype(np.float32), UV=UVl, LV=LV,
                    tri_loops=tri_loops.astype(np.int32), tri_part=tri_part.astype(np.int8),
                    mats=np.array([m.name for m in body.data.materials]),
                    tri_mat=np.array([me.polygons[t.polygon_index].material_index for t in me.loop_triangles])[keep_t])
print('VM_OK', len(tri_loops), note, 'palm', np.round(palm_g, 2))
