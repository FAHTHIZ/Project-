# SPDX-License-Identifier: Apache-2.0
"""Small procedural mesh kit used by the SPECIAL OPS asset generators.

Every function returns (positions[N,3], normals[N,3], indices[M]) as numpy arrays. Parts are
merged with `Mesh.add`, which also records a per-vertex colour and an integer tag (used as the
skin joint index for characters).
"""
from __future__ import annotations
import numpy as np


def _frame(axis, hint=(0.0, 0.0, 1.0)):
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    h = np.asarray(hint, float)
    if abs(np.dot(a, h)) > 0.95:
        h = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(h, a); u /= np.linalg.norm(u)
    v = np.cross(a, u)
    return a, u, v


def loft(p0, p1, profile, segs=12, hint=(0, 0, 1), caps=True):
    """Lathe-like tube from p0 to p1. profile = [(t, rx, rz), ...] with t in 0..1.

    rx is the radius along the frame's u axis, rz along v (v is closest to `hint`).
    Tube ends are closed with a single fan vertex.
    """
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    axis = p1 - p0; length = np.linalg.norm(axis)
    a, u, v = _frame(axis, hint)
    ring_pos, ring_nrm = [], []
    prof = list(profile)
    for k, (t, rx, rz) in enumerate(prof):
        c = p0 + axis * t
        # slope of the radius for normals
        k0 = max(k - 1, 0); k1 = min(k + 1, len(prof) - 1)
        dt = (prof[k1][0] - prof[k0][0]) * length or 1e-6
        drx = (prof[k1][1] - prof[k0][1]) / dt
        drz = (prof[k1][2] - prof[k0][2]) / dt
        for s in range(segs):
            ang = 2 * np.pi * s / segs
            ca, sa = np.cos(ang), np.sin(ang)
            ring_pos.append(c + u * (rx * ca) + v * (rz * sa))
            n = u * (ca / max(rx, 1e-5)) + v * (sa / max(rz, 1e-5))
            n = n / np.linalg.norm(n)
            slope = -(drx * ca * ca + drz * sa * sa)
            n = n + a * slope
            ring_nrm.append(n / np.linalg.norm(n))
    P = list(ring_pos); N = list(ring_nrm); I = []
    R = len(prof)
    for r in range(R - 1):
        for s in range(segs):
            a0 = r * segs + s; a1 = r * segs + (s + 1) % segs
            b0 = a0 + segs; b1 = a1 + segs
            I += [a0, a1, b1, a0, b1, b0]
    if caps:
        c0 = len(P); P.append(p0 + axis * prof[0][0]); N.append(-a)
        c1 = len(P); P.append(p0 + axis * prof[-1][0]); N.append(a)
        for s in range(segs):
            I += [c0, (s + 1) % segs, s]
            base = (R - 1) * segs
            I += [c1, base + s, base + (s + 1) % segs]
    return np.array(P), np.array(N), np.array(I, dtype=np.uint32)


def capsule(p0, p1, r0, r1=None, segs=12, rings=4, hint=(0, 0, 1), squash=1.0):
    """Tapered capsule: hemispherical-ish rounded ends around a straight tube."""
    r1 = r0 if r1 is None else r1
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
    L = np.linalg.norm(p1 - p0)
    prof = []
    # extend the axis by the end radii so the round caps sit outside the joint points
    e0 = r0 / L; e1 = r1 / L
    for k in range(rings + 1):
        th = (np.pi / 2) * (1 - k / rings)
        prof.append((-e0 * np.sin(th), r0 * np.cos(th), r0 * np.cos(th) * squash))
    for k in range(1, rings + 1):
        th = (np.pi / 2) * k / rings
        prof.append((1 + e1 * np.sin(th), r1 * np.cos(th), r1 * np.cos(th) * squash))
    prof[0] = (prof[0][0], 0.001, 0.001); prof[-1] = (prof[-1][0], 0.001, 0.001)
    return loft(p0, p1, prof, segs, hint, caps=False)


