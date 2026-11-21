#!/usr/bin/env python3
"""Render stills of a cinematic for review: the scene plus scripts/tests/cine_probe.luau holding
the playhead at each requested time.

  python3 tools/test/cine_shots.py <scene> <cinematic id> <t1> [t2 ...]   -> /tmp/cine/<id>_<t>.png
Environment: CINE_W, CINE_H (default 960x420), CINE_FRAMES (frames after the hold, default 40).
"""
import json, os, subprocess, sys, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / 'game'
scene, cid, times = sys.argv[1], sys.argv[2], [float(t) for t in sys.argv[3:]]
W, H = os.environ.get('CINE_W', '960'), os.environ.get('CINE_H', '420')
FR = int(os.environ.get('CINE_FRAMES', '40'))
out = Path('/tmp/cine'); out.mkdir(exist_ok=True)
for t in times:
    doc = json.loads((GAME / scene).read_text())
    doc['entities'].append({'uuid': str(uuid.uuid4()), 'name': 'Cine Probe', 'components': {
        'Transform': {'position': [0, 0, 0], 'rotation': [0, 0, 0, 1], 'scale': [1, 1, 1]},
        'Script': {'script': 'scripts/tests/cine_probe.luau', 'enabled': True, 'properties': {'id': cid, 't': t}}}})
    tmp = GAME / 'scenes/tests/_cine_probe.vscene'
    tmp.write_text(json.dumps(doc))
    png = out / f'{cid}_{t:05.1f}.png'
    r = subprocess.run([str(ROOT / 'tools/test/shot.sh'), 'scenes/tests/_cine_probe.vscene', str(FR), str(png), W, H,
                        os.environ.get('CINE_Q', 'high')], capture_output=True, text=True)
    print(png if r.returncode == 0 else r.stdout[-2000:] + r.stderr[-1000:], flush=True)
    tmp.unlink()
