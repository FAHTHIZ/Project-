# SPDX-License-Identifier: Apache-2.0
"""Scene assembly for the HT-4 "Mule" squad transport (art: tools/props/build_vehicle.py).

Entity contract (read by scripts/vehicle.luau and lib/storage.luau):

  <name>                     Transform (ground, centre of wheelbase), kinematic RigidBody,
                             vehicle.luau, AudioSource (engine loop, spatial)
    <name> Body / Glass      models
    <name> Hull / Cabin      box colliders (layer VEHICLE_LAYER)
    <name> Door FL|FR|RL|RR  hinge pivots -> door model + door glass
    <name> Hatch             hinge pivot -> hatch model + hatch glass
    <name> Wheel FL|...      steer pivots -> "<...> Spin" -> wheel model
    <name> Steering          steering wheel pivot
    <name> Seat <seat>       empty markers at each hip point (driver, front_right, rear_*)
    <name> Exit <door>       ground markers just outside each door (where occupants stand up to)
    <name> Cargo             storage root (lib/storage.luau): "Cargo Slot <n>" anchors
    <name> Door Sfx / Hatch Sfx   one-shot spatial sources
"""
from __future__ import annotations

import json
import os

from vscene import Scene, transform, collider, body, script, quat_euler

HERE = os.path.dirname(__file__)
V = "models/vehicle/"
GLASS_MAT = "materials/vehicle_glass.vmat"
VEHICLE_LAYER = 6


def layout():
    with open(os.path.join(HERE, "vehicle_layout.json")) as f:
        return json.load(f)


# World models and pick volumes (size, centre height) for items that can sit in storage.
ITEM_WORLD = {
    "carbine": ("models/weapons/pc7_world.glb", (0.12, 0.1, 0.75)),
    "marksman": ("models/weapons/lr4_world.glb", (0.12, 0.1, 1.0)),
    "sidearm": ("models/weapons/sp2_world.glb", (0.1, 0.06, 0.24)),
    "field_kit": ("models/props/field_kit.glb", (0.32, 0.16, 0.22)),
    "cell_pack": ("models/props/cell_pack.glb", (0.16, 0.14, 0.08)),
}


def add_storage_pool(sc: Scene, storage_name, parent, ids):
    """Pre-placed (parked out of sight) world items a storage container can show: one entity per
    possible item instance, so items moving in and out never spawn or delete entities."""
    count = {}
    for iid in ids:
        count[iid] = count.get(iid, 0) + 1
        rel, size = ITEM_WORLD[iid]
        e = sc.add(f"{storage_name} Item {iid} {count[iid]}", {
            "Transform": transform((0, -20, 0)), "RigidBody": body("kinematic"),
            "Collider": collider("box", size, offset=(0, size[1] / 2, 0), layer=VEHICLE_LAYER)}, parent)
        sc.prop(f"{storage_name} Item {iid} {count[iid]} Model", rel, parent=e)