def ellipsoid(center, radii, segs=14, rings=10, rot=None):
    c = np.asarray(center, float); rx, ry, rz = radii
    P, N, I = [], [], []
    for r in range(rings + 1):
        phi = np.pi * r / rings
        for s in range(segs):
            th = 2 * np.pi * s / segs
            d = np.array([np.sin(phi) * np.cos(th), np.cos(phi), np.sin(phi) * np.sin(th)])
            p = d * [rx, ry, rz]
            n = d / [rx, ry, rz]; n /= np.linalg.norm(n)
            if rot is not None:
                p = rot @ p; n = rot @ n
            P.append(c + p); N.append(n)
    for r in range(rings):
        for s in range(segs):
            a0 = r * segs + s; a1 = r * segs + (s + 1) % segs
            b1 = a1 + segs
            I += [a0, b1, a1, a0, a0 + segs, b1]
    return np.array(P), np.array(N), np.array(I, dtype=np.uint32)


def rounded_box(center, half, roundness=0.35, segs=6, rot=None):
    """Superellipsoid box: half extents, roundness 0 (sharp) .. 1 (ellipsoid)."""
    c = np.asarray(center, float); hx, hy, hz = half
    e = max(0.08, roundness)
    P, N, I = [], [], []
    rings = segs * 2; ss = segs * 4
    def spow(x, p): return np.sign(x) * np.abs(x) ** p
    for r in range(rings + 1):
        phi = -np.pi / 2 + np.pi * r / rings
        for s in range(ss):
            th = -np.pi + 2 * np.pi * s / ss
            cp, sp, ct, st = np.cos(phi), np.sin(phi), np.cos(th), np.sin(th)
            x = spow(cp, e) * spow(ct, e); y = spow(sp, e); z = spow(cp, e) * spow(st, e)
            p = np.array([x * hx, y * hy, z * hz])
            nx = spow(cp, 2 - e) * spow(ct, 2 - e) / hx
            ny = spow(sp, 2 - e) / hy
            nz = spow(cp, 2 - e) * spow(st, 2 - e) / hz
            n = np.array([nx, ny, nz]); ln = np.linalg.norm(n)
            n = n / ln if ln > 1e-8 else np.array([0, np.sign(y) or 1.0, 0])
            if rot is not None: p = rot @ p; n = rot @ n
            P.append(c + p); N.append(n)
    for r in range(rings):
        for s in range(ss):
            a0 = r * ss + s; a1 = r * ss + (s + 1) % ss
            b0 = a0 + ss; b1 = a1 + ss
            I += [a0, b1, a1, a0, b0, b1]
    return np.array(P), np.array(N), np.array(I, dtype=np.uint32)


def rot_y(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_x(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_z(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def fix_winding(P, N, I):
    """Flip triangles whose geometric normal disagrees with the vertex normals."""
    I = I.reshape(-1, 3).copy()
    a, b, c = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = N[I[:, 0]] + N[I[:, 1]] + N[I[:, 2]]
    flip = (fn * vn).sum(1) < 0
    I[flip] = I[flip][:, [0, 2, 1]]
    return I.reshape(-1)


class Mesh:
    def __init__(self):
        self.P, self.N, self.C, self.T, self.I, self.UV = [], [], [], [], [], []
        self.n = 0

    def add(self, part, color=(1, 1, 1), tag=0, uv=None, fix=True):
        P, N, I = part
        if fix:
            I = fix_winding(P, N, I)
        self.P.append(P); self.N.append(N)
        col = np.asarray(color, float)
        if col.ndim == 2:
            if col.shape[1] == 3: col = np.c_[col, np.ones(len(col))]
            self.C.append(col)
        else:
            self.C.append(np.tile(np.array(list(color) + [1.0] * (4 - len(color)))[:4], (len(P), 1)))
        self.T.append(np.full(len(P), tag))
        self.UV.append(uv if uv is not None else np.zeros((len(P), 2)))
        self.I.append(I + self.n); self.n += len(P)
        return self

    def arrays(self):
        return (np.concatenate(self.P).astype(np.float32), np.concatenate(self.N).astype(np.float32),
                np.concatenate(self.C).astype(np.float32), np.concatenate(self.T),
                np.concatenate(self.I).astype(np.uint32), np.concatenate(self.UV).astype(np.float32))
