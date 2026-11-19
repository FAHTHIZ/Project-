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

## Full squad is mandatory

This is a squad-led campaign, not a lone protagonist with occasional NPC cameos. The player is part of a recurring, fully authored team. Use a compact full squad of the player plus **three or four allied operators** as the baseline cast (final count must be chosen after checking scene and device budgets). The same core members recur across operations, travel together when the mission allows, and remain recognisable in gameplay, dialogue and cinematics.

- Give every squad member a name/callsign, face, distinct silhouette, costume, voice, personality, story role, relationship dynamics and animation identity.
- Keep teammates physically present in playable missions wherever the authored mission permits. They must not exist only as radio voices or cutscene extras.
- Implement companion AI for following, spacing, navigation, regrouping, waiting, reacting to mission events, taking authored cover/hold positions, interacting with set pieces and recovering from pathing issues. Keep behaviour readable and avoid teammates blocking the player's view or movement.
- Squad members should naturally communicate with one another as well as with the player: short contextual conversations, radio exchanges, call-and-response, observations, jokes, disagreements and reactions to discoveries. Use authored triggers and a dialogue scheduler so chatter is relevant, non-repetitive and never obscures critical information.
- Support both spatial nearby dialogue (voices positioned at the speaking teammate) and radio-filtered comms. When a teammate speaks, the correct character should visibly speak when in view; off-screen/radio speakers should be identified in subtitles/HUD.
- Teammates should acknowledge one another through eye contact, head turns, gestures, posture changes and brief contextual reactions. Avoid characters standing in a line delivering isolated dialogue turns.
- Cutscenes must show the whole team together regularly: briefing/deployment, moving between spaces, discoveries, arguments/reactions, regrouping, major reveals and mission transitions. Compose shots so viewers understand where each member is and who is speaking.
- In first-person gameplay the player remains first-person, but teammates must be visible in the world and can enter the player's view naturally. Do not switch to third-person gameplay merely to show the squad.
- Provide mission-level continuity: squad members can be temporarily separated only for a clear story reason, with authored reunions and state continuity. Do not silently remove members between areas.
- Create a squad roster and per-operation presence/participation matrix. Track each member's dialogue, animations, facial performance, costume state, mission beats and continuity.
- The full squad is a core feature and acceptance requirement, not an optional later polish item. Do not call the campaign complete if only the player character is implemented.

## Dialogue, voice acting and complete soundscape

- Every operation needs a dialogue and audio plan: who speaks, why they speak, where the voice is positioned, how the player receives the information and what subtitles/captions accompany it.
- Use natural, expressive, clearly performed dialogue for the protagonist's squad, opposing characters and key NPCs. Lines should sound conversational and character-specific, not like flat system announcements.
- Prefer licensed human performances or carefully reviewed offline-generated voice lines. Listen to every line and revise awkward pronunciation, pacing, breaths, emotion, noise and clipping. Never ship unreviewed bulk-generated speech.
- Use distinct voices for the principal cast, with consistent delivery across the campaign. Keep voice identities and recording/model rights documented.
- Add contextual radio communications, squad callouts, mission briefings, character conversations, environmental reactions and cinematic dialogue where they improve story clarity. Avoid constant chatter.
- Build a layered soundscape: location ambience, wind/foliage, room tone, machinery, distant activity, footsteps and surface-specific foley, clothing/gear movement, interactions, weapon/gameplay effects, UI feedback, cinematic transitions and an original music score.
- Give each location a recognisable audio identity. Use spatial placement and attenuation for world sounds, and mix dialogue so it remains intelligible over ambience, music and gameplay effects.
- Use dedicated audio buses and sensible priorities/voice limits. Avoid clipping, overlapping duplicate lines, abrupt volume jumps and excessive simultaneous loops.
- Every spoken line needs synchronized subtitles and a tested skip/pause/resume path. Lip-sync close-up speaking characters where the model and device budget support it.
- The voice pipeline is finite authored content: generate/record, audition, edit, create final game-ready audio, create subtitle and lip-sync data, then test in the packaged build. Do not add runtime TTS merely to avoid authoring the lines.
- Record provenance and redistribution rights for voices, music, ambience, foley and effects. Use original or explicitly licensed assets.

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


