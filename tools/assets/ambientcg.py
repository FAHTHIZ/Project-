# SPDX-License-Identifier: Apache-2.0
"""Fetch CC0 PBR materials from ambientCG (https://ambientcg.com, licence: CC0 1.0).

    python3 tools/assets/ambientcg.py Plastic010 Rubber004

Files are cached under .cache/ambientcg/<id>/ (git-ignored); only the derived, resampled
textures baked into game assets are committed (see docs/ASSET_PROVENANCE.md).
"""
from __future__ import annotations

import glob
import io
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, '.cache', 'ambientcg')
ROLES = {'diff': '_Color', 'nor': '_NormalGL', 'rough': '_Roughness', 'metal': '_Metalness',
         'ao': '_AmbientOcclusion', 'disp': '_Displacement', 'alpha': '_Opacity'}


def material(asset: str, res: str = '1K') -> dict:
    """Download (once) and unpack <asset>_<res>-JPG; returns {role: path}."""
    d = os.path.join(CACHE, asset, res)
    if not glob.glob(os.path.join(d, '*.jpg')):
        os.makedirs(d, exist_ok=True)
        url = f'https://ambientcg.com/get?file={asset}_{res}-JPG.zip'
        req = urllib.request.Request(url, headers={'User-Agent': 'special-ops-asset-tools/1.0'})
        data = urllib.request.urlopen(req, timeout=120).read()
        zipfile.ZipFile(io.BytesIO(data)).extractall(d)
    out = {}
    for role, tag in ROLES.items():
        hit = sorted(glob.glob(os.path.join(d, f'*{tag}.jpg')))
        if hit:
            out[role] = hit[0]
    return out


if __name__ == '__main__':
    for a in sys.argv[1:]:
        print(a, material(a))
