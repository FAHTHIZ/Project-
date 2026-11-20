# SPDX-License-Identifier: Apache-2.0
"""Fetch CC0 source assets from Poly Haven (https://polyhaven.com, licence: CC0 1.0).

    python3 tools/assets/polyhaven.py texture brown_mud_leaves_01 --res 2k
    python3 tools/assets/polyhaven.py model rock_moss_set_01 --res 1k

Downloads go to `.cache/polyhaven/<id>/<res>/` (git-ignored). Nothing here is shipped as-is: the
build scripts in tools/assets/ resize, pack and convert the sources into game assets, and each
shipped asset is listed in docs/ASSET_PROVENANCE.md with its Poly Haven id.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, '.cache', 'polyhaven')
API = 'https://api.polyhaven.com'
UA = {'User-Agent': 'special-ops-asset-build/1.0 (github.com/FAHTHIZ/Project-)'}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _fetch(url: str, dest: str, md5: str | None = None) -> str:
    if os.path.exists(dest) and (md5 is None or hashlib.md5(open(dest, 'rb').read()).hexdigest() == md5):
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    data = _get(url)
    if md5 and hashlib.md5(data).hexdigest() != md5:
        raise RuntimeError(f'md5 mismatch for {url}')
    with open(dest + '.part', 'wb') as f:
        f.write(data)
    os.replace(dest + '.part', dest)
    return dest


def files(asset: str) -> dict:
    return json.loads(_get(f'{API}/files/{asset}'))


def info(asset: str) -> dict:
    return json.loads(_get(f'{API}/info/{asset}'))


# Texture maps are returned by role so callers do not depend on Poly Haven's key spelling.
TEX_KEYS = {'diff': 'Diffuse', 'nor': 'nor_gl', 'rough': 'Rough', 'disp': 'Displacement', 'ao': 'AO', 'arm': 'arm'}


def texture(asset: str, res: str = '2k', fmt: str = 'png', maps=('diff', 'nor', 'rough', 'disp', 'ao')) -> dict:
    """Download the texture maps of a Poly Haven texture asset; returns {role: path}."""
    f = files(asset)
    out = {}
    for role in maps:
        key = TEX_KEYS[role]
        if key not in f or res not in f[key]:
            continue
        entry = f[key][res].get(fmt) or f[key][res].get('jpg')
        dest = os.path.join(CACHE, asset, res, os.path.basename(entry['url']))
        out[role] = _fetch(entry['url'], dest, entry.get('md5'))
    return out


def model(asset: str, res: str = '1k') -> str:
    """Download the glTF (+bin, +textures at RES) of a Poly Haven model; returns the .gltf path."""
    f = files(asset)
    g = f['gltf'][res]['gltf']
    base = os.path.join(CACHE, asset, res)
    path = _fetch(g['url'], os.path.join(base, os.path.basename(g['url'])), g.get('md5'))
    for rel, e in g.get('include', {}).items():
        _fetch(e['url'], os.path.join(base, rel), e.get('md5'))
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=['texture', 'model', 'info'])
    ap.add_argument('asset')
    ap.add_argument('--res', default='2k')
    a = ap.parse_args()
    if a.kind == 'texture':
        print(json.dumps(texture(a.asset, a.res), indent=1))
    elif a.kind == 'model':
        print(model(a.asset, a.res))
    else:
        print(json.dumps(info(a.asset), indent=1)[:2000])
    return 0


if __name__ == '__main__':
    sys.exit(main())
