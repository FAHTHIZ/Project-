# SPDX-License-Identifier: Apache-2.0
"""Shared gameplay rig for every SPECIAL OPS operation scene: the first-person player (camera,
viewmodel, weapons, field device), the HUD canvas (reticle, ammo, objective, prompts,
subtitles, damage feedback, touch controls), the pause/settings modal, the diagnostics overlay
and the operation director."""
from __future__ import annotations

from vscene import (meta_uuid, Scene, transform, collider, body, mesh_renderer, script, ui_rect, ui_panel, ui_text, ui_button,
                    quat_euler)

PAUSE_SETTINGS = [
    ("look_sensitivity", "Look sensitivity"),
    ("aim_sensitivity", "Aim sensitivity"),
    ("fov", "Field of view"),
    ("invert_y", "Invert look"),
    ("camera_shake", "Camera shake"),
    ("reticle_size", "Reticle size"),
    ("reticle_opacity", "Reticle opacity"),
    ("subtitles", "Subtitles"),
    ("subtitle_size", "Subtitle size"),
    ("touch_controls", "Touch controls"),
    ("master_volume", "Master volume"),
    ("music_volume", "Music volume"),
    ("voice_volume", "Dialogue volume"),
    ("sfx_volume", "Effects volume"),
    ("ambient_volume", "Ambience volume"),
    ("diagnostics", "Diagnostics overlay"),
]


def ui(sc, name, parent, rect, panel=None, text=None, button=None, image=None, extra=None):
    c = {"UiRect": rect}
    if panel:
        c["UiPanel"] = panel
    if text:
        c["UiText"] = text
    if button:
        c["UiButton"] = button
    if image:
        c["UiImage"] = image
    if extra:
        c.update(extra)
    return sc.add(name, c, parent)


def button(sc, name, parent, rect, action, label, size=22, panel=None, align="left", inset=22):
    """Button with its label on a child entity "<name> Label" inset from the edges (UiText has no padding)."""
    b = ui(sc, name, parent, rect, panel=panel or ui_panel((0.08, 0.1, 0.11, 0.85), 8, (1, 1, 1, 0.16), 1),
           button=ui_button(action))
    ui(sc, name + " Label", b, ui_rect((0, 0), (inset, 0), (-2 * inset, 0), (0, 0), anchor_max=(1, 1)),
       text=ui_text(label, size, (1, 1, 1, 1), align, "middle", True))
    return b


def add_player(sc: Scene, pos, yaw, viewmodel_builder=None, with_weapons=True, far=600, extra=None):
    player = sc.add("Player", {
        "Transform": transform(pos, yaw=yaw),
        "CharacterController": {"radius": 0.32, "height": 1.78, "max_slope": 48, "step_height": 0.38,
                                "gravity_scale": 1, "mass": 75, "push_force": 300, "air_control": 0.3,
                                "layer": 0, "mask": 65535},
        "Perceptible": {"team": 1, "height": 1.5, "enabled": True},
        "Tags": {"tags": "Player"},
        "AudioListener": {},
        "Script": script("scripts/fp_player.luau"),
        **(extra or {}),
    })
    head = sc.add("Head", {"Transform": transform((0, 1.62, 0))}, player)
    cam = sc.add("Main Camera", {
        "Transform": transform(),
        "Camera": {"projection": "perspective", "fov_y": 70, "ortho_height": 10, "near": 0.03, "far": far,
                   "primary": True},
    }, head)
    # Weapon light: rail-mounted white LED under the barrel line, toggled with the light action
    # (fp_player.luau). The only shadowed local light the player owns, so wet trunks and fences
    # throw real shadows through the rain and fog.
    sc.add("Weapon Light", {"Transform": transform((0.16, -0.16, -0.25), quat_euler(-1.5, -1.0, 0)),
                            "Light": {"type": "spot", "color": [0.92, 0.95, 1.0, 1], "intensity": 18.0, "range": 34.0,
                                      "shadows": True, "inner_angle": 9.0, "outer_angle": 24.0}}, cam)
    vmc = {"Transform": transform()}
    if with_weapons:
        vmc["Script"] = script("scripts/weapons.luau")
    vm = sc.add("Viewmodel", vmc, cam)
    if viewmodel_builder:
        viewmodel_builder(sc, vm)
    elif with_weapons:
        add_viewmodel(sc, vm)
        add_weapon_fx(sc)
    return player