---

# Whole-Game Realism, Immersion and Vehicle Loadout Requirements

**This section is a mandatory extension of the production contract above.** It defines what the owner means by a convincingly realistic game. Apply it to the entire campaign, not only the first forest scene, not only the weapons, and not only cutscenes.

## 1. Realism means a coherent world, not expensive graphics

The required direction is **grounded cinematic realism with systemic consistency**. The world should feel inhabited, physical, authored and continuous. The player should not feel that they are walking through disconnected props and scripted characters.

A feature is not realistic merely because it has a detailed model. Believability comes from the agreement between appearance, animation, sound, physics, lighting, interaction, character behaviour and persistent state.

Use these priorities in order:

1. **Physical and spatial consistency:** objects occupy space, meet the ground, have scale and do not visibly intersect or float. Characters and vehicles have consistent positions and transitions.
2. **Human performance:** characters have weight, intention, natural timing, gaze, gestures, listening behaviour, foot contact and clear relationships.
3. **Interaction completeness:** important objects do what their appearance promises. Doors open, handles are reached, storage contains visible items, switches change something, and the world reflects completed interactions.
4. **Audio-visual agreement:** sounds match visible actions, materials, distance, room size and environment.
5. **Environmental storytelling:** spaces look built and used for a purpose. Objects, wear, lighting, signage, clutter and layout tell a coherent story.
6. **Cinematic direction:** scenes have deliberate staging, camera language, editing, performances and pacing.
7. **Rendering fidelity:** materials, lighting, shadows, atmosphere, geometry and post-processing support the world rather than distract from its weaknesses.
8. **Measured performance:** the chosen quality level must remain stable on the actual target hardware.

Do not chase photorealism by adding uncontrolled detail. Do not use darkness, fog, depth blur, particles or camera shake to conceal unfinished work. Do not accept an object that looks plausible in a screenshot but behaves incorrectly when approached, touched, opened, moved or viewed from another angle.

Every important interaction must be reviewed in motion and from the player's actual first-person camera.

## 2. Whole-game consistency standard

Apply the following to every operation, cutscene, interior, exterior, character, vehicle and interactive prop.

### Geometry, scale and placement
- Establish a consistent world scale in metres and document the dimensions of important spaces, doors, furniture, props, vehicles and characters.
- Ensure objects rest on floors, terrain, shelves, seats or mounting surfaces instead of floating or intersecting them.
- Check collision shapes against visible geometry. The player must not walk through solid walls, get snagged on harmless decoration, or be blocked by invisible oversized colliders.
- Avoid repeated identical prop placement, visibly tiled geometry, duplicated silhouettes and procedural repetition that exposes the generator.
- Give important props a logical storage location, orientation, interaction point and state.
- Check all important objects from multiple camera heights, at close range and at normal gameplay distance.
- Use believable wear and dirt placement: concentrated around edges, contact points, entrances, frequently used surfaces and environmental exposure. Avoid random uniform grunge overlays.

### Materials and surfaces
- Establish a coherent material library with physically plausible roughness, metallic response, normal detail, colour variation and texture scale.
- Distinguish painted metal, bare metal, glass, ceramic, rubber, wood, concrete, fabric, leather-like synthetic material, soil, foliage and wet surfaces.
- Keep material response consistent under different light sources. A surface must not change into a completely different material simply because the camera moves.
- Avoid plastic-looking skin, rubbery clothing, over-glossy concrete, excessively reflective fabric, noisy normal maps and extreme emissive brightness.
- Use decals and dirt as authored storytelling details rather than a substitute for proper base materials.
- Verify texture compression, mip levels, UV scale, normal orientation and LOD behaviour in the VICTUS runtime, not only in an external modelling preview.

