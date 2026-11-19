# SPDX-License-Identifier: Apache-2.0
"""Squad operators, Greyline contractors and civilian NPCs for the operation scene builders.

Each actor is a CharacterController + NavAgent root that a script steers, with the skinned model
as the child "Body" (animation controller anim/characters/human.vanim). Operators and enemies
carry a third-person PC-7 under the Chest bone; two-bone IK on both hands holds it, and a look_at
IK on the head gives eye-lines. Scripts move the carried weapon between low-ready and aim.
"""
from __future__ import annotations

from vscene import Scene, transform, quat_euler, script

CTRL = "anim/characters/human.vanim"
W = "models/weapons/"

# who -> (model, display name, role). Gameplay values live in scripts/lib/squad.luau.
SQUAD = {
    "Anchor": ("models/characters/sops_anchor.glb", "Anchor", "lead"),
    "Patch": ("models/characters/sops_patch.glb", "Patch", "medic"),
    "Echo": ("models/characters/sops_echo.glb", "Echo", "scout"),
    "Tally": ("models/characters/sops_tally.glb", "Tally", "comms"),
    "Brick": ("models/characters/sops_brick.glb", "Brick", "breacher"),
}
ENEMY_MODELS = ["models/characters/sops_greyline_a.glb", "models/characters/sops_greyline_b.glb"]

# Carried weapon placement in character space (+Z forward, +X the character's left). The script
# (scripts/lib/actor.luau) moves it between low-ready and aim and points the muzzle with look_at.
READY = ((-0.07, 1.14, 0.27), (-40, 207, 0))   # muzzle low and slightly inward
GRIP_R = (0.0, -0.035, 0.05)                    # wrist target, weapon space (behind the pistol grip)
GRIP_L = (0.012, -0.05, -0.12)                  # support wrist under the shroud


def _carry(sc: Scene, body, nodes, who, scale=1.0):
    chest = nodes["Chest"]
    carry = sc.add("Carry", {"Transform": transform(READY[0], quat_euler(*READY[1]), (scale,) * 3)}, body,
                   key=f"{sc.name}/{who}/carry")
    sc.prop("Carry Body", W + "pc7_body.glb", parent=carry, shadows=True)
    sc.prop("Carry Cell", W + "pc7_cell.glb", parent=carry, shadows=False)
    gr = sc.add("Grip R", {"Transform": transform(GRIP_R)}, carry, key=f"{sc.name}/{who}/gripr")
    gl = sc.add("Grip L", {"Transform": transform(GRIP_L)}, carry, key=f"{sc.name}/{who}/gripl")
    muzzle = sc.add("Carry Muzzle", {"Transform": transform((0, 0.045, -0.52))}, carry, key=f"{sc.name}/{who}/muzzle")
    pr = sc.add("Pole R", {"Transform": transform((-0.45, -0.3, -0.15))}, chest, key=f"{sc.name}/{who}/poler")
    pl = sc.add("Pole L", {"Transform": transform((0.4, -0.35, 0.05))}, chest, key=f"{sc.name}/{who}/polel")
    for hand, tgt, pole in (("Hand.R", gr, pr), ("Hand.L", gl, pl)):
        sc.add_component(nodes[hand], "IKConstraint", {
            "solver": "two_bone", "enabled": True, "weight": 1.0, "target": tgt, "pole": pole,
            "match_rotation": False, "max_extension": 0.995})
    return carry, muzzle


def _head_ik(sc: Scene, nodes):
    sc.add_component(nodes["Head"], "IKConstraint", {
        "solver": "look_at", "enabled": True, "weight": 0.0, "chain_length": 1, "aim_axis": [0, 0, 1],
        "max_angle": 65, "target_position": [0, 1.6, 10]})


def _voice(sc: Scene, root, name):
    """Spatial voice source at mouth height; scripts/lib/dialogue.luau sets its clip per line."""
    return sc.add("Voice", {"Transform": transform((0, 1.6, 0)),
                            "AudioSource": {"clip": "", "bus": "voice", "volume": 1.0, "pitch": 1.0, "loop": False,
                                            "play_on_start": False, "stream": False, "spatial": True,
                                            "attenuation": "inverse", "min_distance": 2.0, "max_distance": 40.0,
                                            "rolloff": 1.0, "priority": 230, "occlusion": False}},
                  root, key=f"{sc.name}/{name}/voice")