W = "models/weapons/"


def _vm_prop(sc, name, rel, parent, pos=(0, 0, 0), yaw=0.0, rot=None, scale=1.0):
    # Viewmodel parts never cast shadows (the player has no body shadow either).
    return sc.prop(name, rel, pos, yaw=yaw, rot=rot, scale=scale, parent=parent, shadows=False)


def add_viewmodel(sc: Scene, vm):
    """First-person weapons (see scripts/weapons.luau for the entity contract)."""
    pivot = sc.add("VM Pivot", {"Transform": transform((0.135, -0.148, -0.3))}, vm)
    for root, parts, hand_l, muzzle in [
        ("Carbine", [("Body", "pc7_body"), ("Cell", "pc7_cell")], ((0, 0.0, -0.21), (0, 0, 0)), (0, 0.045, -0.515)),
        ("Sidearm", [("Body", "sp2_body"), ("Slide", "sp2_slide"), ("Cell", "sp2_cell")],
         ((-0.014, -0.006, 0.012), (0, -12, 0)), (0, 0.012, -0.152)),
        ("Marksman", [("Body", "lr4_body"), ("Cell", "lr4_cell")], ((0, 0.0, -0.27), (0, 0, 0)), (0, 0.045, -0.745)),
        ("PDW", [("Body", "kv5_body"), ("Cell", "kv5_cell")], ((0, -0.012, -0.17), (0, 0, 0)), (0, 0.05, -0.39)),
        # the Ram's support hand rides the pump (parented to "Breacher Slide" below)
        ("Breacher", [("Body", "br9_body"), ("Slide", "br9_pump"), ("Cell", "br9_cell")],
         ((0, -0.028, -0.28), (0, 0, 0)), (0, 0.058, -0.565)),
        ("DMR", [("Body", "mr6_body"), ("Cell", "mr6_cell")], ((0, 0.0, -0.31), (0, 0, 0)), (0, 0.045, -0.67)),
    ]:
        r = sc.add(root, {"Transform": transform()}, pivot)
        made = {}
        for nm, glb in parts:
            made[nm] = _vm_prop(sc, f"{root} {nm}", W + glb + ".glb", r)
        _vm_prop(sc, f"{root} Hand R", W + "hand_r.glb", r)
        hand_parent = made["Slide"] if root == "Breacher" else r
        _vm_prop(sc, f"{root} Hand L", W + "hand_l.glb", hand_parent, hand_l[0], rot=quat_euler(*hand_l[1]))
        m = sc.add(f"{root} Muzzle", {"Transform": transform(muzzle),
                                      "Light": {"type": "point", "color": [0.45, 0.9, 1.0, 1], "intensity": 0.0,
                                                "range": 5.0, "shadows": False}}, r)
        _vm_prop(sc, f"{root} Flash", W + "pulse_bolt.glb", m, (0, 0, 0.01), scale=(4.0, 4.0, 0.09))
    dev = sc.add("Device", {"Transform": transform((-0.3, 0.03, 0.0), quat_euler(10, 200, 0))}, pivot)
    _vm_prop(sc, "Device Model", "models/env/field_device.glb", dev)
    _vm_prop(sc, "Device Hand L", W + "hand_l.glb", dev, (0.0, 0.0, 0.0), rot=quat_euler(0, 180, 0))
    # FK-1 field kit, held in the left of the frame while it is used (camera space, not swayed).
    kit = sc.add("Kit", {"Transform": transform((-0.16, -0.14, -0.34), quat_euler(28, 18, -6))}, vm)
    _vm_prop(sc, "Kit Model", "models/props/field_kit.glb", kit, scale=(0.55, 0.55, 0.55))
    _vm_prop(sc, "Kit Hand L", W + "hand_l.glb", kit, (0.06, -0.02, 0.02), rot=quat_euler(0, 160, 0))
    return pivot


