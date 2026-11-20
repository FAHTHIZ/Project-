# SPDX-License-Identifier: Apache-2.0
"""Front-end gradients (original, generated): left and bottom shades for the main menu.

    python3 tools/ui/build_menu_art.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "game", "assets", "textures", "ui", "menu")


def ramp(n, a0, a1, start):
    out = []
    for i in range(n):
        t = max(0.0, (i / (n - 1) - start) / (1 - start))
        s = t * t * (3 - 2 * t)
        out.append(int(255 * (a0 + (a1 - a0) * s)))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    a = ramp(512, 0.9, 0.0, 0.18)
    im = Image.new("RGBA", (512, 4))
    for x in range(512):
        for y in range(4):
            im.putpixel((x, y), (4, 6, 8, a[x]))
    im.save(os.path.join(OUT, "shade_left.png"))
    a = ramp(256, 0.0, 0.85, 0.3)
    im = Image.new("RGBA", (4, 256))
    for y in range(256):
        for x in range(4):
            im.putpixel((x, y), (2, 3, 4, a[y]))
    im.save(os.path.join(OUT, "shade_bottom.png"))
    print("menu art ->", OUT)


if __name__ == "__main__":
    main()
