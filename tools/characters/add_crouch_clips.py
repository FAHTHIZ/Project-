# SPDX-License-Identifier: Apache-2.0
"""Add crouched locomotion clips (CrouchWalk, CrouchRun) to the finished human cast GLBs.

    python3 tools/characters/add_crouch_clips.py [game/assets/models/characters/sops_*.glb ...]

The cast GLBs come from tools/assets/build_rocketbox_cast.py (Rocketbox meshes on the
build_humans.py rig and clips), which needs Blender and the Rocketbox sources. This tool works on
the finished files instead: it derives the crouched gaits from each character's own Walk and Run
clips, so the leg cycle, arm swing and timing stay that character's, and appends them as new
animations. It re-runs safely: existing Crouch* clips are replaced (their old bytes are dropped
by rewriting the binary chunk from the surviving accessors).

The crouch layer, per sample, in the same model-space authoring axes as build_humans.py:
thighs flex forward, knees bend, feet pitch to stay flat, the torso leans in and the head comes
back up to keep the eyes level. The hips drop by the amount the bent legs shorten (computed from
this rig's thigh and shin lengths) so the feet stay on the ground, and the cadence slows.
"""
from __future__ import annotations
import glob, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gltf_util import read_glb, accessor, Writer, node_globals, qmul, qconj, qaxis, qnorm  # noqa: E402
from build_humans import axis_sign, X, JOINT_NAMES  # noqa: E402

# name, source clip, slow-down, thigh flex, knee bend, foot pitch, spine, chest, head (deg)
GAITS = [
    ("CrouchWalk", "Walk", 1.3, 48.0, -84.0, 30.0, 16.0, 8.0, -18.0),
    ("CrouchRun", "Run", 1.12, 34.0, -60.0, 20.0, 20.0, 8.0, -20.0),
]


def leg_drop(G, nm, thigh_deg, knee_deg):
    hip = G[nm['UpperLeg.L']][0]; knee = G[nm['LowerLeg.L']][0]; ankle = G[nm['Foot.L']][0]
    l1 = float(np.linalg.norm(knee - hip)); l2 = float(np.linalg.norm(ankle - knee))
    a = np.radians(thigh_deg); b = np.radians(thigh_deg + knee_deg)
    drop = l1 * (1 - np.cos(a)) + l2 * (1 - np.cos(b))
    fwd = l1 * np.sin(a) + l2 * np.sin(b)
    return drop, fwd


def rebuild(j, binc, keep_anims):
    """Rewrite every accessor into a fresh binary chunk (drops bytes of removed animations)."""
    old_acc = j['accessors']; old_bv = j['bufferViews']
    used = set()
    for m in j.get('meshes', []):
        for p in m['primitives']:
            used.update(p['attributes'].values())
            if 'indices' in p: used.add(p['indices'])
            for t in p.get('targets', []): used.update(t.values())
    for s in j.get('skins', []):
        if 'inverseBindMatrices' in s: used.add(s['inverseBindMatrices'])
    for a in keep_anims:
        for s in a['samplers']: used.update((s['input'], s['output']))
    img_views = {im['bufferView'] for im in j.get('images', []) if 'bufferView' in im}
    w = Writer(j)
    remap_bv = {}
    def copy_view(vi):
        if vi in remap_bv: return remap_bv[vi]
        bv = old_bv[vi]; start = bv.get('byteOffset', 0)
        while len(w.bin) % 4: w.bin.append(0)
        nb = dict(bv); nb['byteOffset'] = len(w.bin)
        w.bin += binc[start:start + bv['byteLength']]
        j['bufferViews'].append(nb); remap_bv[vi] = len(j['bufferViews']) - 1
        return remap_bv[vi]
    remap = {}
    for i in sorted(used):
        a = dict(old_acc[i]); a['bufferView'] = copy_view(a['bufferView'])
        j['accessors'].append(a); remap[i] = len(j['accessors']) - 1
    for im in j.get('images', []):
        if 'bufferView' in im: im['bufferView'] = copy_view(im['bufferView'])
    for m in j.get('meshes', []):
        for p in m['primitives']:
            p['attributes'] = {k: remap[v] for k, v in p['attributes'].items()}
            if 'indices' in p: p['indices'] = remap[p['indices']]
            if 'targets' in p: p['targets'] = [{k: remap[v] for k, v in t.items()} for t in p['targets']]
    for s in j.get('skins', []):
        if 'inverseBindMatrices' in s: s['inverseBindMatrices'] = remap[s['inverseBindMatrices']]
    for a in keep_anims:
        for s in a['samplers']: s['input'] = remap[s['input']]; s['output'] = remap[s['output']]
    j['animations'] = keep_anims
    assert not (img_views - set(remap_bv)), "image views lost"
    return w