### Lighting and exposure
- Give each environment its own lighting design. The forest, open perimeter, service yard, facility, bunker, lower basement and final chamber must not all share one generic dark look.
- Motivate lights through the environment: sky, windows, fixtures, work lights, indicator panels, vehicle lamps and practical sources.
- Preserve readable faces, silhouettes and navigation cues. Darkness should be intentional, not a way to hide missing art.
- Keep exposure stable during camera movement and transitions. Avoid sudden brightness pumping, crushed shadows and clipped light sources.
- Use shadows where their visual contribution justifies the cost. Check contact, softness, bias artefacts, foliage shadow noise and temporal stability.
- Treat fog, bloom, reflections and volumetric effects as optional tools. Test their actual cost on the target device.
- Review every scene at its intended time-of-day, camera direction and gameplay exposure, not only in a beauty-shot camera.

### Animation and contact
- No character should visibly skate across the floor, snap between poses, rotate instantly, teleport into a conversation position or move through a closed door.
- Use blended transitions for locomotion, starts/stops, turns, idle, gestures, interactions, talking and listening.
- Keep foot contact credible. Because the current VICTUS audit documents no automatic foot-contact IK, use authored foot-contact animation, tested procedural compensation or restrained camera/framing; do not claim engine foot IK exists.
- Hands must reach the intended object. A hand opening a door should meet the handle area; a character interacting with a console should visibly orient and reach toward it.
- Avoid hand/object clipping, arms passing through torsos, props appearing in hands without an acquisition/release transition, and characters holding poses after the action is over.
- Use root motion only where the clip and controller are verified to support it. Keep the gameplay root/capsule authoritative and avoid drift between collision and visual rigs.
- Facial performance must include gaze, blinks, eyelids, brows, jaw, mouth movement and appropriate expressions when supported by the character rig. Close-up speech requires reviewed lip-sync; distant characters can use simpler performance.
- Characters who are listening should look toward the speaker or relevant event, respond with small gestures and change posture naturally. They must not freeze like mannequins while another character speaks.
- Reuse and extend existing rigs and animation assets rather than layering multiple competing animation controllers onto the same character.

## 3. Vehicle arrival and interactive equipment trunk

The game must include a memorable squad arrival sequence using a believable transport vehicle. The required first implementation is a **cinematic arrival followed by a stationary, fully interactive vehicle**. Do not add drivable-car systems unless a mission genuinely requires driving; the arrival and equipment interaction are the immediate requirement.

### 3.1 Vehicle presentation
Create one original squad transport vehicle with:
- A coherent exterior silhouette, proportion and material treatment.
- A visible, believable cabin with seats and windows; do not use black windows to hide an empty interior.
- Correctly placed wheels that meet the ground, with no visible floating or terrain penetration.
- Door geometry with open/closed states and visible hinges or appropriate pivot behaviour.
- A rear storage compartment with a real opening state and enough physical space for its contents.
- Interior and exterior lighting appropriate to the scene.
- A stable parked state after arrival. The vehicle must not vanish or reset after the team exits.

The vehicle does not need thousands of polygons. It needs convincing scale, proportions, grounded placement, credible materials, useful collision and well-executed interactions.

### 3.2 Arrival sequence
The player and recurring squad arrive together. Stage the sequence so the player understands that the team has travelled to this location.

Required sequence:
1. Establish the approach and location with a deliberate cinematic composition.
2. Show the vehicle entering or arriving at its final parking position. If the current vehicle path is authored rather than physically simulated, it must still move smoothly and consistently.
3. Slow and stop without visible snapping or sliding.
4. Allow the vehicle to settle visually; do not exaggerate suspension movement.
5. Play an appropriate engine idle and shutdown state, matched to what is visible.
6. Stage the occupants and their exits individually. No squad member should simply pop into existence outside.
7. Open the correct doors, animate exits, allow each character to clear the door, and close doors where appropriate.
8. Let the squad naturally regroup around the vehicle or move into authored positions.
9. Continue into a short team exchange and the equipment-selection interaction.

The team members must not all exit on precisely the same frame or repeat one identical animation. Give their exits small timing and personality differences while preserving mission pacing.

### 3.3 The trunk must be a real interaction
The trunk is not a static prop, a flat menu or an inventory screen floating over the car.

The player should be able to approach the rear of the vehicle, see the storage compartment, receive a clear interaction prompt and activate it.

