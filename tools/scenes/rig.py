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
    ("lens_effects", "Body-cam lens"),
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


# HUD v2 layout constants (canvas units, 1280x720 reference).
COMPASS_W = 560          # visible compass strip width
COMPASS_PPD = 4.0        # pixels per degree of heading (560 px shows 140 degrees)
MAG_PIPS = 40            # largest magazine shown as pips (PDW); larger magazines show the number only
SQUAD_ROWS = 5
DMG_DIRS = 8


def _img(rel, tint=(1, 1, 1, 1), aspect=False):
    return {"texture": meta_uuid(rel), "tint": list(tint), "preserve_aspect": aspect, "corner_radius": 0}


def add_hud(sc: Scene):
    """HUD v2: diegetic-leaning, low clutter. A heading compass with the waypoint on it (top
    centre), objective and squad roster (top left), vitals and stance (bottom left), weapon block
    with magazine pips and reload progress (bottom right), directional damage wedges and an edge
    vignette, textured hit / takedown marker and a short takedown feed. Idle blocks fade back
    when nothing is happening (scripts/hud.luau)."""
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
    # Damage: edge vignette (red, pulses at low health) and eight directional wedges round the centre.
    ui(sc, "Damage", canvas, ui_rect((0, 0), (0, 0), (0, 0), (0.5, 0.5), anchor_max=(1, 1), visible=False),
       image=_img("textures/ui/vignette.png", (0.62, 0.04, 0.02, 0.0)))
    dd = ui(sc, "Damage Dirs", canvas, ui_rect((0.5, 0.5), (0, 0), (430, 430)))
    for k in range(DMG_DIRS):
        ui(sc, f"Dmg Dir {k}", dd, ui_rect((0.5, 0.5), (0, 0), (430, 430), visible=False),
           image=_img(f"textures/ui/dmg_dir_{k}.png", (1, 0.22, 0.12, 0.0)))
    # Reticle: four ticks and a dot around the centre.
    ret = ui(sc, "Reticle", canvas, ui_rect((0.5, 0.5), (0, 0), (2, 2)))
    for n, p, sz in [("R Up", (0, 14), (2, 9)), ("R Down", (0, -14), (2, 9)), ("R Left", (-14, 0), (9, 2)),
                     ("R Right", (14, 0), (9, 2)), ("R Dot", (0, 0), (3, 3))]:
        ui(sc, n, ret, ui_rect((0.5, 0.5), p, sz), panel=ui_panel((1, 1, 1, 0.9), 1, (0, 0, 0, 0.5), 1))
    ui(sc, "Hit Marker", canvas, ui_rect((0.5, 0.5), (0, 0), (34, 34), visible=False),
       image=_img("textures/ui/hit_marker.png", (1, 1, 1, 0.95)))
    # Heading compass (top centre): a strip of ticks and labels that slides with the view inside a
    # clipped window, a centre notch, the heading in degrees, and the waypoint diamond + distance.
    comp_rect = ui_rect((0.5, 1), (0, -14), (COMPASS_W, 30), (0.5, 1))
    comp_rect["clip_children"] = True
    comp = ui(sc, "Compass", canvas, comp_rect, panel=ui_panel((0.02, 0.03, 0.04, 0.22), 4, (1, 1, 1, 0.06), 1))
    strip = ui(sc, "Compass Strip", comp, ui_rect((0.5, 0.5), (0, 0), (2, 2)))
    names = {0: "N", 45: "NE", 90: "E", 135: "SE", 180: "S", 225: "SW", 270: "W", 315: "NW"}
    for b in range(-75, 360 + 76, 15):
        bb = b % 360
        x = b * COMPASS_PPD
        if bb in names:
            card = bb % 90 == 0
            ui(sc, f"CL {b}", strip, ui_rect((0.5, 0.5), (x, -2), (40, 20)),
               text=ui_text(names[bb], 16 if card else 13, (1, 0.86, 0.55, 1) if bb == 0 else
                            ((1, 1, 1, 0.95) if card else (0.85, 0.92, 1, 0.75)), "center", "middle", card))
        else:
            ui(sc, f"CT {b}", strip, ui_rect((0.5, 0.5), (x, 7), (2, 7)),
               panel=ui_panel((1, 1, 1, 0.55), 0, (0, 0, 0, 0), 0))
    ui(sc, "Compass Notch", canvas, ui_rect((0.5, 1), (0, -10), (2, 10), (0.5, 1)),
       panel=ui_panel((1, 0.82, 0.45, 0.95), 0, (0, 0, 0, 0), 0))
    ui(sc, "Compass Heading", canvas, ui_rect((0.5, 1), (0, -44), (80, 18), (0.5, 1)),
       text=ui_text("", 13, (0.85, 0.92, 1, 0.8), "center", "middle", True))
    # Waypoint diamond on the compass and its label (distance) under it.
    ui(sc, "Waypoint Tick", canvas, ui_rect((0.5, 1), (0, -31), (14, 14), (0.5, 0.5), visible=False),
       image=_img("textures/ui/wp_diamond.png", (1, 0.84, 0.5, 0.95)))
    ui(sc, "Waypoint", canvas, ui_rect((0.5, 1), (0, -62), (300, 20), (0.5, 1), visible=False),
       text=ui_text("", 14, (1, 0.9, 0.7, 0.95), "center", "middle", True))
    # Awareness: what the contractors know (SEARCHING / COMPROMISED).
    ui(sc, "Awareness", canvas, ui_rect((0.5, 1), (0, -86), (360, 24), (0.5, 1), visible=False),
       text=ui_text("", 15, (1, 0.8, 0.45, 1), "center", "middle", True))
    # Objective (top left) on a soft plate with an accent bar.
    obj = ui(sc, "Objective", canvas, ui_rect((0, 1), (110, -22), (520, 74), (0, 1)),
             image=_img("textures/ui/plate_l.png", (1, 1, 1, 0.9)))
    ui(sc, "Objective Accent", obj, ui_rect((0, 1), (0, -12), (3, 50), (0, 1)),
       panel=ui_panel((1, 0.78, 0.4, 0.9), 0, (0, 0, 0, 0), 0))
    ui(sc, "Objective Op", obj, ui_rect((0, 1), (14, -8), (490, 24), (0, 1)),
       text=ui_text("", 14, (0.62, 0.84, 0.93, 1), "left", "middle", True))
    ui(sc, "Objective Text", obj, ui_rect((0, 1), (14, -32), (490, 34), (0, 1)),
       text=ui_text("", 21, (1, 1, 1, 1), "left", "middle", False, True))
    # Squad roster (under the objective): dot, callsign, what they are doing.
    sq = ui(sc, "Squad", canvas, ui_rect((0, 1), (110, -102), (300, SQUAD_ROWS * 20), (0, 1), visible=False))
    for i in range(1, SQUAD_ROWS + 1):
        y = -(i - 1) * 20 - 10
        ui(sc, f"Squad {i} Dot", sq, ui_rect((0, 1), (16, y), (6, 6), (0.5, 0.5)),
           panel=ui_panel((0.55, 0.9, 0.75, 0.95), 3, (0, 0, 0, 0), 0))
        ui(sc, f"Squad {i} Name", sq, ui_rect((0, 1), (28, y), (90, 18), (0, 0.5)),
           text=ui_text("", 14, (1, 1, 1, 0.92), "left", "middle", True))
        ui(sc, f"Squad {i} State", sq, ui_rect((0, 1), (112, y), (180, 18), (0, 0.5)),
           text=ui_text("", 13, (0.75, 0.85, 0.92, 0.8), "left", "middle", False))
    # Mission update toast (top centre).
    ui(sc, "Toast", canvas, ui_rect((0.5, 1), (0, -182), (780, 46), (0.5, 1), visible=False),
       panel=ui_panel((0.03, 0.05, 0.06, 0.6), 6, (0.75, 0.9, 1, 0.2), 1),
       text=ui_text("", 22, (1, 1, 1, 1), "center", "middle", True))
    # Takedown feed (right, under the diagnostics corner).
    ui(sc, "Feed", canvas, ui_rect((1, 1), (-28, -110), (420, 80), (1, 1), visible=False),
       text=ui_text("", 15, (1, 0.9, 0.72, 0.95), "right", "top", True, True))
    # Interaction prompt (below centre): key chip and label.
    pr = ui(sc, "Prompt", canvas, ui_rect((0.5, 0.5), (0, -92), (440, 40), (0.5, 0.5), visible=False),
            panel=ui_panel((0.03, 0.05, 0.06, 0.5), 6, (1, 1, 1, 0.12), 1))
    ui(sc, "Prompt Key", pr, ui_rect((0.5, 0.5), (-150, 0), (54, 30), (0.5, 0.5)),
       panel=ui_panel((0.92, 0.95, 1, 0.92), 5, (0, 0, 0, 0.3), 1),
       text=ui_text("E", 16, (0.04, 0.05, 0.06, 1), "center", "middle", True))
    ui(sc, "Prompt Label", pr, ui_rect((0.5, 0.5), (-114, 0), (340, 34), (0, 0.5)),
       text=ui_text("", 20, (1, 1, 1, 1), "left", "middle", True))
    ui(sc, "Prompt Detail", canvas, ui_rect((0.5, 0.5), (0, -128), (640, 34), (0.5, 0.5), visible=False),
       panel=ui_panel((0.03, 0.05, 0.06, 0.45), 6, (1, 1, 1, 0.0), 0),
       text=ui_text("", 16, (0.85, 0.93, 1, 1), "center", "middle", False))
    # Weapon block (bottom right): name, big magazine count, reserve, pips, reload progress, state.
    wp = ui(sc, "Weapon Panel", canvas, ui_rect((1, 0), (-24, 20), (360, 100), (1, 0)),
            image=_img("textures/ui/plate_r.png", (1, 1, 1, 0.9)))
    ui(sc, "Weapon Name", wp, ui_rect((1, 1), (-16, -8), (320, 20), (1, 1)),
       text=ui_text("", 14, (0.75, 0.9, 1, 1), "right", "middle", True))
    ui(sc, "Ammo", wp, ui_rect((1, 0), (-92, 14), (150, 50), (1, 0)),
       text=ui_text("", 44, (1, 1, 1, 1), "right", "middle", True))
    ui(sc, "Reserve", wp, ui_rect((1, 0), (-16, 20), (74, 26), (1, 0)),
       text=ui_text("", 18, (0.78, 0.86, 0.92, 0.85), "left", "middle", True))
    pips = ui(sc, "Mag Pips", wp, ui_rect((1, 1), (-16, -34), (MAG_PIPS * 4, 8), (1, 1)))
    for i in range(MAG_PIPS):
        ui(sc, f"Pip {i}", pips, ui_rect((1, 0.5), (-i * 4, 0), (3, 8), (1, 0.5), visible=False),
           panel=ui_panel((1, 1, 1, 0.9), 0, (0, 0, 0, 0), 0))
    ui(sc, "Reload Back", wp, ui_rect((1, 0), (-16, 8), (200, 3), (1, 0), visible=False),
       panel=ui_panel((1, 1, 1, 0.16), 1, (0, 0, 0, 0), 0))
    ui(sc, "Reload Bar", wp, ui_rect((1, 0), (-16, 8), (200, 3), (1, 0), visible=False),
       panel=ui_panel((0.6, 0.9, 1, 0.95), 1, (0, 0, 0, 0), 0))
    ui(sc, "Weapon State", wp, ui_rect((1, 0), (-250, 22), (110, 24), (1, 0)),
       text=ui_text("", 15, (1, 0.8, 0.45, 1), "right", "middle", True))
    # Vitals (bottom left): health with a trailing damage bar and segment marks, stance, tool, kit.
    hp = ui(sc, "Status Panel", canvas, ui_rect((0, 0), (24, 20), (340, 80), (0, 0)),
            image=_img("textures/ui/plate_l.png", (1, 1, 1, 0.9)))
    ui(sc, "Health Back", hp, ui_rect((0, 1), (16, -16), (272, 8), (0, 1)), panel=ui_panel((1, 1, 1, 0.14), 2))
    ui(sc, "Health Trail", hp, ui_rect((0, 1), (16, -16), (272, 8), (0, 1)),
       panel=ui_panel((1, 0.42, 0.28, 0.85), 2, (0, 0, 0, 0), 0))
    ui(sc, "Health Bar", hp, ui_rect((0, 1), (16, -16), (272, 8), (0, 1)),
       panel=ui_panel((0.55, 0.9, 0.75, 0.95), 2, (0, 0, 0, 0), 0))
    for k in range(1, 10):
        ui(sc, f"Health Seg {k}", hp, ui_rect((0, 1), (16 + 272 * k / 10 - 1, -16), (2, 8), (0, 1)),
           panel=ui_panel((0.02, 0.03, 0.04, 0.7), 0, (0, 0, 0, 0), 0))
    ui(sc, "Stance Text", hp, ui_rect((0, 1), (16, -28), (272, 18), (0, 1)),
       text=ui_text("", 12, (0.78, 0.88, 0.95, 0.8), "left", "middle", True))
    ui(sc, "Kit Text", hp, ui_rect((1, 0), (-40, 8), (120, 30), (1, 0)),
       text=ui_text("", 15, (0.65, 1, 0.8, 1), "right", "middle", True))
    ui(sc, "Tool Text", hp, ui_rect((0, 0), (16, 8), (190, 30), (0, 0)),
       text=ui_text("", 15, (0.8, 0.95, 1, 1), "left", "middle", False))
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
    # Touch v2: original line-art icons (tools/ui/build_touch_icons.py) on dark glass discs; the
    # floating stick is a ring with direction ticks and a lit knob.
    ui(sc, "Stick Base", touch, ui_rect((0, 1), (220, -470), (200, 200), (0.5, 0.5)),
       image=_img("textures/ui/touch/stick_ring.png", (1, 1, 1, 0.9)))
    ui(sc, "Stick Knob", touch, ui_rect((0, 1), (220, -470), (84, 84), (0.5, 0.5)),
       image=_img("textures/ui/touch/stick_knob.png", (1, 1, 1, 0.95)))
    from_controls = [("fire", 80, "fire"), ("aim", 46, "aim"), ("reload", 42, "reload"), ("switch", 38, "switch"),
                     ("jump", 40, "jump"), ("crouch", 40, "crouch"), ("interact", 50, "use"), ("tool", 38, "tool"),
                     ("utility", 38, "kit"), ("pause", 32, "pause"), ("objectives", 30, "obj"), ("light", 28, "light")]
    for n, r, icon in from_controls:
        b = ui(sc, f"Touch {n}", touch, ui_rect((1, 1), (0, 0), (2 * r, 2 * r), (0.5, 0.5)),
               image=_img("textures/ui/touch/disc_fire.png" if n == "fire" else "textures/ui/touch/disc.png",
                          (1, 1, 1, 0.92)))
        f = 0.6 if n == "fire" else 0.62
        ui(sc, f"Touch {n} Icon", b, ui_rect((0.5, 0.5), (0, 0), (2 * r * f, 2 * r * f), (0.5, 0.5)),
           image=_img(f"textures/ui/touch/{icon}.png", (1, 1, 1, 0.95)))
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
    _hud_type(sc, canvas)
    add_pause_menu(sc)
    return canvas


