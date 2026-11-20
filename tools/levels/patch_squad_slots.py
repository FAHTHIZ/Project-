"""Re-seats the squad in the built interior scenes (Op04-Op07) with squad_slots.place, without a full
rebuild (which would also rebake ids the lightmaps and later patches depend on).

    python3 tools/levels/patch_squad_slots.py [--dry]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import squad_slots  # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / 'game' / 'scenes'
SCENES = ('op04_interior', 'op05_bunker', 'op06_basement', 'op07_chamber')
SQUAD = ('Anchor', 'Patch', 'Echo', 'Tally', 'Brick')


def main():
    dry = '--dry' in sys.argv
    for s in SCENES:
        path = ROOT / f'{s}.vscene'
        text = path.read_text()
        data = json.loads(text)
        ents = data['entities']
        player = next(e for e in ents if e.get('name') == 'Player' and e.get('parent') is None)
        pp = tuple(player['components']['Transform']['position'])
        moved = squad_slots.place(ents, pp, SQUAD)
        for n, a, b in moved:
            print(f'{s}: {n} {a} -> {b}')
        if not moved:
            print(f'{s}: squad already clear')
        if moved and not dry:
            indent = 1 if text.startswith('{\n "') else 2
            path.write_text(json.dumps(data, indent=indent) + '\n')


if __name__ == '__main__':
    main()