When opened:
- The trunk lid must visibly move to an open state.
- The storage interior must be modelled and lit well enough to read.
- The equipment must already be visibly arranged inside before the player interacts.
- Items must have believable size, orientation, spacing, support and storage positions.
- Items must not float, intersect one another or clip through the trunk.
- The player should be able to identify each available item by looking at it.
- The interaction should support both touch and gamepad/keyboard without requiring pixel-perfect tapping.
- A selected item must visibly leave its storage position and transition into the player's equipment state.
- The trunk contents must update after acquisition. Do not leave an item visible in the trunk after it has been taken.
- Closing and reopening the trunk must preserve the correct contents.
- The vehicle must retain its state through the next checkpoint or scene transition whenever mission continuity requires it.

Build the equipment interaction as a reusable system. Avoid one-off hardcoded pickup scripts for every item.

### 3.4 Teammate-guided selection
A teammate should naturally introduce the equipment choice. The character should make it feel like a squad preparing for a mission, not a shopkeeper reading a menu.

Example intent, not fixed dialogue:

- One teammate approaches the rear of the vehicle and opens the trunk.
- The teammate gives a short contextual explanation that the team has brought additional field equipment.
- The teammate points, looks or gestures toward the available items.
- The player is invited to choose what they need for the upcoming mission.
- The teammate reacts naturally to the player's selection.
- Other squad members may contribute a brief comment, provided the dialogue remains clear and does not overlap.

The conversation must be authored for the actual mission context. A teammate should not recommend an item that is not in the trunk or that the player cannot select.

Use gaze targets, head turns, appropriate hand gestures, pauses, listener reactions and spatially positioned voice. Show the character's hand or gesture in the correct direction. Subtitles must identify the speaker and match the spoken audio.

Do not force the player into a long conversation. The player can inspect the contents, choose an available item, or close the interaction and continue.

### 3.5 Selection and equipment state
- Each selectable item needs a clear name, short role description and visual identity.
- The selection state must be accessible and understandable from the first-person camera.
- Add a contextual pickup prompt and a concise acquisition confirmation.
- Selecting an item should use an authored first-person acquisition/equip animation rather than an instantaneous UI-only change.
- Keep equipment state consistent across the HUD, visible character props, inventory data and subsequent interactions.
- Define what happens when the player already carries an incompatible item or reaches a carrying limit. Present the choice clearly and never silently delete an item.
- Mission-specific equipment and optional equipment must be distinct in the design and save data.
- Save the chosen loadout at the appropriate campaign checkpoint. Loading or restarting must restore the expected state deterministically.

The first trunk scene should offer a small curated selection, including the requested fictional precision/sniper-class game weapon and relevant non-weapon field equipment. The player should be able to choose rather than automatically receiving everything.

## 4. Fictional sniper-class weapon and pickup integration

Add one original, fictional sniper-class weapon as a real usable game item available from the vehicle trunk.

This is a game-design requirement only. Its visual design, handling, scope presentation, audio and balance must be fictional abstractions. Do not model real weapon internals, reproduce real-world specifications, provide construction/maintenance instructions, or translate real-world aiming or tactical procedures into gameplay tutorials.

### Required game experience
- The item must be a complete 3D asset with a distinctive original silhouette, believable material treatment and a readable first-person viewmodel.
- It must be physically represented in the open trunk and have a clear interaction target.
- The player must be able to inspect/select it, pick it up, and see the trunk state update.
- The first-person equip transition must show the character bringing the item into the gameplay view rather than making it appear instantly.
- Its scope must have a polished fictional game UI presentation, with a readable reticle, a limited set of zoom states and a stable camera transition.
- Its audio, HUD identity, viewmodel, animation states and inventory record must all use the same item definition.
- Provide an appropriate stow/holster state and a visible carry representation on the player character when stowed, if the character rig supports it.
- Switching away and back must preserve the item's state.
- The weapon must be selectable and usable in the intended mission, not merely displayed in the trunk or dev range.
- The system must respond correctly to empty/limited fictional charge or ammunition state, reload state and interrupted equip transitions.
- Use invented numerical values for all game balance. Keep the interaction readable and fair; never teach real-world marksmanship, range estimation, wind compensation, firing positions or other real-world weapon-use methods.
- Use non-graphic hit/defeat presentation consistent with the game's existing fictional stun-pulse direction. Do not add gore or realistic injury depiction.

