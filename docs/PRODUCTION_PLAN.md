# Production Plan — Dependency-Ordered Delivery

This plan is an execution queue, not a reason to stop coding after a design document. The autonomous agent should complete verified slices in order, commit them to `main` and continue.

## Canonical campaign narrative

The complete end-to-end campaign is specified in docs/CAMPAIGN_STORY_BIBLE.md. This is the authoritative narrative source for mission objectives, story logic, factions, characters, dialogue direction, the reason for the bunker descent, the VICTUS explanation and the ending. Read it before changing campaign scenes or writing mission dialogue. Read `docs/SQUAD_BANTER_AND_AMBIENCE.md` as well before authoring dialogue, environmental audio or fear reactions; it is the canonical tonal implementation guide.

The story design is complete; implementation is not. Do not invent a replacement plot, turn Greyline into a generic enemy army, change the non-lethal pulse-weapon direction, make VICTUS a superweapon or AI, or alter the inert V-01 dummy reveal. Operation geometry and encounter staging may adapt to verified VICTUS capabilities, but the cause-and-effect story in the story bible is canon.

## Progress status (kept current; details and evidence in BUILD_AND_TEST_LOG.md)

| Piece | State | Evidence |
|---|---|---|
| P0 baseline: VICTUS built, project generated, character/forest asset generators | Done | log P0 |
| P1 scene tooling, first-person controller, unified input, HUD, pause/settings, menu, credits, autotests | Done (desktop/headless; no phone) | log P1, autotests movement/hud/pause_ui |
| Weapons and viewmodel (PC-7 Lantern carbine, SP-2 Wren sidearm, field scanner) | Done (implemented, simulated, visually inspected on lavapipe; not device-tested) | log P1 weapons, autotest weapons 26/26 |
| Squad operators, companions, dialogue, enemies (Anchor, Patch, Echo, Tally; Greyline A/B; Ranger Hollis; 76 voiced lines) | Done on the dev range (implemented, simulated, visually inspected on lavapipe; not device-tested; squad size not yet profiled on the phone) | log P3 squad, autotests squad 17/17, squad_combat 5/5, enemy_fire 3/3 |
| Mule vehicle (drive-in, park, staggered squad egress), cargo trunk storage, shared inventory, LR-4 scope, field kit | Done on the dev range (implemented, simulated, visually inspected on lavapipe; not device-tested) | log "Vehicle, cargo storage…", autotests vehicle 14/14, trunk 26/26, sniper 19/19, docs/evidence/ |
| Squad dark-comedy dialogue, scare-comedy ambience, idle squad chatter on quiet walks | Done (303 voiced lines; chatter plan 5/5; not device-tested) | log "Story revision 2" |
| Campaign story bible revision 2 (storm night 02:40-05:52, convoy deadline, Brick, seeded V-01, Sorn stand-down, epilogue) | Done (design) | docs/CAMPAIGN_STORY_BIBLE.md section 1A, `f30aeb7` |
| Kestrel Valley open world (lay-by, woods, perimeter, yard) and interiors (station, bunker, basement, review chamber) | Done (desktop/headless) | `28eea22`, `3c133b4`, `5ad387b` |
| Prologue, Op01-Op07, V-01 reveal, epilogue, credits | Done (story autotests pass on desktop; Op01 intermittent face watchdog, see log) | story_* autotests |
| Storm night: rain, wet ground, puddles, volumetric fog, moon, lamps, searchlights, lightning/thunder, weapon light | Done (lavapipe-inspected; unprofiled on phone) | `7a235c7`, docs/evidence/night_prologue.png |
| Five-operator squad (Brick added) and extra firearms (KV-5 Hornet, BR-9 Ram, MR-6 Kestrel, camp arms case) | Done (armory 20/20) | `8d6a7b6` |
| Night menu/credits, README rewrite | Done | `35172db`, `26c532e`, docs/evidence/menu_night.png |
| Desktop export | Done (export builds and boots to the menu under xvfb) | log "Story revision 2" |
| Android APK | Attempted on the build machine; see log for the result. Device install/run not done (no phone) | log |
| HUD v2 (compass, squad roster, mag pips, reload bar, damage wedges, vignette, hit/takedown marker, feed, calm fade) | Done (desktop/headless, lavapipe-inspected; not device-tested) | log "HUD v2 and reactive squad voice", docs/evidence/hud_v2.png |
| Reactive squad voice (128 new lines: aimed-at, friendly fire, stare, bump, thunder, flank callouts, waste, torch/sprint near guards, idle, low hp, reload cover) and spatial Greyline barks with real reloads | Done (reactions 10/10; not device-tested) | same log entry |
| story_op01 time-budget error fixed (engine VICTUS cd59c05: background navmesh builds) | Done (story_op01 PASS 19 800 frames, 0 script errors) | log "story_op01 watchdog fixed" |
| Surface-aware footsteps, gear foley, landing, footstep noise heard by AI | Done (footsteps 8/8; regressions pass) | log "Surface footsteps" |
| Contractor tactics: real cover from colliders, peek/duck, one-at-a-time flank, suppress last known, search sweeps | Done (enemy_tactics 10/10; regressions pass) | log "Greyline contractor tactics" |
| Squad takes real cover in follow-mode firefights; contractors relocate instead of shooting their own cover | Done (squad_cover 6/6; regressions pass) | log "Squad cover in firefights" |
| Bounding overwatch: 3-5 s covered rushes with "Moving!/Covering!/Set!", multi-rush flanks, one man up at a time, pair searches (one checks, one covers) | Done (enemy_tactics 15/15; regressions pass) | log "Bounding overwatch" |
| Awareness model (gradual noticing by distance, stance, movement, lights, lightning; "huh" pause), squad weapons tight on unaware contractors, team kneels when the player gets low | Done (stealth 5/5; regressions pass) | log "Awareness" |
| Op01 search line: three contractors sweep east -> west across the trail below the cabin; let it pass low and dark (team holds, kneels, comments) or fight it | Done (op01_line 8/8, op01_line_loud 6/6, story_op01 pass) | log "search line" |
| Forest cover pockets: 30 seeded boulders and deadfall along the footbridge and cabin-to-relay stretches, one 3-5 s rush apart | Done (built, streamed, inspected in renders; story_op01 pass) | log "cover pockets" |
| Halyard bounding overwatch: one man up at a time, 3-5 s rushes, nearest set mate covers with faster bursts, "Moving" / "Covering" / "Set" calls; actor stuck recovery | Done (squad_cover 9/9, op01_line 8/8 with streamed trees, regressions and story_op01 pass) | log "Halyard bounding" |
| Third-person cell changes: magazine-based reloads for operators, tactical top-offs in a lull, rifle cants in and the support hand leaves the gun, positional cell-out/in/charge sounds (contractors too) | Done (squad_cover operators_change_cells; regressions and story_op01 pass) | log "Third-person reloads" |
| Faces react to the fight: strain under fire, startle on near misses and hits (habituating), faster blinking under stress, blinks on big gaze shifts, mouth-breathing after hard running | Done (squad_cover faces_show_the_fight; regressions and story_op01 pass) | log "Faces react" |
| NPC shot impacts: sparks and dust where Halyard and Greyline pulses land near the camera (pooled emitters), impact sound within 14 m | Done (squad_cover npc_impacts; regressions and story_op01 pass) | log "NPC shot impacts" |
| Rifle follows the body: an NPC's carried weapon tracks the chest bone's drop (kneeling, stumbling), so a kneeling operator holds it at the waist instead of at head height | Done (squad_cover kneeling_rifle_low; render docs/media/kneel_carry.png) | log "Rifle follows the body" |
| Crouched gait: CrouchWalk / CrouchRun clips derived from each character's own Walk and Run (tools/characters/add_crouch_clips.py), a Crouch state in human.vanim; the team moves low when the player does and kneels at halts | Done (squad_crouch_look 2/2; render docs/media/crouch_gait.png) | log "Crouched gait" |
| Post-contact sound-off: when the fight is over (no awake contractors, nobody engaged for 3 s) Anchor calls "Halyard, sound off", two operators answer (anyone hit says so) and Anchor moves them on; 17 new voiced lines | Done (squad_cover sound_off; full regression + story_op01) | log "Post-contact sound-off" |
| Surface-aware impacts: rounds that miss sound and kick debris by what they hit (dirt, wood, stone, metal; two synthesized takes each), for the player and NPC fire | Done (squad_cover impact_surfaces; op01_line_loud forest_impacts dirt 35 / wood 73 / stone 10) | log "Surface-aware impacts" |
| Photoscanned interior dressing for Op04–Op07: 48 Poly Haven CC0 props (desks, cabinets, shelving, crates, barrels, generator, compressor, carts, safety kit, CCTV, wall fittings, desk clutter, Venn's radio desk, lab kit) rebuilt to mobile budgets and placed room by room around doors and story marks; playtime measured per chapter (`docs/world/PLAYTIME.md`) | Done (story_op04–op07; squad, squad_combat, enemy_fire) | log "Interior dressing and playtime" |
| Interior exposure lift (bunker, archive) and location-neutral generic barks | Done (17-plan regression) | log "Interior exposure and location-neutral barks" |
| ADS sight pictures: open reflex windows with a red dot for PC-7 and KV-5 (no opaque glass in the eye line), BR-9 stock below the aimed view; ADS plans for every primary | Done (vm_ads, vm_ads_pdw, vm_ads_breacher, vm_ads_dmr; renders docs/media/ads_*.png) | log "ADS sight pictures" |
| HUD centre discipline: toasts wait for title cards and fades, stale objective toasts are dropped, duplicates merged; objective panel slides in with an accent flare on change | Done (hud 6/6, story_prologue) | log "HUD: one thing at a time" |
| Baked interior bounce lighting (Op04, Op05, Op07) | Done — lightmaps baked with VICTUS bake-lighting, story runs PASS; Op06 archive pending a lighting pass | docs/media/bake_interiors_before_after.png |
| Body-cam weapon handling (stress reloads, fumbles, cell check, re-grip) | Done — reload_feel 19/19, weapon regressions PASS | docs/media/reload_tactical.png |
| Body-cam lens motion (roll, acceleration tip, sprint jolt, weapon inertia) | Done — reload_feel 22/22, movement/weapons PASS | |
| Storm-night grade v3 (blue-grey mist, more contrast, thinner rain) | Done — 12 scenes regraded | docs/media/night_grade_v3.png |
| Hands v2: first-person hands with real fingers (MakeHuman CC0 mesh, posed per finger, trigger finger, thumbs forward, clean glove/sleeve cuffs) | Done — `docs/media/hands_v2.png` | `tools/assets/build_vm_arms.py` |
| Hot 10S validation: frame time, memory, thermals, touch feel | Not done — requires the physical phone | |

## P0 — Baseline and device proof

**Goal:** determine that the engine can run a minimal game on the actual target before large art production.

Tasks:
- Inspect this repository and the current VICTUS main branch.
- Run the VICTUS toolchain checks and baseline tests.
- Generate a standard VICTUS 3D project using the current template/CLI.
- Confirm the Android project currently builds with the live SDK/NDK requirements.
- Inspect the real Hot 10S SKU, Android build, ABI, GPU, Vulkan driver and available memory.
- Build/install a minimal exported scene on the phone and prove launch, rendering, audio, touch, pause/resume and clean shutdown.
- Record logs and results. If the Vulkan path fails, isolate the blocker before proceeding with phone-specific performance promises.

**Exit gate:** a clean desktop VICTUS project and a minimal Android scene have both been built/run, with the phone result explicitly known. If device access is temporarily unavailable, record that exact blocker and continue the independent desktop slice.

## P1 — First-person controller, viewmodel and mobile input

**Goal:** establish the first-person shooter feel and prove the landscape controls.

Tasks:
- First-person player controller and camera, grounded movement and collision.
- Unified logical input layer for touch, controller and desktop keyboard/mouse.
- Working left virtual stick and right first-person look/aim region.
- Contextual interaction and field-tool buttons, plus fire, aim, reload and weapon-switch actions.
- Pause/settings modal that blocks background gameplay input.
- Touch pointer ownership, multitouch, cancellation, safe areas and app-resume reset.
- Gamepad discovery and dynamic input hints; touch UI can fade/hide when a gamepad is active.
- First-person arms/hand viewmodel prototype with stable camera alignment and tunable FOV/sensitivity.
- Landscape layout at 1640 × 720 and 16:9 emulator sizes.

**Exit gate:** simultaneous movement/look/interact works without pointer theft, stuck movement, UI click-through or camera jumps. Gamepad and desktop controls reach the same logical actions.

## P2 — Stage 01 environment blockout and render proof

**Goal:** build the complete forest path as a playable greybox, then add final environment assets.

Tasks:
- Lay out the route and player collision.
- Add the path, key sightlines, canopy framing and the four visual beats in `STAGE_01_FOREST.md`.
- Use placeholder geometry only during blockout; replace it with original/redistributable production assets before stage completion.
- Establish the outdoor directional/environment lighting and fog baseline.
- Add one camera-locked benchmark route and repeatable capture points.
- Add the forest's distant answering wildlife howls, nearby foliage movement and one harmless false scare; keep every source plausible and non-hostile.
- Add brief, distinct squad fear reactions with dialogue cooldowns; preserve player control and suppress chatter during critical objectives.
- Profile vegetation, alpha overdraw, shadow casters and asset memory.
- Compare visual captures at Low and Medium mobile quality.

**Exit gate:** the forest reads in landscape, the path stays visible, the player can complete the route, and performance captures exist.

## P3 — Art, materials, foliage, lighting and sound

**Goal:** make Stage 01 feel authored and visually coherent.

Tasks:
- Source or generate hero tree silhouettes, fern fronds, shrubs, ground cover, path materials and environmental props.
- Record per-asset license/provenance.
- Import through the real VICTUS asset pipeline; verify normals, scale, materials, LODs, alpha coverage and mobile texture formats.
- Use instancing and distance grouping for repeated foliage.
- Tune directional light, environment/IBL, selected cast shadows, sky, fog, exposure and restrained post-processing.
- Add spatial forest ambience, footsteps and authored environmental sounds.
- Implement the location-specific sound identities in docs/SQUAD_BANTER_AND_AMBIENCE.md: forest wildlife calls, perimeter sign/fence sounds, facility ventilation/PA, bunker door/pipe sounds, lower-basement cooling/archival machinery and the deliberate quiet before V-01.
- Integrate distinct operator reactions and occasional strong non-sexual profanity where contextually justified; keep the conspiracy, Venn's recovery and Northline losses serious.
- Profile on the physical phone and reduce the highest-cost features first if frame pacing or thermals fail.

**Exit gate:** the environment is not just a screenshot. It is interactive, packaged, visually readable and performs within the measured phone baseline.

## P4 — Operators, fictional weapons, combat and cinematic vertical slice

**Goal:** prove that first-person shooter gameplay, operators, props, dialogue and cinematics work together.

Tasks:
- Reuse V-01/V-02 through normal VICTUS project asset workflows.
- Create the protagonist first-person arms/hand rig, one allied operator and one opposing character; keep the initial cast small.
- Research and document original operator clothing, silhouettes, palette, voice and cinematic identity before final art.
- Create a small original fictional primary/secondary weapon set, first-person viewmodels and invented gameplay values.
- Implement aim, fire, reload, switch, reticle/HUD, sound, visual feedback and enemy response as one integrated gameplay loop.
- Integrate one complete, balanced, non-graphic shooter encounter into the real mission flow.
- Add locomotion, idle, turn, inspect, talk/listen and field-tool animations.
- Implement a bounded stumble/fall/recovery demonstration and verify player-root/capsule continuity.
- Use ragdoll only if its complete recovery path is stable; the audited VICTUS baseline has no automatic get-up/root follow.
- Implement the secondary non-weapon field utility tool and point-of-interest interactions.
- Implement one complete in-engine cinematic with camera choreography, character animation, dialogue, music/SFX, subtitles, skip and return-to-first-person handling.
- Produce real dialogue audio offline after voice/recording rights are checked.
- Add subtitles and lip-sync cue data; reserve morph targets for close-up hero faces and profile CPU cost.

**Exit gate:** one complete first-person shooter encounter is playable in the exported package, with a fictional weapon loop, enemy response, operator/NPC interaction, dialogue audio, subtitles, animation and one skippable cinematic that returns to first-person control correctly.

## P5 — Stage 01 complete with shooter and cinematic integration

**Goal:** deliver an independently playable first stage.

Tasks:
- Implement the prologue and Operation 01 story flow from docs/CAMPAIGN_STORY_BIBLE.md: briefing, Mule arrival/loadout, Hollis forest guide, first Greyline contact, active-site discovery and perimeter transition.
- Complete the route, objective chain, fictional combat encounter(s), field interactions, operator/NPC scenes, environmental awareness/alert states and Stage 02 transition.
- Deliver the opening cinematic, a key forest reveal and a transition cinematic into the perimeter.
- Add start/pause/settings, save/restore and clear stage completion.
- Add user-facing tutorials for mobile controls.
- Add optional diagnostics overlay with real metrics only.
- Add automated stage flow tests and capture checkpoints.
- Add a tone pass for contextual squad banter and brief fear reactions; verify critical objective/dialogue states suppress optional jokes.
- Build/export Android and desktop packages.
- Test a full session on the Hot 10S and record sustained results.

**Exit gate:** a new player can launch, understand controls, finish the stage, save/restore, and reach the conclusion on the target phone without a developer console.

## P6 — Research and build the complete campaign: perimeter, facility, bunker and basement

The narrative order and dramatic purpose for every operation are fixed in docs/CAMPAIGN_STORY_BIBLE.md. Implement the story in that order; do not build disconnected locations or invent new reasons for the player to descend. The Source Vault is the reason for the bunker and lower-basement chapters, and the V-01 dummy is the deliberately mundane final reveal.

For every campaign area after the forest, including a substantial lower-basement chapter, research before asset creation:
- Stage/operation purpose, player activity and campaign continuity.
- Visual reference collection, cited URLs and reference notes.
- Original architecture/prop/lighting design.
- Reusable modules and asset budget.
- Scene transitions and progression.
- Operator/enemy character requirements, costume designs, first-person weapon/viewmodel needs and audio requirements.
- Planned cutscenes and cinematic set pieces, with story triggers and return-to-gameplay states.
- VICTUS feature fit and known blockers.
- Mobile performance risks.
- License and redistribution audit.

Do not freeze a later area from generic assumptions. The required direction is forest → perimeter → facility → bunker → substantial basement → V-01 dummy reveal and ending. Each area must be a distinct playable space with its own objectives, combat/story beats, visual identity, audio and cinematic moments. Add a dedicated research/design brief for every operation/area and link it here. Completing one area is never the project completion gate; continue to the next unfinished area.

## P7 — Full-campaign polish, cinematic completion and showcase evidence

Tasks:
- Run a repeatable end-to-end test through the entire campaign on desktop, emulator and physical phone.
- Verify every operation, every required area including the basement, every weapon action, every operator interaction and all key cutscenes.
- Verify each location's distinct ambient audio and scare-comedy beats, dialogue cooldown/variation, fear animations, subtitle synchronization and target-device audio mix.
- Confirm all cinematic skip/replay/checkpoint/pause states return to first-person gameplay correctly.
- Add crash/log capture and a clean diagnostics/export report.
- Test suspend/resume, audio lifecycle, orientation/safe areas, controller disconnect/reconnect, storage pressure and save corruption recovery.
- Verify no missing/broken assets in packaged player.
- Capture representative visual frames at fixed camera points and compare them between builds.
- Create a public demo capture with device/build/settings disclosed.
- Document known limitations rather than hiding them.
- Ensure the complete VICTUS reveal and ending work as the actual playable campaign conclusion and not merely a screenshot.

## Per-slice engineering checklist

Every implementation slice should answer:
- What user-visible thing changed?
- Which existing VICTUS system owns it?
- What new project assets or code were created?
- What test proves the behavior?
- What platform(s) were actually run?
- What performance or memory data was collected?
- What asset/license/provenance changes were made?
- What is still incomplete?
- What is the next unblocked task?

## Required build/test log

Maintain `docs/BUILD_AND_TEST_LOG.md` with:
- VICTUS SHA and game SHA.
- OS/toolchain/Android SDK versions.
- Build and test commands.
- Pass/fail/skipped details.
- APK/export hashes.
- Physical device information.
- Frame pacing, memory and thermal data where available.
- Crash and lifecycle observations.
- Next actions and exact blockers.

## First useful playable milestone

The earliest worthwhile milestone is not a full forest. It is a small Android-exported first-person landscape scene with the first-person player moving/look-aiming with independent multitouch, a working fictional weapon viewmodel and action loop, an interactable object, a working pause modal and sound. This tests the highest-risk mobile assumptions before the asset-heavy route is built.
