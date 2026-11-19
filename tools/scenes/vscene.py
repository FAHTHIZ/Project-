# SPDX-License-Identifier: Apache-2.0
"""Scene-building library for SPECIAL OPS.

Writes VICTUS `.vscene` JSON (format "victus.scene" version 1) from Python. UUIDs are derived
from names with uuid5 so regenerating a scene gives identical files and stable references.

Model instancing mirrors VICTUS `engine/assets/src/instantiate.cpp`: a root entity, then one
child entity per glTF node in depth-first pre-order from the scene roots with the node's TRS;
a mesh node with one primitive gets a MeshRenderer (and SkinnedMesh when skinned), nodes with
several primitives get one child per primitive named "Name[i]". Cooked mesh indices number the
primitives across all meshes in file order.
"""
from __future__ import annotations

import json
import math
import struct
import uuid
from pathlib import Path

NS = uuid.UUID("5e3c1f0a-7b2d-4c11-9f6e-50b5a0c0e001")
GAME = Path(__file__).resolve().parents[2] / "game"
ASSETS = GAME / "assets"
GROUND_MATERIAL = "5c0a7e11-7f1b-4c2e-9a3d-c4a7e5b0f003"  # template ground.vmat


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


# ---- maths ---------------------------------------------------------------------------------

def quat_euler(pitch=0.0, yaw=0.0, roll=0.0):
    """Quaternion (x, y, z, w) from Euler degrees applied yaw (Y), then pitch (X), then roll (Z)."""
    def axis(ax, deg):
        h = math.radians(deg) / 2
        s = math.sin(h)
        return [ax[0] * s, ax[1] * s, ax[2] * s, math.cos(h)]

    def mul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return [aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
                aw * bw - ax * bx - ay * by - az * bz]

    q = mul(mul(axis((0, 1, 0), yaw), axis((1, 0, 0), pitch)), axis((0, 0, 1), roll))
    return [round(v, 7) for v in q]


def look_rotation(src, dst):
    """Rotation that points -Z (camera forward) from src to dst."""
    dx, dy, dz = (dst[0] - src[0], dst[1] - src[1], dst[2] - src[2])
    yaw = math.degrees(math.atan2(-dx, -dz))
    pitch = math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    return quat_euler(pitch, yaw, 0)


def transform(pos=(0, 0, 0), rot=None, scale=(1, 1, 1), yaw=None):
    if rot is None:
        rot = quat_euler(0, yaw or 0, 0)
    if isinstance(scale, (int, float)):
        scale = (scale, scale, scale)
    return {"position": [round(float(v), 4) for v in pos], "rotation": list(rot), "scale": [float(v) for v in scale]}


# ---- components ----------------------------------------------------------------------------

def collider(shape="box", size=(1, 1, 1), radius=0.5, height=1.0, offset=(0, 0, 0), trigger=False, layer=0,
             mask=65535, mesh_asset=None, mesh_index=0, friction=0.6):
    c = {"shape": shape, "size": list(size), "radius": radius, "height": height, "offset": list(offset),
         "friction": friction, "restitution": 0, "is_trigger": trigger, "layer": layer, "mask": mask,
         "mesh_asset": mesh_asset, "mesh_index": mesh_index}
    return c


def body(kind="static", mass=1.0):
    return {"type": kind, "mass": mass, "linear_damping": 0.05, "angular_damping": 0.05, "gravity_scale": 1,
            "continuous": False, "lock_rotation": False, "start_awake": True, "linear_velocity": [0, 0, 0],
            "angular_velocity": [0, 0, 0]}


def mesh_renderer(primitive=None, color=(1, 1, 1, 1), metallic=0.0, roughness=0.8, material=None, mesh=None,
                  mesh_index=0, shadows=True, visible=True):
    m = {"base_color": list(color) + [1] * (4 - len(color)), "metallic": metallic, "roughness": roughness,
         "cast_shadows": shadows, "visible": visible}
    if primitive:
        m["primitive"] = primitive
    if mesh:
        m["mesh"] = mesh
        m["mesh_index"] = mesh_index
    if material:
        m["material"] = material
    return m


def script(path, **props):
    return {"script": path, "enabled": True, "properties": props}