def add_weapon_fx(sc: Scene):
    """World-space pulse tracers and impact particles used by scripts/weapons.luau."""
    for i in range(6):
        sc.prop(f"Tracer {i}", W + "pulse_bolt.glb", (0, -50, 0), shadows=False)
    sc.add("Impact Sparks", {"Transform": transform((0, -50, 0)), "ParticleEmitter": {
        "emitting": False, "loop": False, "world_space": True, "duration": 0, "rate": 0, "burst": 0,
        "max_particles": 96, "lifetime_min": 0.12, "lifetime_max": 0.32, "shape": "cone", "radius": 0.02,
        "angle": 60, "speed_min": 1.5, "speed_max": 5.0, "gravity": [0, -7, 0], "drag": 1.5,
        "size_start": 0.03, "size_end": 0.0, "size_variation": 0.5, "color_start": [0.55, 0.92, 1.0, 1],
        "color_end": [0.3, 0.7, 1.0, 0], "intensity": 5.0, "blend": "additive", "softness": 0.02,
        "velocity_stretch": 0.025}})
    sc.add("Impact Dust", {"Transform": transform((0, -50, 0)), "ParticleEmitter": {
        "emitting": False, "loop": False, "world_space": True, "duration": 0, "rate": 0, "burst": 0,
        "max_particles": 40, "lifetime_min": 0.5, "lifetime_max": 1.0, "shape": "cone", "radius": 0.04,
        "angle": 35, "speed_min": 0.3, "speed_max": 1.0, "gravity": [0, -0.4, 0], "drag": 2.5,
        "size_start": 0.08, "size_end": 0.32, "size_variation": 0.4, "color_start": [0.5, 0.47, 0.4, 0.5],
        "color_end": [0.5, 0.47, 0.4, 0], "intensity": 1.0, "blend": "alpha", "softness": 0.2}})


