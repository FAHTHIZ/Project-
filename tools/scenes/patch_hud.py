# SPDX-License-Identifier: Apache-2.0
"""Re-emits the HUD and pause/settings canvases in every existing scene from rig.add_hud().

Operation worlds take a long time to regenerate (terrain, scatter, glTF instancing), and the HUD
does not depend on any of it. This replaces the "HUD" and "Pause Menu" subtrees in place with the
entities a fresh Scene(<same name>) + rig.add_hud() produces. Entity UUIDs are derived from
"<scene>/<parent>/<name>" keys (vscene.py), so the result is identical to a full regeneration.
Entities under those subtrees that add_hud() does not create (added by a scene builder after the
fact) are kept with their parents.

    python3 tools/scenes/patch_hud.py            # every scene under game/scenes
    python3 tools/scenes/patch_hud.py --check    # report scenes whose HUD is out of date
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vscene import Scene, GAME  # noqa: E402
import rig  # noqa: E402

ROOTS = ("HUD", "Pause Menu")


def subtree(entities, root_ids):
    ids = set(root_ids)
    changed = True
    while changed:
        changed = False
        for e in entities:
            if e.get("parent") in ids and e["uuid"] not in ids:
                ids.add(e["uuid"])
                changed = True
    return ids


def patch(path: Path, check=False):
    data = json.loads(path.read_text())
    ents = data["entities"]
    roots = [e["uuid"] for e in ents if e["name"] in ROOTS and not e.get("parent")
             and (e["name"] != "HUD" or "scripts/hud.luau" in json.dumps(e["components"].get("Script", {})))]
    if not any(e["name"] == "HUD" for e in ents if e["uuid"] in roots):
        return None
    old = subtree(ents, roots)
    sc = Scene(data["name"])
    rig.add_hud(sc)
    fresh = sc.entities
    fresh_ids = {e["uuid"] for e in fresh}
    # keep foreign children (not produced by add_hud) whose parent still exists
    keep = [e for e in ents if e["uuid"] in old and e["uuid"] not in fresh_ids and e.get("parent") in fresh_ids | old
            and e["uuid"] not in roots and not _generated_name(e["name"])]
    first = min(i for i, e in enumerate(ents) if e["uuid"] in old)
    rest = [e for e in ents if e["uuid"] not in old]
    out = rest[:first] + fresh + keep + rest[first:]
    if out == ents:
        return False
    if check:
        return True
    data["entities"] = out
    path.write_text(json.dumps(data, indent=1) + "\n")
    return True


_known = None


def _generated_name(name):
    """Names add_hud() ever produced (old layouts included) are dropped, not kept as foreign."""
    global _known
    if _known is None:
        sc = Scene("__probe__")
        rig.add_hud(sc)
        _known = {e["name"] for e in sc.entities} | {"Health Back", "Health Bar", "Objective Op", "Objective Text"}
    return name in _known


def main():
    check = "--check" in sys.argv
    paths = [Path(a) for a in sys.argv[1:] if not a.startswith("--")] or sorted((GAME / "scenes").rglob("*.vscene"))
    n = 0
    for p in paths:
        r = patch(p, check)
        if r:
            n += 1
            print(("stale " if check else "patched ") + str(p.relative_to(GAME)))
    print(f"{n} scene(s) {'stale' if check else 'patched'}")
    return 1 if (check and n) else 0


if __name__ == "__main__":
    sys.exit(main())
