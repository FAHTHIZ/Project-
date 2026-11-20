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

## P1 weapons — first-person viewmodels, pulse carbine, sidearm, scanner — 2026-11-19

Engine: VICTUS 82bfd17 (release build `build/rel`). Game base: 88b0bd7.

### What was built

- `tools/props/build_weapons.py` → `assets/models/weapons/*.glb` (carbine body/cell, sidearm body/slide/cell, gloved hands, pulse bolt, stun target).
- `tools/audio/build_sfx.py` → synthesized WAVs in `assets/audio/{weapons,ui,foley}` (numpy/scipy, original, see ASSET_PROVENANCE).
- `lib/combat.luau` — damage/stun handler registry, ray helper, noise events, stats.
- `weapons.luau` — states idle/equip/lower/reload, hitscan with spread cone, head zone, recoil with recovery, sway/bob/breathing/sprint and wall retract, reload choreography (cell out/in, off hand), slide kick, muzzle light, tracers, impact particles, ADS with FOV zoom, field scanner tool (tags `Scannable`, cooldown), touch aim toggle, HUD panel, save/load state; hidden during cinematics.
- `range_target.luau` — stun target that folds back and resets.
- `rig.py` viewmodel/FX rig; dev range targets.

### Commands and results

```sh
victus import game
cd tools/scenes && python3 build_dev_range.py movement hud pause_ui weapons vm_ads vm_reload vm_sidearm vm_scan && cd ../..
victus check game                   # PASS: 11 scenes, 13 scripts, 0 problems
python3 tools/test/run_autotests.py # movement 13/13, hud 2/2, pause_ui 2/2, weapons 26/26, vm_* screenshot plans clean
tools/test/shot.sh scenes/tests/vm_ads.vscene 200 /tmp/vm_ads.png    # sight ring centred on reticle
tools/test/shot.sh scenes/tests/vm_reload.vscene 200 /tmp/vm_reload.png # weapon tilted, cell out, HUD RELOADING
tools/test/shot.sh scenes/tests/vm_sidearm.vscene 200 /tmp/vm_sidearm.png
tools/test/shot.sh scenes/tests/vm_scan.vscene 200 /tmp/vm_scan.png  # device raised, "SCAN 6 contacts"
```

### Defects found and fixed

- `entity:set_visible` errors on entities without a renderer; viewmodel visibility now recurses into renderer children (caused movement/hud/pause_ui to fail once weapons were added).
- First hip pose was too close and bulky in screenshots; moved further out, slimmer open-tube sight.
- Reload screenshot plan started with a full cell (reload correctly refused); plan now empties the cell first.

### Status

Implemented, simulated headless, visually inspected under lavapipe. Not tested on a phone or with a physical gamepad/touchscreen.

## P3 — Halyard Team, dialogue, faces, Greyline contractors — 2026-11-19

Engine: VICTUS 82bfd17. Game base: 4be5c63.

### What was built

- Cast (`tools/characters/build_humans.py`): Anchor (lead), Patch (medic), Echo (scout), Tally (comms), Greyline A/B contractors, plus the existing Explorer and Ranger Hollis, on the shared Vanguard skeleton. Each head has 11 morph targets (Blink JawOpen Smile Frown BrowUp BrowDown MouthO LookL/R/Up/Down). New clips Kneel, Surrender, Halt, Point, Beckon. About 17–21k triangles per character.
- `anim/characters/human.vanim`: locomotion blend, fall/land, kneel, interact, inspect, scan, stumble/get-up, surrender; LeftArm gesture layer and an Arms talk layer.
- `tools/scenes/actors.py`: operators, contractors and civilians as CharacterController + NavAgent roots with a spatial `Voice` source, carried PC-7 with two-bone hand IK and look-at head IK; `add_ensemble` (scene runner + flat radio voice) and an NPC tracer pool.
- Dialogue: `tools/dialogue/lines.py` (76 lines: prologue, Op01 beats, squad-to-squad chatter, barks, Greyline barks); `tools/audio/build_voices.py` renders them offline with Kokoro-82M (see RESEARCH_REGISTER §6) and writes `lib/voice_data.luau` with a 30 Hz jaw envelope and mouth shapes.
- Runtime: `lib/dialogue.luau` (one line at a time, priorities bark/chatter/story/cinematic, stale barks dropped, per-line and per-kind cooldowns, rotating variants among present speakers, conversations with gaps and done callbacks, subtitles with speaker names, spatial voice from the speaker or radio, pause-aware, listener eye-lines, line log), `lib/face.luau` (blinks, emotions, saccades, eye look, lip sync; writes morphs only on change; frozen beyond 22 m), `lib/actor.luau` (facing, animation parameters, carry pose low-ready↔aim, support-hand release for gestures/talk, head look, footsteps), `lib/squad.luau` (roster, orders follow/hold/move, formation slots, NPC hitscan with spread, tracers, near-miss events), `operator.luau`, `enemy.luau` (patrol, hearing, group alerts, 0.6–1.0 s reaction, three-round bursts with pauses, distance/motion spread, stun pool, surrender), `npc.luau`, `ensemble.luau`.

### Commands and results

```sh
python3 tools/characters/build_humans.py --rig ../victus/engine/project/data/characters/victus_vanguard_02.glb --out game/assets/models/characters
python3 tools/audio/build_voices.py --model /tmp/kok          # 76 lines, 1.8 MB OGG
cd tools/scenes && python3 build_dev_range.py movement hud pause_ui weapons vm_ads vm_reload vm_sidearm vm_scan squad squad_combat enemy_fire squad_look && cd ../..
victus import game && victus check game   # 15 scenes, 2 controllers, 23 scripts: 0 problems
python3 tools/test/run_autotests.py movement hud pause_ui weapons squad squad_combat enemy_fire
#   movement PASS, hud PASS, pause_ui PASS, weapons PASS,
#   squad 17/17 (registry, faces, voices, carry IK < 6 cm, formation follow, hold, resume, subtitle,
#                lip sync moving, listeners look, no overlapping lines, conversation callback, cooldown),
#   squad_combat 5/5 (squad stuns two alerted contractors, both surrender, contact bark, player unhurt),
#   enemy_fire 3/3 (contractor hurts the player, player's carbine stuns it, it stops firing)
tools/test/shot.sh scenes/tests/squad_look.vscene 60 /tmp/sq1.png      # squad at low-ready, faces readable
tools/test/shot.sh scenes/tests/squad_combat.vscene 420 /tmp/sq2.png   # contractor surrendering, Greyline subtitle
```

