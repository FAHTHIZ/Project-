# SPDX-License-Identifier: Apache-2.0
"""Vellwood facility interiors: Operations 04-07 (all original).

    python3 tools/levels/build_facility.py            (models + scenes)
    python3 tools/levels/build_facility.py --scenes   (scenes only, models unchanged)

Each level is a list of rooms (axis-aligned rectangles in metres, with floor, wall and ceiling
materials, ceiling height, lighting style and acoustics) and openings between them. The builder
turns that into:

  * one shell model per level (models/interior/<level>_shell.glb): floors, walls and ceilings with
    box-projected UVs on the kit's tileable textures, door lintels above each opening;
  * static box colliders for every wall run and floor slab;
  * doors (scripts/door.luau): sliding leaves that open for anyone nearby, optionally locked until
    the mission unlocks them (a locked door also has a collider; unlocking removes it);
  * ceiling fittings with matching lights (fluorescent, sodium, work lamps, emergency), a
    ReverbZone per room sized to it, and the room's ambience;
  * the furniture kit (models/interior/*.glb) placed by per-room furnishing rules and explicit
    hero props (breaker wall, blast door, archive rows, the chair and V-01);
  * the cast (the squad follows on a navmesh; interiors are small enough), Greyline positions and
    the mission director scripts/missions/facility.luau with `chapter` set.

Coordinates: x east, z south (the player enters from the south and pushes north, -Z).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent / 'props'))
sys.path.insert(0, str(HERE.parent / 'scenes'))
sys.path.insert(0, str(HERE.parent / 'characters'))

import build_structures as BS  # noqa: E402
from build_structures import Part, Model, tex_concrete, tex_paint, tex_planks, tex_sign, periodic_noise, _png  # noqa: E402
import meshkit as mk  # noqa: E402
from vscene import Scene, transform, script, collider, body, quat_euler  # noqa: E402
import common  # noqa: E402
import rig  # noqa: E402
import actors  # noqa: E402

GAME = ROOT / 'game'
ASSETS = GAME / 'assets'
KIT = 'models/interior/'
LAYOUT = {}
DOOR_H = 2.4


# ------------------------------------------------------------------------------------------------
# textures

def tex_tiles(seed, base='#c9c6bd', grout='#8f8b82', n=4, speck=0.06):
    s = BS.TEX
    rng = np.random.default_rng(seed)
    b = np.array(BS._rgb(base), float)
    g = np.array(BS._rgb(grout), float)
    img = np.ones((s, s, 3)) * b
    noise = periodic_noise(s, seed, beta=1.6)
    img *= (0.94 + 0.08 * noise)[..., None]
    cell = s // n
    for i in range(n):
        for j in range(n):
            k = 0.96 + 0.07 * rng.random()
            img[i * cell:(i + 1) * cell, j * cell:(j + 1) * cell] *= k
    w = max(2, s // 170)
    for i in range(n + 1):
        img[max(0, i * cell - w):i * cell + w, :] = g
        img[:, max(0, i * cell - w):i * cell + w] = g
    sp = rng.random((s, s)) < speck * 0.05
    img[sp] *= 0.7
    return _png(img)


def tex_vinyl(seed, base='#b9c0bf'):
    s = BS.TEX
    b = np.array(BS._rgb(base), float)
    n1 = periodic_noise(s, seed, beta=2.4)
    n2 = periodic_noise(s, seed + 1, beta=1.2)
    img = np.ones((s, s, 3)) * b * (0.93 + 0.06 * n1 + 0.03 * n2)[..., None]
    rng = np.random.default_rng(seed)
    flecks = rng.random((s, s)) < 0.01
    img[flecks] *= 0.82
    return _png(img)


def tex_ceiling(seed):
    s = BS.TEX
    rng = np.random.default_rng(seed)
    img = np.ones((s, s, 3)) * np.array(BS._rgb('#d9d7cf'), float)
    holes = rng.random((s, s)) < 0.02
    img[holes] *= 0.75
    img *= (0.95 + 0.05 * periodic_noise(s, seed, beta=2.0))[..., None]
    w = 3
    img[:w, :] = img[-w:, :] = img[:, :w] = img[:, -w:] = np.array(BS._rgb('#a7a7a2'), float)
    return _png(img)


def tex_wallpanel(seed, base='#d6d3c8', stripe='#5d7b86', band=0.18):
    s = BS.TEX
    img = np.ones((s, s, 3)) * np.array(BS._rgb(base), float)
    img *= (0.95 + 0.05 * periodic_noise(s, seed, beta=2.2))[..., None]
    # a painted dado band near the bottom of the tile (1 tile = wall height)
    y0 = int(s * (1 - band - 0.12)); y1 = int(s * (1 - 0.12))
    img[y0:y1, :] = np.array(BS._rgb(stripe), float) * (0.95 + 0.05 * periodic_noise(s, seed + 3)[y0:y1, :, None])
    img[int(s * 0.88):, :] *= 0.72  # skirting
    return _png(img)


def tex_cardboard(seed):
    s = BS.TEX
    img = np.ones((s, s, 3)) * np.array(BS._rgb('#a2814f'), float)
    img *= (0.9 + 0.12 * periodic_noise(s, seed, beta=1.8))[..., None]
    rng = np.random.default_rng(seed)
    for _ in range(6):
        y = int(rng.uniform(0, s))
        img[y:y + 6, :] *= 0.92
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 54)
    except OSError:
        f = ImageFont.load_default()
    for k in range(3):
        d.text((40 + k * 160, 200 + (k % 2) * 90), f'V-{rng.integers(2, 999):03d}', font=f, fill=(45, 38, 30))
    return _png(np.asarray(im).astype(float))


def tex_grate(seed):
    s = BS.TEX
    img = np.ones((s, s, 3)) * np.array(BS._rgb('#4b4f50'), float)
    n = 16
    c = s // n
    for i in range(n):
        img[i * c:i * c + 4, :] = np.array(BS._rgb('#6c7172'), float)
        img[:, i * c:i * c + 4] = np.array(BS._rgb('#6c7172'), float)
    img *= (0.9 + 0.1 * periodic_noise(s, seed))[..., None]
    return _png(img)


def tex_fabric(seed, base='#3f4a57'):
    s = BS.TEX
    b = np.array(BS._rgb(base), float)
    x = np.arange(s)
    weave = 0.95 + 0.05 * np.sin(x[:, None] * 1.3) * np.sin(x[None, :] * 1.3)
    img = np.ones((s, s, 3)) * b * (weave * (0.94 + 0.06 * periodic_noise(s, seed)))[..., None]
    return _png(img)


def tex_wood(seed):
    return tex_planks(seed, '#8a6a48', boards=3)


def tex_dummy(seed):
    """Crash-test style mannequin skin: matte yellow with black-and-yellow target quadrants."""
    s = BS.TEX
    img = np.ones((s, s, 3)) * np.array(BS._rgb('#d9b43a'), float)
    img *= (0.93 + 0.07 * periodic_noise(s, seed, beta=2.2))[..., None]
    return _png(img)


def tex_label(text, sub=''):
    return tex_sign(text, sub, bg='#f2efe6', fg='#1d2124', w=512, h=256)


# ------------------------------------------------------------------------------------------------
# kit models (front faces -Z, origin on the floor at the footprint centre)

class Kit:
    def __init__(self, name):
        self.m = Model(name)
        self.lay = BS.Layout(name)
        self.parts = []
        LAYOUT[name] = BS.LAYOUT[name]

    def part(self, key, png, **kw):
        p = Part(self.m, f'{self.m.name}_{key}', png, **kw)
        self.parts.append(p)
        return p

    def save(self, out):
        for p in self.parts:
            p.emit()
        self.m.save(os.path.join(out, 'models', 'interior', self.m.name + '.glb'))


def k_desk(out):
    k = Kit('desk')
    top = k.part('Top', tex_wood(201), tile=1.2, rough=0.6)
    steel = k.part('Frame', tex_paint(202, '#5a5f63', 0.1, False), tile=1.0, rough=0.5, metal=0.6)
    top.box((-0.8, 0.72, -0.4), (0.8, 0.76, 0.4))
    for x in (-0.75, 0.75):
        steel.box((x - 0.03, 0, -0.36), (x + 0.03, 0.72, -0.3))
        steel.box((x - 0.03, 0, 0.3), (x + 0.03, 0.72, 0.36))
        steel.box((x - 0.03, 0.05, -0.33), (x + 0.03, 0.09, 0.33))
    steel.box((0.3, 0.35, -0.38), (0.72, 0.7, 0.38))  # drawer pedestal
    mon = k.part('Monitor', tex_paint(203, '#1d1f22', 0.0, False), tile=0.5, rough=0.4)
    mon.box((-0.28, 0.98, 0.18), (0.28, 1.3, 0.2))
    mon.box((-0.04, 0.76, 0.16), (0.04, 0.98, 0.22))
    mon.box((-0.12, 0.76, 0.12), (0.12, 0.78, 0.26))
    scr = k.part('Screen', None, rough=0.2, color=(0.05, 0.06, 0.07))
    scr.box((-0.26, 1.0, 0.176), (0.26, 1.28, 0.18))
    mug = k.part('Mug', tex_paint(204, '#e9e6dc', 0.05, False), tile=0.2, rough=0.4)
    mug.raw(mk.capsule((-0.45, 0.77, -0.05), (-0.45, 0.86, -0.05), 0.04, segs=10, rings=2))
    paper = k.part('Paper', tex_label('MEMO', 'Do not lose the card'), tile=0.5, rough=0.9)
    paper.box((0.05, 0.761, -0.2), (0.33, 0.765, 0.02), yaw=12)
    k.lay.col((-0.8, 0, -0.4), (0.8, 0.76, 0.4))
    k.lay.anchor('seat', (0, 0, -0.75), 0.0)
    k.save(out)


def k_chair(out):
    k = Kit('office_chair')
    fab = k.part('Fabric', tex_fabric(210), tile=0.5, rough=0.95)
    steel = k.part('Base', tex_paint(211, '#2a2c2e', 0.05, False), tile=0.5, rough=0.4, metal=0.5)
    fab.raw(mk.rounded_box((0, 0.46, 0), (0.24, 0.05, 0.24), 0.5))
    fab.raw(mk.rounded_box((0, 0.8, 0.22), (0.22, 0.26, 0.04), 0.5))
    steel.box((-0.025, 0.12, -0.025), (0.025, 0.42, 0.025))
    for a in range(5):
        r = math.radians(a * 72)
        steel.beam((0, 0.1, 0), (math.sin(r) * 0.3, 0.06, math.cos(r) * 0.3), 0.04)
        steel.raw(mk.ellipsoid((math.sin(r) * 0.3, 0.03, math.cos(r) * 0.3), (0.03, 0.03, 0.03), segs=8, rings=5))
    steel.beam((0, 0.44, 0.18), (0, 0.6, 0.22), 0.04)
    k.lay.col((-0.3, 0, -0.3), (0.3, 1.0, 0.3))
    k.save(out)


def k_test_chair(out):
    """The V-01 trial chair: an over-engineered ergonomic seat on a turntable plinth."""
    k = Kit('test_chair')
    shell = k.part('Shell', tex_paint(220, '#e4e4e0', 0.02, False), tile=0.6, rough=0.35)
    cush = k.part('Cushion', tex_fabric(221, '#27405a'), tile=0.4, rough=0.95)
    steel = k.part('Steel', tex_paint(222, '#8c9196', 0.05, False), tile=0.6, rough=0.3, metal=0.8)
    plinth = k.part('Plinth', tex_concrete(223, '#bdbab2', 1, 0.2), tile=1.5, rough=0.8)
    plinth.raw(mk.loft((0, 0, 0), (0, 0.18, 0), [(0, 1.2, 1.2), (1, 1.2, 1.2)], segs=24))
    steel.raw(mk.loft((0, 0.18, 0), (0, 0.42, 0), [(0, 0.08, 0.08), (1, 0.06, 0.06)], segs=12))
    shell.raw(mk.rounded_box((0, 0.52, 0), (0.34, 0.08, 0.32), 0.6))
    cush.raw(mk.rounded_box((0, 0.62, -0.02), (0.3, 0.04, 0.28), 0.6))
    shell.raw(mk.rounded_box((0, 1.0, 0.33), (0.34, 0.45, 0.06), 0.6, rot=mk.rot_x(-8)))
    cush.raw(mk.rounded_box((0, 1.0, 0.27), (0.29, 0.4, 0.04), 0.6, rot=mk.rot_x(-8)))
    shell.raw(mk.rounded_box((0, 1.58, 0.38), (0.18, 0.12, 0.06), 0.6))
    for x in (-0.38, 0.38):
        shell.raw(mk.rounded_box((x, 0.78, 0.0), (0.05, 0.04, 0.26), 0.6))
        steel.beam((x, 0.55, 0.12), (x, 0.76, 0.05), 0.04)
    # sensor cables to a small console
    con = k.part('Console', tex_paint(224, '#3b4146', 0.05, False), tile=0.5, rough=0.5)
    con.box((0.9, 0.18, 0.4), (1.3, 1.0, 0.7))
    led = k.part('Led', None, rough=0.3, color=(0.2, 1.0, 0.4), emissive=(0.2, 1.0, 0.4), strength=3.0)
    led.box((0.95, 0.85, 0.395), (1.02, 0.9, 0.4))
    k.lay.col((-1.2, 0, -1.2), (1.2, 0.18, 1.2))
    k.lay.col((-0.42, 0.18, -0.36), (0.42, 1.7, 0.45))
    k.lay.anchor('behind', (0, 0, 0.9), 0.0)
    k.save(out)


def k_dummy(out):
    """V-01: a jointed seating-trial mannequin, slumped where someone left it behind the chair.
    Deliberately friendly (rounded, matte yellow, painted smile marker, a luggage tag on one foot)."""
    k = Kit('v01_dummy')
    skin = k.part('Skin', tex_dummy(230), tile=0.4, rough=0.7)
    joint = k.part('Joint', tex_paint(231, '#222326', 0.0, False), tile=0.3, rough=0.4, metal=0.3)
    mark = k.part('Marker', None, rough=0.6, color=(0.06, 0.06, 0.07))
    tag = k.part('Tag', tex_label('V-01', 'SEATING TRIAL UNIT'), tile=0.2, rough=0.8)
    # sitting on the floor, back against a wall/chair, legs out toward -Z
    pelvis = (0, 0.16, 0.0)
    skin.raw(mk.rounded_box(pelvis, (0.17, 0.1, 0.11), 0.7))
    skin.raw(mk.capsule((0, 0.25, 0.04), (0, 0.6, 0.1), 0.15, 0.17, segs=12))  # torso leaning back
    joint.raw(mk.capsule((0, 0.68, 0.11), (0, 0.74, 0.12), 0.05))
    skin.raw(mk.ellipsoid((0.03, 0.88, 0.1), (0.11, 0.13, 0.11), segs=14, rings=10))  # head tilted
    mark.raw(mk.ellipsoid((0.09, 0.9, 0.0), (0.03, 0.03, 0.012), segs=8, rings=5))
    mark.raw(mk.ellipsoid((-0.01, 0.9, 0.0), (0.03, 0.03, 0.012), segs=8, rings=5))
    for i in range(5):  # painted smile
        a = math.radians(-50 + i * 25)
        mark.raw(mk.ellipsoid((0.04 + math.sin(a) * 0.05, 0.83 - math.cos(a) * 0.012, 0.0), (0.012, 0.008, 0.01),
                              segs=6, rings=4))
    for s in (-1, 1):
        hip = (s * 0.1, 0.13, -0.05)
        knee = (s * 0.13, 0.2, -0.44)
        ankle = (s * 0.14, 0.08, -0.82)
        skin.raw(mk.capsule(hip, knee, 0.08, 0.07))
        joint.raw(mk.ellipsoid(knee, (0.07, 0.07, 0.07), segs=10, rings=6))
        skin.raw(mk.capsule(knee, ankle, 0.065, 0.055))
        skin.raw(mk.rounded_box((ankle[0], 0.06, ankle[2] - 0.08), (0.05, 0.06, 0.12), 0.6))
        sh = (s * 0.2, 0.6, 0.09)
        el = (s * 0.3, 0.36, 0.0)
        wr = (s * 0.27, 0.14, -0.2)
        skin.raw(mk.capsule(sh, el, 0.06, 0.055))
        joint.raw(mk.ellipsoid(el, (0.055, 0.055, 0.055), segs=10, rings=6))
        skin.raw(mk.capsule(el, wr, 0.05, 0.045))
        skin.raw(mk.ellipsoid((wr[0], 0.09, wr[2] - 0.04), (0.05, 0.035, 0.07), segs=10, rings=6))
    # luggage tag on the right foot
    tag.box((0.17, 0.08, -0.93), (0.28, 0.14, -0.928))
    k.lay.col((-0.35, 0, -1.0), (0.35, 0.95, 0.25))
    k.save(out)


def k_lab_bench(out):
    k = Kit('lab_bench')
    top = k.part('Top', tex_paint(240, '#2f3437', 0.02, False), tile=1.0, rough=0.35)
    cab = k.part('Cabinet', tex_paint(241, '#d7d9d4', 0.05, False), tile=0.8, rough=0.5)
    glass = k.part('Glass', None, rough=0.1, color=(0.75, 0.85, 0.85))
    top.box((-1.5, 0.88, -0.45), (1.5, 0.92, 0.45))
    cab.box((-1.45, 0, -0.42), (1.45, 0.88, 0.42))
    cab.box((-1.45, 0.92, 0.3), (1.45, 1.6, 0.42))
    cab.box((-1.45, 1.25, 0.1), (1.45, 1.28, 0.42))
    rng = np.random.default_rng(242)
    for i in range(7):  # soil sample jars (it is, after all, a soil science lab)
        x = -1.3 + i * 0.4 + rng.uniform(-0.05, 0.05)
        glass.raw(mk.capsule((x, 0.93, -0.1), (x, 1.08, -0.1), 0.05, segs=10, rings=2))
    soil = k.part('Soil', None, rough=0.95, color=(0.3, 0.22, 0.15))
    for i in range(7):
        x = -1.3 + i * 0.4
        soil.box((x - 0.035, 0.93, -0.135), (x + 0.035, 1.0, -0.065))
    k.lay.col((-1.5, 0, -0.45), (1.5, 1.6, 0.45))
    k.save(out)


def k_shelf(out, name='shelf_unit', w=2.0, d=0.5, h=2.2, boxes=True, seed=250):
    k = Kit(name)
    steel = k.part('Steel', tex_paint(seed, '#6c7377', 0.15, False), tile=1.0, rough=0.5, metal=0.6)
    card = k.part('Box', tex_cardboard(seed + 1), tile=0.6, rough=0.9)
    for x in (-w / 2, w / 2):
        for z in (-d / 2, d / 2):
            steel.box((x - 0.025, 0, z - 0.025), (x + 0.025, h, z + 0.025))
    levels = np.linspace(0.12, h - 0.1, 5)
    rng = np.random.default_rng(seed)
    for y in levels:
        steel.box((-w / 2, y - 0.02, -d / 2), (w / 2, y, d / 2))
        if boxes and y < h - 0.2:
            x = -w / 2 + 0.05
            while x < w / 2 - 0.35:
                bw = rng.uniform(0.3, 0.45)
                bh = rng.uniform(0.22, min(0.36, (h - 0.1) / 5 - 0.06))
                if rng.random() < 0.88:
                    card.box((x, y, -d / 2 + 0.03), (x + bw, y + bh, d / 2 - 0.03), yaw=float(rng.uniform(-3, 3)))
                x += bw + rng.uniform(0.02, 0.06)
    k.lay.col((-w / 2, 0, -d / 2), (w / 2, h, d / 2))
    k.save(out)


def k_server_rack(out):
    k = Kit('server_rack')
    body_ = k.part('Body', tex_paint(260, '#202326', 0.05, False), tile=0.8, rough=0.45, metal=0.4)
    led = k.part('Led', None, rough=0.3, color=(0.3, 0.8, 1.0), emissive=(0.3, 0.8, 1.0), strength=2.5)
    body_.box((-0.3, 0, -0.5), (0.3, 2.0, 0.5))
    for i in range(12):
        y = 0.2 + i * 0.14
        led.box((-0.25, y, -0.505), (-0.22, y + 0.02, -0.5))
        if i % 3 == 0:
            led.box((-0.18, y, -0.505), (-0.15, y + 0.02, -0.5))
    k.lay.col((-0.3, 0, -0.5), (0.3, 2.0, 0.5))
    k.save(out)


def k_breakers(out):
    """Switch-room breaker wall with labelled rows and the main switch (mission anchor)."""
    k = Kit('breaker_wall')
    cab = k.part('Cabinet', tex_paint(270, '#8f9894', 0.1, True), tile=1.0, rough=0.5, metal=0.5)
    lab = k.part('Labels', tex_label('MAIN SUPPLY', 'Labelled. Every one.'), tile=1.0, rough=0.8)
    lever = k.part('Lever', tex_paint(271, '#b8342b', 0.0, False), tile=0.3, rough=0.4)
    for i in range(4):
        x = -2.4 + i * 1.2
        cab.box((x, 0.3, -0.25), (x + 1.1, 2.1, 0))
        for r in range(6):
            cab.box((x + 0.1, 0.5 + r * 0.26, -0.27), (x + 1.0, 0.62 + r * 0.26, -0.25))
    P, N, I, UV = BS.hexa(BS.box_c((-1.0, 2.15, -0.27), (1.0, 2.55, -0.25)))
    UV = np.c_[(P[:, 0] + 1.0) / 2.0, 1 - (P[:, 1] - 2.15) / 0.4]
    lab.mesh.add((P, N, I), (1, 1, 1), uv=UV)
    lever.box((2.3, 1.0, -0.4), (2.42, 1.5, -0.26))
    k.lay.col((-2.4, 0, -0.27), (2.4, 2.6, 0))
    k.lay.anchor('main', (2.36, 1.2, -0.7), 180.0)
    k.save(out)


def k_bunk(out):
    k = Kit('bunk_bed')
    steel = k.part('Frame', tex_paint(280, '#4e5a4a', 0.2, False), tile=1.0, rough=0.5, metal=0.5)
    mat = k.part('Mattress', tex_fabric(281, '#5d6650'), tile=0.6, rough=0.95)
    for x in (-0.45, 0.45):
        for z in (-1.0, 1.0):
            steel.box((x - 0.025, 0, z - 0.025), (x + 0.025, 1.7, z + 0.025))
    for y in (0.35, 1.25):
        steel.box((-0.47, y - 0.04, -1.02), (0.47, y, 1.02))
        mat.raw(mk.rounded_box((0, y + 0.06, 0), (0.43, 0.06, 0.96), 0.5))
    k.lay.col((-0.47, 0, -1.02), (0.47, 1.7, 1.02))
    k.save(out)


def k_pump(out):
    k = Kit('pump')
    body_ = k.part('Body', tex_paint(290, '#2e6c74', 0.25, True), tile=0.8, rough=0.45, metal=0.6)
    pipe = k.part('Pipe', tex_paint(291, '#7b7f80', 0.2, False), tile=0.8, rough=0.4, metal=0.7)
    body_.raw(mk.loft((-0.6, 0.6, 0), (0.6, 0.6, 0), [(0, 0.45, 0.45), (1, 0.45, 0.45)], segs=16))
    body_.box((-0.8, 0, -0.5), (0.8, 0.2, 0.5))
    pipe.raw(mk.loft((0.6, 0.6, 0), (1.6, 0.6, 0), [(0, 0.15, 0.15), (1, 0.15, 0.15)], segs=12, caps=False))
    pipe.raw(mk.loft((-0.2, 1.0, 0), (-0.2, 4.5, 0), [(0, 0.15, 0.15), (1, 0.15, 0.15)], segs=12, caps=False))
    k.lay.col((-0.8, 0, -0.5), (0.8, 1.1, 0.5))
    k.save(out)


def k_pipes(out):
    k = Kit('pipe_run')
    pipe = k.part('Pipe', tex_paint(300, '#6f7a7c', 0.25, False), tile=1.0, rough=0.4, metal=0.7)
    br = k.part('Bracket', tex_paint(301, '#3a3c3e', 0.05, False), tile=0.5, rough=0.5, metal=0.6)
    for i, (y, r) in enumerate(((0.0, 0.12), (0.32, 0.08), (0.56, 0.06))):
        pipe.raw(mk.loft((-4, y, 0), (4, y, 0), [(0, r, r), (1, r, r)], segs=12, caps=False))
    for x in (-3.5, 0, 3.5):
        br.box((x - 0.03, -0.15, -0.16), (x + 0.03, 0.7, -0.12))
    k.save(out)


def k_lights(out):
    k = Kit('light_fluoro')
    hous = k.part('Housing', tex_paint(310, '#d8d8d2', 0.02, False), tile=0.6, rough=0.4, metal=0.3)
    lens = k.part('Lens', None, rough=0.2, color=(1, 1, 1), emissive=(1.0, 0.98, 0.92), strength=3.0)
    hous.box((-0.65, -0.08, -0.18), (0.65, 0, 0.18))
    lens.box((-0.6, -0.085, -0.13), (0.6, -0.08, 0.13))
    k.save(out)
    k = Kit('light_cage')
    cage = k.part('Cage', tex_paint(311, '#2b2d2f', 0.05, False), tile=0.3, rough=0.5, metal=0.6)
    bulb = k.part('Bulb', None, rough=0.2, color=(1, 0.8, 0.5), emissive=(1.0, 0.72, 0.4), strength=4.0)
    bulb.raw(mk.ellipsoid((0, -0.16, 0), (0.08, 0.1, 0.08), segs=10, rings=6))
    cage.box((-0.12, -0.04, -0.12), (0.12, 0, 0.12))
    for a in range(4):
        r = math.radians(a * 90 + 45)
        cage.beam((math.sin(r) * 0.1, -0.02, math.cos(r) * 0.1), (math.sin(r) * 0.1, -0.28, math.cos(r) * 0.1), 0.015)
    k.save(out)
    k = Kit('light_emergency')
    hous = k.part('Housing', tex_paint(312, '#e2e0d8', 0.02, False), tile=0.3, rough=0.4)
    lens = k.part('Lens', None, rough=0.2, color=(1, 0.5, 0.3), emissive=(1.0, 0.42, 0.18), strength=4.0)
    hous.box((-0.2, -0.05, -0.08), (0.2, 0.05, 0))
    lens.box((-0.17, -0.035, -0.085), (0.17, 0.035, -0.08))
    k.save(out)


def k_doors(out):
    k = Kit('door_leaf')
    leaf = k.part('Leaf', tex_paint(320, '#8e9aa0', 0.1, False), tile=1.0, rough=0.45, metal=0.5)
    win = k.part('Window', None, rough=0.1, color=(0.55, 0.65, 0.7))
    leaf.box((-0.5, 0, -0.04), (0.5, DOOR_H - 0.02, 0.04))
    win.box((-0.2, 1.3, -0.045), (0.2, 1.9, 0.045))
    k.save(out)
    k = Kit('blast_door')
    leaf = k.part('Leaf', tex_paint(321, '#6b6f58', 0.3, True), tile=1.0, rough=0.5, metal=0.6)
    stripe = k.part('Stripe', tex_sign('', '', bg='#d9b13a', fg='#111', stripe='#111111'), tile=1.0, rough=0.6)
    wheel = k.part('Wheel', tex_paint(322, '#b33a2c', 0.1, False), tile=0.3, rough=0.4, metal=0.5)
    leaf.box((-1.6, 0, -0.25), (1.6, 3.2, 0.25))
    stripe.box((-1.6, 2.9, -0.27), (1.6, 3.1, -0.25))
    wheel.raw(mk.loft((0, 1.4, -0.3), (0, 1.4, -0.45), [(0, 0.35, 0.35), (1, 0.35, 0.35)], segs=20))
    k.save(out)
    k = Kit('lift_car')
    wall = k.part('Wall', tex_paint(323, '#9ba3a6', 0.05, False), tile=1.0, rough=0.35, metal=0.7)
    floor = k.part('Floor', tex_grate(324), tile=1.0, rough=0.6, metal=0.6)
    lamp = k.part('Lamp', None, rough=0.2, color=(1, 1, 1), emissive=(1, 0.97, 0.9), strength=2.5)
    floor.box((-1.5, -0.1, -1.5), (1.5, 0, 1.5))
    wall.box((-1.5, 0, 1.4), (1.5, 2.8, 1.5))
    wall.box((-1.5, 0, -1.5), (-1.4, 2.8, 1.5))
    wall.box((1.4, 0, -1.5), (1.5, 2.8, 1.5))
    wall.box((-1.5, 2.8, -1.5), (1.5, 2.9, 1.5))
    lamp.box((-0.5, 2.78, -0.3), (0.5, 2.8, 0.3))
    k.lay.anchor('panel', (1.3, 1.2, 0.6), 90.0)
    k.save(out)


def k_signs(out):
    for key, text, sub in (('sign_soil', 'VELLWOOD', 'Soil Science Annexe'), ('sign_switch', 'SWITCH ROOM', 'Authorised staff'),
                           ('sign_level4', 'LEVEL -4', 'Deep Store'), ('sign_archive', 'ARCHIVE', 'Do not lean on shelves'),
                           ('sign_chamber', 'TRIAL CHAMBER', 'Seating programme'), ('sign_visitor', 'VISITORS', 'Please sign in'),
                           ('sign_pump', 'PUMP ROOM', 'Wet floor'), ('sign_manager', 'SITE MANAGER', 'Knock first')):
        k = Kit(key)
        pl = k.part('Plate', tex_sign(text, sub, bg='#eceae2', fg='#1f2a33', w=1024, h=512), tile=1.0, rough=0.6)
        P, N, I, UV = BS.hexa(BS.box_c((-0.6, 0, -0.02), (0.6, 0.6, 0)))
        UV = np.c_[(P[:, 0] + 0.6) / 1.2, 1 - P[:, 1] / 0.6]
        pl.mesh.add((P, N, I), (1, 1, 1), uv=UV)
        k.save(out)


def k_misc(out):
    k = Kit('reception_desk')
    wood = k.part('Wood', tex_wood(330), tile=1.0, rough=0.55)
    top = k.part('Top', tex_paint(331, '#e0ddd3', 0.02, False), tile=1.0, rough=0.4)
    wood.box((-2.0, 0, -0.35), (2.0, 1.1, 0.35))
    top.box((-2.05, 1.1, -0.45), (2.05, 1.14, 0.45))
    book = k.part('Book', tex_label('VISITOR LOG', 'Sign in. Sign out.'), tile=0.4, rough=0.8)
    book.box((-0.6, 1.14, -0.4), (-0.2, 1.17, -0.1), yaw=-8)
    k.lay.col((-2.05, 0, -0.45), (2.05, 1.14, 0.45))
    k.lay.anchor('log', (-0.4, 1.2, -0.75), 180.0)
    k.save(out)
    k = Kit('crate_stack')
    wood = k.part('Wood', tex_planks(340, '#7d6646', 4), tile=0.8, rough=0.85)
    for (x, y, z, s) in ((0, 0, 0, 1.0), (1.05, 0, 0.1, 0.9), (0.4, 1.0, 0.0, 0.8)):
        wood.box((x - 0.5 * s, y, z - 0.5 * s), (x + 0.5 * s, y + s, z + 0.5 * s))
    k.lay.col((-0.5, 0, -0.5), (1.5, 1.8, 0.55))
    k.save(out)
    k = Kit('column')
    conc = k.part('Concrete', tex_concrete(350, '#9c9a92', 1, 0.6), tile=1.5, rough=0.9)
    conc.box((-0.4, 0, -0.4), (0.4, 6.0, 0.4))
    k.lay.col((-0.4, 0, -0.4), (0.4, 6.0, 0.4))
    k.save(out)
    k = Kit('key_ring')
    st = k.part('Steel', tex_paint(360, '#c9c7bd', 0.0, False), tile=0.1, rough=0.25, metal=0.9)
    st.raw(mk.loft((0, 0.01, 0), (0, 0.02, 0), [(0, 0.05, 0.05), (1, 0.05, 0.05)], segs=14, caps=False))
    for i in range(10):
        a = math.radians(i * 36)
        st.box((math.sin(a) * 0.05, 0.005, math.cos(a) * 0.05), (math.sin(a) * 0.1, 0.012, math.cos(a) * 0.1 + 0.012))
    smile = k.part('Smiley', tex_paint(361, '#e3c32c', 0.0, False), tile=0.1, rough=0.5)
    smile.raw(mk.ellipsoid((0.12, 0.01, 0.0), (0.02, 0.005, 0.02), segs=10, rings=4))
    k.save(out)


def build_kit(out):
    for fn in (k_desk, k_chair, k_test_chair, k_dummy, k_lab_bench, k_shelf, k_server_rack, k_breakers, k_bunk,
               k_pump, k_pipes, k_lights, k_doors, k_signs, k_misc):
        fn(out)
    k_shelf(out, 'archive_shelf', w=8.0, d=1.0, h=3.4, seed=380)
    k_shelf(out, 'store_shelf', w=3.0, d=0.8, h=2.6, seed=390)


# ------------------------------------------------------------------------------------------------
# level shells

MATS = {
    # key: (texture fn, tile metres, roughness, metal)
    'tile': (lambda: tex_tiles(400), 2.4, 0.5, 0.0),
    'vinyl': (lambda: tex_vinyl(401), 2.0, 0.45, 0.0),
    'conc': (lambda: tex_concrete(402, '#8e8c86', 2, 0.6), 3.0, 0.9, 0.0),
    'conc_wet': (lambda: tex_concrete(403, '#6f7272', 2, 0.9), 3.0, 0.3, 0.0),
    'grate': (lambda: tex_grate(404), 1.0, 0.6, 0.6),
    'wall_office': (lambda: tex_wallpanel(405, '#d8d4c7', '#5f7d88'), 3.2, 0.8, 0.0),
    'wall_lab': (lambda: tex_wallpanel(406, '#e4e6e3', '#7aa2a0', 0.1), 3.2, 0.6, 0.0),
    'wall_conc': (lambda: tex_concrete(407, '#a3a198', 3, 0.5), 3.0, 0.92, 0.0),
    'wall_bunker': (lambda: tex_wallpanel(408, '#7e8470', '#4f5446', 0.35), 4.5, 0.85, 0.0),
    'wall_white': (lambda: tex_wallpanel(409, '#eeeeea', '#c8ccd0', 0.06), 9.0, 0.5, 0.0),
    'ceil_tile': (lambda: tex_ceiling(410), 1.2, 0.9, 0.0),
    'ceil_conc': (lambda: tex_concrete(411, '#7c7b76', 2, 0.4), 3.0, 0.95, 0.0),
}


class Room:
    def __init__(self, name, x0, z0, x1, z1, floor='tile', wall='wall_office', ceil='ceil_tile', h=3.2,
                 lights='fluoro', reverb=(0.4, 0.25), tone=None, sign=None):
        self.name, self.x0, self.z0, self.x1, self.z1 = name, x0, z0, x1, z1
        self.floor, self.wall, self.ceil, self.h = floor, wall, ceil, h
        self.lights, self.reverb, self.tone, self.sign = lights, reverb, tone, sign

    def inside(self, x, z):
        return self.x0 <= x < self.x1 and self.z0 <= z < self.z1

    @property
    def c(self):
        return ((self.x0 + self.x1) / 2, (self.z0 + self.z1) / 2)


class Level:
    def __init__(self, key, rooms, openings, env='interior', tone='audio/ambient/interior.wav'):
        self.key, self.rooms, self.openings = key, rooms, openings
        self.env, self.tone = env, tone
        self.room = {r.name: r for r in rooms}

    def room_at(self, x, z):
        for r in self.rooms:
            if r.inside(x, z):
                return r
        return None

    def opening_at(self, axis, line, t):
        """An opening (dict) covering unit edge t on the wall `line` along `axis`."""
        for o in self.openings:
            if o['axis'] == axis and abs(o['at'] - line) < 1e-6 and o['a'] <= t < o['b']:
                return o
        return None

    def wall_runs(self):
        out = []
        xs = [r.x0 for r in self.rooms] + [r.x1 for r in self.rooms]
        zs = [r.z0 for r in self.rooms] + [r.z1 for r in self.rooms]
        X0, X1, Z0, Z1 = int(min(xs)) - 1, int(max(xs)) + 1, int(min(zs)) - 1, int(max(zs)) + 1
        for axis in ('z', 'x'):
            lines = range(X0, X1 + 1) if axis == 'z' else range(Z0, Z1 + 1)
            span = range(Z0, Z1) if axis == 'z' else range(X0, X1)
            for L in lines:
                cur = None
                for t in span:
                    if axis == 'z':
                        a, b = self.room_at(L - 0.5, t + 0.5), self.room_at(L + 0.5, t + 0.5)
                    else:
                        a, b = self.room_at(t + 0.5, L - 0.5), self.room_at(t + 0.5, L + 0.5)
                    key = None
                    if a is not b and (a or b):
                        op = self.opening_at(axis, L, t)
                        h = max(x.h for x in (a, b) if x)
                        owner = a if (a and (not b or a.h >= b.h)) else b
                        key = (owner.wall, op['id'] if op else None, h, owner.name)
                    if cur and key == cur['key']:
                        cur['b'] = t + 1
                    else:
                        if cur:
                            out.append(cur)
                        cur = {'key': key, 'axis': axis, 'line': L, 'a': t, 'b': t + 1} if key else None
                if cur:
                    out.append(cur)
        return out


def build_shell(level, out):
    """Floors, ceilings and walls of one level -> models/interior/<key>_shell.glb + collider list."""
    m = Model(f'{level.key}_shell')
    parts = {}

    def part(mat):
        if mat not in parts:
            fn, tile, rough, metal = MATS[mat]
            parts[mat] = Part(m, f'{level.key}_{mat}', fn(), tile=tile, rough=rough, metal=metal)
        return parts[mat]

    cols = []
    T = 0.3  # wall thickness (centred on the grid line)
    for r in level.rooms:
        part(r.floor).box((r.x0, -0.3, r.z0), (r.x1, 0.0, r.z1))
        part(r.ceil).box((r.x0, r.h, r.z0), (r.x1, r.h + 0.25, r.z1))
        cols.append({'c': [(r.x0 + r.x1) / 2, -0.25, (r.z0 + r.z1) / 2], 'h': [(r.x1 - r.x0) / 2, 0.25, (r.z1 - r.z0) / 2]})
    for w in level.wall_runs():
        mat, op_id, h, _ = w['key']
        p = part(mat)
        y0 = DOOR_H if op_id else 0.0
        if op_id:
            o = next(o for o in level.openings if o['id'] == op_id)
            y0 = o.get('h', DOOR_H)
            if y0 >= h:
                continue
        if w['axis'] == 'z':
            lo, hi = (w['line'] - T / 2, y0, w['a']), (w['line'] + T / 2, h, w['b'])
        else:
            lo, hi = (w['a'], y0, w['line'] - T / 2), (w['b'], h, w['line'] + T / 2)
        p.box(lo, hi)
        c = [(lo[i] + hi[i]) / 2 for i in range(3)]
        hh = [(hi[i] - lo[i]) / 2 for i in range(3)]
        cols.append({'c': c, 'h': hh})
    for p in parts.values():
        p.emit()
    m.save(os.path.join(out, 'models', 'interior', m.name + '.glb'))
    return cols


# ------------------------------------------------------------------------------------------------
# levels

def door(id_, axis, at, a, b, kind='auto', h=DOOR_H, locked=False, **kw):
    return dict(id=id_, axis=axis, at=at, a=a, b=b, kind=kind, h=h, locked=locked, **kw)


def level_op04():
    R = [
        Room('Tunnel', -3, 30, 3, 46, 'conc', 'wall_conc', 'ceil_conc', 4.0, 'cage', (0.6, 0.35)),
        Room('Reception', -9, 18, 9, 30, 'tile', 'wall_office', 'ceil_tile', 3.4, 'fluoro', (0.35, 0.2), sign='sign_visitor'),
        Room('Corridor A', -2, -2, 2, 18, 'vinyl', 'wall_office', 'ceil_tile', 3.0, 'fluoro', (0.45, 0.25)),
        Room('Offices', -20, 2, -2, 16, 'tile', 'wall_office', 'ceil_tile', 3.0, 'fluoro', (0.3, 0.2)),
        Room('Corridor B', -24, -6, 24, -2, 'vinyl', 'wall_lab', 'ceil_tile', 3.0, 'fluoro', (0.5, 0.3)),
        Room('Lab West', -22, -22, -4, -6, 'vinyl', 'wall_lab', 'ceil_tile', 3.4, 'fluoro', (0.35, 0.2), sign='sign_soil'),
        Room('Lab East', 4, -22, 22, -6, 'vinyl', 'wall_lab', 'ceil_tile', 3.4, 'fluoro', (0.35, 0.2)),
        Room('Switch Room', 24, -12, 32, 2, 'conc', 'wall_conc', 'ceil_conc', 3.6, 'cage', (0.5, 0.3), sign='sign_switch'),
        Room('Corridor C', -2, -32, 2, -6, 'vinyl', 'wall_lab', 'ceil_tile', 3.0, 'fluoro', (0.5, 0.3)),
        Room('Lift Lobby', -5, -40, 5, -32, 'grate', 'wall_conc', 'ceil_conc', 3.6, 'cage', (0.55, 0.3), sign='sign_level4'),
    ]
    O = [
        door('tunnel_rec', 'x', 30, -2, 2, 'arch', h=3.4),
        door('rec_corA', 'x', 18, -1, 1, 'auto'),
        door('corA_off', 'z', -2, 8, 10, 'auto'),
        door('corA_corB', 'x', -2, -1, 1, 'arch', h=3.0),
        door('corB_labW', 'x', -6, -14, -12, 'auto', locked=True),
        door('corB_labE', 'x', -6, 12, 14, 'auto', locked=True),
        door('corB_switch', 'z', 24, -5, -3, 'auto'),
        door('corB_corC', 'x', -6, -1, 1, 'auto', locked=True),
        door('corC_lift', 'x', -32, -1, 1, 'arch', h=3.0),
    ]
    return Level('op04', R, O, env='interior')


def level_op05():
    R = [
        Room('Lift Shaft', -3, 30, 3, 38, 'grate', 'wall_conc', 'ceil_conc', 4.0, 'cage', (0.6, 0.35)),
        Room('Antechamber', -8, 14, 8, 30, 'conc', 'wall_bunker', 'ceil_conc', 4.5, 'sodium', (0.6, 0.4), sign='sign_level4'),
        Room('Bunker Hall', -14, -16, 14, 14, 'conc', 'wall_bunker', 'ceil_conc', 5.0, 'sodium', (0.7, 0.45)),
        Room('Dormitory', -30, -8, -14, 8, 'conc', 'wall_bunker', 'ceil_conc', 3.4, 'cage', (0.4, 0.25)),
        Room('Stores', 14, -12, 30, 6, 'conc', 'wall_bunker', 'ceil_conc', 4.0, 'cage', (0.5, 0.3)),
        Room('Stairwell', -3, -28, 3, -16, 'grate', 'wall_conc', 'ceil_conc', 4.5, 'cage', (0.6, 0.4)),
    ]
    O = [
        door('lift_ante', 'x', 30, -2, 2, 'arch', h=3.0),
        door('blast', 'x', 14, -3, 3, 'blast', h=3.2, locked=True),
        door('hall_dorm', 'z', -14, -1, 1, 'auto'),
        door('hall_store', 'z', 14, -3, -1, 'auto'),
        door('hall_stairs', 'x', -16, -1, 1, 'auto', locked=True),
    ]
    return Level('op05', R, O, env='bunker', tone='audio/ambient/bunker.wav')


def level_op06():
    R = [
        Room('Stair Foot', -3, 34, 3, 42, 'grate', 'wall_conc', 'ceil_conc', 4.0, 'cage', (0.6, 0.35)),
        Room('Archive', -30, -10, 30, 34, 'conc', 'wall_conc', 'ceil_conc', 6.0, 'work', (0.8, 0.5), sign='sign_archive'),
        Room('Pump Room', -44, 2, -30, 20, 'conc_wet', 'wall_conc', 'ceil_conc', 5.0, 'cage', (0.75, 0.45), sign='sign_pump'),
        Room('Manager Office', 30, 10, 42, 22, 'tile', 'wall_office', 'ceil_tile', 3.0, 'fluoro', (0.3, 0.2), sign='sign_manager'),
        Room('North Corridor', -3, -30, 3, -10, 'conc', 'wall_conc', 'ceil_conc', 4.0, 'cage', (0.6, 0.35)),
        Room('Chamber Antechamber', -12, -44, 12, -30, 'tile', 'wall_white', 'ceil_tile', 5.0, 'fluoro', (0.5, 0.3), sign='sign_chamber'),
    ]
    O = [
        door('foot_arch', 'x', 34, -2, 2, 'arch', h=3.6),
        door('arch_pump', 'z', -30, 9, 12, 'auto'),
        door('arch_mgr', 'z', 30, 15, 17, 'auto'),
        door('arch_north', 'x', -10, -2, 2, 'arch', h=3.6),
        door('north_ante', 'x', -30, -1, 1, 'auto', locked=True),
    ]
    return Level('op06', R, O, env='basement', tone='audio/ambient/basement.wav')


def level_op07():
    R = [
        Room('Chamber Antechamber', -6, 12, 6, 22, 'tile', 'wall_white', 'ceil_tile', 5.0, 'fluoro', (0.5, 0.3)),
        Room('Trial Chamber', -12, -14, 12, 12, 'vinyl', 'wall_white', 'ceil_tile', 8.0, 'chamber', (0.65, 0.4), sign='sign_chamber'),
    ]
    O = [door('ante_chamber', 'x', 12, -2, 2, 'auto', h=3.0)]
    return Level('op07', R, O, env='chamber')


LEVELS = {'op04': level_op04, 'op05': level_op05, 'op06': level_op06, 'op07': level_op07}
SCENE_PATH = {'op04': 'scenes/op04_interior.vscene', 'op05': 'scenes/op05_bunker.vscene',
              'op06': 'scenes/op06_basement.vscene', 'op07': 'scenes/op07_chamber.vscene'}
MUSIC = {'op04': 'facility', 'op05': 'deep', 'op06': 'deep', 'op07': 'facility'}


# ------------------------------------------------------------------------------------------------
# furnishing and cast

def kit_prop(sc, name, model, x, z, yaw=0.0, y=0.0, parent=None, tags=None, collide=True, scale=1.0):
    root = sc.prop(name, KIT + model + '.glb', (x, y, z), yaw, scale, parent=parent, tags=tags)
    if collide:
        for k, c in enumerate(LAYOUT.get(model, {}).get('colliders', [])):
            sc.add(f'{name} Col {k}', {'Transform': transform(tuple(c['c']), yaw=c['yaw']),
                                        'Collider': collider('box', tuple(2 * v for v in c['h'])),
                                        'RigidBody': body('static')}, root)
    return root


def anchor(model, key, x, z, yaw, y=0.0):
    a = LAYOUT[model]['anchors'][key]
    px, py, pz = a['p']
    r = math.radians(yaw)
    return (x + px * math.cos(r) + pz * math.sin(r), y + py, z - px * math.sin(r) + pz * math.cos(r))


LIGHT = {
    # style: (fitting model, colour, intensity, range, spacing)
    'fluoro': ('light_fluoro', (0.95, 0.97, 1.0), 5.0, 9.0, 6.0),
    'cage': ('light_cage', (1.0, 0.78, 0.5), 5.5, 8.0, 6.0),
    'sodium': ('light_cage', (1.0, 0.66, 0.32), 7.0, 11.0, 8.0),
    'work': ('light_cage', (0.86, 0.93, 1.0), 8.0, 13.0, 10.0),
    'chamber': ('light_fluoro', (1.0, 1.0, 1.0), 9.0, 14.0, 7.0),
}


def light_room(sc, r, lights, group, emergency_ok=True):
    model, col, inten, rng_, sp = LIGHT[r.lights]
    nx = max(1, int(round((r.x1 - r.x0) / sp)))
    nz = max(1, int(round((r.z1 - r.z0) / sp)))
    for i in range(nx):
        for j in range(nz):
            x = r.x0 + (i + 0.5) * (r.x1 - r.x0) / nx
            z = r.z0 + (j + 0.5) * (r.z1 - r.z0) / nz
            n = f'{r.name} Light {i}{j}'
            yaw = 90.0 if (r.z1 - r.z0) > (r.x1 - r.x0) else 0.0
            kit_prop(sc, n + ' Fitting', model, x, z, yaw, y=r.h - 0.02, collide=False)
            # only every other fitting carries a real light in big rooms (mobile light budget)
            if (i + j) % 2 == 0 or nx * nz <= 4:
                lights.append(sc.light(n, (x, r.h - 0.35, z), 'point', col, inten, rng_, shadows=False, parent=group))
    if emergency_ok:
        x, z = r.x0 + 0.5, r.z0 + 0.6
        kit_prop(sc, f'{r.name} Emergency', 'light_emergency', x, z, 90.0, y=min(2.6, r.h - 0.3), collide=False)


def add_room_audio(sc, r):
    sx, sz = r.x1 - r.x0, r.z1 - r.z0
    sc.add(f'{r.name} Reverb', {'Transform': transform((r.c[0], r.h / 2, r.c[1])),
                                'ReverbZone': {'size': [sx, r.h, sz], 'decay': r.reverb[0], 'wet': r.reverb[1],
                                               'lowpass': 0.0, 'fade': 1.5, 'priority': 1}})


def furnish(sc, lv):
    """Room dressing. Every placement is deliberate: furniture sits against walls or in rows with
    walking aisles at least 1.4 m wide (the squad and contractors need to get through)."""
    rr = lv.room
    k = lv.key
    if k == 'op04':
        r = rr['Reception']
        kit_prop(sc, 'Reception Desk', 'reception_desk', -4, 23, 180.0, tags='Reception')
        kit_prop(sc, 'Reception Chair', 'office_chair', -4, 22, 0.0)
        for i, x in enumerate((4.5, 6.0, 7.5)):
            kit_prop(sc, f'Waiting Chair {i}', 'office_chair', x, 28.5, 180.0)
        kit_prop(sc, 'Reception Plant Crates', 'crate_stack', 7, 20, 90.0)
        r = rr['Offices']
        for row, z in enumerate((5.0, 9.0, 13.0)):
            for col, x in enumerate((-17.0, -13.0, -9.0, -5.5)):
                if row == 1 and col == 3:
                    continue  # aisle to the door
                kit_prop(sc, f'Desk {row}{col}', 'desk', x, z, 0.0)
                kit_prop(sc, f'Desk Chair {row}{col}', 'office_chair', x + 0.1, z - 0.8, 10.0 * ((row + col) % 3 - 1))
        kit_prop(sc, 'Office Shelf', 'shelf_unit', -19.2, 9, 90.0)
        for name, x0 in (('Lab West', -22), ('Lab East', 4)):
            for i, z in enumerate((-19.0, -14.5, -10.0)):
                kit_prop(sc, f'{name} Bench {i}', 'lab_bench', x0 + 9, z, 0.0)
            kit_prop(sc, f'{name} Rack', 'server_rack', x0 + 1.0, -20.0, 90.0)
            kit_prop(sc, f'{name} Shelf', 'store_shelf', x0 + 16.5, -21.2, 0.0)
        kit_prop(sc, 'Breaker Wall', 'breaker_wall', 28, -11.7, 180.0, tags='Breakers')
        kit_prop(sc, 'Switch Pipes', 'pipe_run', 28, 1.6, 0.0, y=2.6, collide=False)
        kit_prop(sc, 'Lift Car', 'lift_car', 0, -37, 0.0, collide=False)
    if k == 'op05':
        for i, (x, z) in enumerate(((-7, 6), (7, 6), (-7, -6), (7, -6), (0, 0))):
            kit_prop(sc, f'Column {i}', 'column', x, z, 0.0)
        for i, (x, z, y) in enumerate(((-11, 10, 0), (10, 11, 90), (-11, -12, 0), (9, -13, 0), (4, 3, 30))):
            kit_prop(sc, f'Hall Crates {i}', 'crate_stack', x, z, y)
        for i in range(5):
            kit_prop(sc, f'Bunk {i}', 'bunk_bed', -28.5, -6 + i * 3.0, 90.0)
            kit_prop(sc, f'Bunk East {i}', 'bunk_bed', -20, -6 + i * 3.0, 90.0) if i % 2 == 0 else None
        for i in range(4):
            kit_prop(sc, f'Store Shelf {i}', 'store_shelf', 22, -9 + i * 4.0, 90.0)
        kit_prop(sc, 'Hall Pipes', 'pipe_run', 0, 13.5, 0.0, y=4.2, collide=False)
    if k == 'op06':
        # archive: rows of long shelves north-south with 2.2 m aisles
        n = 0
        for x in np.arange(-26.0, 27.0, 4.0):
            if abs(x) < 3:
                continue  # central avenue
            for z in (24.0, 12.0, 0.0):
                kit_prop(sc, f'Archive Shelf {n}', 'archive_shelf', float(x), z, 90.0)
                n += 1
        kit_prop(sc, 'Pump A', 'pump', -40, 6, 0.0)
        kit_prop(sc, 'Pump B', 'pump', -40, 14, 0.0)
        kit_prop(sc, 'Pump Pipes', 'pipe_run', -37, 19.6, 0.0, y=3.6, collide=False)
        kit_prop(sc, 'Manager Desk', 'desk', 36, 13, 0.0, tags='ManagerDesk')
        kit_prop(sc, 'Manager Chair', 'office_chair', 36, 12.2, 0.0)
        kit_prop(sc, 'Manager Shelf', 'shelf_unit', 41.2, 18, 90.0)
        kit_prop(sc, 'Key Ring', 'key_ring', 35.4, 13.1, 20.0, y=0.765, collide=False)
        for i, x in enumerate((-9, 9)):
            kit_prop(sc, f'Ante Crates {i}', 'crate_stack', x, -34, 90.0 * i)
        # the trial chamber's doors (opened from the chamber side in Operation 07)
        for s_, nm in ((-1, 'L'), (1, 'R')):
            sc.prop(f'Chamber Door {nm}', KIT + 'door_leaf.glb', (s_ * 0.75, 0, -43.8), 0.0, (1.5, 1.25, 1))
    if k == 'op07':
        kit_prop(sc, 'Test Chair', 'test_chair', 0, -4, 0.0, tags='TestChair')
        bx, by, bz = anchor('test_chair', 'behind', 0, -4, 0.0)
        kit_prop(sc, 'V-01', 'v01_dummy', bx, bz + 0.3, 180.0, tags='V01 Scannable')
        kit_prop(sc, 'Chamber Rack A', 'server_rack', -10.5, -10, 90.0)
        kit_prop(sc, 'Chamber Rack B', 'server_rack', -10.5, -8.5, 90.0)
        kit_prop(sc, 'Observation Desk', 'desk', 8, 8, 180.0)
        kit_prop(sc, 'Observation Chair', 'office_chair', 8, 8.8, 180.0)


def add_doors(sc, lv):
    for o in lv.openings:
        if o['kind'] == 'arch':
            continue
        a, b = o['a'], o['b']
        mid = (a + b) / 2
        if o['axis'] == 'x':
            pos, yaw = (mid, 0.0, o['at']), 0.0
        else:
            pos, yaw = (o['at'], 0.0, mid), 90.0
        width = b - a
        kind = o['kind']
        root = sc.add(f'Door {o["id"]}', {'Transform': transform(pos, yaw=yaw),
                                          'Script': script('scripts/door.luau', id=o['id'], width=float(width),
                                                           locked=bool(o['locked']), kind=kind)})
        if kind == 'blast':
            sc.prop('Leaf', KIT + 'blast_door.glb', (0, 0, 0), 0.0, parent=root)
        else:
            for s, nm in ((-1, 'Leaf L'), (1, 'Leaf R')):
                sc.prop(nm, KIT + 'door_leaf.glb', (s * width / 4, 0, 0), 0.0, (width / 2, 1, 1), parent=root)
        # blocker while locked (removed by the door script on unlock)
        sc.add('Blocker', {'Transform': transform((0, o['h'] / 2, 0)),
                           'Collider': collider('box', (width, o['h'], 0.3)), 'RigidBody': body('static')}, root)


def add_signs(sc, lv):
    for r in lv.rooms:
        if not r.sign:
            continue
        # on the wall facing the player's approach (the room's south wall, inside), right of centre
        x = min(r.x1 - 1.0, r.c[0] + 2.0)
        sc.prop(f'{r.name} Sign', KIT + r.sign + '.glb', (x, 2.0, r.z1 - 0.16), 180.0)


ENEMIES = {
    'op04': [('Greyline Lab 1', -16, -12, 0, 'labs', dict(voice='greyline1')),
             ('Greyline Lab 2', -9, -18, 30, 'labs', dict()),
             ('Greyline Lab 3', 10, -12, -20, 'labs', dict(voice='greyline2')),
             ('Greyline Lab 4', 17, -18, 0, 'labs', dict()),
             ('Greyline Lift', 0, -30, 0, 'lift', dict())],
    'op05': [('Greyline Hall 1', -6, -4, 0, 'hall', dict(voice='greyline1', patrol='-6,-4;6,-4;6,8;-6,8')),
             ('Greyline Hall 2', 8, -12, 20, 'hall', dict()),
             ('Greyline Hall 3', -10, -14, 0, 'hall', dict(voice='greyline2')),
             ('Greyline Dorm', -24, 0, 90, 'hall', dict()),
             ('Greyline Stores', 20, -2, -90, 'hall', dict())],
    'op06': [('Greyline Archive 1', 0, 20, 0, 'archive', dict(patrol='0,20;0,-6', voice='greyline1')),
             ('Greyline Archive 2', -16, 6, 90, 'archive', dict(patrol='-16,6;-16,30')),
             ('Greyline Archive 3', 16, 28, -90, 'archive', dict(patrol='16,28;16,2', voice='greyline2')),
             ('Greyline Pump', -36, 10, 90, 'archive', dict()),
             ('Greyline Last 1', -6, -36, 180, 'last', dict()),
             ('Greyline Last 2', 6, -36, 180, 'last', dict(voice='greyline1')),
             ('Greyline Last 3', -9, -41, 180, 'last', dict()),
             ('Greyline Last 4', 9, -41, 180, 'last', dict(voice='greyline2'))],
    'op07': [],
}
START = {'op04': ((0, 0.05, 43), 0.0), 'op05': ((0, 0.05, 34), 0.0), 'op06': ((0, 0.05, 39), 0.0),
         'op07': ((0, 0.05, 19), 0.0)}
MARKS = {
    'op04': {'Mark Visitor Log': ('reception_desk', 'log', -4, 23, 180.0), 'Mark Breakers': ('breaker_wall', 'main', 28, -11.7, 180.0),
             'Mark Lift': (None, (1.2, 1.2, -37.5))},
    'op05': {'Mark Crank': (None, (2.4, 1.2, 15.2)), 'Mark Stairs': (None, (0, 1.0, -22))},
    'op06': {'Mark Keys': (None, (35.4, 0.9, 13.1)), 'Mark Chamber Door': (None, (0, 1.2, -43.3))},
    'op07': {'Mark V01': (None, (0, 0.6, -2.4))},
}


def build_scene(key):
    lv = LEVELS[key]()
    cols = json.loads((HERE / f'{key}_cols.json').read_text())
    sc = Scene({'op04': 'Operation 04 - Quiet Rooms', 'op05': 'Operation 05 - Deep Store',
                'op06': 'Operation 06 - Undercroft', 'op07': 'Operation 07 - The Chair'}[key])
    common.environment(sc, lv.env, fog_density=0.004, fog_start=20, fog_end=200, fog_max_opacity=0.4,
                       ambient_intensity={'interior': 0.42, 'bunker': 0.34, 'basement': 0.32, 'chamber': 0.5}[lv.env],
                       shadow_distance=24)
    shell = sc.prop('Shell', KIT + f'{key}_shell.glb', (0, 0, 0), 0.0, tags='Shell')
    for i, c in enumerate(cols):
        sc.add(f'Shell Col {i}', {'Transform': transform(tuple(c['c'])),
                                   'Collider': collider('box', tuple(2 * v for v in c['h'])),
                                   'RigidBody': body('static'), 'AcousticMaterial': {'material': 'concrete'}}, shell)
    lights = []
    group = sc.add('Lights', {'Transform': transform()})
    for r in lv.rooms:
        light_room(sc, r, lights, group)
        add_room_audio(sc, r)
    furnish(sc, lv)
    add_doors(sc, lv)
    add_signs(sc, lv)
    for name, spec in MARKS[key].items():
        if spec[0]:
            p = anchor(spec[0], spec[1], spec[2], spec[3], spec[4])
        else:
            p = spec[1]
        sc.add(name, {'Transform': transform(p)})
    pos, yaw = START[key]
    rig.add_player(sc, pos, yaw, with_weapons=True, far=200)
    rig.add_hud(sc)
    actors.USE_NAV = True
    actors.add_ensemble(sc)
    for i, who in enumerate(('Anchor', 'Patch', 'Echo', 'Tally')):
        x, z = pos[0] + (i - 1.5) * 1.3, pos[2] + 2.2 + (i % 2) * 0.8
        actors.add_operator(sc, who, (x, 0.05, z), 180.0, surface='concrete')
    for name, x, z, yaw, group, extra in ENEMIES[key]:
        actors.add_enemy(sc, name, (x, 0.05, z), yaw, variant=hash(name) % 2, group=group, surface='concrete', **extra)
    if key == 'op07':
        actors.add_npc(sc, 'Voss', 'models/characters/sops_greyline_a.glb', (2.5, 0.05, -1.5), 200.0, who='voss')
    # music and room tone
    root = sc.add('Music', {'Transform': transform(), 'Script': script('scripts/music.luau')})
    for nm, clip, bus, vol, loop in (('Explore', f'audio/music/{MUSIC[key]}_explore.ogg', 'music', 0.5, True),
                                     ('Tension', f'audio/music/{MUSIC[key]}_tension.ogg', 'music', 0.0, True),
                                     ('Cue', '', 'music', 0.8, False), ('Bed', lv.tone, 'ambient', 0.6, True)):
        sc.add(nm, {'Transform': transform(), 'AudioSource': {
            'clip': clip, 'bus': bus, 'volume': vol, 'pitch': 1.0, 'loop': loop, 'play_on_start': False,
            'stream': bus == 'music', 'spatial': False, 'priority': 250, 'occlusion': False}}, root)
    sc.add('Mission', {'Transform': transform(), 'Script': script('scripts/missions/facility.luau', chapter=key)})
    sc.save(SCENE_PATH[key])
    print(key, SCENE_PATH[key], len(sc.entities), 'entities', len(lights), 'lights', len(cols), 'colliders')


SCENES_ONLY = False


def main():
    global SCENES_ONLY
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenes', action='store_true')
    a = ap.parse_args()
    SCENES_ONLY = a.scenes
    lay_path = HERE / 'interior_layout.json'
    if a.scenes and lay_path.exists():
        LAYOUT.update(json.loads(lay_path.read_text()))
    else:
        build_kit(str(ASSETS))
        lay_path.write_text(json.dumps(LAYOUT, indent=1))
        for key, fn in LEVELS.items():
            (HERE / f'{key}_cols.json').write_text(json.dumps(build_shell(fn(), str(ASSETS))))
    for key in LEVELS:
        build_scene(key)


if __name__ == '__main__':
    main()
