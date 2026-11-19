# Autonomous Agent Instructions — SPECIAL OPS

## Mission

Build and finish this game in this repository using the owner's VICTUS engine. Work directly on `main`; do not create a branch or pull request unless the owner changes that instruction. The owner authorizes independent research, ordinary reversible decisions, implementation, validation and continuous progress through unblocked tasks.

Read VICTUS's own `AGENTS.md` whenever engine code is inspected or changed.

## First action: establish the actual baseline

1. Inspect this repository's current `main`, working tree and complete file tree. Preserve owner changes. It began with only a tiny README, but never assume it remains empty.
2. Read every project document linked from the root README.
3. Inspect the live `https://github.com/FAHTHIZ/VICTUS` main branch. This handoff was initially audited against commit `31457931542d52c0572970139d161a73428c21bd` on 2026-11-19. That is only a historical audit point; reconcile APIs, assets, features and limitations against current main.
4. Read VICTUS `AGENTS.md`, `docs/GETTING_STARTED.md`, `docs/USER_GUIDE.md`, `docs/ANDROID.md`, `docs/PLATFORM_SUPPORT.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/STATUS.md`, `docs/CHARACTERS.md`, `docs/ANIMATION.md`, `docs/AI.md`, `docs/RENDERING_SPEC.md`, `docs/PERFORMANCE_STRATEGY.md`, plus `samples/arena` and its scripts.
5. Record the exact VICTUS SHA, compiler/toolchain, baseline build, tests and commands in `docs/BUILD_AND_TEST_LOG.md` before changing the game.

## Continuous engineering loop

Repeat until blocked by physical hardware, credentials, an owner decision or an external dependency:

1. Inspect latest `main`, current diff, project tree and relevant implementation.
2. Research the unknown that changes the implementation. Prefer primary documentation, maintained upstream repositories, release notes and license texts. Stop when the decision is supported.
3. Write a focused decision note for consequential architecture choices.
4. Implement one coherent, playable vertical slice.
5. Integrate it into the real VICTUS project and packaged game; no unused demo subsystem counts.
6. Add automated tests and diagnostics.
7. Build, run and test all available environments. State clearly when Android hardware is unavailable.
8. Inspect the diff for duplicated systems, dead files, unlicensed assets, secrets, accidental engine vendoring and regressions.
9. Commit the verified slice directly to `main`.
10. Update the production plan and test log with exact commit SHA, commands, outcomes, measured results and next action.
11. Continue to the next unblocked task.

Do not stop after documentation or scaffolding. Never claim that a feature, build, test, APK, performance target or hardware run succeeded unless it actually did. Never claim background work will continue after the session ends; persist a precise handoff.

## Product constraints

- Landscape orientation and landscape composition are mandatory.
- The first physical device target is the Infinix Hot 10S, 6 GB RAM variant. Verify the exact SKU, Android build, GPU/driver and Vulkan capability on the actual device; published specs do not prove the installed driver works.
- Begin with a measured 30 FPS target and adaptive rendering resolution/quality. Do not chase 90 FPS because the panel supports 90 Hz. Consider 60 FPS only after sustained tests justify it.
- The four supplied videos define the Stage 01 forest atmosphere. Their visual content is captured in `docs/STAGE_01_FOREST.md`. They are portrait videos; the game must be built in landscape.
- The intended experience is a first-person, cinematic shooter campaign with exploration, authored combat encounters, objectives, character interactions and story progression. It is atmospheric and dramatic, not a horror game. Avoid gore, graphic injury detail, jump scares and horror tropes.
- Use VICTUS's own supported asset import, scene, scripting, animation, physics, navigation, audio, UI, diagnostic and export workflows. Extend the engine only when a genuine reusable engine gap blocks progress.
- The end reveal uses the existing Vanguard V-01 behind a chair. It is an ordinary, harmless dummy, not an AI, boss or mastermind.
- Build a complete but tightly scoped fictional shooter layer: original game-only weapons, first-person viewmodels, aiming/firing/reload/switch animations, enemy encounters, hit feedback, ammunition UI and encounter balancing. Weapon research is limited to fictional visual design, animation, sound design and abstract game balance; do not reproduce real weapon specifications, operating instructions or real-world tactical training. Keep the field utility device as a separate secondary tool for scanning, illumination and environmental interaction.
- Prioritize control feel, readable animation, stable camera motion, strong environment lighting, useful audio, touch responsiveness and clear feedback.

## Art and licensing

- Prefer original procedural assets or assets with clearly verified redistribution rights. CC0 libraries can be useful starting points.
- Record provenance for each imported model, texture, HDRI, sound, voice, font, animation, dataset and authoring tool.
- A library-wide license does not replace checking the specific downloaded item's provenance and license.
- Read voice model cards and training lineage. An open inference engine does not automatically grant rights to voice weights, training recordings or redistribution.
- Prefer pre-rendering finite dialogue into ordinary audio assets after licensing checks. Avoid adding a heavy speech model to the target phone's runtime without compelling, measured evidence.
- Keep source assets and reproducible generation scripts where practical; exclude build products and caches.