### Defects found and fixed

- `entity:set(component, field, value)` is not the API; it takes a partial table (`set("NavAgent", {speed = 3})`).
- Head morph targets do not resolve during `start()`; `Face` retries for 30 frames.
- `entity.id` is a string; seeds are hashed from the entity name.
- `entity:look_at` works in the parent's space; the carried weapon is aimed with a character-space direction, and the carry is parented to the model root rather than the Chest bone (chest axes made the pose unpredictable).
- Euler `.y` is ambiguous at 180°; facing is read from `entity.forward`.
- Support hand was 10 cm short of the grip at low-ready; carry moved inward and the grip forward.

### Status

Implemented, simulated headless and visually inspected under lavapipe on the dev range. Voices were listened to only as waveforms/lengths (no speakers on the build machine). Not tested on a phone; the squad-of-four cost on the Infinix Hot 10S is unmeasured.

## Vehicle, cargo storage, LR-4 scope, field kit, squad egress — 2026-11-19

Base: game `f04419d`, VICTUS `82bfd17`. Machine: 2-core x86-64, lavapipe (software Vulkan), no phone.

### Commands and results

```sh
python3 tools/characters/build_humans.py --rig ../victus/engine/project/data/characters/victus_vanguard_02.glb --out game/assets/models/characters   # + Sit, SitStand, Lift, Reach
python3 tools/ui/build_ui_textures.py --out game/assets                          # scope_mask.png
cd tools/scenes && python3 build_dev_range.py movement hud pause_ui weapons vm_ads vm_reload vm_sidearm vm_scan squad squad_combat enemy_fire squad_look vehicle trunk sniper vehicle_look trunk_look scope_look && cd ../..
victus import game && victus check game     # 21 scenes, 2 controllers, 28 scripts: 0 problems
python3 tools/test/run_autotests.py         # 18/18 scenes PASS
#   vehicle 14/14: registered, 4 seated (worst 0.003 m), engine idle, drives 3.75 m/s on spline, wheels spin,
#                  occupants follow (worst 0.063 m), parks at target, heading, engine off, doors open in turn,
#                  all four out, doors closed, none inside the body, all grounded
#   trunk 26/26:   storage found, contents, locked while closed, hatch prompt/animates/open, look identifies,
#                  description, take, swap stows carbine, swap lowers first, equip, carbine visible in slot,
#                  refused when cells full, supply consumed, kit, invalid item, duplicate refused, drop,
#                  re-pick keeps ammo state, swap back, save/restore inventory + storage, hatch close, reopen preserves
#   sniper 19/19:  scope FOV/sensitivity, zoom step 2, bounded sway, scoped shot hit, bolt interval,
#                  unscope, interrupted equip without snap, kit heal/charge/removal/HUD, no kit no use
sh tools/test/shot.sh scenes/tests/vehicle_look.vscene 90 docs/evidence/vehicle_seated.png
sh tools/test/shot.sh scenes/tests/trunk_look.vscene 150 docs/evidence/trunk_open.png
sh tools/test/shot.sh scenes/tests/scope_look.vscene 220 docs/evidence/scope.png
```

### Defects found and fixed

- `Game.register_interactable` lived in fp_player.luau, so vehicle/storage scripts that started first called nil; moved to lib/game.luau.
- Seated operators stood with heads through the roof: `set_anim_param` during `start()` was lost and the rider (gravity off) reported not grounded, sending the graph to Fall. The actor now drives `seated`/`grounded` every frame; `seated_pose = false` lets SitStand play while still attached.
- The HUD never resolved Scope, Scope Zoom, Prompt Detail and Kit Text (missing from its element list) so the scope overlay never showed; added, and the HUD now warns about any missing element.
- Cargo bay contents were unreadable in shade; added a hatch-switched courtesy lamp.
- Trunk test assumed reserve below max; it refills first so the "cells full" refusal is actually exercised.

### Status

Implemented, simulated headless (autotests) and visually inspected on lavapipe (three evidence shots above). Drive is an authored spline, not physics driving. No foot IK. Not tested on a phone.

## Story revision 2: storm night, five-operator squad, new firearms, epilogue — 2026-11-19

Base: game `28eea22`, VICTUS `9cb14c4`. Machine: 2-core x86-64, 7 GB RAM, lavapipe (software
Vulkan) under xvfb, no phone. Commits, in order: `a38892e` dialogue rewrite to Iron Veil canon,
`3c133b4` Kestrel Valley canon beats Prologue-Op03, `585954c` contractor parley/retreat/surrender,
`f30aeb7` story bible rev 2, `5ad387b` interiors Op04-07 director + Brick + Venn + Sorn stand-down,
`dfad0bb`/`901cf60` all 303 voice lines re-rendered, `7a235c7` storm night, `f5a8f6b` epilogue and
story drivers, `8d6a7b6` KV-5/BR-9/MR-6 + camp arms case, `5b96b9a` idle chatter + face throttle,
`35172db` night menu/credits, `26c532e` README rewrite.

### Commands and results

```sh
export PATH=/home/user/victus/build/rel/bin:$PATH
python3 tools/props/build_weapons.py --out game/assets     # + kv5_*, br9_*, mr6_*, arms_case
python3 tools/audio/build_sfx.py --out game/assets         # + kv5_fire, br9_fire, br9_pump, mr6_fire, thunder_0..2
python3 tools/audio/build_voices.py --model /tmp/kok       # 303 lines
python3 tools/world/worldgen.py scene && python3 tools/world/chapters.py
nice python3 tools/levels/build_facility.py --scenes
cd tools/scenes && python3 build_dev_range.py <plans> && python3 build_menu.py && cd ../..
victus import game && victus check game   # 246 scenes, 2 controllers, 40 scripts: 0 problems
SOPS_TEST_FRAMES=<N> python3 tools/test/run_autotests.py <plan>
#   PASS: weapons, vm_ads, vm_reload, vm_sidearm, vm_scan, squad, squad_combat, squad_look,
#         vehicle, trunk, sniper, armory 20/20, chatter 5/5,
#         story_prologue (20000 frames), story_op02, story_op03, story_op04, story_op05,
#         story_op06, story_op07, story_epilogue
#   story_op01: every check passes (reaches enter_facility) but the runner reports FAIL when the
#         intermittent face.luau watchdog below fires; one later run was clean.
#   world_* and gallery_* plans fail on this machine; they fail identically on the baseline 28eea22
#         (pre-existing, not caused by this work).
victus export game --out /tmp/sops_export --name special_ops
#   1039 files, 332 cooked assets, game.vpak 411,855,575 bytes
VICTUS_NO_AUDIO=1 xvfb-run -s "-screen 0 1280x720x24" /tmp/sops_export/special_ops --frames 120 \
    --screenshot /tmp/export_menu.png --quality low     # rc 0, menu rendered
sh tools/test/shot.sh scenes/menu.vscene 240 docs/evidence/menu_night.png 960 432 medium
```

