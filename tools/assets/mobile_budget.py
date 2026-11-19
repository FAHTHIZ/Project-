# SPDX-License-Identifier: Apache-2.0
"""Apply the mobile texture budget to every model and texture .meta in the game.

    python3 tools/assets/mobile_budget.py [--check]

Before this pass no asset used GPU texture compression, so the phone uploaded every texture as
RGBA8 (32 bits per texel) at up to 4096 px. The VICTUS cooker stores several compressed
variants and the player picks the one the GPU supports (STATUS slice 49, ADR-0047):
    BC7 (desktop, 8 bpp) and ASTC (Android: 4x4 = 8 bpp, 6x6 = 3.56 bpp)
Budget by asset class (max texel size, codecs):
    first-person weapons/hands, character heads/bodies   2048  bc7+astc4x4 (seen up close)
    everything else                                      1024  bc7+astc6x6
UI textures keep their size and use bc7+astc4x4 (sharp edges). HDR environment maps are left
untouched (the cooker keeps them as half floats).
`--check` exits non-zero if any .meta is outside the budget (used by the asset tests).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, 'game', 'assets')
CLOSE_UP = ('models/weapons/', 'models/characters/')


def budget(rel: str) -> tuple[int, str]:
    if rel.startswith(CLOSE_UP):
        return 2048, 'bc7+astc4x4'
    if rel.startswith('textures/ui/'):
        return 4096, 'bc7+astc4x4'
    return 1024, 'bc7+astc6x6'


def want(meta: dict, rel: str) -> dict | None:
    size, codec = budget(rel)
    s = dict(meta.get('settings', {}))
    if meta.get('importer') == 'gltf':
        s['max_texture_size'] = min(int(s.get('max_texture_size', 4096)), size)
        s['texture_compression'] = codec
    elif meta.get('importer') == 'texture':
        if rel.lower().endswith(('.hdr', '.exr')):
            return None
        s['max_size'] = min(int(s.get('max_size', 4096)), size)
        s['compression'] = codec
    else:
        return None
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    changed, bad = 0, []
    for dirpath, _, names in os.walk(ASSETS):
        for n in names:
            if not n.endswith('.meta'):
                continue
            p = os.path.join(dirpath, n)
            rel = os.path.relpath(p, ASSETS)[:-5].replace(os.sep, '/')
            meta = json.load(open(p))
            s = want(meta, rel)
            if s is None or s == meta.get('settings'):
                continue
            if a.check:
                bad.append(rel)
                continue
            meta['settings'] = s
            with open(p, 'w') as f:
                json.dump(meta, f, indent=2)
                f.write('\n')
            changed += 1
    if a.check:
        for r in bad:
            print(f'over budget: {r}')
        return 1 if bad else 0
    print(f'{changed} .meta files updated')
    return 0


if __name__ == '__main__':
    sys.exit(main())
