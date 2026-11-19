# SPDX-License-Identifier: Apache-2.0
"""Writes game/victus.project: window, rendering, startup scene and the logical input actions
shared by keyboard/mouse and gamepad (touch maps onto the same names in controls.luau)."""
import json
from vscene import GAME

AXES = {
    "move_x": (["D", "Right", "Pad.LeftX+"], ["A", "Left", "Pad.LeftX-"]),
    "move_y": (["W", "Up", "Pad.LeftY-"], ["S", "Down", "Pad.LeftY+"]),
    "look_x": (["Pad.RightX+"], ["Pad.RightX-"]),
    "look_y": (["Pad.RightY-"], ["Pad.RightY+"]),
}
BUTTONS = {
    "fire": ["Mouse0", "Pad.RightTrigger"],
    "aim": ["Mouse1", "Pad.LeftTrigger"],
    "reload": ["R", "Pad.West"],
    "switch": ["Q", "Pad.North"],
    "weapon1": ["1"],
    "weapon2": ["2"],
    "interact": ["E", "F", "Pad.East"],
    "tool": ["T", "Pad.DpadUp"],
    "jump": ["Space", "Pad.South"],
    "sprint": ["LeftShift", "Pad.LeftStick"],
    "crouch": ["C", "LeftCtrl", "Pad.RightStick"],
    "pause": ["Escape", "P", "Pad.Start"],
    "objectives": ["Tab", "Pad.Back"],
    "diagnostics": ["F3", "Pad.DpadDown"],
    "skip": ["Space", "Enter", "Pad.South", "Pad.East"],
    "quick_save": ["F5"],
    "quick_load": ["F9"],
    "menu_up": ["Up", "Pad.DpadUp"],
    "menu_down": ["Down", "Pad.DpadDown"],
}


def main():
    actions = []
    for name, (pos, neg) in AXES.items():
        actions.append({"name": name, "positive": pos, "negative": neg, "dead_zone": 0.18})
    for name, b in BUTTONS.items():
        actions.append({"name": name, "bindings": b})
    proj = {
        "format": "victus.project",
        "version": 1,
        "name": "Special Ops",
        "startup_scene": "scenes/menu.vscene",
        "template": "3d",
        "engine_version": "0.2.0",
        "save_version": 1,
        "default_locale": "en",
        "window": {"width": 1600, "height": 720, "vsync": True},
        "rendering": {"quality": "high"},
        "input": {"actions": actions},
    }
    (GAME / "victus.project").write_text(json.dumps(proj, indent=2) + "\n")


if __name__ == "__main__":
    main()
