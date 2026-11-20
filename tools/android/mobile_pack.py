#!/usr/bin/env python3
"""Export the phone pack: same content as the desktop export, textures cooked ASTC-only.

The desktop .meta settings ask for "bc7+astc4x4" / "bc7+astc6x6". A phone never samples BC7,
and the VICTUS cooker stores every requested codec plus the RGBA8 mip chain, so the Android
pack would carry ~400 MB of BC7 it can never use and would not fit a 2 GiB release asset.

This script temporarily strips "bc7+" from every .meta, runs `victus import` and
`victus export --pack-only`, then restores the .meta files byte-for-byte (they are never
committed in their phone form) and re-imports so the desktop cache is back to normal.

usage: python3 tools/android/mobile_pack.py OUT_DIR [--no-restore-import]
"""
import pathlib, subprocess, sys

root = pathlib.Path(__file__).resolve().parents[2] / "game"
out = pathlib.Path(sys.argv[1]).resolve()
metas = [p for p in root.rglob("*.meta") if ".victus" not in p.parts]
saved = {}
for p in metas:
    t = p.read_text()
    if "bc7+" in t:
        saved[p] = t
        p.write_text(t.replace("bc7+", ""))
print(f"phone codecs on {len(saved)} assets")
try:
    subprocess.run(["victus", "import", str(root)], check=True)
    subprocess.run(["victus", "export", str(root), "--out", str(out), "--name", "specialops", "--pack-only"], check=True)
finally:
    for p, t in saved.items():
        p.write_text(t)
    print("desktop .meta settings restored")
if "--no-restore-import" not in sys.argv:
    subprocess.run(["victus", "import", str(root)], check=True)
