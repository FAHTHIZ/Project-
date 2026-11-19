# Build and Test Log

This file is an evidence record. Add entries as work is executed. Never mark a check as passed based only on reading documentation.

## Initial handoff audit — 2026-11-19

### Repositories

- Game repository: https://github.com/FAHTHIZ/Project-
- Game repository default branch: `main`
- Initial game repo state: starter README only; no game source/assets/scenes/scripts/tests were present at first inspection.
- VICTUS repository: https://github.com/FAHTHIZ/VICTUS
- VICTUS main SHA inspected: `31457931542d52c0572970139d161a73428c21bd`
- VICTUS status/known limitations/docs were read for the initial handoff.
- Current VICTUS HEAD must be checked again by the implementing agent.

### Video references inspected

Four uploaded videos were inspected in upload order:
1. 720 × 1280, 30 fps, about 14.07 s.
2. 720 × 1280, 30 fps, about 16.11 s.
3. 720 × 1280, 30 fps, about 11.14 s.
4. 720 × 1280, 30 fps, about 13.12 s.

Visual observations are preserved in `docs/STAGE_01_FOREST.md`. The source videos themselves are not stored in this repository as of this initial handoff.

### Tests/builds actually executed

- No game build was run.
- No VICTUS build was run in this handoff.
- No CTest run was executed in this handoff.
- No Android APK was built here.
- No APK was installed on a physical phone or emulator here.
- No frame-rate, memory, GPU, thermal or battery performance was measured.
- No voice assets or third-party game assets were downloaded or integrated.

### Next required action

Follow P0 in `docs/PRODUCTION_PLAN.md`: inspect the current main branches, run the live VICTUS setup/build/test workflow, inspect the actual Hot 10S device and prove a minimal landscape Android scene before building the full forest.


## Campaign direction revision — 2026-11-19

The owner corrected the game direction from third-person exploration to a **first-person cinematic shooter campaign**. The documentation now specifies:
- First-person gameplay and first-person arms/hand/weapon viewmodels; external camera angles are reserved for authored cutscenes.
- A real fictional shooter loop with original primary/secondary game weapons, aim/fire/reload/switch actions, HUD, effects, audio and enemy encounters.
- Original operator and opposing-character costume research, with clothing, silhouettes, palettes, voice and animation requirements.
- Frequent, purposeful campaign cutscenes for the opening, operator moments, location reveals, transitions, bunker descent, basement reveal, V-01 reveal and ending.
- The complete route: forest → perimeter → facility → bunker → substantial lower basement → V-01 chair reveal and ending.
- New dedicated handoff documents: `docs/CAMPAIGN_AND_CINEMATICS.md` and `docs/OPERATORS_AND_WEAPON_DESIGN.md`.

**Validation for this documentation-only revision:** no engine build, game build, automated test, APK export/install or physical-device performance test was run. No playable implementation is claimed. Weapon research in this project is confined to original fictional game art, animation, sound and abstract balance; no real-world weapon instructions or specifications are part of the brief.


## Full squad direction clarification — 2026-11-19

The owner clarified that the campaign must feature a complete recurring squad, not a lone protagonist with occasional NPCs. The handoff now defines a baseline roster of the first-person player plus three or four allied operators, with final count subject to measured device budgets. The squad must accompany the player in playable missions where authored staging allows, communicate with one another and the player, use companion navigation/regroup/wait/recovery behaviour, and appear together in major cinematics.

Character performance requirements now explicitly include expressive eye direction, blinks, eyelids, brows, gaze targets, facial expressions, synchronized mouth shapes/visemes and jaw movement. Listening characters must react rather than freeze. Dialogue must support spatial nearby conversations, radio exchanges, speaker identification and synchronized subtitles.

**Validation:** documentation-only update. No companion AI, facial rig, lip-sync runtime, voice assets, build or device test has been implemented or verified by this update.

## P0 — Baseline, VICTUS build and generated project — 2026-11-19

### Environment (cloud sandbox, no phone attached)

- VICTUS: https://github.com/FAHTHIZ/VICTUS main at `bc0ce15ad4dd0ae037ae87aa3e50acf2d01a82f0` ("Script Debugger in Studio play mode (ADR-0106)"), shallow clone. VICTUS reports `VICTUS 0.2.0`.
- OS: Ubuntu 26.04.1 LTS (x86_64); g++ 15.2.0; cmake 4.2.3; Ninja; Python 3.14.8. Vulkan: Mesa lavapipe (software) only. No GPU, no Android device or emulator.
- Engine dependencies: `tools/setup/install_deps.sh` (VICTUS).

### Commands run and results

```sh
cmake -S . -B build/rel -G Ninja -DCMAKE_BUILD_TYPE=Release -DVICTUS_BUILD_TESTS=OFF -DVICTUS_BUILD_SAMPLES=OFF -DVICTUS_BUILD_BENCHMARKS=OFF
cmake --build build/rel --parallel 2          # PASS: 964/964 steps, bin/victus, bin/victus_editor, bin/victus_player
victus new /tmp/tpl3d --template 3d --character v01 --name "Special Ops"   # PASS
victus check /tmp/tpl3d                       # PASS: 1 scene, 6 scripts, 0 problems
victus simulate /tmp/tpl3d --frames 300 --hold W --seed 1 --save /tmp/final.vscene   # PASS: 97 entities, 0 script errors
```