def add_hud(sc: Scene):
    canvas = sc.add("HUD", {
        "UiCanvas": {"visible": True, "scale_mode": "scale_with_screen", "reference_size": [1280, 720], "match": 1,
                     "sort_order": 0, "keyboard_navigation": False, "blocks_input": False},
        "Script": script("scripts/hud.luau"),
    })
    # Cinematic letterbox bars (hidden in gameplay).
    ui(sc, "Letterbox Top", canvas, ui_rect((0, 1), (0, 0), (0, 0), (0.5, 1), anchor_max=(1, 1), visible=False),
       panel=ui_panel((0, 0, 0, 1), 0, (0, 0, 0, 0), 0))
    ui(sc, "Letterbox Bottom", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0), anchor_max=(1, 0), visible=False),
       panel=ui_panel((0, 0, 0, 1), 0, (0, 0, 0, 0), 0))
    # LR-4 scope overlay: lens mask (square, fits the canvas height) and housing panels to the sides.
    scope = ui(sc, "Scope", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1), visible=False))
    ui(sc, "Scope Lens", scope, ui_rect((0.5, 0.5), (0, 0), (724, 724), (0.5, 0.5)),
       image={"texture": meta_uuid("textures/ui/scope_mask.png"), "tint": [1, 1, 1, 1], "preserve_aspect": True,
              "corner_radius": 0})
    ui(sc, "Scope Left", scope, ui_rect((0.5, 0.5), (-360, 0), (2400, 900), (1, 0.5)),
       panel=ui_panel((0.004, 0.004, 0.004, 1), 0, (0, 0, 0, 0), 0))
    ui(sc, "Scope Right", scope, ui_rect((0.5, 0.5), (360, 0), (2400, 900), (0, 0.5)),
       panel=ui_panel((0.004, 0.004, 0.004, 1), 0, (0, 0, 0, 0), 0))
    ui(sc, "Scope Zoom", scope, ui_rect((0.5, 0), (0, 40), (300, 28), (0.5, 0)),
       text=ui_text("", 16, (0.85, 0.95, 1, 0.8), "center", "middle", True))
    # Damage vignette and fade.
    ui(sc, "Damage", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1), visible=False),
       panel=ui_panel((0.55, 0.08, 0.04, 0.0), 0, (0.8, 0.1, 0.05, 0.0), 26))
    # Reticle: four ticks and a dot around the centre.
    ret = ui(sc, "Reticle", canvas, ui_rect((0.5, 0.5), (0, 0), (2, 2)))
    for n, p, s in [("R Up", (0, 14), (2, 9)), ("R Down", (0, -14), (2, 9)), ("R Left", (-14, 0), (9, 2)),
                    ("R Right", (14, 0), (9, 2)), ("R Dot", (0, 0), (3, 3))]:
        ui(sc, n, ret, ui_rect((0.5, 0.5), p, s), panel=ui_panel((1, 1, 1, 0.9), 1, (0, 0, 0, 0.5), 1))
    ui(sc, "Hit Marker", canvas, ui_rect((0.5, 0.5), (0, 0), (30, 30), visible=False),
       panel=ui_panel((1, 1, 1, 0), 15, (1, 1, 1, 0.95), 2.5))
    # Objective (top left).
    obj = ui(sc, "Objective", canvas, ui_rect((0, 1), (110, -22), (520, 74), (0, 1)),
             panel=ui_panel((0.03, 0.05, 0.06, 0.45), 6, (0.75, 0.9, 1, 0.12), 1))
    ui(sc, "Objective Op", obj, ui_rect((0, 1), (14, -8), (490, 24), (0, 1)),
       text=ui_text("", 15, (0.62, 0.84, 0.93, 1), "left", "middle", True))
    ui(sc, "Objective Text", obj, ui_rect((0, 1), (14, -32), (490, 34), (0, 1)),
       text=ui_text("", 21, (1, 1, 1, 1), "left", "middle", False, True))
    # Mission update toast (top centre).
    ui(sc, "Toast", canvas, ui_rect((0.5, 1), (0, -182), (780, 46), (0.5, 1), visible=False),
       panel=ui_panel((0.03, 0.05, 0.06, 0.6), 6, (0.75, 0.9, 1, 0.2), 1),
       text=ui_text("", 22, (1, 1, 1, 1), "center", "middle", True))
    # Squad / awareness indicator (top centre small).
    ui(sc, "Awareness", canvas, ui_rect((0.5, 1), (0, -24), (360, 30), (0.5, 1), visible=False),
       text=ui_text("", 17, (1, 0.8, 0.45, 1), "center", "middle", True))
    # Waypoint bearing (top centre, below awareness): label and distance slide along a strip by the
    # target's bearing relative to the view and pin to the strip ends when it is behind you.
    ui(sc, "Waypoint", canvas, ui_rect((0.5, 1), (0, -60), (300, 30), (0.5, 1), visible=False),
       text=ui_text("", 17, (0.88, 0.97, 1, 0.95), "center", "middle", True))
    ui(sc, "Waypoint Tick", canvas, ui_rect((0.5, 1), (0, -46), (4, 10), (0.5, 1), visible=False),
       panel=ui_panel((0.88, 0.97, 1, 0.9), 1, (0, 0, 0, 0.4), 1))
    # Interaction prompt (below centre).
    ui(sc, "Prompt", canvas, ui_rect((0.5, 0.5), (0, -88), (520, 40), (0.5, 0.5), visible=False),
       panel=ui_panel((0.03, 0.05, 0.06, 0.55), 6, (1, 1, 1, 0.15), 1),
       text=ui_text("", 21, (1, 1, 1, 1), "center", "middle", True))
    ui(sc, "Prompt Detail", canvas, ui_rect((0.5, 0.5), (0, -128), (640, 34), (0.5, 0.5), visible=False),
       panel=ui_panel((0.03, 0.05, 0.06, 0.45), 6, (1, 1, 1, 0.0), 0),
       text=ui_text("", 16, (0.85, 0.93, 1, 1), "center", "middle", False))
    # Weapon / ammo (bottom right, above touch buttons when touch is off).
    wp = ui(sc, "Weapon Panel", canvas, ui_rect((1, 0), (-28, 24), (300, 88), (1, 0)),
            panel=ui_panel((0.03, 0.05, 0.06, 0.45), 6, (1, 1, 1, 0.12), 1))
    ui(sc, "Weapon Name", wp, ui_rect((0, 1), (14, -8), (272, 24), (0, 1)),
       text=ui_text("", 16, (0.75, 0.9, 1, 1), "left", "middle", True))
    ui(sc, "Ammo", wp, ui_rect((0, 0), (14, 8), (180, 48), (0, 0)),
       text=ui_text("", 36, (1, 1, 1, 1), "left", "middle", True))
    ui(sc, "Weapon State", wp, ui_rect((1, 0), (-14, 12), (120, 30), (1, 0)),
       text=ui_text("", 16, (1, 0.85, 0.5, 1), "right", "middle", True))
    # Health and tool (bottom left).
    hp = ui(sc, "Status Panel", canvas, ui_rect((0, 0), (28, 24), (300, 70), (0, 0)),
            panel=ui_panel((0.03, 0.05, 0.06, 0.45), 6, (1, 1, 1, 0.12), 1))
    ui(sc, "Health Back", hp, ui_rect((0, 1), (14, -14), (272, 10), (0, 1)), panel=ui_panel((1, 1, 1, 0.15), 3))
    ui(sc, "Health Bar", hp, ui_rect((0, 1), (14, -14), (272, 10), (0, 1)),
       panel=ui_panel((0.55, 0.9, 0.75, 0.95), 3, (0, 0, 0, 0), 0))
    ui(sc, "Kit Text", hp, ui_rect((1, 0), (-14, 8), (120, 34), (1, 0)),
       text=ui_text("", 16, (0.65, 1, 0.8, 1), "right", "middle", True))
    ui(sc, "Tool Text", hp, ui_rect((0, 0), (14, 8), (170, 34), (0, 0)),
       text=ui_text("", 17, (0.8, 0.95, 1, 1), "left", "middle", False))
    # Subtitles (bottom centre).
    sub = ui(sc, "Subtitle", canvas, ui_rect((0.5, 0), (0, 128), (760, 74), (0.5, 0), visible=False),
             panel=ui_panel((0, 0, 0, 0.55), 6, (0, 0, 0, 0), 0))
    ui(sc, "Subtitle Speaker", sub, ui_rect((0.5, 1), (0, -6), (740, 26), (0.5, 1)),
       text=ui_text("", 20, (1, 0.85, 0.45, 1), "center", "middle", True))
    ui(sc, "Subtitle Text", sub, ui_rect((0.5, 0), (0, 6), (740, 40), (0.5, 0)),
       text=ui_text("", 24, (1, 1, 1, 1), "center", "middle", False, True))
    # Skip hint for cinematics.
    ui(sc, "Skip Hint", canvas, ui_rect((1, 0), (-28, 22), (360, 34), (1, 0), visible=False),
       text=ui_text("", 18, (1, 1, 1, 0.85), "right", "middle", False))
    ui(sc, "Skip Button", canvas, ui_rect((1, 1), (-24, -24), (150, 52), (1, 1), visible=False),
       panel=ui_panel((0.05, 0.06, 0.07, 0.6), 8, (1, 1, 1, 0.25), 1), button=ui_button("skip_cinematic"),
       text=ui_text("SKIP", 22, (1, 1, 1, 1), "center", "middle", True))
    # Fade (above everything else but the modal).
    ui(sc, "Fade", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1), visible=False),
       panel=ui_panel((0, 0, 0, 1), 0, (0, 0, 0, 0), 0))
    ui(sc, "Title Card", canvas, ui_rect((0.5, 0.5), (0, 20), (1000, 160), (0.5, 0.5), visible=False),
       text=ui_text("", 46, (1, 1, 1, 1), "center", "middle", True, True))
    ui(sc, "Title Sub", canvas, ui_rect((0.5, 0.5), (0, -60), (1000, 40), (0.5, 0.5), visible=False),
       text=ui_text("", 22, (0.75, 0.9, 1, 1), "center", "middle", False))
    # Touch controls: stick base/knob and buttons (positions set by hud.luau from controls.luau).
    touch = ui(sc, "Touch", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0, 0), anchor_max=(1, 1), visible=False))
    ui(sc, "Stick Base", touch, ui_rect((0, 1), (220, -470), (180, 180), (0.5, 0.5)),
       panel=ui_panel((1, 1, 1, 0.08), 90, (1, 1, 1, 0.35), 2))
    ui(sc, "Stick Knob", touch, ui_rect((0, 1), (220, -470), (76, 76), (0.5, 0.5)),
       panel=ui_panel((1, 1, 1, 0.32), 38, (1, 1, 1, 0.6), 2))
    from_controls = [("fire", 74, "FIRE"), ("aim", 52, "AIM"), ("reload", 44, "RELOAD"), ("switch", 44, "SWITCH"),
                     ("jump", 44, "JUMP"), ("crouch", 40, "CROUCH"), ("interact", 48, "USE"), ("tool", 44, "TOOL"), ("utility", 40, "KIT"),
                     ("pause", 34, "II"), ("objectives", 34, "OBJ"), ("light", 30, "LIGHT")]
    for n, r, label in from_controls:
        ui(sc, f"Touch {n}", touch, ui_rect((1, 1), (0, 0), (2 * r, 2 * r), (0.5, 0.5)),
           panel=ui_panel((0.05, 0.07, 0.08, 0.35), r, (1, 1, 1, 0.45), 2),
           text=ui_text(label, 15 if r < 60 else 20, (1, 1, 1, 0.92), "center", "middle", True))
    # Diagnostics overlay (top right).
    # Sits left of the pause button and above the right-hand touch cluster.
    diag = ui(sc, "Diagnostics", canvas, ui_rect((1, 1), (-108, -16), (440, 150), (1, 1), visible=False),
              panel=ui_panel((0, 0, 0, 0.55), 6, (1, 1, 1, 0.1), 1))
    ui(sc, "Diagnostics Text", diag, ui_rect((0, 0), (12, 8), (-24, -16), (0, 0), anchor_max=(1, 1)),
       text=ui_text("", 15, (0.8, 1, 0.85, 1), "left", "top", False, True))
    # Objectives log (toggle with objectives action).
    ui(sc, "Objectives Log", canvas, ui_rect((0, 1), (110, -108), (560, 300), (0, 1), visible=False),
       panel=ui_panel((0.02, 0.03, 0.04, 0.78), 8, (1, 1, 1, 0.14), 1),
       text=ui_text("", 18, (0.92, 0.96, 1, 1), "left", "top", False, True))
    add_pause_menu(sc)
    return canvas


