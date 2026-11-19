# SPDX-License-Identifier: Apache-2.0
"""Dev range: a flat lit test space for the first-person controller, weapons and AI.
Writes scenes/dev_range.vscene and the autotest variants under scenes/tests/."""
from __future__ import annotations

import sys

from vscene import Scene, GROUND_MATERIAL, collider, body, script, transform
from common import environment, sun, autotest
import rig
import actors
import vehicle


TARGETS = [(0, -6), (-5, -12), (5, -12), (-9, -22), (0, -26), (9, -22)]


def add_target(sc, name, pos, yaw=0.0, reset=3.0, group=""):
    """Kinematic collider (plate + head) on the root so the fold-back moves the hit volume."""
    root = sc.add(name, {"Transform": transform(pos, yaw=yaw),
                         "Collider": collider("box", (0.46, 0.98, 0.08), offset=(0, 1.38, 0)),
                         "RigidBody": body("kinematic"), "Tags": {"tags": "Target Scannable"},
                         "Script": script("scripts/range_target.luau", reset_time=reset, group=group)})
    sc.prop(name + " Model", "models/weapons/stun_target.glb", parent=root)
    return root


# Plans that place the Halyard Team, Greyline contractors and Ranger Hollis on the range.
SQUAD_PLANS = {"squad", "squad_combat", "enemy_fire", "squad_look"}


def add_squad_setup(sc, plan):
    actors.add_ensemble(sc)
    actors.add_npc_tracers(sc)
    if plan != "enemy_fire":
        for who, (x, z) in (("Anchor", (-1.7, 8.0)), ("Patch", (1.6, 8.6)), ("Echo", (-3.0, 9.6)), ("Tally", (2.6, 10.4))):
            actors.add_operator(sc, who, (x, 0, z), 180.0 if plan == "squad_look" else 0.0)
    if plan == "squad":
        actors.add_npc(sc, "Hollis", "models/characters/sops_ranger.glb", (8, 0, 4), -90.0, who="hollis",
                       prompt="Talk", event="talk_hollis")
    if plan == "squad_combat":
        actors.add_enemy(sc, "Greyline 1", (-8, 0, -8), 0.0, variant=0, voice="greyline1", group="range", alert=True)
        actors.add_enemy(sc, "Greyline 2", (8, 0, -8), 0.0, variant=1, voice="greyline2", group="range", alert=True)
    if plan == "enemy_fire":
        actors.add_enemy(sc, "Greyline 1", (3, 0, -3), -20.0, variant=0, voice="greyline1")


# Vehicle plans: the Mule on the open north side of the range.
VEHICLE_PLANS = {"vehicle", "trunk", "sniper", "vehicle_look", "trunk_look", "scope_look"}
SEATS = (("Anchor", "driver"), ("Patch", "front_right"), ("Echo", "rear_left"), ("Tally", "rear_right"))


def add_vehicle_setup(sc, plan):
    if plan in ("vehicle", "vehicle_look"):
        vehicle.add_vehicle(sc, "Mule", (-16, 0, 28), -90.0, cargo=["marksman", "field_kit", "cell_pack", "cell_pack"])
        actors.add_ensemble(sc)
        actors.add_npc_tracers(sc)
        for who, seat in SEATS:
            actors.add_operator(sc, who, (-16, 0, 36), -90.0, order="hold", ride="Mule", seat=seat)
    else:
        vehicle.add_vehicle(sc, "Mule", (0, 0, 16), 0.0, cargo=["marksman", "field_kit", "cell_pack", "cell_pack"])


def build(plan=None):
    name = "Dev Range" if not plan else f"Test {plan}"
    sc = Scene(name)
    environment(sc, "range")
    sun(sc)
    sc.box("Ground", (0, -0.1, 0), (80, 0.2, 80), (0.62, 0.64, 0.6), material=GROUND_MATERIAL)
    # Walls, cover blocks and a ramp to exercise collision and steps.
    for i, (x, z, w, d, h) in enumerate([(0, -30, 40, 1, 3), (-20, -10, 1, 40, 3), (20, -10, 1, 40, 3),
                                         (-6, -14, 3, 1, 1.2), (6, -14, 3, 1, 1.2), (0, -20, 4, 1, 1.4)]):
        sc.box(f"Wall {i}", (x, h / 2, z), (w, h, d), (0.5, 0.52, 0.55))
    for i in range(4):
        sc.box(f"Step {i}", (-10, 0.15 + i * 0.3, -4 - i * 0.9), (3, 0.3 + i * 0.6, 0.9), (0.55, 0.5, 0.45))
    # Pop-up stun targets at several distances (scripts/range_target.luau).
    for i, (x, z) in enumerate(TARGETS):
        add_target(sc, f"Target {i}", (x, 0, z))
    if plan in SQUAD_PLANS:
        add_squad_setup(sc, plan)
    if plan in VEHICLE_PLANS:
        add_vehicle_setup(sc, plan)
    ppos = {"trunk": (0, 0, 20.6), "trunk_look": (0, 0, 20.4), "vehicle": (-4, 0, 12), "vehicle_look": (-12.6, 0, 31.4)}.get(plan, (0, 0, 6))
    rig.add_player(sc, ppos, 0, with_weapons=True)
    rig.add_hud(sc)
    if plan:
        autotest(sc, plan)
        return sc.save(f"scenes/tests/{plan}.vscene")
    return sc.save("scenes/dev_range.vscene")


if __name__ == "__main__":
    build()
    for p in sys.argv[1:] or []:
        build(p)