The template was copied to `game/` (the game's VICTUS project). Generated assets were added with:

```sh
python3 tools/characters/build_humans.py --rig <victus>/engine/project/data/characters/victus_vanguard_02.glb --out game/assets/models/characters
python3 tools/props/build_forest.py --out game/assets
victus import game     # PASS: 37 imported, 0 failed
victus check game      # PASS: 0 problems
victus simulate game --frames 300 --hold W --seed 1 --save /tmp/f.vscene   # PASS: 0 script errors
```

- Engine CTest was not run (tests disabled in this configuration to save disk/time). Not claimed.
- Android: not built yet in P0. No phone is available in this environment; the Hot 10S SKU/driver inspection remains blocked on physical access.
- Character GLBs were reviewed with the CPU preview tool `tools/characters/preview.py` (rest pose, Walk, Stumble, GetUp, Scan, Talk, Wave, Inspect, Blink/JawOpen morphs). This is an asset review, not an engine render.

### Next

First-person controller + unified input layer + virtual touch controls (P1).

## P1 — Scene tooling, first-person controller, unified input, HUD, menus — 2026-11-19

### What was built

- `tools/scenes/` — Python generators that write every `.vscene` (deterministic uuid5 ids): `vscene.py` (scene/entity/component writer, glTF instancing that mirrors the engine's `instantiate.cpp` hierarchy), `rig.py` (player rig, HUD canvas, pause/settings modal, padded buttons), `common.py` (environment presets), `project.py` (`victus.project`: window, input actions and axes), `build_menu.py` (menu, credits), `build_dev_range.py` (dev range and autotest variants).
- `game/assets/scripts/lib/game.luau` — shared state: pause/cinematic flags, persisted settings, campaign progress save, flags, event bus.
- `lib/controls.luau` — one logical action layer for keyboard/mouse, gamepad and touch: floating left stick (sprint on full push), right-side look drag, on-screen buttons, test injection (`Controls.virtual`), mouse settle window after focus/scene changes and pointer-warp rejection.
- `fp_player.luau` — first-person controller: walk/sprint/crouch with acceleration, jump, head bob, landing dip, shake, FOV, health with regeneration, aim ray, interaction focus (ray plus cone fallback).
- `hud.luau` — reticle, hit marker, objective and log, toasts, prompt, weapon panel, health, subtitles with speaker, letterbox/fade/title card, skip hint, touch overlay, diagnostics overlay (FPS, frame max, window, entities, position/yaw/pitch, touches, pad; GPU time reported as unavailable).
- `pause_menu.luau` — resume, restart from checkpoint (event), settings (13 rows), objectives, quit to menu. `menu.luau` — continue / begin, new campaign with confirm, operation select (locked until unlocked), settings, credits. `credits.luau` — scrolling roll.
- `autotest.luau` + `tests/plans.luau` and `tools/test/run_autotests.py` — scripted input timelines run headless through `victus simulate`; `tools/test/shot.sh` — renders a frame to PNG under Xvfb with Mesa lavapipe.

### Commands and results

```sh
cd tools/scenes && python3 project.py && python3 build_menu.py && python3 build_dev_range.py movement hud pause_ui && cd ../..
victus check game                  # PASS: 6 scenes, 10 scripts, 0 problems
python3 tools/test/run_autotests.py
#   movement: PASS 13/13 (walk_forward, look_yaw, pitch_clamp, jump, land, crouch, stand,
#             pause_opens, pause_blocks_movement, pause_resumes, moves_after_resume, rig checks)
#   hud:      PASS 2/2
#   pause_ui: PASS 2/2
tools/test/shot.sh scenes/menu.vscene 60 /tmp/menu.png
tools/test/shot.sh scenes/tests/hud.vscene 90 /tmp/hud.png       # touch overlay + diagnostics forced on
tools/test/shot.sh scenes/tests/pause_ui.vscene 75 /tmp/pause.png
```

### Defects found by the screenshots and fixed

- All UI was laid out upside down: VICTUS `UiRect` is y-down from the top-left (`engine/gameui/include/victus/gameui/gameui.hpp`), the generators were authored y-up. `vscene.ui_rect` now mirrors the vertical axis in one place; the HUD's runtime rect writes (touch buttons, stick, reticle, credits roll) were corrected.
- The camera started at yaw -88 / pitch -40 with no input: the first relative mouse deltas after the window appears are pointer warps. Fixed with an 8-frame settle window after any polling gap and rejection of single-frame deltas above 400 px.
- Overlaps at 1600x720: OBJ touch button over the objective panel, diagnostics panel over SWITCH/RELOAD/TOOL, subtitle under AIM, toast under diagnostics. All moved/resized; button labels now have inner padding.
- "Continue" was offered on a fresh install; it now reads "Begin campaign" until a campaign save exists.

### Limitations recorded (not hidden)

- Mouse capture: `Window::set_relative_mouse` exists in `engine/platform` but is not exposed to Luau or used by the player, so desktop mouse-look reads `input.mouse_delta()` without cursor capture; the pointer can leave the window. Gamepad and touch are unaffected.
- Touch is verified through `Controls.virtual` injection and layout screenshots only; no physical touchscreen or phone is attached to this environment.
- Screenshots are Mesa lavapipe (software Vulkan) renders; they prove layout and content, not phone performance.