### Defects found and known issues

- Menu and credits backdrop was still the daytime forest; now the night_storm environment.
- Credits named Anchor and Patch with names that contradicted their voice casting and omitted
  Tally; credits now list callsigns and roles only.
- Known issue: `scripts/lib/face.luau` can exceed the engine's 250 ms wall-clock script budget
  (`call_budget_seconds`, VICTUS `engine/script/include/victus/script/script.hpp`) on the first
  head-mesh lookup, which appears to resolve the model synchronously. The engine then disables that
  operator's script for the rest of the scene. Mitigated (distance cull first, 0.5 s retry
  throttle) but still intermittent on this 2-core software-rendered machine. Not measured on a phone.

### Status

Implemented, simulated headless and visually inspected on lavapipe. Not tested on a phone; the
five-operator squad, rain, volumetric fog and shadowed weapon light are unprofiled on the Hot 10S.

## Photoreal pass 1: mobile texture budget, photoscanned terrain, props and grass (2026-11-20)

- Game `fa7cc56` (texture budget) and the following commit; VICTUS `4213be3` (ADR-0121 terrain height blending, `VICTUS_NO_COMPRESSED_TEXTURES`).
- Machine: Linux x86-64, 2 cores, Mesa lavapipe (software Vulkan). No phone.
- Commands: `python3 tools/assets/mobile_budget.py`, `python3 tools/assets/build_photoreal_terrain.py`,
  `BLENDER=.../blender python3 tools/assets/build_photoreal_props.py`, `python3 tools/assets/build_photoreal_grass.py`,
  `victus import game` (332 imported, 0 failed), `victus check game` (246 scenes, 0 problems),
  `tools/test/shot.sh scenes/tests/world_trailhead.vscene 20 /tmp/trailhead.png 960 432` and `world_forest` (visually inspected).
- Triangle budgets per instance (LOD0): grass 12 (photo cards; was 12), fern 360-420 (was 252-336), hero fern 1800, shrubs 1500-2200, rocks 500-1400, log 1600, stump 1000.
- Finding: lavapipe decodes BC7/ASTC per sample, so a capture of the compressed project took more than 10 minutes; `shot.sh` now sets `VICTUS_NO_COMPRESSED_TEXTURES=1` (about 5 minutes for 20 frames at 960x432).
- Not measured: frame time, memory and thermals on the Hot 10S.

## 2026-11-20 Photoreal trees

- `tools/assets/build_photoreal_trees.py`: same tree shapes and triangle counts (1058-2387 tris), photo bark plus leaf-cluster and fir-bough cards baked from Poly Haven scans.
- Ran: `victus import game` (5 imported, 0 failed), `victus check game` (246 scenes, 0 problems), `tools/test/shot.sh scenes/tests/world_forest.vscene 20 /tmp/forest.png 960 432` (visually inspected, lavapipe).
- Not measured: Hot 10S frame time or thermals.

## 2026-11-20 Weapon and kit surfaces

- `tools/assets/retexture.py weapons`: box-projected UVs plus scanned detail, normal and roughness maps (ambientCG CC0) on 25 weapon, hand and kit GLBs. Glow, lens and emissive materials are untouched.
- Ran: `victus import game` (25 imported, 0 failed), `victus check game` (246 scenes, 0 problems). Not yet visually inspected on device.

## 2026-11-20 PC-7 hard-surface rebuild

- `tools/assets/blender_pc7.py` (Blender 4.2): new original PC-7 body/cell/world with chamfered extruded profiles, shroud vent slots, toothed rail, hooded optic, seams and screws. It has the same bounds, pivot and muzzle (z = -0.5) as before. Tris: body 12.6k, cell 1.2k, world 13.8k.
- Rebuild order: `build_weapons.py --out <tmp>` -> copy -> `blender_pc7.py` -> `retexture.py weapons` (detail now uses a fixed relative std, which removed the streaks from the near-black plastic scan).
- Ran: `victus import game` (25 imported, 0 failed), `victus check game` (246 scenes, 0 problems), `shot.sh scenes/tests/armory.vscene` (inspected).

## 2026-11-20 Mobile pacing and memory settings

- `game/victus.project`: mobile target 60 FPS. With VICTUS 590ffef (ADR-0124) the player sleeps out each frame period instead of rendering at the 90 Hz vsync rate, and dynamic resolution has a 0.55 floor. The asset cache is capped at 1024 MB with texture mip streaming on, so the cache evicts instead of growing until Android kills the app.
- Ran: `victus check game` (0 problems), `shot.sh scenes/tests/world_trailhead.vscene 20 ... low` (Low tier, inspected).
- Not measured: Hot 10S frame time, memory, thermals, or whether 60 holds. If 60 does not hold, set `mobile_target_fps` to 45, which paces evenly on a 90 Hz panel.

## 2026-11-20 Rocketbox cast

- `tools/assets/blender_rocketbox.py` (Blender 4.2) poses each Microsoft Rocketbox `_facial.fbx` (MIT) into the rig's rest A-pose. It merges the Biped weights onto the 21 joints and mixes ARKit/viseme blendshapes into the 11 morphs `lib/face.luau` drives.
- `tools/assets/build_rocketbox_cast.py` keeps each `sops_*.glb` rig and its 22 clips (translations re-based to the new proportions) and writes one atlased primitive per mesh. The originals are kept as sources in `.cache/rocketbox/_src/`.
- Ran: `victus import game` (9 imported, 0 failed), `victus check game` (246 scenes, 0 problems), and a squad close-up from `squad_look` (inspected: faces, kit and held rifles render).
- Not measured: on-device skinning cost (about 7k to 15k tris per human), memory or frame time.

