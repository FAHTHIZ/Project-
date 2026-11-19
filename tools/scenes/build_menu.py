# SPDX-License-Identifier: Apache-2.0
"""Main menu and credits scenes."""
from __future__ import annotations

import random

from vscene import Scene, transform, quat_euler, script, ui_rect, ui_panel, ui_text, ui_button, GROUND_MATERIAL
from common import environment, sun
import rig
from rig import ui

CHAPTERS = [("prologue", "Prologue: Lantern"), ("op01", "Operation 01: Greenline"), ("op02", "Operation 02: Fenceline"),
            ("op03", "Operation 03: Service Yard"), ("op04", "Operation 04: Quiet Rooms"),
            ("op05", "Operation 05: Deep Store"), ("op06", "Operation 06: Undercroft"),
            ("op07", "Operation 07: The Chair")]

CREDITS = """SPECIAL OPS

A VICTUS field demonstration

Created by FAHTHIZ

Engine
VICTUS 0.2.0 (Apache-2.0)

Design, code, characters, environments and sound
Generated in this repository from source scripts
(see docs/ASSET_PROVENANCE.md)

Voices
Kokoro-82M text-to-speech by hexgrad (Apache-2.0)
synthesised offline with kokoro-onnx (MIT)

Squad LANTERN
Rook  -  the player
Mara Ostrova  -  "Anchor"
Theo Okafor  -  "Patch"
Ines Calder  -  "Echo"
Dmitri Halvorsen  -  "Brick"

Special thanks
Vanguard V-01, for sitting very still

Thank you for playing
"""


def backdrop(sc: Scene, seed=3):
    environment(sc, "forest", fog_density=0.03, fog_color=[0.55, 0.62, 0.62, 1])
    sun(sc, pitch=-30, yaw=60, intensity=2.6)
    sc.box("Menu Ground", (0, -0.1, 0), (120, 0.2, 120), (0.22, 0.26, 0.16), material=None, collide=False)
    rnd = random.Random(seed)
    trees = ["models/env/tree_broadleaf_a.glb", "models/env/tree_broadleaf_b.glb", "models/env/tree_broadleaf_c.glb",
             "models/env/tree_conifer_a.glb", "models/env/tree_conifer_b.glb"]
    for i in range(46):
        x = rnd.uniform(-30, 30)
        z = rnd.uniform(-45, 2)
        if abs(x) < 2.2 and z > -30:
            continue
        sc.prop(f"Menu Tree {i}", rnd.choice(trees), (x, 0, z), rnd.uniform(0, 360), rnd.uniform(0.85, 1.25))
    for i in range(60):
        x = rnd.uniform(-14, 14)
        z = rnd.uniform(-20, 4)
        if abs(x) < 1.2:
            continue
        sc.prop(f"Menu Fern {i}", rnd.choice(["models/env/fern_a.glb", "models/env/fern_b.glb", "models/env/shrub_a.glb"]),
                (x, 0, z), rnd.uniform(0, 360), rnd.uniform(0.8, 1.3), shadows=False)
    sc.add("Menu Camera", {"Transform": transform((0, 1.7, 6), quat_euler(-4, 12, 0)),
                           "Camera": {"projection": "perspective", "fov_y": 58, "ortho_height": 10, "near": 0.1,
                                      "far": 400, "primary": True}})


