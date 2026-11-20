#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generates original HUD textures (deterministic).

    python3 tools/ui/build_ui_textures.py --out game/assets

textures/ui/scope_mask.png  LR-4 Heron scope: opaque housing outside a circular lens, soft lens
                             edge, faint lens tint falloff and a thin stadia reticle (fictional design).
textures/ui/hit_marker.png  four diagonal strokes with a centre gap (tinted per hit zone by hud.luau).
textures/ui/dmg_dir_<k>.png directional damage wedge, k = 0..7 clockwise from straight ahead
                             (pre-rotated: VICTUS UiRect has no rotation).
textures/ui/wp_diamond.png  waypoint diamond for the compass strip.
textures/ui/plate_l.png     soft horizontal plate (opaque left, fades right) behind HUD blocks;
textures/ui/plate_r.png     its mirror.
textures/ui/vignette.png    radial edge vignette (white, tinted red for damage / low health).
"""
import argparse
import os

import numpy as np
from PIL import Image


def scope_mask(n=1024):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    dx, dy = (x - c) / c, (y - c) / c
    r = np.sqrt(dx * dx + dy * dy)
    rgb = np.zeros((n, n, 3), np.float32)
    a = np.zeros((n, n), np.float32)
    lens = 0.93
    # housing: opaque outside the lens with a soft 2% edge
    edge = np.clip((r - lens) / 0.025, 0, 1)
    a = np.maximum(a, edge)
    # inner falloff: lens darkens toward its rim (vignetting), alpha only
    a = np.maximum(a, np.clip((r - 0.62) / (lens - 0.62), 0, 1) ** 2.2 * 0.55)
    rgb[:] = 0.01
    # reticle: thin dark lines with a centre gap, thicker outer posts, small centre dot
    px = 2.0 / n * 1.6
    gap = 0.045
    def line(mask, w):
        return mask & (r < lens)
    horiz = (np.abs(dy) < px) & (np.abs(dx) > gap)
    vert = (np.abs(dx) < px) & (np.abs(dy) > gap) & (dy > 0)   # lower post only
    vert_top = (np.abs(dx) < px) & (dy < -gap) & (dy > -0.35)
    posts = ((np.abs(dy) < px * 3.2) & (np.abs(dx) > 0.55)) | ((np.abs(dx) < px * 3.2) & (dy > 0.55))
    dot = r < px * 1.8
    ticks = np.zeros_like(horiz)
    for k in (0.12, 0.22, 0.32):
        ticks |= (np.abs(dy - k) < px * 0.9) & (np.abs(dx) < 0.03)
        ticks |= (np.abs(dx - k) < px * 0.9) & (np.abs(dy) < 0.02) | (np.abs(dx + k) < px * 0.9) & (np.abs(dy) < 0.02)
    ret = (horiz | vert | vert_top | posts | dot | ticks) & (r < lens)
    a = np.where(ret, np.maximum(a, 0.92), a)
    img = np.dstack([rgb, a[..., None]])
    return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")


def _rgba(rgb, a):
    img = np.dstack([rgb, a[..., None]])
    return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")


def _seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy), 0, 1)
    dx, dy = px - (ax + t * vx), py - (ay + t * vy)
    return np.sqrt(dx * dx + dy * dy)


def hit_marker(n=128):
    """Four diagonal strokes from r=0.32 to r=0.86 (of the half size), anti-aliased."""
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    px, py = (x - c) / c, (y - c) / c
    d = np.full((n, n), 9.0, np.float32)
    for sx in (-1, 1):
        for sy in (-1, 1):
            k = 0.7071
            d = np.minimum(d, _seg_dist(px, py, sx * 0.32 * k, sy * 0.32 * k, sx * 0.86 * k, sy * 0.86 * k))
    w = 0.075
    a = np.clip((w - d) / (2.0 / n) + 0.5, 0, 1)
    # thin dark outline for contrast on bright backgrounds
    ao = np.clip((w + 0.05 - d) / (2.0 / n) + 0.5, 0, 1) * 0.45
    rgb = np.repeat(a[..., None], 3, 2)
    return _rgba(rgb, np.maximum(a, ao))


def dmg_dir(k, n=256):
    """Crescent wedge on the ring, centred on bearing k*45 deg clockwise from up."""
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    px, py = (x - c) / c, (y - c) / c
    r = np.sqrt(px * px + py * py)
    ang = np.degrees(np.arctan2(px, -py))            # 0 = up, clockwise positive
    da = np.abs((ang - k * 45 + 540) % 360 - 180)
    radial = np.clip(1 - np.abs(r - 0.86) / 0.11, 0, 1) ** 1.4
    angular = np.clip(1 - da / 24, 0, 1) ** 1.2
    a = radial * angular
    rgb = np.ones((n, n, 3), np.float32)
    return _rgba(rgb, a)


def wp_diamond(n=64):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    d = (np.abs(x - c) + np.abs(y - c)) / c
    a = np.clip((0.92 - d) * n / 4, 0, 1)
    inner = np.clip((0.55 - d) * n / 4, 0, 1)
    rgb = np.repeat((0.15 + 0.85 * (a - inner * 0.35))[..., None], 3, 2)
    return _rgba(rgb, a)


def plate(n_w=512, n_h=64, mirror=False):
    y, x = np.mgrid[0:n_h, 0:n_w].astype(np.float32)
    u = x / (n_w - 1)
    if mirror:
        u = 1 - u
    a = np.clip(1 - u, 0, 1) ** 1.6 * 0.9
    v = np.abs(y / (n_h - 1) - 0.5) * 2
    a *= np.clip((1 - v) / 0.25, 0, 1)
    rgb = np.zeros((n_h, n_w, 3), np.float32) + 0.02
    return _rgba(rgb, a)


def vignette(n=512):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    px, py = (x - c) / c, (y - c) / c
    r = np.sqrt(px * px * 1.0 + py * py * 1.0)
    a = np.clip((r - 0.55) / 0.75, 0, 1) ** 1.8
    rgb = np.ones((n, n, 3), np.float32)
    return _rgba(rgb, a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = os.path.join(a.out, "textures", "ui")
    os.makedirs(d, exist_ok=True)
    out = {"scope_mask.png": scope_mask(), "hit_marker.png": hit_marker(), "wp_diamond.png": wp_diamond(),
           "plate_l.png": plate(), "plate_r.png": plate(mirror=True), "vignette.png": vignette()}
    for k in range(8):
        out[f"dmg_dir_{k}.png"] = dmg_dir(k)
    for name, img in out.items():
        img.save(os.path.join(d, name), optimize=True)
        print("wrote", os.path.join(d, name))


if __name__ == "__main__":
    main()
