# SPDX-License-Identifier: Apache-2.0
"""Photographic grass clumps as crossed cards (Poly Haven grass_medium_01, CC0).

    python3 tools/assets/build_photoreal_grass.py

Ground cover is drawn thousands of times per frame, so a decimated photoscan (hundreds of
triangles per clump) is the wrong tool on a Mali-G52: it either costs millions of triangles or
collapses into specks. The scanned asset ships pre-rendered clump cards at the bottom of its
colour atlas; this cuts two of them out, derives an alpha matte from the black background,
bleeds colour into the transparent texels (no dark fringes in the mips) and builds three
crossed quads, both windings (12 triangles) per clump. Normals point up, so a clump shades like
the ground it grows from instead of flickering card by card.

Outputs keep the paths, .meta UUIDs and the single "*_Blades" primitive of the originals.
"""
from __future__ import annotations

import io
import math
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'characters'))
import polyhaven as ph  # noqa: E402
from gltf_util import Writer, add_image  # noqa: E402

ENV = os.path.join(ph.ROOT, 'game', 'assets', 'models', 'env')

# name -> (atlas boxes (l, t, r, b) at 1k, card height m, yaw offsets)
CLUMPS = {
    'grass_a': dict(boxes=[(200, 760, 505, 900), (600, 770, 835, 884)], height=0.55),
    'grass_b': dict(boxes=[(25, 885, 200, 1000), (588, 885, 815, 1018)], height=0.38),
}


def atlas_path():
    d = ph.model('grass_medium_01', '1k')
    return os.path.join(os.path.dirname(d), 'textures', 'grass_medium_01_diff_1k.jpg')


def cut(img, box, w=256, h=128):
    c = img[box[1]:box[3], box[0]:box[2]]
    a = np.clip((c.max(2) - 0.06) / 0.12, 0.0, 1.0)
    # bleed: replace background colour with the average blade colour, blurred outwards
    mean = (c * a[..., None]).sum((0, 1)) / max(a.sum(), 1.0)
    rgb = c * a[..., None] + mean * (1.0 - a[..., None])
    im = Image.fromarray((np.dstack([rgb, a]) * 255).astype(np.uint8), 'RGBA').resize((w, h), Image.LANCZOS)
    return im


def build(name, spec, img):
    cards = [cut(img, b) for b in spec['boxes']]
    # one texture: the two cards stacked (256 x 256)
    tex = Image.new('RGBA', (256, 256))
    for i, c in enumerate(cards): tex.paste(c, (0, i * 128))
    buf = io.BytesIO(); tex.save(buf, 'PNG', optimize=True)

    hgt = spec['height']
    pos, nrm, uv, idx = [], [], [], []
    for k in range(3):
        card = k % 2
        bw, bh = spec['boxes'][card][2] - spec['boxes'][card][0], spec['boxes'][card][3] - spec['boxes'][card][1]
        half = 0.5 * hgt * bw / bh * 0.7  # slightly narrowed: keeps the footprint (and overdraw) near the original clumps
        yaw = math.radians(k * 60.0 + 15.0)
        dx, dz = math.cos(yaw) * half, math.sin(yaw) * half
        v0 = len(pos)
        v_top, v_bot = card * 0.5, card * 0.5 + 0.5
        for (x, y, z, u, v) in ((-dx, 0, -dz, 0, v_bot), (dx, 0, dz, 1, v_bot),
                                (dx, hgt, dz, 1, v_top), (-dx, hgt, -dz, 0, v_top)):
            pos.append((x, y, z)); nrm.append((0.0, 1.0, 0.0)); uv.append((u, v))
        # both windings, single-sided material: a double-sided material would flip the up
        # normal on back faces (VICTUS shades back faces with -N) and turn them black
        idx += [v0, v0 + 1, v0 + 2, v0, v0 + 2, v0 + 3, v0, v0 + 2, v0 + 1, v0, v0 + 3, v0 + 2]
    j = {'asset': {'version': '2.0', 'generator': 'SPECIAL OPS build_photoreal_grass.py'},
         'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': name, 'mesh': 0}],
         'meshes': [{'name': name, 'primitives': []}], 'materials': []}
    w = Writer(j)
    t = add_image(w, buf.getvalue(), f'{name}_cards')
    j['materials'].append({'name': f'{name}_Blades', 'doubleSided': False, 'alphaMode': 'MASK', 'alphaCutoff': 0.5,
                           'pbrMetallicRoughness': {'baseColorTexture': {'index': t}, 'metallicFactor': 0.0,
                                                    'roughnessFactor': 0.85}})
    P = np.array(pos, np.float32)
    prim = {'attributes': {'POSITION': w.add(P, 'VEC3', 34962, minmax=True),
                           'NORMAL': w.add(np.array(nrm, np.float32), 'VEC3', 34962),
                           'TEXCOORD_0': w.add(np.array(uv, np.float32), 'VEC2', 34962)},
            'indices': w.add(np.array(idx, np.uint16), 'SCALAR', 34963), 'material': 0}
    j['meshes'][0]['primitives'].append(prim)
    out = os.path.join(ENV, f'{name}.glb')
    w.save(out)
    print('GRASS_OK', out, len(idx) // 3, 'tris')


def main():
    img = np.asarray(Image.open(atlas_path()).convert('RGB')).astype(np.float32) / 255.0
    for name, spec in CLUMPS.items(): build(name, spec, img)


if __name__ == '__main__':
    main()