def process(path):
    j, binc = read_glb(path)
    G, _ = node_globals(j)
    nm = {n['name']: i for i, n in enumerate(j['nodes'])}
    rest_local = {jn: np.array(j['nodes'][nm[jn]].get('rotation', [0, 0, 0, 1]), float) for jn in JOINT_NAMES}
    grot = {jn: G[nm[jn]][1] for jn in JOINT_NAMES}
    src = {a['name']: a for a in j['animations']}
    # sample the source clips before the binary is rewritten
    sampled = {}
    for name, clip, *_ in GAITS:
        a = src[clip]; chans = {}
        for c in a['channels']:
            s = a['samplers'][c['sampler']]
            chans[(c['target']['node'], c['target']['path'])] = (accessor(j, binc, s['input']).astype(np.float32).copy(),
                                                                accessor(j, binc, s['output']).astype(np.float32).copy(),
                                                                s.get('interpolation', 'LINEAR'))
        sampled[name] = chans
    keep = [a for a in j['animations'] if not a['name'].startswith('Crouch')]
    w = rebuild(j, binc, keep)
    for name, clip, slow, thigh, knee, foot, spine, chest, head in GAITS:
        drop, fwd = leg_drop(G, nm, thigh, knee)
        deltas = {'UpperLeg.L': thigh, 'UpperLeg.R': thigh, 'LowerLeg.L': knee, 'LowerLeg.R': knee,
                  'Foot.L': foot, 'Foot.R': foot, 'Spine': spine, 'Chest': chest, 'Head': head}
        ld = {}
        for jn, deg in deltas.items():
            d = qaxis(X, deg * axis_sign(jn, X)); gr = grot[jn]
            ld[nm[jn]] = qnorm(qmul(qmul(qconj(gr), d), gr))
        samplers, channels = [], []
        for (node, chan), (t, out, interp) in sampled[name].items():
            t2 = t * slow
            o2 = out.copy()
            if chan == "rotation" and node in ld:
                for k in range(len(o2)):
                    o2[k] = qnorm(qmul(o2[k].astype(float), ld[node]))
            if chan == "translation" and j["nodes"][node]["name"] == "Hips":
                # drop the hips by the leg shortening; sit back so the feet stay under the body
                o2 = o2 + np.array([0, -drop, -0.25 * fwd], np.float32)
            samplers.append({'input': w.add(t2.astype(np.float32), 'SCALAR', None, True),
                             'output': w.add(o2.astype(np.float32), {3: 'VEC3', 4: 'VEC4'}[o2.shape[1]]),
                             'interpolation': interp})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": chan}})
        j['animations'].append({'name': name, 'samplers': samplers, 'channels': channels})
        print(f"{os.path.basename(path)}: {name} from {clip} x{slow}, hips -{drop:.3f} m")
    w.save(path)


def main():
    paths = sys.argv[1:] or sorted(p for p in glob.glob(os.path.join(HERE, '../../game/assets/models/characters/sops_*.glb')))
    for p in paths:
        process(p)


if __name__ == '__main__':
    main()
