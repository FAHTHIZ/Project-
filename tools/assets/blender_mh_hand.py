# SPDX-License-Identifier: Apache-2.0
"""Blender worker: first-person gloved hand + sleeved forearm from the MakeHuman base mesh (CC0).

    blender -b --factory-startup --python tools/assets/blender_mh_hand.py -- job.json

job.json: {"mh": dir with base.obj, default.mhskel, default_weights.mhw, "out": path.npz,
           optional "wrist", "elbow", "curl", "glove_mm", "sleeve_mm"}

Same contract and npz layout as blender_vm_arm.py (the Rocketbox worker): in glTF axes the wrist
sits at WRIST, the forearm runs back toward ELBOW, the hand's long axis points forward (-Z), the
knuckle row runs down (-Y), the palm faces -X and wraps a vertical grip at the origin.
The MakeHuman hand has five fully modelled fingers with three phalanges each and a CC0 skeleton
with skin weights, so the fingers curl around the grip individually instead of as a mitten.
The glove is the skin pushed out by glove_mm along the normals; the sleeve is the forearm pushed
out by sleeve_mm, with a thicker cuff ring at the wrist end.
"""
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

job = json.load(open(sys.argv[sys.argv.index('--') + 1]))
MH = job['mh']
WRIST = np.array(job.get('wrist', [0.03, -0.045, 0.072]))
ELBOW = np.array(job.get('elbow', [0.13, -0.24, 0.42]))
CURL = job.get('curl', [58, 72, 46])           # MCP, PIP, DIP degrees
TRIGGER = job.get('trigger')                    # index finger curl for the firing hand (on the trigger)
GLOVE = job.get('glove_mm', 1.6) / 1000.0
SLEEVE = job.get('sleeve_mm', 11.0) / 1000.0
SIDE = '.R'


def g2b(v):
    return Vector((v[0], -v[2], v[1]))


def b2g(v):
    return np.array([v[0], v[2], -v[1]], np.float64)


# ---- MakeHuman base mesh (decimetres, Y up) -> Blender metres, Z up ---------------------------
V, VT, F, FT = [], [], [], []
group = None
for line in open(os.path.join(MH, 'base.obj')):
    if line.startswith('v '):
        x, y, z = map(float, line.split()[1:4])
        V.append((x * 0.1, -z * 0.1, y * 0.1))
    elif line.startswith('vt '):
        u, v = map(float, line.split()[1:3])
        VT.append((u, v))
    elif line.startswith('g '):
        group = line.split()[1]
    elif line.startswith('f ') and group == 'body':
        idx = [p.split('/') for p in line.split()[1:]]
        F.append([int(p[0]) - 1 for p in idx])
        FT.append([int(p[1]) - 1 for p in idx])
V = np.array(V)

bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('mh_body')
me.from_pydata(V.tolist(), [], F)
uvl = me.uv_layers.new(name='UV')
k = 0
for poly, ft in zip(me.polygons, FT):
    for li, t in zip(poly.loop_indices, ft):
        uvl.data[li].uv = VT[t]
me.update()
body = bpy.data.objects.new('body', me)

# ---- glove zones (rest pose): second UV layer Z = (dorsal, knuckle) per loop -------------------
# dorsal: +1 on the back of the hand, -1 on the palm; knuckle: 1 over the MCP row (and 0.7 over
# the PIP row) on the back. UVs survive subdivision, decimation and the bisect cuts, so the posed,
# evaluated mesh still knows which glove panel each face belongs to.
_sk = json.load(open(os.path.join(MH, 'default.mhskel')))
_J = {n: V[np.array(ix)].mean(0) for n, ix in _sk['joints'].items()}


def _head(b):
    return _J[_sk['bones'][b + SIDE]['head']]


_mcp = np.array([_head(f'finger{i}-1') for i in (2, 3, 4, 5)])
_pip = np.array([_head(f'finger{i}-2') for i in (2, 3, 4, 5)])
_wr = _head('wrist')
_Lr = _mcp.mean(0) - _wr; _Lr /= np.linalg.norm(_Lr)
_Wr = _mcp[3] - _mcp[0]; _Wr -= _Lr * _Wr.dot(_Lr); _Wr /= np.linalg.norm(_Wr)
_Nr = np.cross(_Lr, _Wr)
if (_head('finger1-1') - _wr).dot(_Nr) > 0:   # thumb base is on the palm side
    _Nr = -_Nr                                   # _Nr now points out of the back of the hand