## 2026-11-20 First-person arms

- `tools/assets/build_vm_arms.py` builds `hand_r.glb` and `hand_l.glb` from the Rocketbox Military_Male_04 arm: wrist and forearm on the old contract (grip at the origin), curled fingers, olive sleeve and dark glove. They keep two primitives (glove, sleeve) so the existing viewmodel entities still match. 757 tris each.
- Ran: `victus import game` (2 imported, 0 failed), plus armory and vm_sidearm captures at 1920x864 (inspected).

## 2026-11-20 Storm-night grade toward the misty-forest reference

- `tools/world/night_grade.py` applies a new storm-night grade to the 10 night scenes; the `common.py` `night_storm` preset uses the same values. Fog and volumetric albedo are a deep green, shadows are lifted (ambient 0.68, exposure +1.75 EV) with contrast 1.07, so trunks read as silhouettes in luminous mist instead of crushed black.
- Ran: `shot.sh scenes/tests/story_op01.vscene` before and after (inspected; before it was near-black).

## 2026-11-20 Cast kit to match the bible

- `tools/assets/cast_kit.py` is a kit stage for `build_rocketbox_cast.py` that follows OPERATORS_AND_WEAPON_DESIGN section 10. Accessories are generated, skinned rigidly and given swatches in the free atlas tile, so each mesh is still one primitive.
  - Anchor borrows Military_Male_01's pouches and webbing, plus a backpack.
  - Tally has a headset, boom mic, radio pack and whip antenna.
  - Patch has a teal armband, white gloves, a red bun and a medic pack.
  - Echo drops the vest (slim scout) and Brick gets a backpack.
  - Greyline are recast to Rocketbox Police_Male_02 (charcoal kit, helmet, balaclava). Their goggle lenses are tinted safety orange and the unit patches are painted out. The _b variant is lifted to mid grey.
- Ran: `build_rocketbox_cast.py` (all nine CAST_OK), Blender close-ups of Patch, Tally, Anchor, Echo and Greyline (inspected), `victus import game` (7 imported, 0 failed), `victus check game` (246 scenes, 0 problems), and an in-engine squad close-up (inspected: accessories follow the rig).
- Not measured: on-device cost. Accessories add under 2k tris per character.

## 2026-11-20 PC-7 parts restored in every scene; auto device-class quality

- Bug: the Blender PC-7 (`pc7_body` 8 primitives, `pc7_cell` 3, `pc7_world` 10) replaced a 3/2/5-primitive model, but scenes kept one prop child per old primitive. In-game the carbine drew without its metal, optic, lens, glow and grip parts.
- `tools/scenes/sync_model_prims.py` aligns every scene's `<name>[i]` prop children with the model's primitive count and adds the missing children with stable uuid5 ids. It fixed 563 prop groups in 52 scenes, only adding entities; existing entities are byte-identical. Run it with `--check` after any model rebuild that changes the material count.
- `game/victus.project`: `mobile_quality` is now `auto` (VICTUS ADR-0127). A Mali-G52 MC2 (Infinix Hot 10S) still classifies as Low, the same tier as before. Medium and High phones now get their own tier instead of Low. Packed R11G11B10F HDR (ADR-0126) is automatic on phones.
- Engine rebuilt at VICTUS edb3409. Ran: `victus check game` (246 scenes, 0 problems), plus armory and squad close-up captures (inspected: the PC-7 rail, optic and accents now render).
- Not measured: anything on the device.

## 2026-11-20 HUD v2 and reactive squad voice

- Commit a437436 (game main).
- HUD v2 (`tools/scenes/rig.py` `add_hud`, `game/assets/scripts/hud.luau`, new textures from `tools/ui/build_ui_textures.py`):
  - A heading compass sits top centre: a clipped strip with ticks every 15 degrees, cardinal and intercardinal labels, a centre notch, a heading readout, and the waypoint diamond with its distance.
  - A squad roster lists each operator with a status dot and state (ON YOU / HOLDING / MOVING / MOUNTED / ENGAGED / HIT, plus distance past 25 m).
  - Vitals show health with a trailing damage bar, segment marks and colour by level, plus a stance and torch line.
  - The weapon block has a large magazine count (amber at a quarter, red when empty), the reserve, up to 40 magazine pips and a reload progress bar. `weapons.luau` now writes `Game.weapon_hud.mag` and `.reload`.
  - Damage feedback is eight directional wedges and a red edge vignette with a heartbeat pulse at low health.
  - The textured hit marker is white for a body hit and red for a head hit, and turns into a larger amber mark on a takedown. A short takedown feed shows "CONTRACTOR STUNNED · HEAD" and surrenders.
  - The reticle turns red over an awake contractor and blue over a teammate (raycast every 0.08 s).
  - The interaction prompt is a key chip plus a label.
  - The calm HUD fades the vitals, weapon and squad blocks to 40 % after 8 s with nothing happening.
- `tools/scenes/patch_hud.py` re-emits the HUD and pause canvases in every scene from `rig.add_hud()`. That beats regenerating the worlds, and the uuid5 keys are the same. It patched 49 scenes; `--check` now reports 0 stale. A patched `tests/hud.vscene` matches a full `build_dev_range.py hud` regeneration entity-for-entity, apart from six `Carbine Body[i]` uuids where the committed dev-range scenes already differ from the current generator (pre-existing).
- Reactive squad voice (`game/assets/scripts/lib/reactions.luau`, run by `ensemble.luau`). Its 128 new voiced lines (`react_*`, `grey_*`) are rendered with Kokoro, with emotion-paced tempo for these new barks only; story lines keep their takes. Operators react to:
  - being aimed at and to friendly fire, both voiced by the operator involved;
  - staring and bumping;
  - close thunder outdoors;
  - player hurt, low health, kit use, multi-takedowns and headshots;
  - wasted fire at nothing;
  - the torch on, or sprinting, near unaware contractors;
  - standing idle, jump spam, reloading under fire and running dry;
  - low cells while it's quiet, and the occasional rain remark;
  - flank callouts (behind / left / right) when the player is shot at from outside the view;
  - surrenders, and operators getting hit.
  Each reaction has its own cooldown, and every speaker must be present and within earshot (`Dialogue.bark` `near`/`radius`/`exclude`, up to 16 variants).
