# SPDX-License-Identifier: Apache-2.0
"""CPU preview of a skinned GLB: evaluates a clip at a time, skins the meshes and rasterizes a
flat-shaded image with a z-buffer. Used for asset review independent of the engine.

    python3 tools/characters/preview.py char.glb out.png [--clip Walk --time 0.3] [--yaw 30]
"""
from __future__ import annotations
import argparse, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
from gltf_util import read_glb, accessor, qmul, qrot, qnorm  # noqa: E402


def mat_from_trs(t, r, s):
    x, y, z, w = r
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.asarray(s); M[:3, 3] = t
    return M


def sample(times, vals, t, path):
    if t <= times[0]: return vals[0]
    if t >= times[-1]: return vals[-1]
    i = int(np.searchsorted(times, t)) - 1
    u = (t - times[i]) / (times[i + 1] - times[i])
    a, b = vals[i], vals[i + 1]
    if path == 'rotation':
        if np.dot(a, b) < 0: b = -b
        return qnorm(a * (1 - u) + b * u)
    return a * (1 - u) + b * u


def evaluate(j, binc, clip=None, t=0.0, morph=None):
    nodes = j['nodes']
    trs = [[np.array(n.get('translation', [0, 0, 0]), float), np.array(n.get('rotation', [0, 0, 0, 1]), float),
            np.array(n.get('scale', [1, 1, 1]), float)] for n in nodes]
    if clip:
        a = next(a for a in j['animations'] if a['name'] == clip)
        for c in a['channels']:
            s = a['samplers'][c['sampler']]
            ti = accessor(j, binc, s['input']).reshape(-1); vo = accessor(j, binc, s['output'])
            k = {'translation': 0, 'rotation': 1, 'scale': 2}[c['target']['path']]
            trs[c['target']['node']][k] = sample(ti, vo, t, c['target']['path'])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []): parent[c] = i
    W = {}
    def g(i):
        if i not in W:
            L = mat_from_trs(*trs[i]); W[i] = (g(parent[i]) @ L) if i in parent else L
        return W[i]
    for i in range(len(nodes)): g(i)
    tris, cols = [], []
    for ni, n in enumerate(nodes):
        if 'mesh' not in n: continue
        mesh = j['meshes'][n['mesh']]
        for p in mesh['primitives']:
            P = accessor(j, binc, p['attributes']['POSITION']).astype(float)
            if 'targets' in p and morph:
                names = mesh.get('extras', {}).get('targetNames', [])
                for ti_, tg in enumerate(p['targets']):
                    wgt = morph.get(names[ti_] if ti_ < len(names) else str(ti_), 0)
                    if wgt: P = P + wgt * accessor(j, binc, tg['POSITION'])
            C = accessor(j, binc, p['attributes']['COLOR_0'])[:, :3] if 'COLOR_0' in p['attributes'] else np.ones_like(P) * .7
            I = accessor(j, binc, p['indices']).reshape(-1, 3)
            if 'skin' in n:
                sk = j['skins'][n['skin']]
                ibm = accessor(j, binc, sk['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
                Js = accessor(j, binc, p['attributes']['JOINTS_0']).astype(int)
                Ws = accessor(j, binc, p['attributes']['WEIGHTS_0'])
                mats = np.array([W[jn] @ ibm[k] for k, jn in enumerate(sk['joints'])])
                Ph = np.c_[P, np.ones(len(P))]
                out = np.zeros_like(P)
                for c in range(4):
                    out += Ws[:, c:c + 1] * np.einsum('nij,nj->ni', mats[Js[:, c]], Ph)[:, :3]
                P = out
            else:
                P = (W[ni] @ np.c_[P, np.ones(len(P))].T).T[:, :3]
            tris.append(P[I]); cols.append(C[I].mean(1))
    return np.concatenate(tris), np.concatenate(cols)


def render(tris, cols, size=(512, 640), yaw=25.0, pitch=8.0, center=(0, 0.9, 0), extent=1.0):
    cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    cp, sp = np.cos(np.radians(pitch)), np.sin(np.radians(pitch))
    R = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    R = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]]) @ R
    V = (tris - np.array(center)) @ R.T
    w, h = size; scale = h / (2.2 * extent)
    sx = w / 2 + V[..., 0] * -scale  # model +X is the character's left -> screen right when facing camera
    sy_ = h / 2 - V[..., 1] * scale
    z = V[..., 2]
    nrm = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    light = np.array([0.4, 0.7, 0.6]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(np.abs(nrm @ light), 0, 1)
    img = np.full((h, w, 3), 0.16); zb = np.full((h, w), -1e9)
    lin = np.clip(cols * shade[:, None], 0, 1)
    rgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    for k in np.argsort(z.mean(1)):
        xs, ys, zs = sx[k], sy_[k], z[k]
        x0, x1 = int(max(0, np.floor(xs.min()))), int(min(w - 1, np.ceil(xs.max())))
        y0, y1 = int(max(0, np.floor(ys.min()))), int(min(h - 1, np.ceil(ys.max())))
        if x1 < x0 or y1 < y0: continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
        d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(d) < 1e-9: continue
        a = ((ys[1] - ys[2]) * (X - xs[2]) + (xs[2] - xs[1]) * (Y - ys[2])) / d
        b = ((ys[2] - ys[0]) * (X - xs[2]) + (xs[0] - xs[2]) * (Y - ys[2])) / d
        c = 1 - a - b
        m = (a >= 0) & (b >= 0) & (c >= 0)
        zz = a * zs[0] + b * zs[1] + c * zs[2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        m &= zz > sub
        sub[m] = zz[m]; img[y0:y1 + 1, x0:x1 + 1][m] = rgb[k]
    return Image.fromarray((img * 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('glb'); ap.add_argument('out')
    ap.add_argument('--clip'); ap.add_argument('--time', type=float, default=0.0)
    ap.add_argument('--yaw', type=float, default=25.0); ap.add_argument('--pitch', type=float, default=8.0)
    ap.add_argument('--blink', type=float, default=0.0); ap.add_argument('--jaw', type=float, default=0.0)
    ap.add_argument('--zoom', choices=['body', 'head'], default='body')
    a = ap.parse_args()
    j, b = read_glb(a.glb)
    tris, cols = evaluate(j, b, a.clip, a.time, {'Blink': a.blink, 'JawOpen': a.jaw})
    if a.zoom == 'head':
        img = render(tris, cols, (400, 400), a.yaw, a.pitch, (0, 1.63, 0), 0.16)
    else:
        img = render(tris, cols, yaw=a.yaw, pitch=a.pitch)
    img.save(a.out); print(a.out)


if __name__ == '__main__':
    main()