# ---- UI ------------------------------------------------------------------------------------

def ui_rect(anchor=(0.5, 0.5), pos=(0, 0), size=(100, 40), pivot=None, anchor_max=None, visible=True, opacity=1.0):
    """Layouts here are authored y-up (0,0 = bottom-left, +y up); VICTUS UiRect is y-down from the
    top-left, so the vertical axis is mirrored on the way out."""
    amin = list(anchor)
    amax = list(anchor_max or anchor)
    pv = list(pivot or anchor)
    return {"anchor_min": [amin[0], 1 - amax[1]], "anchor_max": [amax[0], 1 - amin[1]], "pivot": [pv[0], 1 - pv[1]],
            "position": [pos[0], -pos[1]], "size": list(size), "visible": visible, "opacity": opacity,
            "clip_children": False}


def ui_panel(color=(0.05, 0.06, 0.07, 0.6), radius=8, border=(1, 1, 1, 0.12), border_width=1.0):
    return {"color": list(color), "corner_radius": radius, "border_color": list(border), "border_width": border_width}


def ui_text(text="", size=22, color=(1, 1, 1, 1), align="center", valign="middle", bold=False, wrap=False, key=""):
    return {"text": text, "key": key, "font_size": size, "color": list(color), "align": align,
            "vertical_align": valign, "wrap": wrap, "bold": bold, "shadow_color": [0, 0, 0, 0.55],
            "shadow_offset": [0, 2], "font": ""}


def ui_button(action, normal=(0.12, 0.14, 0.16, 0.85), hovered=(0.2, 0.24, 0.27, 0.92),
              pressed=(0.08, 0.09, 0.1, 1)):
    return {"interactable": True, "action": action, "normal": list(normal), "hovered": list(hovered),
            "pressed": list(pressed), "disabled": [0.2, 0.2, 0.22, 0.5]}


# ---- glTF ----------------------------------------------------------------------------------

def read_glb_json(path):
    b = Path(path).read_bytes()
    assert b[:4] == b"glTF", path
    jl = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + jl])


def meta_uuid(rel):
    """UUID from the asset's .meta (written by `victus import`)."""
    meta = ASSETS / (rel + ".meta")
    if not meta.exists():
        raise SystemExit(f"{meta} missing: run `victus import game` after generating assets")
    return json.loads(meta.read_text())["uuid"]


_glb_cache = {}


def glb_info(rel):
    if rel not in _glb_cache:
        _glb_cache[rel] = read_glb_json(ASSETS / rel)
    return _glb_cache[rel]


# ---- scene ---------------------------------------------------------------------------------

