#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generates original HUD textures (deterministic).

    python3 tools/ui/build_ui_textures.py --out game/assets

textures/ui/scope_mask.png  LR-4 Heron scope: opaque housing outside a circular lens, soft lens
                             edge, faint lens tint falloff and a thin stadia reticle (fictional design).
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = os.path.join(a.out, "textures", "ui")
    os.makedirs(d, exist_ok=True)
    scope_mask().save(os.path.join(d, "scope_mask.png"), optimize=True)
    print("wrote", os.path.join(d, "scope_mask.png"))


if __name__ == "__main__":
    main()