def _seg_dist(P, A):
    d = np.full(len(P), 1e9)
    for a, b in zip(A[:-1], A[1:]):
        ab = b - a; t = np.clip(((P - a) @ ab) / ab.dot(ab), 0, 1)
        d = np.minimum(d, np.linalg.norm(P - (a + t[:, None] * ab), axis=1))
    return d


_vn = np.array([v.normal[:] for v in me.vertices])
_dors = _vn @ _Nr
_km = np.clip(1.0 - _seg_dist(V, _mcp) / 0.019, 0, 1)
_kp = 0.7 * np.clip(1.0 - _seg_dist(V, _pip) / 0.013, 0, 1)
_kn = np.maximum(_km, _kp) * np.clip((_dors - 0.2) / 0.3, 0, 1)
zl = me.uv_layers.new(name='Z')
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index
        zl.data[li].uv = (float(_dors[vi]), float(_kn[vi]))
me.uv_layers.active = uvl
bpy.context.scene.collection.objects.link(body)

# ---- skeleton -------------------------------------------------------------------------------
skel = json.load(open(os.path.join(MH, 'default.mhskel')))
joints = {n: V[np.array(ix)].mean(0) for n, ix in skel['joints'].items()}
armd = bpy.data.armatures.new('mh_rig')
arm = bpy.data.objects.new('rig', armd)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
for n, b in skel['bones'].items():
    eb = armd.edit_bones.new(n)
    eb.head = Vector(joints[b['head']])
    eb.tail = Vector(joints[b['tail']])
    if (eb.tail - eb.head).length < 1e-4:
        eb.tail = eb.head + Vector((0, 0, 0.005))
for n, b in skel['bones'].items():
    if b.get('parent'):
        armd.edit_bones[n].parent = armd.edit_bones[b['parent']]
bpy.ops.object.mode_set(mode='OBJECT')

weights = json.load(open(os.path.join(MH, 'default_weights.mhw')))['weights']
for bn, pairs in weights.items():
    if bn not in skel['bones']:
        continue
    vg = body.vertex_groups.new(name=bn)
    for vi, w in pairs:
        vg.add([int(vi)], float(w), 'REPLACE')
# trim to the right hand + forearm (+ the elbow end of the upper arm) before subdividing
import bmesh
nv0 = len(V)
wsum = {0: np.zeros(nv0), 1: np.zeros(nv0), 2: np.zeros(nv0)}
for bname, pairs in weights.items():
    if not bname.endswith(SIDE):
        continue
    r = bname[:-len(SIDE)]
    pid = 0 if (r == 'wrist' or r.startswith(('finger', 'metacarpal'))) else 1 if r.startswith('lowerarm') \
        else 2 if r.startswith('upperarm') else -1
    if pid >= 0:
        for vi, w in pairs:
            wsum[pid][int(vi)] += float(w)
tot0 = wsum[0] + wsum[1] + wsum[2]
part0 = np.where(tot0 < 0.5, -1, np.argmax(np.stack([wsum[0], wsum[1], wsum[2]], 1), 1))
elb0 = joints[skel['bones']['lowerarm01' + SIDE]['head']]
keep0 = (part0 == 0) | (part0 == 1) | ((part0 == 2) & (np.linalg.norm(V - elb0, axis=1) < 0.06))
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep0[v.index]], context='VERTS')
bm.to_mesh(me); bm.free(); me.update()
mod = body.modifiers.new('rig', 'ARMATURE')
mod.object = arm
if job.get('subsurf', 1):
    ss = body.modifiers.new('smooth', 'SUBSURF')
    ss.levels = ss.render_levels = int(job.get('subsurf', 1))
    ss.uv_smooth = 'PRESERVE_BOUNDARIES'
if job.get('decimate', 0.55) < 1:
    dm = body.modifiers.new('budget', 'DECIMATE')
    dm.ratio = job.get('decimate', 0.55)