def build_menu():
    sc = Scene("Main Menu")
    backdrop(sc)
    canvas = sc.add("Menu UI", {
        "UiCanvas": {"visible": True, "scale_mode": "scale_with_screen", "reference_size": [1280, 720], "match": 1,
                     "sort_order": 0, "keyboard_navigation": True, "blocks_input": False},
        "Script": script("scripts/menu.luau"),
    })
    ui(sc, "Menu Shade", canvas, ui_rect((0, 0), (0, 0), (560, 0), (0, 0), anchor_max=(0, 1)),
       panel=ui_panel((0.01, 0.02, 0.02, 0.62), 0, (0, 0, 0, 0), 0))
    ui(sc, "Menu Title", canvas, ui_rect((0, 1), (64, -70), (600, 80), (0, 1)),
       text=ui_text("SPECIAL OPS", 64, (1, 1, 1, 1), "left", "middle", True))
    ui(sc, "Menu Tag", canvas, ui_rect((0, 1), (68, -142), (600, 30), (0, 1)),
       text=ui_text("A VICTUS field demonstration", 20, (0.7, 0.88, 0.95, 1), "left", "middle"))
    main = ui(sc, "Menu Main", canvas, ui_rect((0, 1), (64, -210), (420, 420), (0, 1)))
    for i, (label, action) in enumerate([("Continue", "continue"), ("New campaign", "new"), ("Operations", "ops"),
                                          ("Settings", "settings"), ("Credits", "credits")]):
        name = "Menu Continue" if action == "continue" else f"Menu {label}"
        rig.button(sc, name, main, ui_rect((0, 1), (0, -i * 68), (420, 56), (0, 1)), action, label, 23)
    ops = ui(sc, "Menu Ops", canvas, ui_rect((0, 1), (64, -200), (480, 520), (0, 1), visible=False))
    for i, (cid, title) in enumerate(CHAPTERS):
        rig.button(sc, f"Op {cid}", ops, ui_rect((0, 1), (0, -i * 56), (480, 48), (0, 1)), f"op:{cid}", title, 20)
    ui(sc, "Ops Back", ops, ui_rect((0, 1), (0, -len(CHAPTERS) * 56 - 10), (200, 48), (0, 1)),
       panel=ui_panel((0.12, 0.14, 0.16, 0.9), 8, (1, 1, 1, 0.16), 1), button=ui_button("cancel"),
       text=ui_text("Back", 20, (1, 1, 1, 1), "center", "middle", True))
    conf = ui(sc, "Menu Confirm", canvas, ui_rect((0, 1), (64, -220), (460, 200), (0, 1), visible=False),
              panel=ui_panel((0.05, 0.06, 0.07, 0.92), 10, (1, 1, 1, 0.18), 1))
    ui(sc, "Confirm Text", conf, ui_rect((0.5, 1), (0, -20), (420, 80), (0.5, 1)),
       text=ui_text("Start a new campaign? Current progress will be replaced.", 21, (1, 1, 1, 1), "center",
                    "middle", False, True))
    ui(sc, "Confirm Yes", conf, ui_rect((0, 0), (20, 20), (200, 52), (0, 0)),
       panel=ui_panel((0.3, 0.12, 0.08, 0.9), 8, (1, 1, 1, 0.2), 1), button=ui_button("confirm_new"),
       text=ui_text("Start new", 21, (1, 1, 1, 1), "center", "middle", True))
    ui(sc, "Confirm No", conf, ui_rect((1, 0), (-20, 20), (200, 52), (1, 0)),
       panel=ui_panel((0.12, 0.14, 0.16, 0.9), 8, (1, 1, 1, 0.2), 1), button=ui_button("cancel"),
       text=ui_text("Cancel", 21, (1, 1, 1, 1), "center", "middle", True))
    ui(sc, "Menu Status", canvas, ui_rect((1, 0), (-24, 18), (600, 28), (1, 0)),
       text=ui_text("VICTUS 0.2.0  |  Landscape  |  Touch, gamepad and keyboard", 15, (1, 1, 1, 0.6), "right"))
    rig.add_pause_menu(sc)
    return sc.save("scenes/menu.vscene")


def build_credits():
    sc = Scene("Credits")
    backdrop(sc, seed=9)
    canvas = sc.add("Credits UI", {
        "UiCanvas": {"visible": True, "scale_mode": "scale_with_screen", "reference_size": [1280, 720], "match": 1,
                     "sort_order": 0, "keyboard_navigation": False, "blocks_input": False},
        "Script": script("scripts/credits.luau"),
    })
    ui(sc, "Credits Shade", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1)),
       panel=ui_panel((0, 0, 0, 0.55), 0, (0, 0, 0, 0), 0))
    ui(sc, "Credits Roll", canvas, ui_rect((0.5, 0), (0, 0), (900, 1500), (0.5, 1)),
       text=ui_text(CREDITS, 26, (1, 1, 1, 1), "center", "top", False, True))
    ui(sc, "Credits Hint", canvas, ui_rect((1, 0), (-24, 18), (420, 30), (1, 0)),
       text=ui_text("Press any button to return", 17, (1, 1, 1, 0.7), "right"))
    ui(sc, "Credits Button", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1)),
       panel=ui_panel((0, 0, 0, 0), 0, (0, 0, 0, 0), 0), button=ui_button("back", (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)))
    return sc.save("scenes/credits.vscene")


if __name__ == "__main__":
    build_menu()
    build_credits()
