#!/usr/bin/env python3
"""Put the phone game.vpak into an engine-built APK without a second full copy on disk.

The VICTUS Gradle project copies the pack into build/generated and then into the APK, which
needs three copies of a ~2 GB file at once. Instead the APK is built against a tiny dummy pack
and this script rewrites it with the real pack streamed in as a STORED entry:

  * every original entry is copied raw (same compression, same bytes, same CRC);
  * STORED entries are aligned the way zipalign -p does it: 16 KiB for lib/**/*.so
    (Android 15 16 KB page kernels, uncompressed native libs), 4 bytes for the rest;
  * assets/game.vpak is replaced by the real pack, stored and 4-byte aligned, as the
    engine's `noCompress 'vpak'` expects.

The output is unsigned; sign it with apksigner afterwards (tools/android/build_apk.sh).

usage: inject_pack.py IN.apk GAME.vpak|- OUT.apk [THIRD_PARTY_NOTICES.txt]
       ("-" keeps the pack already in IN.apk)
"""
import os
import struct
import sys
import zipfile


def aligned_extra(fp_offset, name, extra, align):
    """Extra-field padding so the entry data starts on an `align` boundary."""
    data_off = fp_offset + 30 + len(name.encode()) + len(extra)
    pad = (-data_off) % align
    if pad == 0:
        return extra
    if pad < 4:  # an extra-field record needs 4 header bytes; skip to the next boundary
        pad += align
    return extra + struct.pack("<HH", 0xD935, pad - 4) + b"\0" * (pad - 4)


def main(src_apk, pack, out_apk, notices=None):
    src = zipfile.ZipFile(src_apk)
    with open(out_apk, "wb") as f:
        out = zipfile.ZipFile(f, "w", allowZip64=True)
        for info in src.infolist():
            if info.filename == "assets/game.vpak":
                continue
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            ni.create_system = info.create_system
            data = src.read(info.filename)
            if notices and info.filename == "assets/THIRD_PARTY_NOTICES.txt":
                data = open(notices, "rb").read()
            if info.compress_type == zipfile.ZIP_STORED:
                align = 16384 if info.filename.endswith(".so") else 4
                ni.extra = aligned_extra(f.tell(), ni.filename, b"", align)
            out.writestr(ni, data)
        own = pack == "-"  # re-align/re-sign: keep the pack already inside IN.apk
        size = src.getinfo("assets/game.vpak").file_size if own else os.path.getsize(pack)
        ni = zipfile.ZipInfo("assets/game.vpak", date_time=(2026, 1, 1, 0, 0, 0))
        ni.compress_type = zipfile.ZIP_STORED
        ni.file_size = size
        ni.extra = aligned_extra(f.tell(), ni.filename, b"", 4)
        with (src.open("assets/game.vpak") if own else open(pack, "rb")) as p, out.open(ni, "w") as w:
            while chunk := p.read(1 << 22):
                w.write(chunk)
        out.close()
    chk = zipfile.ZipFile(out_apk)
    for i in chk.infolist():
        if i.compress_type == zipfile.ZIP_STORED:
            with open(out_apk, "rb") as f:
                f.seek(i.header_offset + 26)
                n, e = struct.unpack("<HH", f.read(4))
            off = i.header_offset + 30 + n + e
            need = 16384 if i.filename.endswith(".so") else 4
            assert off % need == 0, (i.filename, off)
    print(f"{out_apk}: {len(chk.infolist())} entries, pack {size} bytes, alignment ok")


if __name__ == "__main__":
    main(*sys.argv[1:5])
