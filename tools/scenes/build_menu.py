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
Anchor  -  team lead
Patch  -  medic
Echo  -  scout
Tally  -  communications
Brick  -  breacher

Special thanks
Vanguard V-01, for standing very still

Thank you for playing
"""


def backdrop(sc: Scene, seed=3):
    # The campaign's own night (common.py "night_storm"): rain, wet ground, volumetric ground fog,
    # a weak moon behind cloud, one sodium lamp pooling light on the trail, a perimeter searchlight
    # sweeping through the fog far behind the trees, and the storm's lightning (scripts/world/storm.luau).
    environment(sc, "night_storm", precipitation_radius=12.0)
    sc.add("Moon", {"Transform": transform((0, 30, 0), quat_euler(-55, 125, 0)), "Light": {
        "type": "directional", "color": [0.56, 0.66, 0.88, 1], "intensity": 0.42, "range": 10, "shadows": True}})
    sc.prop("Menu Lamp Post", "models/structures/light_pole.glb", (2.6, 0, -7.0), 200.0)
    sc.add("Menu Lamp", {"Transform": transform((2.0, 6.2, -6.6), quat_euler(-82, 200, 0)), "Light": {
        "type": "spot", "color": [1.0, 0.66, 0.32, 1], "intensity": 55.0, "range": 24.0, "shadows": True,
        "inner_angle": 38.0, "outer_angle": 62.0}})
    sc.add("Menu Searchlight", {"Transform": transform((-14, 9, -60), quat_euler(-8, 160, 0)),
                                "Light": {"type": "spot", "color": [0.86, 0.92, 1.0, 1], "intensity": 140.0,
                                          "range": 90.0, "shadows": False, "inner_angle": 4.0, "outer_angle": 9.0},
                                "Script": script("scripts/world/searchlight.luau", arc=40.0, period=16.0, phase=0.2,
                                                 pitch=-8.0, yaw=160.0)})
    storm = sc.add("Storm", {"Transform": transform(), "Script": script(
        "scripts/world/storm.luau", min_gap=14.0, max_gap=34.0, first=10.6, volume=0.7)})
    sc.add("Lightning", {"Transform": transform((0, 50, 0), quat_euler(-62, 150, 0)), "Light": {
        "type": "directional", "color": [0.78, 0.84, 1.0, 1], "intensity": 0.0, "range": 10, "shadows": False}}, storm)
    sc.box("Menu Ground", (0, -0.1, 0), (120, 0.2, 120), (0.10, 0.11, 0.08), material=None, collide=True)
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


FONT_B = "fonts/BarlowCondensed-Bold.ttf"
FONT_S = "fonts/BarlowCondensed-SemiBold.ttf"
FONT_M = "fonts/BarlowCondensed-Medium.ttf"
AMBER = (0.93, 0.68, 0.34, 1)


def ft(text, size, color=(1, 1, 1, 1), align="left", valign="middle", font=FONT_S, wrap=False, shadow=0.55):
    t = ui_text(text, size, color, align, valign, False, wrap)
    t["font"] = font
    t["shadow_color"] = [0, 0, 0, shadow]
    return t


def menu_row(sc, name, parent, i, label, action, y0=0, h=50, num=True, width=430):
    """Tactical list row: number tag, condensed caps label, hairline divider; transparent until hovered."""
    b = ui(sc, name, parent, ui_rect((0, 1), (0, y0 - i * h), (width, h - 4), (0, 1)),
           panel=ui_panel((0, 0, 0, 0), 2, (0, 0, 0, 0), 0),
           button=ui_button(action, (0, 0, 0, 0), (0.93, 0.68, 0.34, 0.2), (0.93, 0.68, 0.34, 0.34)))
    if num:
        ui(sc, name + " Num", b, ui_rect((0, 0.5), (14, 0), (40, 30), (0, 0.5)),
           text=ft(f"{i + 1:02d}", 17, AMBER, font=FONT_M))
    ui(sc, name + " Label", b, ui_rect((0, 0), (54 if num else 18, 0), (-70, 0), (0, 0), anchor_max=(1, 1)),
       text=ft(label.upper(), 29))
    ui(sc, name + " Rule", b, ui_rect((0, 0), (0, -2), (0, 1), (0, 0), anchor_max=(1, 0)),
       panel=ui_panel((1, 1, 1, 0.09), 0, (0, 0, 0, 0), 0))
    return b


def squad_key_art(sc: Scene):
    """Three of LANTERN on the trail under the sodium lamp, rail lights cutting the rain (hold
    order, weapons safe: they stand and idle, nobody to engage)."""
    import actors
    for who, pos, yaw in (("Anchor", (1.1, 0, -3.2), 196.0), ("Echo", (2.5, 0, -4.4), 172.0),
                          ("Brick", (-0.1, 0, -5.2), 204.0)):
        actors.add_operator(sc, who, pos, yaw, order="hold", engage=False)


def build_menu(test_plan=None):
    sc = Scene("Main Menu")
    backdrop(sc)
    squad_key_art(sc)
    canvas = sc.add("Menu UI", {
        "UiCanvas": {"visible": True, "scale_mode": "scale_with_screen", "reference_size": [1280, 720], "match": 1,
                     "sort_order": 0, "keyboard_navigation": True, "blocks_input": False},
        "Script": script("scripts/menu.luau"),
    })
    # soft cinematic shades instead of a hard panel: left for the list, bottom for the status line
    ui(sc, "Menu Shade", canvas, ui_rect((0, 0), (0, 0), (760, 0), (0, 0), anchor_max=(0, 1)),
       image=rig._img("textures/ui/menu/shade_left.png", (1, 1, 1, 1)))
    ui(sc, "Menu Shade Bottom", canvas, ui_rect((0, 0), (0, 0), (0, 220), (0, 0), anchor_max=(1, 0)),
       image=rig._img("textures/ui/menu/shade_bottom.png", (1, 1, 1, 1)))
    head = ui(sc, "Menu Head", canvas, ui_rect((0, 1), (72, -56), (640, 190), (0, 1)))
    ui(sc, "Menu Kicker", head, ui_rect((0, 1), (2, 0), (600, 26), (0, 1)),
       text=ft("HALYARD TEAM  //  SQUAD LANTERN", 18, AMBER, font=FONT_M))
    ui(sc, "Menu Title", head, ui_rect((0, 1), (0, -18), (640, 110), (0, 1)),
       text=ft("SPECIAL OPS", 104, font=FONT_B, shadow=0.7))
    ui(sc, "Menu Title Rule", head, ui_rect((0, 1), (4, -134), (64, 3), (0, 1)),
       panel=ui_panel(AMBER, 0, (0, 0, 0, 0), 0))
    ui(sc, "Menu Tag", head, ui_rect((0, 1), (84, -124), (560, 24), (0, 1)),
       text=ft("KESTREL VALLEY  \u00b7  DAWN DEADLINE  \u00b7  NON-LETHAL", 18, (0.78, 0.84, 0.88, 0.9), font=FONT_M))
    main = ui(sc, "Menu Main", canvas, ui_rect((0, 1), (58, -282), (440, 300), (0, 1)))
    for i, (label, action) in enumerate([("Continue", "continue"), ("New campaign", "new"), ("Operations", "ops"),
                                          ("Settings", "settings"), ("Credits", "credits")]):
        name = "Menu Continue" if action == "continue" else f"Menu {label}"
        menu_row(sc, name, main, i, label, action)
    ops = ui(sc, "Menu Ops", canvas, ui_rect((0, 1), (58, -250), (520, 470), (0, 1), visible=False))
    ui(sc, "Ops Heading", ops, ui_rect((0, 1), (14, 34), (400, 30), (0, 1)),
       text=ft("SELECT OPERATION", 20, AMBER, font=FONT_M))
    for i, (cid, title) in enumerate(CHAPTERS):
        menu_row(sc, f"Op {cid}", ops, i, title, f"op:{cid}", h=48, width=520)
    menu_row(sc, "Ops Back", ops, len(CHAPTERS), "Back", "cancel", y0=-12, h=48, num=False, width=200)
    conf = ui(sc, "Menu Confirm", canvas, ui_rect((0, 1), (58, -282), (480, 210), (0, 1), visible=False),
              panel=ui_panel((0.02, 0.025, 0.03, 0.86), 3, (0.93, 0.68, 0.34, 0.5), 1))
    ui(sc, "Confirm Text", conf, ui_rect((0.5, 1), (0, -18), (430, 96), (0.5, 1)),
       text=ft("Start a new campaign? Current progress will be replaced.", 26, align="center", wrap=True))
    ui(sc, "Confirm Yes", conf, ui_rect((0, 0), (22, 22), (205, 54), (0, 0)),
       panel=ui_panel((0.5, 0.2, 0.1, 0.9), 3, (1, 1, 1, 0.2), 1), button=ui_button("confirm_new"),
       text=ft("START NEW", 25, align="center"))
    ui(sc, "Confirm No", conf, ui_rect((1, 0), (-22, 22), (205, 54), (1, 0)),
       panel=ui_panel((0.1, 0.11, 0.12, 0.9), 3, (1, 1, 1, 0.2), 1), button=ui_button("cancel"),
       text=ft("CANCEL", 25, align="center"))
    ui(sc, "Menu Status", canvas, ui_rect((1, 0), (-36, 22), (700, 26), (1, 0)),
       text=ft("VICTUS 0.2.0   |   TOUCH  \u00b7  GAMEPAD  \u00b7  KEYBOARD", 16, (1, 1, 1, 0.55), "right", font=FONT_M))
    ui(sc, "Menu Version", canvas, ui_rect((0, 0), (72, 22), (500, 26), (0, 0)),
       text=ft("A VICTUS FIELD DEMONSTRATION  \u00b7  FAHTHIZ", 16, (1, 1, 1, 0.55), font=FONT_M))
    # Title screen ("tap to start") and the boot sequence, both full-screen buttons so any tap,
    # click or Enter/Space advances (scripts/menu.luau). The boot plays once per launch.
    title = ui(sc, "Menu Press", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1), visible=False),
               panel=ui_panel((0, 0, 0, 0), 0, (0, 0, 0, 0), 0), button=ui_button("start", (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)))
    ui(sc, "Menu Press Text", title, ui_rect((0.5, 0), (0, 118), (700, 34), (0.5, 0.5)),
       text=ft("TAP TO START", 24, (1, 1, 1, 0.9), "center", font=FONT_M))
    bb = ui(sc, "Boot", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1)),
            panel=ui_panel((0, 0, 0, 1), 0, (0, 0, 0, 0), 0), button=ui_button("skip_boot", (0, 0, 0, 1), (0, 0, 0, 1), (0, 0, 0, 1)))
    st = ui(sc, "Boot Studio", bb, ui_rect((0.5, 0.5), (0, 0), (800, 140), (0.5, 0.5)))
    ui(sc, "Boot Studio Name", st, ui_rect((0.5, 0.5), (0, 8), (800, 80), (0.5, 0.5)),
       text=ft("FAHTHIZ", 70, align="center", font=FONT_B, shadow=0))
    ui(sc, "Boot Studio Sub", st, ui_rect((0.5, 0.5), (0, -46), (800, 30), (0.5, 0.5)),
       text=ft("PRESENTS", 20, (1, 1, 1, 0.6), "center", font=FONT_M, shadow=0))
    en = ui(sc, "Boot Engine", bb, ui_rect((0.5, 0.5), (0, 0), (800, 160), (0.5, 0.5)))
    ui(sc, "Boot Engine Kicker", en, ui_rect((0.5, 0.5), (0, 60), (800, 26), (0.5, 0.5)),
       text=ft("BUILT ON", 18, AMBER, "center", font=FONT_M, shadow=0))
    ui(sc, "Boot Engine Name", en, ui_rect((0.5, 0.5), (0, 8), (800, 84), (0.5, 0.5)),
       text=ft("VICTUS", 78, align="center", font=FONT_B, shadow=0))
    ui(sc, "Boot Engine Rule", en, ui_rect((0.5, 0.5), (0, -40), (120, 2), (0.5, 0.5)),
       panel=ui_panel((1, 1, 1, 0.35), 0, (0, 0, 0, 0), 0))
    ui(sc, "Boot Engine Sub", en, ui_rect((0.5, 0.5), (0, -62), (800, 28), (0.5, 0.5)),
       text=ft("REAL-TIME RENDERING FOR PHONES", 18, (1, 1, 1, 0.6), "center", font=FONT_M, shadow=0))
    ui(sc, "Boot Warn", bb, ui_rect((0.5, 0.5), (0, 0), (760, 160), (0.5, 0.5)),
       text=ft("A work of fiction. Every weapon in this story is a non-lethal pulse carbine.\n"
               "Headphones recommended.", 24, (1, 1, 1, 0.8), "center", font=FONT_M, wrap=True, shadow=0))
    rig.add_pause_menu(sc)
    if test_plan:
        from common import autotest
        autotest(sc, test_plan)
        return sc.save(f"scenes/tests/{test_plan}.vscene")
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
    build_menu("menu_flow")
    build_credits()