## VICTUS integration rules

- Do not copy the full VICTUS engine into this game repository or make a second renderer.
- Start by generating a normal VICTUS 3D project with the live CLI/template. Inspect that result and adapt it. Use `samples/arena` as an API example, not as code to duplicate blindly.
- VICTUS exposes touch queries and gamepad support, but its Android guide states that virtual sticks/buttons are not built in. Implement a game-level virtual control layer using documented touch/input APIs first. Track multitouch pointers independently and test simultaneous movement, camera and UI interactions.
- Keep the player's gameplay root/capsule/controller independent from the visual rig hierarchy.
- Reuse existing animation controllers, IK, layers and ragdoll systems when appropriate. VICTUS ragdolls do not currently provide automatic get-up or root/capsule follow in the audited baseline. Build and test a proper recovery state machine rather than assuming the engine does this.
- Morph-target facial animation exists, but current weights are updated on the CPU and a modified vertex copy is uploaded when weights change. Reserve detailed face animation for close-up speaking characters and profile it.
- The renderer exposes CPU profiling and render-path reason codes, but SDL_GPU has no GPU timestamp queries. Report GPU pass time as unavailable; never invent it.
- Android APK build support is not equivalent to real device support. In the audited baseline, no physical Android device or emulator had been validated.

## First-stage deliverables

- A polished, explorable Stage 01 forest based on all four reference clips.
- A landscape first-person controller with responsive look/aim, a stable head/camera rig, collision-aware movement and first-person arms/hand/weapon viewmodels. Gameplay remains first-person; external camera angles are reserved for authored cutscenes. Keep camera, field of view, sensitivity and motion settings data-driven.
- Responsive mobile controls: left movement stick, right first-person look/aim region, contextual interaction and field-tool buttons, pause/settings, and a clear gamepad mode. Keyboard/mouse must work in desktop testing.
- A polished shooter HUD with clear objectives, context prompts, reticle/aim feedback, ammunition and weapon state, interaction prompts, an understandable encounter/objective alert state, subtitles and pause/settings. Keep it readable on the target phone and allow comfort/accessibility customization.
- At least one voiced NPC encounter, subtitles and a working dialogue interaction.
- Responsive fictional weapon gameplay and a separate field utility device for scanning/illumination/inspection. Both must be fully implemented and playable; neither may be a static mockup.
- Natural locomotion, transitions, safe non-graphic trips/falls and a tested return to ordinary movement.
- A complete campaign route through the forest, perimeter, facility, bunker and a substantial lower-basement area, ending at the V-01 chair reveal. Research and document every area before locking its visual design.
- A reachable V-01 dummy reveal behind a chair.
- A diagnostics display for frame rate/frame-time, internal resolution scale, quality tier and render-path reasons. Include further counters only when VICTUS really exposes them.
- Reproducible VICTUS export and Android APK build/install instructions, plus a truthful physical-device validation report.

## Campaign, first-person presentation and cinematic cutscenes

- The gameplay camera is first-person. Do not build a third-person follow-camera controller or make third-person the default gameplay mode.
- Use authored, high-quality campaign cutscenes throughout the experience: an opening, mission/operation transitions, major area reveals, important character moments, discoveries, the bunker descent, the basement sequence, the V-01 reveal and the ending. Add shorter in-engine cinematic beats where they genuinely improve pacing.
- Cutscenes should feel like a polished, story-driven military-action campaign: deliberate shot composition, camera movement, character blocking, facial/body performance, lighting, editing, spatial sound, music, dialogue and subtitles. Treat this as a quality target only; do not copy Call of Duty scenes, characters, levels, dialogue, logos or signature compositions.
- Prefer real-time in-engine sequences that use the shipped characters, environment, animation and audio so they fit the phone's memory/storage budget. Research VICTUS's actual sequencer/camera capabilities on current main; build a supported sequence/timeline system only if a genuine gap exists.
- Cutscene requirements: reliable gameplay-to-cinematic transitions, camera ownership, input lock/restore, pause/resume handling, subtitle timing, audio mixing, skip controls, checkpoint/save consistency, and a clean return to first-person gameplay. Critical information must also be available in subtitles/objectives so skipping never blocks progression.
- Cutscenes must run at the target device's measured quality tier. Profile scene loads, character count, facial animation, camera effects and audio; do not assume desktop cinematic performance transfers to Android.

## Visual quality and rendering acceptance bar

The finished game should look deliberately art-directed and polished, not merely technically rendered. Build a consistent visual identity across forest, perimeter, facility, bunker and basement.

