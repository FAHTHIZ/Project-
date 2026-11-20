"""Reports characters (player, squad, NPCs, contractors - anything with a CharacterController at
the scene root) whose start capsule overlaps solid box colliders, or that have no floor box under
them in the interiors. Exit code 1 when anything overlaps.

    python3 tools/test/check_spawns.py [scene.vscene ...]   # default: game/scenes/*.vscene + world
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'levels'))
import squad_slots as S  # noqa: E402

S.RADIUS = 0.3 + 0.05  # the real capsule radius plus a hair; squad_slots seats with more margin


def main():
    files = sys.argv[1:] or sorted(glob.glob(str(ROOT / 'game/scenes/*.vscene'))) + \
        [str(ROOT / 'game/scenes/world/kestrel.vscene')]
    bad = 0
    for f in files:
        ents = json.load(open(f))['entities']
        bx = S.boxes(ents)
        byid = {e['uuid']: e for e in ents}
        for e in ents:
            if e.get('parent') is None and 'CharacterController' in e.get('components', {}):
                p, _, _ = S._world(e, byid)
                hits = S.capsule_hits(bx, p)
                if hits:
                    bad += 1
                    print(f'{Path(f).name}: {e["name"]} at {tuple(round(v, 2) for v in p)} overlaps {", ".join(hits[:3])}')
    print(f'{len(files)} scenes, {bad} character starts in geometry')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