# HUD type system (2026-11-20): labels, numbers and the chapter title use Barlow Condensed (the
# front-end face, SIL OFL); running sentences (subtitles, objective line, toasts, logs) stay on
# the built-in Inter for reading speed, as do labels under 16 units. Condensed glyphs are ~20 % narrower, so sizes go up 18 %.
HUD_FONT_BOLD = "fonts/BarlowCondensed-Bold.ttf"
HUD_FONT = "fonts/BarlowCondensed-SemiBold.ttf"
HUD_SENTENCES = {"Subtitle Text", "Objective Text", "Toast", "Prompt Detail", "Objectives Log", "Diagnostics Text",
                 "Title Sub", "Skip Hint"}


def _hud_type(sc: Scene, canvas):
    under = {canvas}
    for e in sc.entities:
        if e.get("parent") in under:
            under.add(e["uuid"])
        t = e["components"].get("UiText")
        if e["uuid"] not in under or not t or e["name"] in HUD_SENTENCES or t.get("font"):
            continue
        if t["font_size"] < 16:  # small labels stay on Inter: condensed caps smudge below ~18 px on a phone
            continue
        t["font"] = HUD_FONT_BOLD if t.get("bold") else HUD_FONT
        t["font_size"] = round(t["font_size"] * 1.18)


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