def add_ensemble(sc: Scene):
    """Per-scene dialogue + squad runner and the flat radio voice (HQ, the player, absent speakers)."""
    sc.add("Ensemble", {"Script": script("scripts/ensemble.luau")})
    sc.add("Radio Voice", {"Transform": transform((0, 0, 0)),
                           "AudioSource": {"clip": "", "bus": "voice", "volume": 0.95, "pitch": 1.0, "loop": False,
                                           "play_on_start": False, "stream": False, "spatial": False,
                                           "priority": 240, "occlusion": False}})


def _root(sc: Scene, name, pos, yaw, script_path, props, team, tags, speed=3.2, radius=0.3):
    root = _root_entity(sc, name, pos, yaw, script_path, props, team, tags, speed, radius)
    _voice(sc, root, name)
    return root


# Open-world scenes set this False: any NavAgent makes VICTUS build one navmesh tile over the whole
# scene (terrain plus every streamed tree), so actors there steer themselves (scripts/lib/actor.luau).
USE_NAV = True


def _root_entity(sc: Scene, name, pos, yaw, script_path, props, team, tags, speed, radius):
    comps = {
        "Transform": transform(pos, yaw=yaw),
        "CharacterController": {"radius": radius, "height": 1.76, "max_slope": 48, "step_height": 0.36,
                                "gravity_scale": 1, "mass": 75, "push_force": 60, "air_control": 0.3,
                                "layer": 0, "mask": 65535},
        "NavAgent": {"speed": speed, "acceleration": 9.0, "radius": radius + 0.05, "height": 1.76,
                     "stopping_distance": 0.35, "avoidance": True, "rotate": False, "turn_speed": 360},
        "Perceptible": {"team": team, "height": 1.45, "enabled": True},
        "Tags": {"tags": tags},
        "Script": script(script_path, **props),
    }
    if not USE_NAV:
        del comps["NavAgent"]
    return sc.add(name, comps)


def add_operator(sc: Scene, who, pos, yaw=0.0, armed=True, **props):
    model, _, role = SQUAD[who]
    root = _root(sc, who, pos, yaw, "scripts/operator.luau", dict(props, who=who, role=role), 1, "Squad Operator",
                 speed=3.6)
    sc.add_component(root, "Perception", {"sight_range": 30, "fov": 150, "eye_height": 1.6, "hearing_range": 18,
                                          "memory": 4, "target_mask": 2, "occlusion_mask": 65535,
                                          "line_of_sight": True, "target_key": "target"})
    body = sc.character("Body", model, parent=root, controller=CTRL)
    nodes = sc.last_nodes
    if armed:
        _carry(sc, body, nodes, who)
    _head_ik(sc, nodes)
    return root


def add_enemy(sc: Scene, name, pos, yaw=0.0, variant=0, **props):
    root = _root(sc, name, pos, yaw, "scripts/enemy.luau", props, 2, "Enemy Greyline Scannable", speed=3.0)
    sc.add_component(root, "Perception", {"sight_range": 26, "fov": 120, "eye_height": 1.6, "hearing_range": 16,
                                          "memory": 6, "target_mask": 1, "occlusion_mask": 65535,
                                          "line_of_sight": True, "target_key": "target"})
    body = sc.character("Body", ENEMY_MODELS[variant % len(ENEMY_MODELS)], parent=root, controller=CTRL)
    nodes = sc.last_nodes
    _carry(sc, body, nodes, name)
    _head_ik(sc, nodes)
    return root


def add_npc(sc: Scene, name, model, pos, yaw=0.0, script_path="scripts/npc.luau", **props):
    root = _root(sc, name, pos, yaw, script_path, dict(props, who=name), 4, "NPC Scannable", speed=2.2)
    sc.character("Body", model, parent=root, controller=CTRL)
    _head_ik(sc, sc.last_nodes)
    return root


def add_npc_tracers(sc: Scene, n=8):
    """Shared pool of pulse tracers for NPC fire (scripts/lib/squad.luau reuses them)."""
    for i in range(n):
        sc.prop(f"NPC Tracer {i}", W + "pulse_bolt.glb", pos=(0, -50, 0), shadows=False)
