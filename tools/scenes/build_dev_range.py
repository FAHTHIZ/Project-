# SPDX-License-Identifier: Apache-2.0
"""Dev range: a flat lit test space for the first-person controller, weapons and AI.
Writes scenes/dev_range.vscene and the autotest variants under scenes/tests/."""
from __future__ import annotations

import sys

from vscene import Scene, GROUND_MATERIAL, collider, body, script, transform
from common import environment, sun, autotest
import rig


TARGETS = [(0, -6), (-5, -12), (5, -12), (-9, -22), (0, -26), (9, -22)]


def add_target(sc, name, pos, yaw=0.0, reset=3.0, group=""):
    """Kinematic collider (plate + head) on the root so the fold-back moves the hit volume."""
    root = sc.add(name, {"Transform": transform(pos, yaw=yaw),
                         "Collider": collider("box", (0.46, 0.98, 0.08), offset=(0, 1.38, 0)),
                         "RigidBody": body("kinematic"), "Tags": {"tags": "Target Scannable"},
                         "Script": script("scripts/range_target.luau", reset_time=reset, group=group)})
    sc.prop(name + " Model", "models/weapons/stun_target.glb", parent=root)
    return root


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
    rig.add_player(sc, (0, 0, 6), 0, with_weapons=True)
    rig.add_hud(sc)
    if plan:
        autotest(sc, plan)
        return sc.save(f"scenes/tests/{plan}.vscene")
    return sc.save("scenes/dev_range.vscene")


if __name__ == "__main__":
    build()
    for p in sys.argv[1:]:
        build(p)