def add_pause_menu(sc: Scene):
    modal = sc.add("Pause Menu", {
        "UiCanvas": {"visible": False, "scale_mode": "scale_with_screen", "reference_size": [1280, 720], "match": 1,
                     "sort_order": 10, "keyboard_navigation": True, "blocks_input": True},
        "Script": script("scripts/pause_menu.luau"),
    })
    ui(sc, "Pause Dim", modal, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1)),
       panel=ui_panel((0.01, 0.02, 0.03, 0.78), 0, (0, 0, 0, 0), 0))
    main = ui(sc, "Pause Main", modal, ui_rect((0.5, 0.5), (0, 0), (440, 470)),
              panel=ui_panel((0.04, 0.06, 0.07, 0.92), 10, (1, 1, 1, 0.14), 1))
    ui(sc, "Pause Title", main, ui_rect((0.5, 1), (0, -18), (400, 48), (0.5, 1)),
       text=ui_text("PAUSED", 34, (1, 1, 1, 1), "center", "middle", True))
    ui(sc, "Pause Op", main, ui_rect((0.5, 1), (0, -64), (400, 30), (0.5, 1)),
       text=ui_text("", 18, (0.65, 0.85, 0.95, 1), "center", "middle", False))
    for i, (label, action) in enumerate([("Resume", "resume"), ("Restart from checkpoint", "restart_checkpoint"),
                                          ("Settings", "settings"), ("Objectives", "objectives"),
                                          ("Quit to main menu", "quit_menu")]):
        ui(sc, f"Pause {label}", main, ui_rect((0.5, 1), (0, -112 - i * 66), (360, 54), (0.5, 1)),
           panel=ui_panel((0.1, 0.13, 0.15, 0.9), 8, (1, 1, 1, 0.18), 1), button=ui_button(action),
           text=ui_text(label, 22, (1, 1, 1, 1), "center", "middle", True))
    settings = ui(sc, "Settings Panel", modal, ui_rect((0.5, 0.5), (0, 0), (760, 640), visible=False),
                  panel=ui_panel((0.04, 0.06, 0.07, 0.95), 10, (1, 1, 1, 0.14), 1))
    ui(sc, "Settings Title", settings, ui_rect((0.5, 1), (0, -10), (700, 40), (0.5, 1)),
       text=ui_text("SETTINGS", 28, (1, 1, 1, 1), "center", "middle", True))
    scroll = ui(sc, "Settings Scroll", settings, ui_rect((0.5, 1), (0, -56), (720, 500), (0.5, 1)),
                extra={"UiScroll": {"vertical": True, "horizontal": False, "offset": [0, 0], "wheel_step": 40,
                                    "drag_to_scroll": True}})
    for i, (key, label) in enumerate(PAUSE_SETTINGS):
        row = ui(sc, f"Set {key}", scroll, ui_rect((0.5, 1), (0, -i * 58), (700, 52), (0.5, 1)),
                 panel=ui_panel((0.08, 0.1, 0.12, 0.8), 6, (1, 1, 1, 0.08), 1))
        ui(sc, f"Set {key} Label", row, ui_rect((0, 0.5), (18, 0), (340, 40), (0, 0.5)),
           text=ui_text(label, 20, (1, 1, 1, 1), "left", "middle"))
        ui(sc, f"Set {key} Value", row, ui_rect((1, 0.5), (-130, 0), (150, 40), (0.5, 0.5)),
           text=ui_text("", 20, (0.7, 0.9, 1, 1), "center", "middle", True))
        ui(sc, f"Set {key} Minus", row, ui_rect((1, 0.5), (-228, 0), (48, 42), (0.5, 0.5)),
           panel=ui_panel((0.14, 0.17, 0.2, 0.95), 6, (1, 1, 1, 0.2), 1), button=ui_button(f"set:{key}:-"),
           text=ui_text("-", 26, (1, 1, 1, 1), "center", "middle", True))
        ui(sc, f"Set {key} Plus", row, ui_rect((1, 0.5), (-34, 0), (48, 42), (0.5, 0.5)),
           panel=ui_panel((0.14, 0.17, 0.2, 0.95), 6, (1, 1, 1, 0.2), 1), button=ui_button(f"set:{key}:+"),
           text=ui_text("+", 26, (1, 1, 1, 1), "center", "middle", True))
    ui(sc, "Settings Back", settings, ui_rect((0.5, 0), (0, 18), (300, 54), (0.5, 0)),
       panel=ui_panel((0.1, 0.13, 0.15, 0.9), 8, (1, 1, 1, 0.18), 1), button=ui_button("settings_back"),
       text=ui_text("Back", 22, (1, 1, 1, 1), "center", "middle", True))
    return modal
