# SPDX-License-Identifier: Apache-2.0
"""Minimal GLB read/write helpers and quaternion maths for the SPECIAL OPS character tools."""
from __future__ import annotations
import json, struct
import numpy as np

def read_glb(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'glTF'
    jl = struct.unpack('<I', b[12:16])[0]
    j = json.loads(b[20:20 + jl])
    off = 20 + jl
    bl = struct.unpack('<I', b[off:off + 4])[0]
    binc = b[off + 8: off + 8 + bl]
    return j, bytearray(binc)

CT = {5126: ('f', 4), 5125: ('I', 4), 5123: ('H', 2), 5121: ('B', 1), 5120: ('b', 1), 5122: ('h', 2)}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
DT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8, 5120: np.int8, 5122: np.int16}

def accessor(j, binc, i):
    a = j['accessors'][i]; bv = j['bufferViews'][a['bufferView']]
    n = NC[a['type']]; dt = DT[a['componentType']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    arr = np.frombuffer(bytes(binc[start:start + a['count'] * n * np.dtype(dt).itemsize]), dtype=dt)
    return arr.reshape(a['count'], n) if n > 1 else arr

class Writer:
    """Accumulates buffer views/accessors into one binary chunk."""
    def __init__(self, j):
        self.j = j; self.bin = bytearray()
        j['bufferViews'] = []; j['accessors'] = []
    def add(self, arr, typ, target=None, minmax=False, normalized=False):
        arr = np.ascontiguousarray(arr)
        while len(self.bin) % 4: self.bin.append(0)
        ct = {np.float32: 5126, np.uint32: 5125, np.uint16: 5123, np.uint8: 5121, np.int8: 5120, np.int16: 5122}[arr.dtype.type]
        bv = {'buffer': 0, 'byteOffset': len(self.bin), 'byteLength': arr.nbytes}
        if target: bv['target'] = target
        self.bin += arr.tobytes()
        self.j['bufferViews'].append(bv)
        a = {'bufferView': len(self.j['bufferViews']) - 1, 'componentType': ct,
             'count': int(arr.shape[0]), 'type': typ}
        if normalized: a['normalized'] = True
        if minmax:
            a['min'] = [float(x) for x in np.atleast_1d(arr.min(axis=0))]
            a['max'] = [float(x) for x in np.atleast_1d(arr.max(axis=0))]
        self.j['accessors'].append(a)
        return len(self.j['accessors']) - 1
    def save(self, path):
        while len(self.bin) % 4: self.bin.append(0)
        self.j['buffers'] = [{'byteLength': len(self.bin)}]
        js = json.dumps(self.j, separators=(',', ':')).encode()
        while len(js) % 4: js += b' '
        out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(self.bin))
        out += struct.pack('<II', len(js), 0x4E4F534A) + js
        out += struct.pack('<II', len(self.bin), 0x004E4942) + bytes(self.bin)
        open(path, 'wb').write(out)

# quaternions are (x, y, z, w)
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw*bx + ax*bw + ay*bz - az*by, aw*by - ax*bz + ay*bw + az*bx,
                     aw*bz + ax*by - ay*bx + az*bw, aw*bw - ax*bx - ay*by - az*bz])
def qconj(q): return np.array([-q[0], -q[1], -q[2], q[3]])
def qaxis(axis, deg):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis); h = np.radians(deg) / 2
    return np.array([*(axis * np.sin(h)), np.cos(h)])
def qrot(q, v):
    p = np.array([v[0], v[1], v[2], 0.0]); return qmul(qmul(q, p), qconj(q))[:3]
def qnorm(q): return q / np.linalg.norm(q)

def node_globals(j):
    """Return dict node index -> (global position, global rotation) for the rest pose."""
    parent = {}
    for i, n in enumerate(j['nodes']):
        for c in n.get('children', []): parent[c] = i
    out = {}
    def g(i):
        if i in out: return out[i]
        n = j['nodes'][i]
        t = np.array(n.get('translation', [0, 0, 0]), float); r = np.array(n.get('rotation', [0, 0, 0, 1]), float)
        if i in parent:
            pp, pr = g(parent[i]); out[i] = (pp + qrot(pr, t), qnorm(qmul(pr, r)))
        else: out[i] = (t, r)
        return out[i]
    for i in range(len(j['nodes'])): g(i)
    return out, parent


def add_image(writer, png_bytes, name):
    """Embed a PNG in the GLB binary chunk; returns the texture index (sampler 0 = repeat, trilinear)."""
    j = writer.j
    while len(writer.bin) % 4: writer.bin.append(0)
    j['bufferViews'].append({'buffer': 0, 'byteOffset': len(writer.bin), 'byteLength': len(png_bytes)})
    writer.bin += png_bytes
    j.setdefault('images', []).append({'name': name, 'mimeType': 'image/png', 'bufferView': len(j['bufferViews']) - 1})
    if not j.get('samplers'):
        j['samplers'] = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]
    j.setdefault('textures', []).append({'sampler': 0, 'source': len(j['images']) - 1})
    return len(j['textures']) - 1
