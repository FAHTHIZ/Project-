# SPDX-License-Identifier: Apache-2.0
"""Storm-night grade: neutral blue-grey rain mist (v3, replaces the green mist) that stays luminous
enough to silhouette trunks, a slightly stronger moon key and more contrast, matched to real rainy
night body-cam footage rather than a tinted look.

    python3 tools/world/night_grade.py      # re-applies GRADE to every night_storm scene

The same values live in tools/scenes/common.py ("night_storm"), so regenerated scenes match.
"""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GRADE = {
    "sky_zenith": [0.011, 0.014, 0.02, 1], "sky_horizon": [0.045, 0.054, 0.066, 1],
    "ground": [0.02, 0.024, 0.021, 1], "ambient_intensity": 0.68,
    "exposure_compensation": 1.75, "saturation": 0.86, "contrast": 1.12,
    "fog_color": [0.044, 0.054, 0.064, 1], "fog_start": 2,
    "volumetric_albedo": [0.76, 0.8, 0.86, 1], "volumetric_ambient": 0.85,
    "precipitation_brightness": 1.1,
}
OLD_FOG = [[0.03, 0.035, 0.042], [0.05, 0.07, 0.058], [0.045, 0.064, 0.052], GRADE["fog_color"][:3]]
MOON = 0.42


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
            for e in s['entities']:
                l = e['components'].get('Light')
                if e['name'] == 'Moon' and l and l.get('type') == 'directional':
                    l['intensity'] = MOON
        if hit:
            raw = open(f).read()
            indent = 1 if raw.startswith('{\n "') else None
            open(f, 'w').write(json.dumps(s, indent=indent) + ('\n' if raw.endswith('\n') else ''))
            n += 1
    print('night grade applied to', n, 'scenes')


if __name__ == '__main__':
    main()