# ---- pose (same method as blender_vm_arm.py) -------------------------------------------------
BN = {'Forearm': 'lowerarm01', 'Hand': 'wrist',
      'Finger0': 'finger1-1', 'Finger01': 'finger1-2', 'Finger02': 'finger1-3'}
for i, f in enumerate('1234'):
    BN[f'Finger{f}'] = f'finger{i + 2}-1'
    BN[f'Finger{f}1'] = f'finger{i + 2}-2'
    BN[f'Finger{f}2'] = f'finger{i + 2}-3'


def bn(n):
    return BN[n] + SIDE


bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')
for pb in arm.pose.bones:
    pb.rotation_mode = 'QUATERNION'
Aw = arm.matrix_world.to_3x3().normalized()


def whead(n):
    bpy.context.view_layer.update()
    return arm.matrix_world @ arm.pose.bones[bn(n)].head


def rotate_world(bone, Rw):
    pb = arm.pose.bones[bn(bone)]
    Rarm = Aw.inverted() @ Rw @ Aw
    h = pb.head.copy()
    pb.matrix = Matrix.Translation(h) @ Rarm.to_4x4() @ Matrix.Translation(-h) @ pb.matrix
    bpy.context.view_layer.update()


def align(bone, child, want):
    cur = (whead(child) - whead(bone)).normalized()
    rotate_world(bone, cur.rotation_difference(want.normalized()).to_matrix())


def hand_frame():
    h = whead('Hand')
    f1, f4 = whead('Finger1'), whead('Finger4')
    L = ((f1 + f4) * 0.5 - h).normalized()
    W = (f4 - f1); W = (W - L * W.dot(L)).normalized()
    return L, W, L.cross(W)


align('Forearm', 'Hand', g2b(WRIST) - g2b(ELBOW))
L0, W0, N0 = hand_frame()
thumb = whead('Finger0') - whead('Hand')
# the thumb base lies on the palm side of the index-pinky line
palm_sign = 1.0 if thumb.dot(N0) > 0 else -1.0
Lt = g2b(np.array([0.0, 0.18, -1.0])).normalized()
Wt = g2b(np.array([0.0, -1.0, -0.18])).normalized()
Wt = (Wt - Lt * Wt.dot(Lt)).normalized()
Nt = g2b(np.array([-1.0, 0.0, 0.0]))
for _ in range(2):
    L0, W0, N0 = hand_frame()
    P0 = N0 * palm_sign
    Wt_use = -Wt if (Lt.cross(Wt)).dot(Nt) * (L0.cross(W0)).dot(P0) < 0 else Wt
    A = Matrix((L0, W0, P0)).transposed()
    B = Matrix((Lt, Wt_use, Lt.cross(Wt_use) if (L0.cross(W0)).dot(P0) > 0 else -Lt.cross(Wt_use))).transposed()
    rotate_world('Hand', B @ A.inverted())
L1, W1, N1 = hand_frame()
palm = N1 * palm_sign

for f in '1234':
    chain = [f'Finger{f}', f'Finger{f}1', f'Finger{f}2']
    extra = {'1': -8, '2': 0, '3': 5, '4': 11}[f]  # pinky wraps tighter, index looser (trigger side)
    for k, b in enumerate(chain):
        nxt = chain[k + 1] if k + 1 < len(chain) else None
        d = (whead(nxt) - whead(b)).normalized() if nxt else L1
        axis = d.cross(palm).normalized()
        curl = TRIGGER if (f == '1' and TRIGGER) else CURL
        ang = np.radians(curl[k] + (extra if k == 0 and curl is CURL else 0))
        rotate_world(b, Matrix.Rotation(ang, 3, axis))
# thumbs-forward grip: the thumb lies along the far side of the frame pointing at the target
THUMB = np.array(job.get('thumb', [-0.38, 0.22, -1.0]))
align('Finger0', 'Finger01', g2b(THUMB / np.linalg.norm(THUMB)))
for b, c in (('Finger01', 'Finger02'),):
    align(b, c, g2b(THUMB / np.linalg.norm(THUMB)))
