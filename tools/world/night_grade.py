# SPDX-License-Identifier: Apache-2.0
"""Storm-night grade, tuned toward the misty-forest reference: deep green mist that stays
luminous enough to silhouette trunks, lifted shadows instead of crushed black, gentle contrast.

    python3 tools/world/night_grade.py      # re-applies GRADE to every night_storm scene

The same values live in tools/scenes/common.py ("night_storm"), so regenerated scenes match.
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRADE = {
    "sky_zenith": [0.012, 0.016, 0.018, 1], "sky_horizon": [0.05, 0.064, 0.058, 1],
    "ground": [0.02, 0.028, 0.02, 1], "ambient_intensity": 0.68,
    "exposure_compensation": 1.75, "saturation": 0.92, "contrast": 1.07,
    "fog_color": [0.045, 0.064, 0.052, 1], "fog_start": 2,
    "volumetric_albedo": [0.7, 0.82, 0.74, 1], "volumetric_ambient": 0.85,
}
OLD_FOG = [[0.03, 0.035, 0.042], [0.05, 0.07, 0.058], GRADE["fog_color"][:3]]


def main():
    n = 0
    for f in glob.glob(os.path.join(ROOT, 'game', 'scenes', '**', '*.vscene'), recursive=True):
        s = json.load(open(f))
        hit = False
        for e in s['entities']:
            env = e['components'].get('Environment')
            if env and env.get('fog_color', [0])[:3] in OLD_FOG and env.get('precipitation') == 'rain':
                env.update(json.loads(json.dumps(GRADE))); hit = True
        if hit:
            raw = open(f).read()
            indent = 1 if raw.startswith('{\n "') else None
            open(f, 'w').write(json.dumps(s, indent=indent) + ('\n' if raw.endswith('\n') else ''))
            n += 1
    print('night grade applied to', n, 'scenes')


if __name__ == '__main__':
    main()