### Shared item architecture
Do not create a separate hardcoded sniper system that bypasses the existing weapon implementation.

Audit the existing PC-7 Lantern, SP-2 Wren, field scanner and shared combat registration first. Preserve working behaviour. Extend or refactor the current system into one coherent item/equipment framework only where the current architecture requires it.

A shared item definition should own the identity and runtime data needed by:
- First-person viewmodel and presentation.
- Inventory/loadout ownership.
- Pickup and world representation.
- Equip/stow transitions.
- HUD identification and state.
- Audio/VFX presentation.
- Save/checkpoint serialization.
- NPC/squad loadout assignment where needed.

The player, friendly NPCs and opposing NPCs should not maintain incompatible duplicate definitions for the same fictional item. A world pickup should instantiate from the same definition that the player's inventory and character presentation use.

### Pickup/drop consistency
- World pickups must have a visible mesh, an intentional position and a reliable interaction target.
- Pickup must update the world's item state and the player's inventory as one coherent transaction.
- Repeated interaction must never duplicate an item.
- Dropping an item, where permitted by mission design, must create a world representation with the correct identity and state.
- Re-picking up a dropped item must preserve its state unless the design explicitly resets it.
- NPC equipment changes must be reflected in the NPC's visible carry presentation and inventory.
- Mission-critical items must not become permanently inaccessible through an accidental drop or scene transition.
- Save/load must not duplicate or lose items.
- Add tests for duplicate pickup, invalid pickup, inventory limit, failed equip, interrupted equip, drop, repick, scene reload and save restoration.

## 5. Character realism — people must feel alive

The recurring squad is central to the campaign. It must consist of the player plus three or four allied operators, chosen after performance testing, with the same core characters recurring across operations.

Every named character needs:
- A recognisable face and silhouette.
- Distinct clothing shapes, materials, palette and personal visual details.
- A clear personality and conversational voice.
- A defined relationship with the other squad members.
- A consistent animation identity.
- A role in the story beyond merely following the player.
- A documented presence and continuity plan across the campaign.

### Movement
- Idle must not look like a frozen character. Use restrained breathing, weight shifts, head movement, gaze and occasional gestures.
- Walking and running must show clear foot placement and consistent pace. Avoid foot sliding and floating.
- Starts, stops and direction changes need transitions rather than abrupt velocity changes.
- Characters must turn toward their destination or the person they are addressing.
- Characters should avoid walking through one another, furniture, vehicles and narrow doorways.
- Teammates must follow at readable distances, avoid crowding the player and recover sensibly when navigation fails.
- Their pathing must respond to doors, obstacles and mission staging; do not allow them to stand permanently in a doorway or block an interaction.
- Teammates should occasionally look at the environment or each other rather than constantly stare at the player's camera.

### Conversation and social behaviour
- Conversation is a small group performance, not a sequence of isolated subtitles.
- Characters should use turn-taking, eye contact, head turns, gestures, posture, pauses and listening reactions.
- Let a teammate answer another teammate directly. The player is not the only person the squad acknowledges.
- Use contextual dialogue triggers with cooldowns, variation and state checks. Do not repeat the same generic line every few seconds.
- Avoid overlapping speech. Important mission instructions must be intelligible and remain available in subtitles or objectives.
- Spatial dialogue must originate from the speaker's world position. Radio dialogue must have a distinct but restrained audio treatment.
- Keep speaker identity and subtitle timing consistent through pause, skip, load and scene transition.
- Facial animation must be reviewed on the actual models and under actual lighting; a successful morph-target import alone does not prove convincing performance.