d = (whead('Finger02') - whead('Finger01')).normalized()
rotate_world('Finger02', Matrix.Rotation(np.radians(12), 3, d.cross(palm).normalized()))
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

# ---- evaluate, classify, inflate, cut -------------------------------------------------------
dg = bpy.context.evaluated_depsgraph_get()
wrist_g = b2g(whead('Hand'))
elb = b2g(whead('Forearm'))
ax = (wrist_g - elb) / np.linalg.norm(wrist_g - elb)
GLOVE_END = -job.get('gauntlet_cm', 3.5) / 100.0   # glove gauntlet reaches this far up the forearm
SLEEVE_START = -job.get('cuff_cm', 1.0) / 100.0    # the sleeve cuff covers the gauntlet from here
bm = bmesh.new()
bm.from_object(body, dg)
# cut exactly on the glove and sleeve edge planes so both edges are clean rings
for d in (GLOVE_END, SLEEVE_START):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=g2b(wrist_g + ax * d), plane_no=g2b(ax))
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bm.normal_update()
bm.verts.ensure_lookup_table()
P = np.array([b2g(v.co) for v in bm.verts])
Nv = np.array([b2g(v.normal) for v in bm.verts])
uvk = bm.loops.layers.uv['UV']
zk = bm.loops.layers.uv.get('Z')
UVl, Zl, LV, tri_loops = [], [], [], []
for f in bm.faces:
    tl = []
    for l in f.loops:
        tl.append(len(LV)); LV.append(l.vert.index)
        uv = l[uvk].uv; UVl.append([uv[0], 1.0 - uv[1]])
        Zl.append(l[zk].uv[:] if zk is not None else (0.0, 0.0))
    tri_loops.append(tl)
UVl = np.array(UVl, np.float32); Zl = np.array(Zl, np.float32); LV = np.array(LV); tri_loops = np.array(tri_loops)

t = (P - wrist_g) @ ax            # >0: hand side of the wrist joint, <0: up the forearm
tv = LV[tri_loops]
tc = t[tv].mean(1)
glove_t = tc > GLOVE_END
sleeve_t = tc < SLEEVE_START
# glove: skin + GLOVE, swelling to +3 mm at the gauntlet so it reads as a separate cuff
g_off = GLOVE + 0.0016 * np.clip(-t / 0.03, 0, 1)
# sleeve: forearm + SLEEVE, with a rolled cuff ring (+4 mm) in its last 1.5 cm
cuffring = np.clip(1.0 - (SLEEVE_START - t) / 0.015, 0, 1)
s_off = SLEEVE + 0.004 * cuffring
Pg = P + Nv * g_off[:, None]
Ps = P + Nv * s_off[:, None]
# clean, round edges: pull vertices past each edge back onto the cutting plane
Pg = Pg - np.minimum((Pg - wrist_g) @ ax - GLOVE_END, 0)[:, None] * ax
Ps = Ps - np.maximum((Ps - wrist_g) @ ax - SLEEVE_START, 0)[:, None] * ax
# two copies of the loop/vertex arrays: glove verts then sleeve verts
nv = len(P)
P = np.concatenate([Pg, Ps])
Nv2 = np.concatenate([Nv, Nv])
LV = np.concatenate([LV, LV + nv])
nl = len(UVl)
UVl = np.concatenate([UVl, UVl])
Zl = np.concatenate([Zl, Zl * 0])
tri_loops = np.concatenate([tri_loops[glove_t], tri_loops[sleeve_t] + nl])
tri_part = np.concatenate([np.zeros(glove_t.sum(), np.int8), np.ones(sleeve_t.sum(), np.int8)])
Nv = Nv2
P = P + (WRIST - wrist_g)
Nl = Nv[LV]
np.savez_compressed(job['out'], P=P.astype(np.float32), N=Nl.astype(np.float32), UV=UVl, Z=Zl, LV=LV,
                    tri_loops=tri_loops.astype(np.int32), tri_part=tri_part.astype(np.int8),
                    mats=np.array(['mh_skin']), tri_mat=np.zeros(len(tri_loops), np.int32))
print('VM_OK', len(tri_loops), 'glove tris', int((tri_part == 0).sum()), 'palm', np.round(b2g(palm), 2))