def add_vehicle(sc: Scene, name, pos, yaw, cargo=None, pool_extra=("carbine", "sidearm"), hatch_prompt="Open hatch",
                driving=False):
    L = layout()
    root = sc.add(name, {
        "Transform": transform(pos, yaw=yaw),
        "AudioSource": {"clip": "audio/vehicle/engine_idle.wav", "bus": "sfx", "volume": 0.0, "pitch": 1.0,
                        "loop": True, "play_on_start": True, "spatial": True, "attenuation": "inverse",
                        "min_distance": 4.0, "max_distance": 60.0, "rolloff": 1.0, "priority": 200},
        "Tags": {"tags": "Vehicle"},
        "Script": script("scripts/vehicle.luau", running=driving, hatch_prompt=hatch_prompt),
    })
    # Chassis: everything sprung (body, doors, hatch, seats, cargo). vehicle.luau pitches and rolls
    # it for weight transfer and the settle after stopping; wheels and colliders stay on the root.
    ch = sc.add(f"{name} Chassis", {"Transform": transform()}, root)
    sc.prop(f"{name} Body", V + "mule_body.glb", parent=ch)
    sc.prop(f"{name} Glass", V + "mule_glass.glb", parent=ch, shadows=False, material=GLASS_MAT)
    # Collision (kinematic, follows the vehicle): nose + cabin block, the cargo bay as floor, walls
    # and roof so items inside stay reachable by look rays when the hatch is open, and the hatch.
    def col(nm, centre, size, parent=root):
        return sc.add(f"{name} {nm}", {"Transform": transform(centre), "RigidBody": body("kinematic"),
                                       "Collider": collider("box", size, layer=VEHICLE_LAYER)}, parent)
    col("Hull", (0, 0.78, -0.7), (1.96, 0.76, 3.6))
    col("Cabin", (0, 1.53, 0.02), (1.94, 0.74, 2.16))
    col("Bay Floor", (0, 0.57, 1.8), (1.96, 0.34, 1.4))
    col("Bay Left", (-0.93, 1.32, 1.75), (0.08, 1.16, 1.3))
    col("Bay Right", (0.93, 1.32, 1.75), (0.08, 1.16, 1.3))
    col("Bay Roof", (0, 1.9, 1.75), (1.94, 0.1, 1.3))
    for key, d in L["doors"].items():
        hp = sc.add(f"{name} Door {key.upper()}", {"Transform": transform(tuple(d["hinge"]))}, ch)
        sc.prop(f"{name} Door {key.upper()} Model", V + f"mule_door_{key}.glb", parent=hp)
        gx = -0.035 if key.endswith("l") else 0.035
        sc.prop(f"{name} Door {key.upper()} Glass", V + "mule_door_glass.glb", (-gx, 0, 0), parent=hp, shadows=False,
                material=GLASS_MAT)
        out = 1 if key.endswith("r") else -1
        hx, _, hz = d["hinge"]
        sc.add(f"{name} Exit {key}", {"Transform": transform((hx + out * 0.62, 0, hz + d["len"] * 0.62))}, root)
    hh = sc.add(f"{name} Hatch", {"Transform": transform(tuple(L["hatch_hinge"]))}, ch)
    sc.add(f"{name} Hatch Collider", {"Transform": transform((0, -0.58, 0.02)), "RigidBody": body("kinematic"),
                                      "Collider": collider("box", (1.7, 1.16, 0.08), layer=VEHICLE_LAYER)}, hh)
    sc.prop(f"{name} Hatch Model", V + "mule_hatch.glb", parent=hh)
    sc.prop(f"{name} Hatch Glass", V + "mule_hatch_glass.glb", parent=hh, shadows=False, material=GLASS_MAT)
    r = L["wheel_radius"]
    for key, x, z in (("FL", -L["wheel_x"], L["front_axle_z"]), ("FR", L["wheel_x"], L["front_axle_z"]),
                      ("RL", -L["wheel_x"], L["rear_axle_z"]), ("RR", L["wheel_x"], L["rear_axle_z"])):
        st = sc.add(f"{name} Wheel {key}", {"Transform": transform((x, r, z))}, root)
        sp = sc.add(f"{name} Wheel {key} Spin", {"Transform": transform()}, st)
        sc.prop(f"{name} Wheel {key} Model", V + "mule_wheel.glb", parent=sp)
    s = L["steering"]
    sw = sc.add(f"{name} Steering", {"Transform": transform(tuple(s), quat_euler(-22, 0, 0))}, ch)
    sc.prop(f"{name} Steering Model", V + "mule_steering.glb", parent=sw)
    for seat, d in L["seats"].items():
        sc.add(f"{name} Seat {seat}", {"Transform": transform(tuple(d["pos"]))}, ch)
    for nm in ("Door Sfx", "Hatch Sfx"):
        sc.add(f"{name} {nm}", {"Transform": transform((0, 1.0, 0)), "AudioSource": {
            "clip": "audio/vehicle/door_open.wav", "bus": "sfx", "volume": 0.9, "loop": False, "play_on_start": False,
            "spatial": True, "min_distance": 2.0, "max_distance": 35.0}}, root)
    sc.add(f"{name} Tyres", {"Transform": transform((0, 0.3, 0)), "AudioSource": {
        "clip": "audio/vehicle/tyre_roll.wav", "bus": "sfx", "volume": 0.0, "loop": True, "play_on_start": True,
        "spatial": True, "min_distance": 3.0, "max_distance": 45.0}}, root)
    # Cargo storage: anchors on the bay floor (vehicle frame), filled by lib/storage.luau.
    cy = L["cargo_floor_y"] + 0.03
    cz0, cz1 = L["cargo_z"]
    cargo_root = sc.add(f"{name} Cargo", {"Transform": transform((0, cy, 0)), "Tags": {"tags": "Storage"},
                                          "Script": script("scripts/storage.luau", id=f"{name}_cargo",
                                                           contents=",".join(cargo or []))}, ch)
    # Long slots hold rifles across the bay (nearest the hatch first); small slots line the front.
    slots = [("L1", 0.05, 2.12, 90), ("L2", 0.05, 1.8, 90), ("S1", -0.5, 1.42, 0), ("S2", -0.04, 1.42, 0),
             ("S3", 0.44, 1.42, 0)]
    for nm, x, z, ry in slots:
        sc.add(f"{name} Cargo Slot {nm}", {"Transform": transform((x, 0, z), yaw=ry)}, cargo_root)
    # Dressing that stays in the bay: Patch's medical bag and a coiled tow strap.
    sc.prop(f"{name} Cargo Bag", "models/env/abandoned_pack.glb", (-0.68, 0, 1.98), yaw=-80, parent=cargo_root,
            scale=0.8)
    add_storage_pool(sc, f"{name} Cargo", cargo_root, list(cargo or []) + list(pool_extra))
    return root