### Costume and carried items
- Clothing must have believable thickness, seams, folds, layering and material response.
- Hands, sleeves, gloves, footwear and headwear must fit the character and remain consistent between gameplay and cinematics.
- Carried equipment must be attached to appropriate visual mount points and must not float or intersect the torso.
- If an item is selected, removed, stowed or handed over, the visual representation must change with the underlying equipment state.
- Weather and environment variants should be authored only when they improve continuity and are affordable to maintain.

## 6. Environment realism across the complete campaign

Each area must have an individual art-direction brief, distinct playable layout, meaningful landmarks, audio identity, lighting design and story purpose.

### Forest
- Layered canopy, trees of varied silhouette, undergrowth, grounded vegetation, trail edges and clear navigation landmarks.
- Natural light variation, believable shadows and atmospheric depth.
- Footsteps and movement sounds that reflect soil, leaves, wood, stone and other authored surfaces.
- Foliage should have enough variation to avoid obvious repetition without overwhelming CPU/GPU and memory budgets.
- The forest should feel open in some places and enclosed in others; avoid repeating one corridor-like path.

### Perimeter and exterior service areas
- A visible transition from organic forest to controlled infrastructure.
- Clear approach geometry, boundary structures, gates, service routes, drainage, surface transitions and environmental wear.
- Lighting and signage appropriate to the intended fictional site.
- Readable cover and navigation geometry without confusing the player or creating arbitrary invisible barriers.

### Facility interiors
- Spaces should look like real rooms designed for clear fictional purposes: operations, work areas, storage, circulation, laboratories or maintenance.
- Furniture, consoles, cables, lighting, equipment and clutter should have a reason to be where they are.
- Room scale, ceiling height, doors, stairs, corridors and furnishings must remain consistent.
- Avoid filling every room with generic props. Leave intentional negative space and strong landmarks.

### Bunker and lower basement
- Give the bunker and lower basement separate architecture, light, audio and visual identities.
- The basement must be a substantial playable space, not an extra corridor.
- Use vertical transitions and spatial landmarks so the player understands their position.
- Keep dark areas navigable and visually legible. Do not make every room uniformly black or fog-filled.
- Use wear, moisture, dust and maintenance details in a controlled, location-specific way.

### Final VICTUS chamber
- The final room should feel deliberately designed and support the mundane V-01 chair reveal.
- The reveal is not horror, a boss encounter or an artificial-intelligence twist.
- Stage the room, chair, dummy, camera and silence carefully so the humour lands.
- Maintain the established story and character continuity.

## 7. Sound design and acoustic realism

Sound is a primary part of believability, not a layer added after the visuals.

Every operation requires a sound plan covering:
- Environmental bed and location ambience.
- Distinct room tone for indoor spaces.
- Surface-dependent footsteps and movement.
- Clothing and carried-equipment movement.
- Door, trunk, latch, switch, drawer and prop interactions.
- Vehicle approach, engine state, doors and storage interactions.
- Spatial NPC voices, radio communication and reactions.
- Fictional game-item sounds, UI feedback and cinematic cues.
- Music that supports pacing without constantly telling the player how to feel.

Use VICTUS's actual spatial audio, bus and acoustic features after checking current API support.

Required quality:
- Sounds must be synchronized to visible events, not merely triggered at approximately the same time.
- The same action should not produce an obviously identical sample every time where variation is appropriate.
- Distance and occlusion should affect world sounds plausibly.
- Interior spaces should sound different from open outdoor spaces.
- Dialogue must remain intelligible without making every other sound unnaturally quiet.
- Avoid constant ambience loops with obvious start/end points.
- Ensure one-shot and looping sources are correctly stopped, faded and restored across pause, cinematics, scene loads and application lifecycle changes.
- Review every shipped audio asset for clipping, silence, noise, inconsistent level, poor edit points and licensing.

## 8. Cinematic realism and direction

Cinematics should be deliberately staged and edited, not simply a camera slowly moving toward a character.

Every major sequence requires:
- A written dramatic purpose.
- A storyboard or shot list.
- Character blocking and clear screen direction.
- Camera placement, movement, framing and edit timing.
- Character gaze and reactions.
- Accurate dialogue and subtitle cues.
- Spatial ambience, effects and score.
- Safe gameplay-to-cinematic camera ownership and return.
- A skip/pause/resume plan.
- Performance testing at the intended device quality tier.