- Greyline contractors: voices are spatial now (not radio). Each contractor claims the shared voice key before speaking, so a line plays from that contractor's own head, and barks from more than 40 m away are skipped. New barks cover investigating (alert), being hit, giving up a search (calm), losing the target, suppressing fire and changing cells. Contractors now carry an 18-30 round magazine and take a real 2.4-3.2 s pause to reload (`enemy_reloading` event). `Game.awareness` / `Game.awareness_level` are set from contractor states (SEARCHING / COMPROMISED).
- New events: `thunder`, `friendly_hit`, `operator_hit`, `player_jumped`, `dry_fire`, `reload_started`, `squad_reaction`, `enemy_reloading`.
- Fixed during testing: `near_miss` passes a muzzle position (vector), not an entity. The first reactions build indexed it as an entity and broke enemy fire in squad_combat/enemy_fire; the handler now accepts both.
- Ran (engine VICTUS 1e0d86a, Release): `python3 tools/audio/build_voices.py --model /tmp/kok` (425 lines), `victus import game` (0 failed), `victus check game` (247 scenes, 41 scripts: 0 problems), `python3 tools/scenes/patch_hud.py` (49 patched) and `--check` (0 stale).
- Autotests PASS: reactions 10/10 (new), hud_look 1/1 (new), squad, squad_combat 5/5, enemy_fire 3/3, chatter 5/5, hud, weapons, pause_ui, sniper, vm_reload, trunk, vehicle.
- story_op01 still FAIL: the known face.luau 250 ms watchdog fired on both runs, so the plan did not reach its checks in 1800 frames. This is the pre-existing issue above, not yet fixed.
- Captured `shot.sh scenes/tests/hud_look.vscene 40 docs/evidence/hud_v2.png 1280 576` and inspected it on lavapipe. The compass heading matches the view (347°, N 13° right), the waypoint diamond and distance show, the squad roster, health trail, mag pips, hit marker, damage wedge, feed and awareness all render, and a squad hurt bark replaced the scripted subtitle.
- Not measured: on-device cost of the extra ~130 HUD entities per scene, or the reticle raycast.

## 2026-11-20 story_op01 watchdog fixed (engine: background navmesh builds)

- Cause: it was not the face code. `VICTUS_SCRIPT_SLOW_CALLS=40` (new engine diagnostic) logged `slow native call available: 24591.2 ms`. The first `nav.available()` call in `operator.luau` (follow mode, `nav.nearest` for the slot) built the 1024 m terrain navmesh synchronously inside the script call. The budget error then surfaced at the next VM interrupt check, which happened to be in `face.luau`'s head search. A coarser `NavMeshSurface` (0.3 m cells) only cut the stall to 14.8 s, so it was not kept.
- Fix in VICTUS cd59c05 (engine main, see its docs/STATUS.md "Background navmesh builds and script budget accounting"): large navmeshes cook on a worker thread. `nav.available()` returns false until the mesh is installed, and `operator.luau`/`enemy.luau` already fall back to the raw slot or noise point. Navmesh builds and first-use model loads are no longer charged to the script budget. No game script change was needed.
- Ran: `SOPS_TEST_FRAMES=2400 python3 tools/test/run_autotests.py story_op01` before the fix: script error at the first operator update. After the fix: `SOPS_TEST_FRAMES=19800 ... story_op01` PASS, 19 800 frames, 0 script errors, all 15 stages (trail through enter_facility), completed=op03.


## 2026-11-20 Surface footsteps, gear foley and footstep noise for AI

- Commit: 4fb0e42 (game main).

- New `game/assets/scripts/lib/footsteps.luau`.
  - It detects the surface under a foot with a downward ray. On terrain, the splat layer picks dirt, gravel or grass. Off terrain, keywords in the entity name and up to 5 parent names pick metal or wood, and anything else is concrete. Results are cached per entity per scene.
  - It reads the scene's `Weather` component. In rain, outdoor soft ground becomes mud and puddles add splashes.
  - It plays a step, a gear rattle when moving fast, and a soft or hard landing.
- `fp_player.luau`: one footfall per head-bob half cycle.
  - Each footfall emits `player_step` and an AI noise through `Combat.noise`. Reach is 7.5 m sprinting and 1.8 m walking; crouching is silent. Reach is scaled by surface loudness, halved in rain, and throttled to one noise per 0.55 s.
  - Landings make a sound and a noise (9 or 5 m × loudness). A hard landing (fall speed > 6.5 m/s) shakes the camera.
- Operators, NPCs and Greyline contractors (`lib/actor.luau`) default to `surface = "auto"` with gear rattle. The surface is re-detected every 4 steps.
- `tools/audio/build_sfx.py` adds 4 variants each of gravel, grass, mud, wood and splash steps, plus `gear_0..2`, `land_soft` and `land_hard`. All are synthesised and deterministic; existing outputs are byte-identical.
- Ran (engine VICTUS cd59c05, Release): `victus import game` (0 failed), `victus check game` (249 scenes, 42 scripts: 0 problems).
- Autotests PASS: footsteps 8/8 (new: surface = concrete on the range, walk 2.67 steps/s with 1.8 m reach, sprint 3.50 steps/s with 7.5 m reach, crouch 5 steps with 0 noises, landing noise), movement, weapons, hud, squad, squad_combat, enemy_fire, reactions, chatter.
- `SOPS_TEST_FRAMES=19800 ... story_op01` PASS: 19 800 frames, 0 script errors.
- Not tested: whether the rain/mud and terrain-layer branches pick the right surface in the outdoor worlds. The new plan only covers the dev-range ground. The sounds have not been listened to on a device.

## 2026-11-20 Greyline contractor tactics: real cover, peeking, flanking, suppression, sweeps

- Commit: ed61743 (game main).

- New `game/assets/scripts/lib/tactics.luau`. Kestrel has no authored cover nodes, so cover is whatever stops a pulse: terrain folds, tree trunks, rocks, logs, vehicles and walls (the colliders the shots use).
  - `find_cover` samples 18 points within 9 m and snaps them to the ground (terrain height or a ray down) and the navmesh. It keeps points where a ray from the threat's eye to a crouched chest (0.95 m) hits a non-character collider.
  - Scoring favours peek spots (standing at 1.55 m clears the obstacle) and short, sideways rather than forward moves. It penalises open midpoints on the run and points another fighter has claimed.
  - Also adds `exposed`, `flank_point` (70° off the line of fire, 10-18 m from the threat) and `search_points`.
