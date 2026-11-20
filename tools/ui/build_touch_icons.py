# SPDX-License-Identifier: Apache-2.0
"""Touch-control icon set (original line art, drawn here with Pillow).

    python3 tools/ui/build_touch_icons.py

Writes game/assets/textures/ui/touch/<name>.png: white strokes on transparent, 192 px, drawn at
4x and downsampled so the edges stay clean at every phone density. Also the floating-stick ring
and knob. Icons replace the text-in-a-circle prototype buttons (see docs/BUILD_AND_TEST_LOG.md).
"""
from __future__ import annotations

import math
import os

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "game", "assets", "textures", "ui", "touch")
S = 192
K = 4
N = S * K
W = int(N * 0.055)  # stroke width
WHITE = (255, 255, 255, 255)


def canvas():
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def P(x, y):
    """Normalised (-1..1, y down) to pixels."""
    return (N / 2 + x * N / 2, N / 2 + y * N / 2)


def line(d, pts, w=W):
    pts = [P(*p) for p in pts]
    d.line(pts, fill=WHITE, width=w, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse([p[0] - w / 2, p[1] - w / 2, p[0] + w / 2, p[1] + w / 2], fill=WHITE)


def circle(d, cx, cy, r, w=W, fill=False):
    a, b = P(cx - r, cy - r), P(cx + r, cy + r)
    if fill:
        d.ellipse([a, b], fill=WHITE)
    else:
        d.ellipse([a, b], outline=WHITE, width=w)


def arc(d, cx, cy, r, a0, a1, w=W):
    a, b = P(cx - r, cy - r), P(cx + r, cy + r)
    d.arc([a, b], a0, a1, fill=WHITE, width=w)


def poly(d, pts):
    d.polygon([P(*p) for p in pts], fill=WHITE)


def save(im, name, soft=True):
    if soft:
        # faint dark halo so the white line art reads over bright sky and fog too
        a = im.split()[3].filter(ImageFilter.GaussianBlur(K * 3))
        halo = Image.new("RGBA", im.size, (0, 0, 0, 0))
        halo.putalpha(a.point(lambda v: int(v * 0.55)))
        im = Image.alpha_composite(halo, im)
    im = im.resize((S, S), Image.LANCZOS)
    im.save(os.path.join(OUT, name + ".png"))


def icon_fire():
    im, d = canvas()
    circle(d, 0, 0, 0.42)
    for a in range(4):
        c, s = math.cos(a * math.pi / 2), math.sin(a * math.pi / 2)
        line(d, [(c * 0.24, s * 0.24), (c * 0.62, s * 0.62)])
    circle(d, 0, 0, 0.07, fill=True)
    save(im, "fire")


def icon_aim():
    # rifle scope, side view: objective bell, tube with turret, ocular bell
    im, d = canvas()
    poly(d, [(-0.72, -0.2), (-0.5, -0.12), (-0.5, 0.12), (-0.72, 0.2)])
    poly(d, [(0.72, -0.24), (0.42, -0.12), (0.42, 0.12), (0.72, 0.24)])
    a, b = P(-0.52, -0.1), P(0.44, 0.1)
    d.rectangle([a, b], fill=WHITE)
    a, b = P(-0.1, -0.3), P(0.1, -0.08)
    d.rectangle([a, b], fill=WHITE)
    line(d, [(-0.3, 0.1), (-0.3, 0.38)]); line(d, [(0.22, 0.1), (0.22, 0.38)])
    line(d, [(-0.42, 0.38), (0.34, 0.38)])
    save(im, "aim")


def icon_reload():
    # magazine inside a circular arrow
    im, d = canvas()
    arc(d, 0, 0, 0.6, 210, 500)
    poly(d, [(-0.66, -0.06), (-0.36, -0.08), (-0.56, -0.36)])
    poly(d, [(-0.18, -0.3), (0.18, -0.3), (0.24, 0.32), (-0.12, 0.32)])
    save(im, "reload")


def icon_switch():
    im, d = canvas()
    line(d, [(-0.55, -0.2), (0.5, -0.2)])
    line(d, [(0.28, -0.42), (0.55, -0.2), (0.28, 0.02)])
    line(d, [(0.55, 0.24), (-0.5, 0.24)])
    line(d, [(-0.28, 0.02), (-0.55, 0.24), (-0.28, 0.46)])
    save(im, "switch")


def icon_jump():
    im, d = canvas()
    line(d, [(-0.42, 0.0), (0, -0.4), (0.42, 0.0)])
    line(d, [(-0.42, 0.34), (0, -0.06), (0.42, 0.34)])
    save(im, "jump")


def icon_crouch():
    # kneeling figure: head, back, thigh, shin
    im, d = canvas()
    circle(d, 0.06, -0.5, 0.13, fill=True)
    line(d, [(0.0, -0.3), (-0.12, 0.08), (0.3, 0.12), (0.3, 0.52)], w=int(W * 1.25))
    line(d, [(-0.12, 0.08), (-0.38, 0.5), (-0.6, 0.5)], w=int(W * 1.25))
    line(d, [(0.0, -0.2), (0.36, -0.08)], w=int(W * 1.1))
    save(im, "crouch")


def icon_use():
    # open hand reaching (index finger + palm block)
    im, d = canvas()
    a, b = P(-0.42, -0.42), P(0.42, 0.42)
    d.rounded_rectangle([a, b], radius=N * 0.08, outline=WHITE, width=W)
    circle(d, 0, 0, 0.12, fill=True)
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        line(d, [(sx * 0.62, sy * 0.3), (sx * 0.62, sy * 0.62), (sx * 0.3, sy * 0.62)])
    save(im, "use")


def icon_tool():
    # scanner: emitter dot with three radiating arcs
    im, d = canvas()
    circle(d, -0.42, 0.3, 0.1, fill=True)
    for r in (0.34, 0.6, 0.86):
        arc(d, -0.42, 0.3, r, 275, 355)
    save(im, "tool")


def icon_kit():
    # thrown utility: canister with lever and pin ring
    im, d = canvas()
    a, b = P(-0.26, -0.18), P(0.26, 0.6)
    d.rounded_rectangle([a, b], radius=N * 0.07, outline=WHITE, width=W)
    line(d, [(-0.14, -0.18), (-0.14, -0.36), (0.3, -0.36), (0.42, -0.04)])
    circle(d, -0.36, -0.5, 0.13)
    line(d, [(-0.26, 0.2), (0.26, 0.2)])
    save(im, "kit")


def icon_pause():
    im, d = canvas()
    for x in (-0.2, 0.2):
        a, b = P(x - 0.08, -0.36), P(x + 0.08, 0.36)
        d.rounded_rectangle([a, b], radius=N * 0.03, fill=WHITE)
    save(im, "pause")


def icon_obj():
    im, d = canvas()
    for i, y in enumerate((-0.36, 0.0, 0.36)):
        circle(d, -0.42, y, 0.08, fill=True)
        line(d, [(-0.16, y), (0.52 - 0.12 * i, y)])
    save(im, "obj")


def icon_light():
    # weapon light: body plus beam rays
    im, d = canvas()
    a, b = P(-0.62, -0.16), P(-0.1, 0.16)
    d.rounded_rectangle([a, b], radius=N * 0.03, fill=WHITE)
    poly(d, [(-0.1, -0.24), (0.04, -0.24), (0.04, 0.24), (-0.1, 0.24)])
    for ang in (-28, 0, 28):
        r = math.radians(ang)
        line(d, [(0.2 * math.cos(r) + 0.04, 0.2 * math.sin(r)), (0.58 * math.cos(r) + 0.04, 0.58 * math.sin(r))])
    save(im, "light")


def stick_ring():
    # floating stick base: thin ring, faint fill, four direction ticks
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([P(-0.98, -0.98), P(0.98, 0.98)], fill=(8, 10, 12, 70))
    d.ellipse([P(-0.95, -0.95), P(0.95, 0.95)], outline=(255, 255, 255, 120), width=int(K * 2.2))
    d.ellipse([P(-0.62, -0.62), P(0.62, 0.62)], outline=(255, 255, 255, 34), width=int(K * 1.5))
    for a in range(4):
        c, s = math.cos(a * math.pi / 2), math.sin(a * math.pi / 2)
        tip = (c * 0.86, s * 0.86)
        side = (-s * 0.07, c * 0.07)
        base = (c * 0.76, s * 0.76)
        d.polygon([P(*tip), P(base[0] + side[0], base[1] + side[1]), P(base[0] - side[0], base[1] - side[1])],
                  fill=(255, 255, 255, 150))
    save(im, "stick_ring", soft=False)


def stick_knob():
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # soft radial fill, brighter rim
    for i in range(40):
        r = 0.96 * (1 - i / 40)
        v = int(60 + 120 * (i / 40) ** 0.6)
        d.ellipse([P(-r, -r), P(r, r)], fill=(v, v + 4, v + 8, 150))
    d.ellipse([P(-0.95, -0.95), P(0.95, 0.95)], outline=(255, 255, 255, 200), width=int(K * 2.5))
    save(im, "stick_knob", soft=False)


def disc(name, rim, fill_a, rim_w=2.0):
    """Button base: dark glass disc with a soft inner gradient and a thin rim."""
    im = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(48):
        r = 0.97 * (1 - i / 48 * 0.55)
        t = i / 48
        a = int(fill_a * (0.75 + 0.25 * t))
        d.ellipse([P(-r, -r), P(r, r)], fill=(int(10 + 14 * t), int(12 + 15 * t), int(14 + 16 * t), a))
    d.ellipse([P(-0.95, -0.95), P(0.95, 0.95)], outline=rim, width=int(K * rim_w))
    save(im, name, soft=False)


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in (icon_fire, icon_aim, icon_reload, icon_switch, icon_jump, icon_crouch, icon_use, icon_tool, icon_kit,
              icon_pause, icon_obj, icon_light, stick_ring, stick_knob):
        f()
    disc("disc", (255, 255, 255, 110), 120)
    disc("disc_fire", (232, 178, 92, 210), 135, rim_w=3.0)
    print("icons ->", OUT, len(os.listdir(OUT)))


if __name__ == "__main__":
    main()