The squad arrival, vehicle exit and trunk selection should be one of the first complete cinematic-plus-interaction vertical slices. The sequence should transition naturally from an authored arrival to player-controlled exploration and equipment choice.

Do not use cutscenes to conceal missing gameplay. Every scene that promises interaction must return control to the player and allow the promised action.

## 9. UI and player feedback

The interface should be diegetic where it adds meaning and conventional where clarity matters. Do not force every element into a fictional device or hologram.

- Keep the mobile HUD readable at the actual landscape resolution.
- Ensure interaction prompts appear only when an interaction is available.
- Identify speakers and important equipment clearly.
- Show a selected item's actual state and current ownership.
- Avoid excessive popups, redundant labels and panels that obscure the world.
- Keep touch targets large enough for comfortable use and avoid overlap between movement, look, aim and interaction.
- Provide settings for sensitivity, reticle, subtitles, subtitle background, camera shake, audio and quality.
- Support gamepad and keyboard/mouse without leaving touch-only controls visible when inappropriate.
- Preserve essential story information in objectives, subtitle logs or mission records.

## 10. Performance and fidelity on the actual target

The target is a stable, attractive game on the Infinix Hot 10S, not an unmeasured desktop showcase.

- Begin with a 30 FPS target and measure sustained frame pacing.
- Verify the actual handset model, Android version, GPU/driver, Vulkan support, memory, storage and available thermal headroom.
- Profile dense forest scenes, full-squad scenes, vehicle arrival, trunk interaction, indoor scenes, cinematics and the most expensive encounter.
- Measure CPU frame time, frame pacing, resident/peak memory, asset load times and thermal behaviour where the device and tooling expose them.
- Do not claim GPU pass timings if the current VICTUS path cannot provide GPU timestamps.
- Use LOD, instancing, culling, texture compression, sensible shadow budgets, controlled lights, audio voice limits and effect budgets.
- Avoid a sudden quality drop when several characters or the vehicle become visible. Test the exact worst-case scene.
- Keep the game stable through suspend/resume, pause, scene changes, low-memory conditions and audio-device changes.
- Do not use emulator performance as evidence of physical-device performance.
- Keep high-detail assets for the views where they matter, including the vehicle, first-person hands, important characters and close-up props. Use measured reductions for distant or background content.

A beautiful still image is not sufficient. Capture and inspect representative gameplay video at the target resolution and sustained frame rate.

## 11. Production research and originality

Before finalising each major environment, vehicle, character or cinematic:
1. Identify the specific visual or technical question to resolve.
2. Research primary documentation, professional art breakdowns, credible animation references and legitimate asset sources.
3. Record source URL, author/provider, date accessed and exactly what the reference informs.
4. Separate observations from original proposals.
5. Verify redistribution rights before importing any asset.
6. Design original silhouettes, layouts, dialogue, props and shot compositions.
7. Test the result through the real VICTUS importer and packaged player.

Use other games as quality references only. Do not reproduce their characters, levels, dialogue, logos, signature shots or proprietary assets.

The purpose of research is to make decisions better, not to accumulate links or postpone implementation. Record the key findings and move into a playable slice.

## 12. Required implementation order for this expansion

Do not build everything at once. Work through independently testable slices while continuing the campaign plan.

1. **Baseline reconciliation:** inspect the latest game and VICTUS commits, scripts, scenes, build/test log and current limitations. Update stale claims.
2. **Existing weapon/equipment audit:** preserve the working PC-7, SP-2 and scanner behaviour; identify the smallest coherent shared item/inventory design that supports new item classes and pickups.
3. **Vehicle art and placement:** create one original transport vehicle with correct scale, grounded placement, cabin, doors and trunk.
4. **Arrival cinematic:** implement approach/stop/idle, team occupancy and individual exits.
5. **Trunk interaction:** implement open/close state, visible contents, teammate guidance, contextual selection and persistent inventory changes.
6. **Fictional sniper-class item:** create the original visual asset, viewmodel, scope UI, animations, audio, item definition and mission integration as a selectable game pickup.
7. **Shared pickup/drop:** implement consistent world pickup, inventory, optional drop, NPC carry state, save/load and duplicate prevention.
8. **Full squad integration:** ensure each recurring operator is present and responds during the arrival, equipment conversation and subsequent mission.
9. **Mission integration:** place the whole sequence into a real campaign operation; do not leave it only in a development range.
10. **Quality pass:** inspect animation contact, vehicle placement, trunk contents, sound synchronisation, lighting, first-person usability, mobile touch interaction and performance.