- `enemy.luau`:
  - After the first burst, or at once when hit, an exposed contractor dashes to cover (3.8 m/s, no firing while moving) and barks `grey_cover_*`.
  - In cover it crouches between bursts and while changing cells, and stands to fire. Every 1.4-2.2 s it re-checks the cover and relocates if the threat has moved round it, or sometimes after being hit.
  - In a group with two or more engaged, one contractor at a time flanks via cover near the flank point (25 s group cooldown). It barks `grey_flank_*` and emits `enemy_flanking`, and the squad warns `react_eflank_*`.
  - On losing sight, a contractor fires a few wider bursts at the last known position for 0.35-2.4 s, then searches after 3 s (was 1.5 s).
  - On reaching a search spot, it sweeps 3 points around it, pausing and looking around at each (gives up after 26 s).
  - Repeated noises within 5 m refine the search spot instead of restarting it. A new noise halts the old walk.
- 10 new voiced lines (Kokoro, `tools/audio/build_voices.py`, 435 total): `grey_flank_1..3`, `grey_cover_1..3`, `react_eflank_1..4`.
- New events: `enemy_in_cover`, `enemy_flanking`, `enemy_sweep`.
- New autotest `enemy_tactics` (dev range, two alerted contractors, player made unhittable; scene `tests/enemy_tactics.vscene`). It PASSES 10/10, on 3 runs:
  - the cover geometry check;
  - both contractors reach cover;
  - the held position is hidden from the player;
  - both crouch in cover;
  - exactly 1 flank;
  - contact, cover and flank barks;
  - 6 shots at the last known position after the player hides;
  - both switch to searching;
  - a nearby noise starts a sweep.
- Ran (engine VICTUS cd59c05, Release): `victus import game` (0 failed), `victus check game` (250 scenes, 43 scripts: 0 problems).
- Regressions PASS: squad_combat, enemy_fire, reactions, chatter, hud_look, footsteps, squad, and story_op01 (19 800 frames, 0 script errors).
- Not tested: the squad `eflank` warning (no plan has operators and a flanker together). Also untested: cover choice among the streamed trees and rocks of the open world, and the cost of the ~70 rays per cover search on device. The search runs at most every 0.45-0.75 s per engaged contractor, and only while it is in the open.

## 2026-11-20 Squad cover in firefights; contractors stop shooting into their own cover

- `operator.luau` (`Op:combat_move`): in follow mode, engaged and within 12 m of the player, an operator no longer just stops. It uses `Tactics.find_cover` (7 m radius, 5 m minimum from the threat) against its last target and keeps clear of other operators' spots and the player's. It runs there at 1.4× speed, barks `bark_cover_*` (its own voice), crouches between bursts and when staggered, and re-checks the cover every 1.1-1.8 s. The cover only counts if it stays within 14 m of the player; when the fight ends or the player moves away, it returns to formation. New event `squad_in_cover`.
- `enemy.luau`: before each shot, `Tactics.clear_shot` checks the first min(6 m, half the range) of the line. A shot blocked by the contractor's own rock or step is not fired.
  - After 3 blocked attempts the contractor relocates to cover where standing clears the obstacle (`Tactics.can_peek`), or sidesteps 2.5 m.
  - Holding the current spot as cover now also requires being able to peek.
  - Found by the new plan: one contractor squatted behind the range's Step 2 for 40 s, firing 25 bursts into it while the squad could not see it (asymmetric 1.6 m eye vs 1.45 m target point).
  - Blocks further out (the cover the target ducked behind) still take suppressing fire.
- `reactions.luau`: the `eflank` warning gets a 3 s queue ttl so it is not dropped behind combat barks.
- 4 new voiced lines: `bark_cover_1..4` (Kokoro; 439 lines total).
- New autotest `squad_cover`: four operators, two alerted contractors and four crates; the player is unhittable. Scene `tests/squad_cover.vscene`; 3620 frames by default in `run_autotests.py`, and `enemy_tactics` defaults to 1620. Result: PASS 6/6.
  - all 4 operators reached cover;
  - 5 arrivals were hidden from their target;
  - the 1 flank was warned about by the squad (`react_eflank`);
  - 4 operators crouched in cover;
  - both contractors were down by 45 s (before the clear-shot fix: 1 of 2 by 60 s).
- Regressions PASS: enemy_tactics 10/10, squad_combat, enemy_fire, reactions, chatter, squad, hud_look, story_op01 (19 800 frames, 0 script errors). `victus check game`: 251 scenes, 43 scripts, 0 problems.
- Not tested: operators in hold/move orders (unchanged: they stay put), and cover choice among open-world trees.

## 2026-11-20 Bounding overwatch and pair searches (Greyline)