class Scene:
    def __init__(self, name):
        self.name = name
        self.entities = []
        self._names = set()

    def add(self, name, components, parent=None, key=None):
        key = key or f"{self.name}/{parent or ''}/{name}"
        u = uid(key)
        assert u not in self._names, f"duplicate entity key {key}"
        self._names.add(u)
        comps = dict(components)
        comps.setdefault("Transform", transform())
        e = {"uuid": u, "name": name, "components": comps}
        if parent:
            e["parent"] = parent
        self.entities.append(e)
        return u

    # A static or dynamic prop from a single-node glb (one child per primitive).
    def prop(self, name, rel, pos=(0, 0, 0), yaw=0.0, scale=1.0, rot=None, parent=None, col=None, tags=None,
             shadows=True, extra=None, kind="static"):
        model = meta_uuid(rel)
        j = glb_info(rel)
        comps = {"Transform": transform(pos, rot, scale, yaw)}
        if col:
            comps["Collider"] = col
            comps["RigidBody"] = body(kind, 20.0)
        if tags:
            comps["Tags"] = {"tags": tags if isinstance(tags, str) else " ".join(tags)}
        if extra:
            comps.update(extra)
        root = self.add(name, comps, parent)
        index = 0
        for mi, m in enumerate(j["meshes"]):
            for pi, _ in enumerate(m["primitives"]):
                self.add(f"{name}[{index}]", {"MeshRenderer": mesh_renderer(mesh=model, mesh_index=index, shadows=shadows,
                                                                            roughness=0.85)}, root)
                index += 1
        return root

    # A skinned character from a multi-node glb, mirroring instantiate.cpp.
    def character(self, name, rel, pos=(0, 0, 0), yaw=0.0, scale=1.0, parent=None, controller=None, clip="Idle",
                  root_motion=False, components=None):
        model = meta_uuid(rel)
        j = glb_info(rel)
        comps = {"Transform": transform(pos, None, scale, yaw),
                 "Animator": {"model": model, "clip_source": None, "clip": clip, "controller": controller or "",
                              "playing": True, "loop": True, "speed": 1, "crossfade": 0.2, "time": 0,
                              "apply_root_motion": root_motion}}
        if components:
            comps.update(components)
        root = self.add(name, comps, parent)
        prim_base = []
        n = 0
        for m in j["meshes"]:
            prim_base.append(n)
            n += len(m["primitives"])
        nodes = j["nodes"]

        def visit(ni, parent_uuid, path):
            nd = nodes[ni]
            nm = nd.get("name", f"node{ni}")
            t = {"position": [float(v) for v in nd.get("translation", [0, 0, 0])],
                 "rotation": [float(v) for v in nd.get("rotation", [0, 0, 0, 1])],
                 "scale": [float(v) for v in nd.get("scale", [1, 1, 1])]}
            c = {"Transform": t}
            prims = j["meshes"][nd["mesh"]]["primitives"] if "mesh" in nd else []
            skinned = "skin" in nd
            if len(prims) == 1:
                c["MeshRenderer"] = mesh_renderer(mesh=model, mesh_index=prim_base[nd["mesh"]], roughness=0.6)
                if skinned:
                    c["SkinnedMesh"] = {"skeleton": root, "skin": nd["skin"]}
            me = self.add(nm, c, parent_uuid, key=f"{self.name}/{name}/{path}/{nm}")
            if len(prims) > 1:
                for i in range(len(prims)):
                    cc = {"MeshRenderer": mesh_renderer(mesh=model, mesh_index=prim_base[nd["mesh"]] + i, roughness=0.6)}
                    if skinned:
                        cc["SkinnedMesh"] = {"skeleton": root, "skin": nd["skin"]}
                    self.add(f"{nm}[{i}]", cc, me, key=f"{self.name}/{name}/{path}/{nm}[{i}]")
            for ch in nd.get("children", []):
                visit(ch, me, f"{path}/{nm}")

        for r in j["scenes"][j.get("scene", 0)]["nodes"]:
            visit(r, root, "")
        return root

    def box(self, name, pos, size, color, parent=None, yaw=0.0, rot=None, roughness=0.85, metallic=0.0,
            collide=True, material=None, shadows=True, primitive="cube"):
        comps = {"Transform": transform(pos, rot, size, yaw),
                 "MeshRenderer": mesh_renderer(primitive, color, metallic, roughness, material, shadows=shadows)}
        if collide:
            shape = {"cube": "box", "cylinder": "cylinder", "sphere": "sphere"}[primitive]
            comps["Collider"] = collider(shape)
            comps["RigidBody"] = body("static")
        return self.add(name, comps, parent)

    def trigger(self, name, pos, size, script_path=None, parent=None, **props):
        comps = {"Transform": transform(pos), "Collider": collider("box", size, trigger=True),
                 "RigidBody": body("static")}
        if script_path:
            comps["Script"] = script(script_path, **props)
        return self.add(name, comps, parent)

    def light(self, name, pos, kind="point", color=(1, 0.85, 0.65), intensity=4.0, rng=10.0, shadows=False,
              rot=None, inner=25.0, outer=40.0, parent=None):
        l = {"type": kind, "color": list(color) + [1], "intensity": intensity, "range": rng, "shadows": shadows}
        if kind == "spot":
            l["inner_angle"] = inner
            l["outer_angle"] = outer
        return self.add(name, {"Transform": transform(pos, rot), "Light": l}, parent)

    def save(self, rel):
        path = GAME / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"format": "victus.scene", "version": 1, "name": self.name, "entities": self.entities}
        path.write_text(json.dumps(data, indent=1) + "\n")
        return path


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_meta(path, guid, importer=""):
    meta = Path(str(path) + ".meta")
    if not meta.exists():
        write_json(meta, {"victus_meta": 1, "uuid": guid, "importer": importer})
