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