Doctrine followed (cited in docs/world/SCALE_AND_PACING.md): individual rushes last 3-5 s ("I'm up, he sees me, I'm down", [FM 3-21.8 / InfantryDrills](https://infantrydrills.com/manuals/fm-atp-3-21-8-infantry-rifle-platoon-squad-2024/movement-and-maneuver/tactical-movement-approach-march/movement-techniques/), [USMC patrolling](https://www.trngcmd.marines.mil/Portals/207/Docs/FMTBE/Student%20Materials/FMST/204.pdf)); in bounding overwatch one element is always stopped to cover the one that moves ([FM 3-21.9](https://www.globalsecurity.org/military/library/policy/army/fm/3-21-9/chap3.htm)).

- `enemy.luau`:
  - every cover move and flank rush asks the nearest set group mate to overwatch. The mate steps up his fire on the threat (0.45-0.75 s between bursts instead of 1.2-2.0 s) and holds his position until the rush ends. The mover calls `grey_moving_*`, the mate answers `grey_covering_*` ~0.9 s later, and the arrival may call `grey_set_*`.
  - one man up at a time: a contractor waits (0.7 s re-checks) while a mate is mid-rush, unless rounds are landing on him (hit in the last 1.5 s).
  - cover rushes are capped at 4.5 s; flanks are now up to 4 rushes of ≤ ~14 m (12 m step plus cover near it), each ≤ 5 s with a 1-2 s pause in cover, instead of one 9 s run in the open.
  - searching in pairs: a contractor heading for a spot a mate is already sweeping holds within 11 m and watches the mate's current search point (`enemy_sweep_cover`); it stands down when the mate finishes. While both sweep, the one paused holds while the other walks (≤ 6 s).
  - fixed a sweep bug: after reaching a search point the arrival check re-fired every frame, so a contractor whose halt left it > 1 m from the point never moved on (seen as `sweep_i` stuck at 1 for 14 s). Legs now also time out after 6 s.
  - new events: `enemy_bound` (kind, {dur, by}), `enemy_overwatch`, `enemy_sweep_cover`. Note: `Game.emit` passes at most 3 arguments.
- 12 new voiced lines `grey_moving/covering/set_1..4` (Kokoro; 451 lines).
- `tools/test/run_autotests.py`: a plan now also fails on any `[error] [script]` line in the log. The engine's "N script errors" count does not include runtime errors that disable a script mid-run (seen while writing this slice: count 0 with `enemy.luau` disabled). `enemy_tactics` default raised to 2140 frames.
- `enemy_tactics` now 15/15: 3 rushes, longest 3.9 s; 3 of 3 rushes covered by a mate; 0 samples with both rushing; moving and covering callouts heard; the second searcher held and covered the first (1 hold); plus the 10 earlier checks.
- Ran (engine VICTUS cd59c05, Release): `victus import game`, `victus check game` (251 scenes, 43 scripts: 0 problems).
- Regressions PASS (with the stricter error check): movement, weapons, hud, squad, squad_combat, enemy_fire, reactions, chatter, hud_look, footsteps, squad_cover. story_op01: see below.
- Not tested: bounding among open-world trees (the dev range has blocks and crates), three-man groups, and the Halyard side (operators do not bound yet).
- story_op01 PASS (19 800 frames, 330 s game time, 0 script errors, no runtime script errors in the log): all 15 stages through `enter_facility`.

## 2026-11-20 Awareness: gradual noticing, weapons tight, team takes a knee

- `enemy.luau` `E:notice_rate`: seeing a target fills an awareness meter instead of starting a fight on the first visible frame (rates and multipliers in docs/world/SCALE_AND_PACING.md). At 0.4 a patrolling contractor halts, says `grey_huh_*`, stares and then walks over to look (`enemy_suspicious` event). At 1.0 he engages. The meter decays out of sight. Searching contractors skip the "huh" (they are already suspicious), so it does not mask the `contact` bark.
- Pair search refinement: the closer contractor checks the spot and the other covers. The one who arrives first waits up to 10 s for a mate still on his way (11-40 m out) before going in.
- `world/storm.luau` publishes `Game.flash` (lightning level 0-1); lightning makes everyone easier to see.
- `operator.luau`:
  - weapons tight. Operators do not open fire on contractors still in `patrol` state unless the player has fired in the last 15 s (`Squad.state().player_shot_t`, set in `weapons.luau`).
  - when the player crouches, operators take a knee at every halt.
- 4 new voiced lines `grey_huh_1..4` (459 with the Op01 search-line lines staged next).
- New autotest `stealth` (dev range, one unalerted contractor 18 m out, player unhittable): PASS 5/5. Crouched, still, light off for 6 s: not engaged (awareness 0.29). Standing, light on: suspicious 0.3 s later, engaged 2.5 s later; the "huh" bark was heard.
- `run_autotests.py`: picks the engine log by the child's pid (`victus-<t>-<pid>.log`), not "newest". A concurrent run had been read as this run's log, and that produced false FAILs.
- Regressions PASS: stealth, movement, weapons, hud, squad, squad_combat, enemy_fire, reactions, chatter, hud_look, footsteps, enemy_tactics 15/15, squad_cover 6/6.
- Not tested: foliage concealment (grass and bushes do not lower awareness yet; only colliders block sight), and the lightning multiplier (no plan has a storm).
- story_op01 PASS (19 800 frames, 0 script errors) with the awareness model and weapons tight.

## 2026-11-20 Op01 search line (a stealth-or-fight beat between the footbridge and the cabin)

- Why: the Op01 forest is about 300 m x 600 m, and only one authored fight (the ravine) fell in its first 400 m (docs/world/SCALE_AND_PACING.md). The search line adds a decision point at ~120 m from the trailhead.
- `tools/world/chapters.py` group `line`: three dormant contractors at x 112-120, z 162/172/182, with patrols running west to x -40..-48 (10 m apart, as in a real line search). It also writes `scenes/tests/op01_line.vscene` and `op01_line_loud.vscene`.
- `missions/kestrel.luau` `M:update_line` runs in the `trail` and `cabin` stages:
  - within 28 m of the footbridge the line wakes and walks at 1.25 m/s, weapons at low ready, sweeping its lights ±40°;
  - 4 s later the team holds and talks it through (`op1_line_01..04`), and resumes following if the player walks off more than 25 m;
  - overheard contractor talk `grey_line_1..6` within 34 m;
  - if anyone engages: `op1_line_08/09`;
  - the contractors are stowed past x -36. On completion: quiet → `op1_line_05..07`, loud → `op1_line_10`. Events: `line_start`, `line_loud`, `line_passed`;
  - the cabin talk and trail progress wait while a fight is within 45 m.
- `enemy.luau`: `E:stow()`, and low-ready plus light sweep while on the line.
- New plans in `tests/world_plans.luau` (player unhittable):
  - op01_line PASS 8/8: crouched with the light off 22-32 m from the line, max awareness 0.01, never engaged; `line_passed` fired, all 3 stowed, the team calls were heard and the contractors were overheard.
  - op01_line_loud PASS 6/6: standing in its path with the light on, `line_loud` fired, the team call was heard, 3 of 3 contractors were down by 110 s, and there was no quiet ending.
- Ran: `python3 tools/world/chapters.py`, `victus import game`, `victus check game` (254 scenes: 0 problems), `run_autotests.py op01_line op01_line_loud` (9700/6700 frames), and story_op01 with SOPS_TEST_FRAMES=19800: PASS.
- Note: regenerating the chapters also renumbered some Mule cargo entity UUIDs in every chapter scene. Names and transforms are unchanged.
- Not tested: a player who stands still with the light off (only the crouched case), and walking alongside the line.

## 2026-11-20 Forest cover pockets

- `tools/world/world_scene.py` `COVER_POCKETS` / `place_cover_pockets` (seed 907) adds 30 pieces of cover:
  - 7 on the footbridge / search-line stretch (TRAIL 4-8): 5 boulders, 2 deadfall;
  - 23 between the cabin and the relay (TRAIL 10-15): 6 boulders, 17 deadfall.
- Piece types:
  - boulder: photoscanned rock_b at x1.2-1.45 with a box collider just inside the scan, plus a rock_a beside it;
  - deadfall: two crossed log_a trunks, ~1.1 m high, with box colliders.
- Placement rules:
  - every 9-12 m along the path, on alternating sides; rows at 3-7 m and 11-16 m off the path;
  - long axis along the trail;
  - ≥ 2.6 m from the trail centreline and clear of the creek;
  - ≥ 1.6 m from trunks;
  - ≥ 4.5 m from every patrol leg in `chapters.GROUPS`, so the line and patrol contractors never walk into one.
- Measured before the pass (r = 20 m around trail points, streamed cells): footbridge 2 logs and 1 large rock, line crossing 3 logs and 0 rocks, patrol 5 logs and 0 rocks. The ravine already had 14-19 large rocks.
- Ran: `python3 tools/world/worldgen.py scene` (194 cells; only the cells of the two pockets changed in content), `python3 tools/world/chapters.py`, `victus import game`, `victus check game` (254 scenes, 0 problems).
- Renders: `tools/test/shot.sh` at 960x540 medium from (22,196) and (28,84) (temporary scenes, removed). Boulders and deadfall sit on the ground, read as natural forest cover, and are clear of the trail.
- op01_line PASS, op01_line_loud PASS, story_op01 PASS (19 800 frames).
- Limitation found: `victus simulate` does not stream world cells, so no headless test has seen trees, rocks or this cover. The world_* view plans (world_forest, world_relay, world_creek, world_trail_walk) fail on "streamed" for that reason, as they did before this change. Next: stream cells in `victus simulate` (engine).

## 2026-11-20 Halyard bounding overwatch, stuck recovery

This follows the doctrine notes in docs/world/SCALE_AND_PACING.md: 3-5 s rushes, one man up while a mate covers, and "Moving" / "Set" calls.

- `operator.luau`:
  - one man up: an operator holds (re-checking every 0.6 s) while a mate is rushing to cover, unless he was hit in the last 1.5 s;
  - rushes are capped at 4.5 s;
  - the nearest engaged, set mate within 22 m covers the move. His burst gap drops to 0.45-0.75 x cadence, and he calls "covering" 0.8 s later;
  - the mover calls "moving", or falls back to the "cover" bark when nobody can cover. On arrival there is a 40% chance of a "set" call;
  - event `squad_bound` {who, by};
  - the reload bark is now attributed to the operator who reloads.
- `lib/actor.luau` `Actor:steer` (direct-steered actors): if an actor moves less than 25% of the wanted speed for 0.8 s, it detours toward the clearer side (3 m rays) for 0.9-1.5 s. `unsticks` counts the detours.
- `tools/dialogue/lines.py`: added bark_moving_1..8, bark_covering_1..6, bark_set_1..5, bark_cover_5 and bark_reload_4/5. Voices were rebuilt with `python3 tools/audio/build_voices.py --model /tmp/kok` (493 lines).
- `missions/kestrel.luau`: search-line contractors are stowed past x -30 instead of -36, still out of sight in the west woods. With engine d1e1227 the headless test now streams the real trees. The last contractor took a few seconds longer through them and was 2 m short of the old line when the plan ended; unsticks was 0, so he was not stuck.
- `tests/squad_plans.luau` squad_cover adds three checks: `bounding_overwatch`, `one_man_up` and `moving_covering_calls`. `tests/world_plans.luau` op01_line now names any contractor that was not stowed.
- Results:
  - squad_cover PASS 9/9: 6 moves, all 6 covered by a mate, 2 samples with two men rushing;
  - op01_line PASS;
  - op01_line_loud PASS;
  - PASS: stealth, movement, weapons, hud, squad, squad_combat, enemy_fire, reactions, chatter, hud_look, footsteps, enemy_tactics;
  - world_forest, world_relay, world_creek, world_ravine and world_trail_walk PASS. They had failed on "streamed" until engine d1e1227;
  - story_op01 PASS (19 800 frames, all 15 stages).

## 2026-11-20 Third-person reloads (operators and contractors)

- `lib/actor.luau`: `Actor:reload(seconds, {out, inn, charge})` and `Actor:reloading()`.
  - The carry blends to a chest-high pose with the muzzle forward-down (RELOAD_P/RELOAD_DIR) and is canted 38° onto its side. `look_at` cannot roll, so the script sets the rotation directly. A small dip and lift happen as the cell comes out and goes in.
  - The support-hand IK weight goes to 0 from 14% to 60% of the reload (strip the cell, fetch a fresh one), then back onto the gun.
  - Cue sounds at 18/58/78% are played at the actor when the camera is within 28 m.
- `operator.luau`:
  - a real cell per weapon from `Items.defs` (pdw 40, dmr 12, breacher 6, carbine 30) replaces the old "every 24 shots";
  - running dry calls "reload", pauses fire for `reload_empty` + 0.35 s and animates;
  - after contact ends (or 1.2-2.7 s later), a cell under 75% is topped off with a quieter "topoff" call;
  - event `npc_reload` {who, tactical}.
- `enemy.luau`: contractors animate and sound their existing cell-change pause.
- Lines: bark_topoff_1..5 and bark_reload_6/7. Voices rebuilt (500 lines).
- Tests:
  - `squad_cover` `operators_change_cells` PASS: 6 reloads (2 tactical), 48 samples mid-reload, canted, hand off the gun.
  - `enemy_tactics` `cover_is_cover` is now sampled every 0.5 s from 10 to 20 s instead of a single 16.0 s snapshot. The cell-change pose moves the muzzle a little, which shifts the whole fight. At 16.0 s one contractor was mid-rush to cover and the other was not yet in cover. The property itself is unchanged: a holding position hidden from the player.
  - New screenshot plan `squad_reload_look` (operators frozen mid-change). Rendered with `tools/test/shot.sh scenes/tests/squad_reload_look.vscene 40 … 960 540 medium`, saved as docs/media/npc_reload.png: rifles canted in at the chest, support hands off.
  - Known limitation: the hand hangs at the side rather than reaching a pouch, because there is no arm clip for that yet.
- Results:
  - squad_cover PASS;
  - enemy_tactics PASS;
  - squad_combat, squad, enemy_fire, reactions, chatter, hud_look, stealth PASS;
  - op01_line and op01_line_loud PASS;
  - story_op01 PASS (19 800 frames).
