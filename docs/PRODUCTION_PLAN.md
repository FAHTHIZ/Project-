# Production Plan — Dependency-Ordered Delivery

This plan is an execution queue, not a reason to stop coding after a design document. The autonomous agent should complete verified slices in order, commit them to `main` and continue.

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

## P1 — Playable controller and mobile input

**Goal:** establish the core feel and prove the landscape controls.

Tasks:
- Third-person player controller and camera, grounded movement and collision.
- Unified logical input layer for touch, controller and desktop keyboard/mouse.
- Working left virtual stick and right camera-look region.
- Contextual interaction and field-tool buttons.
- Pause/settings modal that blocks background gameplay input.
- Touch pointer ownership, multitouch, cancellation, safe areas and app-resume reset.
- Gamepad discovery and dynamic input hints; touch UI can fade/hide when a gamepad is active.
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
- Profile on the physical phone and reduce the highest-cost features first if frame pacing or thermals fail.

**Exit gate:** the environment is not just a screenshot. It is interactive, packaged, visually readable and performs within the measured phone baseline.

## P4 — Character and interaction vertical slice

**Goal:** prove that game characters, props and dialogue work together.

Tasks:
- Reuse V-01/V-02 through normal VICTUS project asset workflows.
- Create the player/NPC model(s) that the story actually needs; keep the initial cast small.
- Add locomotion, idle, turn, inspect, talk/listen and field-tool animations.
- Implement a bounded stumble/fall/recovery demonstration and verify player-root/capsule continuity.
- Use ragdoll only if its complete recovery path is stable; the audited VICTUS baseline has no automatic get-up/root follow.
- Implement the non-weapon field utility tool and point-of-interest interactions.
- Produce real dialogue audio offline after voice/recording rights are checked.
- Add subtitles and lip-sync cue data; reserve morph targets for close-up hero faces and profile CPU cost.

**Exit gate:** one complete character interaction is playable in the exported package with audio, subtitles, animation and correct gameplay state transitions.

## P5 — Stage 01 complete

**Goal:** deliver an independently playable first stage.

Tasks:
- Complete the route, objective chain, field interactions, NPC encounter, environmental awareness/alert states and Stage 02 transition.
- Add start/pause/settings, save/restore and clear stage completion.
- Add user-facing tutorials for mobile controls.
- Add optional diagnostics overlay with real metrics only.
- Add automated stage flow tests and capture checkpoints.
- Build/export Android and desktop packages.
- Test a full session on the Hot 10S and record sustained results.

**Exit gate:** a new player can launch, understand controls, finish the stage, save/restore, and reach the conclusion on the target phone without a developer console.

## P6 — Research and build Stage 02 onward

For each later stage, research before asset creation:
- Stage purpose and player activity.
- Visual reference collection, cited URLs and reference notes.
- Original architecture/prop/lighting design.
- Reusable modules and asset budget.
- Scene transitions and progression.
- Audio and character requirements.
- VICTUS feature fit and known blockers.
- Mobile performance risks.
- License and redistribution audit.

Do not freeze a later stage from generic assumptions. The broad direction remains forest → perimeter → facility → bunker → V-01 dummy reveal; detailed art direction is owned by the researched stage briefs. Add one document per stage and link it here.

## P7 — Product polish and showcase evidence

Tasks:
- Run a repeatable end-to-end test on desktop, emulator and physical phone.
- Add crash/log capture and a clean diagnostics/export report.
- Test suspend/resume, audio lifecycle, orientation/safe areas, controller disconnect/reconnect, storage pressure and save corruption recovery.
- Verify no missing/broken assets in packaged player.
- Capture representative visual frames at fixed camera points and compare them between builds.
- Create a public demo capture with device/build/settings disclosed.
- Document known limitations rather than hiding them.
- Ensure the VICTUS reveal works as the actual playable ending and not merely a screenshot.

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

The earliest worthwhile milestone is not a full forest. It is a small Android-exported landscape scene with the player moving, the camera responding to independent multitouch, an interactable object, a working pause modal and sound. This tests the highest-risk mobile assumptions before the asset-heavy route is built.
