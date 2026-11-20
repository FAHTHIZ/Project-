#!/usr/bin/env python3
"""Campaign tour: play every chapter headless, keep each checkpoint, then render the game there.

  python3 tools/test/tour.py play  [chapter ...]   # story_<chapter> autotests, checkpoint saves
  python3 tools/test/tour.py shoot [chapter ...]   # one screenshot per kept checkpoint
  python3 tools/test/tour.py restore [chapter ...] # headless: every checkpoint resumes without script errors
  python3 tools/test/tour.py sheet                 # contact sheet of all shots

Rendering a whole chapter on the software Vulkan driver takes hours (about 1 frame/s), so the
tour renders only where the campaign saves: the chapter scene restores the checkpoint (player
position, squad, downed enemies) from the copied save, runs FRAMES frames and captures. Output
in /tmp/sops_tour/<chapter>/cpNN.{vsave,png}.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "game"
OUT = Path(os.environ.get("SOPS_TOUR", "/tmp/sops_tour"))
CHAPTERS = ["prologue", "op01", "op02", "op03", "op04", "op05", "op06", "op07", "epilogue"]
SCENES = {"prologue": "scenes/prologue.vscene", "op01": "scenes/op01_forest.vscene",
          "op02": "scenes/op02_perimeter.vscene", "op03": "scenes/op03_approach.vscene",
          "op04": "scenes/op04_interior.vscene", "op05": "scenes/op05_bunker.vscene",
          "op06": "scenes/op06_basement.vscene", "op07": "scenes/op07_chamber.vscene",
          "epilogue": "scenes/epilogue.vscene"}
W, H = int(os.environ.get("SOPS_TOUR_W", 960)), int(os.environ.get("SOPS_TOUR_H", 420))
FRAMES = int(os.environ.get("SOPS_TOUR_FRAMES", 150))
QUALITY = os.environ.get("SOPS_TOUR_QUALITY", "medium")


def play(ch):
    d = OUT / ch
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    saves = Path(f"/tmp/sops_tour_saves_{ch}")
    shutil.rmtree(saves, ignore_errors=True)
    env = dict(os.environ, VICTUS_NO_AUDIO="1", SDL_VIDEO_DRIVER="offscreen")
    cmd = ["victus", "simulate", str(GAME), "--scene", f"scenes/tests/story_{ch}.vscene",
           "--frames", "20000", "--saves", str(saves)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    seen, n = set(), 0
    while True:
        done = p.poll() is not None
        f = saves / "campaign.vsave"
        try:
            j = json.loads(f.read_text())
            cp = j["data"].get("checkpoint")
            key = json.dumps(cp, sort_keys=True) if cp else None
            if cp and key not in seen:
                seen.add(key)
                (d / f"cp{n:02d}.vsave").write_text(f.read_text())
                print(f"  {ch} cp{n:02d}: {cp.get('op')} {cp.get('stage')} pos {cp.get('pos')}", flush=True)
                n += 1
        except (OSError, ValueError, KeyError):
            pass
        if done:
            break
        time.sleep(0.25)
    out = p.stdout.read().strip().splitlines()
    print(f"  {ch}: {n} checkpoints; {out[-1] if out else ''}")


def shoot(ch):
    for sv in sorted((OUT / ch).glob("cp*.vsave")):
        j = json.loads(sv.read_text())
        op = j["data"]["checkpoint"]["op"]
        saves = Path("/tmp/sops_tour_shot")
        shutil.rmtree(saves, ignore_errors=True)
        saves.mkdir()
        shutil.copy(sv, saves / "campaign.vsave")
        png = sv.with_suffix(".png")
        env = dict(os.environ, VICTUS_NO_AUDIO="1", VICTUS_NO_COMPRESSED_TEXTURES="1",
                   XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
        cmd = ["timeout", "900", "xvfb-run", "-a", "-s", f"-screen 0 {W}x{H}x24", "victus", "run", str(GAME),
               "--scene", SCENES[op], "--frames", str(FRAMES), "--screenshot", str(png), "--width", str(W),
               "--height", str(H), "--quality", QUALITY, "--saves", str(saves)]
        t = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        errs = [l for l in (r.stdout + r.stderr).splitlines() if "error" in l.lower()][:3]
        print(f"  {sv.stem} {op} {j['data']['checkpoint']['stage']}: {'ok' if png.exists() else 'FAILED'} "
              f"{time.time() - t:.0f}s {errs}", flush=True)


def restore(ch):
    bad = 0
    for sv in sorted((OUT / ch).glob("cp*.vsave")):
        cp = json.loads(sv.read_text())["data"]["checkpoint"]
        saves = Path("/tmp/sops_tour_restore")
        shutil.rmtree(saves, ignore_errors=True)
        saves.mkdir()
        shutil.copy(sv, saves / "campaign.vsave")
        env = dict(os.environ, VICTUS_NO_AUDIO="1", SDL_VIDEO_DRIVER="offscreen")
        r = subprocess.run(["victus", "simulate", str(GAME), "--scene", SCENES[cp["op"]], "--frames", "240",
                            "--saves", str(saves)], capture_output=True, text=True, env=env)
        errs = [l for l in r.stdout.splitlines() if l.startswith("script error")]
        bad += bool(errs) or r.returncode != 0
        print(f"  {ch}/{sv.stem} {cp['op']} {cp['stage']}: {'ok' if not errs and r.returncode == 0 else 'FAIL'} {errs[:2]}",
              flush=True)
    return bad


def sheet():
    from PIL import Image, ImageDraw
    shots = sorted(OUT.glob("*/cp*.png"), key=lambda p: (CHAPTERS.index(p.parent.name), p.name))
    for i in range(0, len(shots), 6):
        group = shots[i:i + 6]
        ims = [Image.open(p).convert("RGB") for p in group]
        w, h = ims[0].size
        s = Image.new("RGB", (w * 2, h * ((len(ims) + 1) // 2)))
        for k, (im, p) in enumerate(zip(ims, group)):
            s.paste(im, ((k % 2) * w, (k // 2) * h))
            st = json.loads(p.with_suffix(".vsave").read_text())["data"]["checkpoint"]["stage"]
            ImageDraw.Draw(s).text(((k % 2) * w + 6, (k // 2) * h + 4), f"{p.parent.name}/{p.stem} {st}", fill=(255, 255, 0))
        s.save(OUT / f"sheet_{i // 6:02d}.jpg", quality=88)
        print(OUT / f"sheet_{i // 6:02d}.jpg")


if __name__ == "__main__":
    mode, chs = sys.argv[1], sys.argv[2:] or CHAPTERS
    if mode == "sheet":
        sheet()
    else:
        for c in chs:
            {"play": play, "shoot": shoot, "restore": restore}[mode](c)