Do not let equipment expansion become an excuse to postpone the campaign, environments, squad, dialogue and ending. Once this vertical slice is stable, continue through the next unfinished operation.

## 13. Mandatory test and review matrix

Automated tests must cover state and failure cases. Visual review must cover the actual sequence and packaged game.

### Vehicle and arrival
- Vehicle begins at the correct authored location and reaches the intended parked state.
- Vehicle does not snap, float, sink into terrain or visibly slide after stopping.
- Occupants match their assigned seats and exit from the correct doors.
- No character appears outside without an authored transition.
- Doors and trunk open/close reliably and do not pass through characters or geometry.
- The vehicle remains in the correct state after the sequence.

### Trunk and equipment
- Trunk starts with the intended items in valid positions.
- Every available item can be identified and selected.
- Selection removes the item from the trunk and adds it exactly once to the player's inventory.
- Reopening the trunk shows the updated contents.
- Closing the trunk does not lose the selection.
- Repeated interaction cannot duplicate items.
- Invalid or unavailable selections fail gracefully.
- Interrupted interaction returns to a valid state.
- The selected loadout survives the required checkpoint/save/load path.
- Touch, gamepad and keyboard/mouse all support the same interaction.

### Item framework
- Existing PC-7, SP-2 and scanner regression tests remain green.
- The fictional sniper-class item uses the common definition/inventory pipeline.
- Equip, stow, switch, reload/charge, empty state and interrupted transition are tested.
- World pickup, optional drop, repick, NPC assignment, scene transition and save restoration are tested.
- HUD, first-person presentation and visible carried item never contradict inventory state.

### Squad and performance
- All required squad members appear in the arrival and trunk scene.
- Characters have distinct timing, dialogue, gaze, gestures and reactions.
- Dialogue does not overlap confusingly; subtitles are correct.
- No character is trapped, blocking the player, floating or visibly skating.
- Vehicle plus full squad plus environment runs within the measured quality budget.
- The sequence works when paused, skipped, resumed and reloaded.

### Evidence
- Save screenshots and gameplay captures in a tracked evidence location or attach them to the build/test record. Do not leave the only evidence in a temporary directory.
- Record the exact command, environment, game SHA and VICTUS SHA used.
- Distinguish source-level checks, headless simulation, software-rendered screenshots, desktop GPU runs, emulator tests and physical-device tests.
- Never label visual quality or performance "verified" without inspecting the relevant output.
- Never report an Android or physical-device result unless the game was actually installed and exercised on that device.

## 14. Definition of done: realism

The game does not meet the requested realism standard merely because it has:
- A detailed vehicle model.
- A trunk lid that rotates.
- A weapon mesh in the inventory.
- A teammate standing beside the player.
- A subtitle over a static character.
- A forest screenshot with fog.
- A successful headless simulation.
- An APK that compiles.

It meets the standard only when the entire sequence and campaign work together: the vehicle arrives convincingly, the squad exits naturally, the teammate introduces the available equipment, the player physically inspects and selects an item from the trunk, the visible contents and inventory update correctly, the chosen equipment is usable in the real mission, and the squad, world, animation, audio, camera, save state and performance remain coherent.

Apply the same standard to every major interaction throughout the campaign.

**Final instruction:** build the most believable and polished game VICTUS can actually sustain on the target phone. Do not settle for a technically passing prototype when the visible result is still obviously artificial. Do not fake realism with effects. Make it believable through consistent systems, careful art direction, excellent character performance, strong sound, authored cinematography, tested interactions and measured mobile optimisation.