- Research and author each area's composition, silhouette, scale, materials, palette, lighting direction, atmospheric depth, landmarks, prop language and transitions.
- Use VICTUS's verified PBR materials, physically based lighting/atmosphere, shadows, IBL/reflection probes, fog, decals, LOD, instancing and post-processing where they visibly improve the result.
- Prioritize strong composition, believable material response, readable silhouettes, contact shadows, controlled highlights, restrained emissive accents, depth cues and a coherent colour grade.
- Forest: layered canopy, varied trunk/foliage silhouettes, believable ground cover, path readability, natural diffuse light, depth haze and selective shafts of light only if the renderer/device supports them affordably.
- Facility/bunker/basement: distinct architectural language, convincing material scale, purposeful practical lights, readable dark areas, designed sightlines, prop storytelling and non-repetitive spaces. Do not make every room uniformly dark or rely on fog to hide weak geometry.
- Character faces, clothing and hands must read under the actual scene lighting. Avoid plastic-looking skin/fabric, over-sharp roughness, floating props, texture repetition and visibly low-quality asset seams.
- Cinematic shots need deliberate framing, foreground/midground/background separation, exposure continuity, controlled camera movement, motivated lighting, readable faces and a carefully reviewed grade.
- Use high quality where it matters on screen, then optimize through measured LODs, texture sizes/compression, instancing, culling, shadow budgets, effect budgets and adaptive resolution.
- Do not assume every listed renderer feature is available, enabled or affordable on Android. Verify current VICTUS main and capture evidence from the actual renderer. Compare quality tiers on the target device.
- Create reference screenshots and video captures for each environment and major cinematic; inspect for lighting, material, animation, aliasing, shadow, foliage and temporal artefacts.
- The visual target is the best stable result the Hot 10S can sustain, not an unmeasured desktop Ultra preset. Begin with a stable 30 FPS target and document measured compromises instead of silently accepting broken frame pacing.

## Stage 02 onward: required reference research

Stage 01 is directly based on the four supplied clips. Later stages are intentionally not visually frozen by this handoff. Research them before production:

1. Define the stage's narrative purpose, route, player actions and transition.
2. Collect several legitimate reference images/videos for architecture, light, materials, composition, signs, props and atmosphere.
3. Prefer primary artist breakdowns, official documentation and first-party reference material.
4. Derive a concise art-direction sheet and reusable environment-module list.
5. Fit the design to VICTUS's verified capabilities and the mobile budgets.
6. Record exact source URLs and asset license/provenance in `docs/RESEARCH_REGISTER.md`.
7. Do not copy copyrighted game levels, maps, character designs, distinctive compositions or branded signage. References inform technique and mood; the finished level must be original.
8. Clearly separate observed references, researched facts and creative proposals. Do not invent details the owner has not approved.

## Completion gates

A stage is complete only when the scene can be entered, played, completed, saved and loaded; packaged assets are present; automated tests pass; touch and gamepad controls work; audio/subtitles work; performance is measured; and docs match the actual implementation.

A pretty screenshot, imported model, APK compilation, emulator FPS, unreachable script, silent dialogue panel or static dummy placement is not completion.


## Operator, enemy and fictional weapon research

- Research a small, memorable cast of original operators and opposing facility personnel. Give each character a readable silhouette, clothing layers, palette, role in the story, voice, personality and animation needs. Cover headwear, face visibility, field clothing, footwear, gloves, load-bearing costume shapes, communication accessories and weather/lighting variants as art-direction subjects, not as real-world equipment instructions.
- Make the protagonist, allied operators and opposing characters visually distinct without copying real military units, insignia or identifiable characters from other games.
- The campaign must have genuine shooter gameplay. Research fictional game-weapon art direction and game feel: silhouette, material language, fictional naming, first-person viewmodel readability, animation polish, sound identity, UI feedback and abstract balance. Keep weapon designs original and non-functional outside the game.
- Do not research or reproduce real-world weapon construction, specifications, operational procedures, handling instruction, maintenance, real-world aiming techniques or tactical doctrine. Do not turn the game into a training simulator. All firing, reload timing, recoil, spread, damage and ammunition values are invented game parameters.
- Keep combat readable and non-graphic. Use authored encounter pacing, clear objectives, fair difficulty, useful feedback and non-gory hit/reaction effects.
- Every character model, uniform texture, insignia, weapon mesh, animation, sound and reference asset must have verified provenance and a recorded license. A reference image is not permission to copy or ship its contents.

## Whole-game completion requirement

The definition of done is the complete playable campaign, not the forest, a single stage, a cinematic teaser or an isolated shooter prototype. The finished route must include the forest, perimeter, facility, bunker, a meaningful lower-basement section, the V-01 chair reveal and a proper ending. All planned operations, operator appearances, shooter systems, cutscenes, transitions, save/load, mobile controls, audio, packaging and final validation must be complete. Completing one area is a checkpoint; immediately continue to the next unfinished area. Commit each independently finished and tested piece directly to `main`, update the progress log, and proceed without waiting for another user prompt unless a genuine external blocker or owner-only decision prevents progress.

## When blocked

Record the blocker, exact commit and code state, commands and relevant output, hardware/access needed, and the next independent task. Do not hide unverified work behind a green status.
