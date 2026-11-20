#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Runs SPECIAL OPS autotest scenes headless with `victus simulate` and reports their checks.

    python3 tools/test/run_autotests.py [plan ...]     # default: every scenes/tests/*.vscene

Each scene's Autotest entity logs "AUTOTEST PASS|FAIL <plan> <check>" and "AUTOTEST END" lines
through log.warn; VICTUS writes them to the diagnostics log (~/.config/victus/diagnostics/logs).
A plan passes when it reaches END with no FAIL lines and the run reports 0 script errors.
Exit code 0 only when every plan passes.
"""
import glob
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "game"
LOGDIR = Path.home() / ".config/victus/diagnostics/logs"


def newest_log(after):
    logs = [p for p in LOGDIR.glob("victus-*.log") if p.stat().st_mtime >= after - 1]
    return max(logs, key=lambda p: p.stat().st_mtime) if logs else None


def run(plan, frames):
    env = dict(os.environ, VICTUS_NO_AUDIO="1", SDL_VIDEO_DRIVER="offscreen")
    t0 = time.time()
    cmd = ["victus", "simulate", str(GAME), "--scene", f"scenes/tests/{plan}.vscene", "--frames", str(frames),
           "--saves", f"/tmp/sops_saves_{plan}"]
    subprocess.run(["rm", "-rf", f"/tmp/sops_saves_{plan}"])
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    out, _ = p.communicate(timeout=900)
    # the engine names its log victus-<time>-<pid>.log: take this run's, not a concurrent one's
    mine = sorted(LOGDIR.glob(f"victus-*-{p.pid}.log"), key=lambda q: q.stat().st_mtime)
    log = mine[-1] if mine else newest_log(t0)
    lines = log.read_text(errors="replace").splitlines() if log else []
    auto = [l.split("[script] ", 1)[-1] for l in lines if "AUTOTEST" in l]
    errors = [l for l in lines if "[error]" in l]
    m = re.search(r"(\d+) script errors", out)
    script_errors = int(m.group(1)) if m else -1
    ended = any("AUTOTEST END" in l for l in auto)
    fails = [l for l in auto if "AUTOTEST FAIL" in l]
    # runtime script errors (a script disabled mid-run) are only in the log, not the engine's count
    runtime = [l for l in errors if "[script]" in l]
    ok = ended and not fails and script_errors == 0 and not runtime and p.returncode == 0
    return ok, out.strip().splitlines()[-1:] , auto, errors[:10]


def main():
    plans = sys.argv[1:] or sorted(Path(p).stem for p in glob.glob(str(GAME / "scenes/tests/*.vscene")))
    frames = int(os.environ.get("SOPS_TEST_FRAMES", "0"))
    allok = True
    for plan in plans:
        f = frames or {"movement": 660, "squad": 2200, "squad_combat": 2600,
                            "enemy_tactics": 2140, "squad_cover": 3620}.get(plan, 1800)
        ok, tail, auto, errors = run(plan, f)
        allok &= ok
        print(f"== {plan}: {'PASS' if ok else 'FAIL'}  ({f} frames)")
        for l in tail:
            print("   ", l)
        for l in auto:
            print("   ", l)
        for l in errors:
            print("   ERR", l)
    sys.exit(0 if allok else 1)


if __name__ == "__main__":
    main()
