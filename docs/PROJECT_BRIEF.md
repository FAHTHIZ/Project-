# Project Brief — SPECIAL OPS / VICTUS Field Demonstration

**Document date:** 2026-11-19  
**Game orientation:** Landscape  
**Primary device:** Infinix Hot 10S, 6 GB RAM variant  
**Engine:** VICTUS, live main branch  
**Genre:** First-person cinematic shooter campaign with exploration and environmental interaction  
**Working title:** SPECIAL OPS (title can be reconsidered after a playable build)

## 1. Product purpose

This game is a real, playable demonstration of VICTUS. It should show that the engine can deliver a coherent 3D experience on a budget-class Android phone: attractive outdoor lighting, dense vegetation, fog, convincing materials, responsive character animation, physical reactions, voiced dialogue, interactive props, stable controls, loading, save/restore, and a complete packaged game.

It is not a renderer screenshot scene. The player must have meaningful control, discover the route, interact with the environment and characters, reach a conclusion, and be able to play it again.

The game should be recognizable as a product even to someone who has never heard of VICTUS. Engine demonstrations should happen naturally during gameplay rather than interrupting the experience with a technical checklist.

## 2. Player experience

The player enters a secluded forest and follows a faint route toward a remote underground facility. The first stage is quiet and visually rich. The player notices environmental details, inspects points of interest with a field utility device, encounters at least one speaking character, and gradually discovers signs of the facility.

The tone is grounded, curious and cinematic. The forest can feel mysterious, isolated and atmospheric, but this is not intended to be a horror game. Do not build the experience around jump scares, gore or disturbing imagery.

At the end of the bunker sequence, the player discovers the VICTUS dummy: an ordinary Vanguard V-01 robot awkwardly positioned behind a chair. It is a deliberately mundane, funny reveal. The dummy is not secretly intelligent, a mastermind, a final boss or a supercomputer. The joke works because the preceding presentation has made the facility feel important, only for the final discovery to be a harmless dummy.

## 3. First-person player presentation

Use a **first-person gameplay camera** as the default and throughout ordinary play. This is a shooter campaign, so aiming, movement, weapon presentation, interactions and environmental discovery are experienced through the player's eyes. Do not implement a third-person follow-camera as the gameplay controller.

Requirements:
- Responsive first-person movement and look, with tunable field of view, sensitivity, acceleration and camera-motion options.
- Stable camera/head rig that respects collision and avoids clipping through walls, floors, door frames and props.
- First-person arms, hands and weapon/tool viewmodels with polished proportions, alignment, animation and lighting.
- Distinct, reliable viewmodel states for idle, aim, firing, reload, weapon switch, utility-tool use, interaction and cinematic handoff.
- Clear reticle/aim feedback with user options for size, opacity, sensitivity and camera shake.
- Maintain consistent camera and player state across pause/resume, checkpoint restore, scene loading and cutscene transitions.
- Full-body player/character models remain useful for authored cinematics, shadows, reflections and other characters' views; they do not change the first-person gameplay direction.
- Cutscenes may use external cinematic cameras to show the squad, character performances and location reveals. Return to first-person before gameplay resumes.
- Test the wide landscape phone aspect ratio and common 16:9 windows; do not assume every screen is identical.

## 4. Core gameplay loop

1. Receive an operation objective and enter the current area.
2. Explore in first person, follow landmarks and notice visual/audio clues.
3. Encounter allied characters, opposing personnel and authored story events.
4. Use the fictional primary/secondary game weapons when combat encounters occur; use readable aim, fire, reload and switch actions with responsive feedback.
5. Manage encounter objectives and progress through the mission rather than simply clearing disconnected enemy waves.
6. Use the separate field utility device to inspect, illuminate or scan selected environmental objects.
7. Trigger conversations, short cinematic beats and major story cutscenes at meaningful discoveries and transitions.
8. Reach mission checkpoints and progress through the forest, perimeter, facility, bunker and lower basement.
9. Complete the final approach, discover the V-01 dummy behind the chair and see the ending.

The game must include actual shooter gameplay, not just weapon props or a HUD mock-up. Combat is fictional game activity with invented weapon attributes, non-graphic feedback and fair, authored encounters. Touch and gamepad users must be able to move, look/aim and use combat actions without pointer conflicts.

## 5. The field utility device

Create an original **secondary non-weapon field utility device** for exploration and environmental storytelling. It can combine:
- A focused light for inspecting dark corners and surfaces.
- A scan mode that reveals or labels authored points of interest.
- A simple interaction pulse/confirmation effect for environment objects.
- Clear on-screen feedback and a polished equip/use/stow presentation.

The utility device complements the shooter loop; it does not replace the player's fictional game weapons. Keep its mesh, effects, animation and UI mobile-friendly.

## 6. Combat, alert and objective feedback

Combat and mission feedback should be immediately understandable without imitating a real-world training interface.

HUD should include:
- Current operation objective and short mission updates.
- Contextual interaction prompt.
- A restrained reticle and aim state.
- Fictional weapon/ammunition state and weapon-switch feedback.
- Encounter/mission awareness state with clear authored changes.
- Optional subtitle and speaker name.
- Utility-tool status.
- Pause/settings and optional performance overlay for demonstration builds.

Keep all weapon statistics and combat behaviour as invented game parameters. Avoid real-world tactical guidance, operational weapon detail or graphic hit presentation. The UI must remain readable on the target phone and support input/accessibility settings.

## 7. Existing characters and intended use

VICTUS already ships two original robot models in its project data:

- **Vanguard V-01**: the broader, angular version. Use this as the VICTUS dummy in the final chair reveal.
- **Vanguard V-02**: the narrower, tapered version. It may appear as a secondary facility character or background presence.

Both variants share the same documented 21-joint skeleton, material family, sockets, and seven animation clips. They are useful assets, not a substitute for human-looking NPCs if the story needs expressive human faces.

For a human protagonist or speaking NPC, create or source original/redistributable models and verify their actual rig, materials, facial geometry, animation clips, and licensing. Do not pretend V-01/V-02 have human faces: their heads use a visor with two eye indicators.

## 8. Campaign and operation structure

The full campaign must travel through every area below. The perimeter, facility, bunker and basement are not optional mentions or a single corridor. Each needs its own researched visual identity, playable space, objectives, cinematic beats and transition.

| Chapter / operation | Main spaces | Purpose |
|---|---|---|
| Prologue | Briefing/deployment space | Establish the mission, player and operator cast |
| Operation 01 — Forest | Forest approach, trails, clearings and landmarks | Introduce movement, first-person shooter controls, environmental clues and first encounters |
| Operation 02 — Perimeter | Outer boundary and access structures | Transition from forest to the facility |
| Operation 03 — Facility approach | Exterior service areas, yards and entry spaces | Build scale and tension before entering |
| Operation 04 — Facility interior | Operations rooms, labs/workspaces and service corridors | Character interactions, discoveries and combat encounters |
| Operation 05 — Bunker | Main bunker rooms and connecting spaces | Develop the story and lead to lower levels |
| Operation 06 — Basement | A substantial lower level with its own layout, props, atmosphere and gameplay | A distinct playable chapter, not a brief hallway |
| Operation 07 — VICTUS chamber | Final approach and chair area | V-01 dummy reveal and ending |

Add original operations/objectives within these spaces as the story requires. Every operation must have a written mission brief, route, objective chain, character appearances, combat beats, checkpoint plan, audio plan and cinematic plan.

## 9. Cinematic cutscenes

Frequent, purposeful, high-quality campaign cutscenes are a core part of the game. Plan an opening/deployment sequence, major location reveals, operator introductions and character moments, transitions between campaign areas, the bunker descent, a dedicated basement reveal, the V-01 chair reveal and an ending. Use shorter in-engine cinematic beats for major discoveries and mission milestones.

Aim for the polished cinematic rhythm of a story-driven military-action campaign, while keeping all scenes, characters, compositions, dialogue, mission designs and assets original. Do not copy Call of Duty content. Prefer real-time VICTUS sequences after verifying the engine's actual timeline/camera/animation support. Build a small documented game-owned timeline only if VICTUS has a genuine gap.

Each cutscene needs deliberate composition, camera motion, actor blocking, expressive animation, lighting, audio/music, voice performance, subtitles, reliable skip/pause/resume, checkpoint-safe state changes and a clean return to first-person gameplay. Cutscenes must be tested on the target device and cannot break mission progression when skipped.

## 9. Visual quality principles

- Prefer a strong coherent frame over an excessive count of effects.
- Every important path junction, prop and character silhouette must remain readable on a phone.
- Use physically based materials and coherent roughness/metalness. Avoid making every surface glossy.
- Let the canopy shape the lighting; use fog to create depth rather than hiding the scene.
- Use a limited palette: wet dark earth, layered forest greens, muted bark, cool mist and restrained warm practical lights as the route nears the facility.
- Preserve shadow and highlight detail. Dark does not mean crushed black, and mist does not mean a white screen.
- Keep foliage density, transparency and shadow casting within measured budgets.
- Prefer authored landmarks and local detail to an unnecessarily large open world.
- Use framing, sound and environmental cues to create atmosphere; do not rely on loud stingers.

## 10. Production quality principles

- All core controls must work with multitouch and gamepad.
- Input must be responsive, with no camera jerks, stuck touches or controls triggering through a modal.
- Dialogue must play real licensed audio with synchronized subtitles. A placeholder beep is not a voice implementation.
- Character transitions must avoid foot sliding, snapping, limb inversion and collision/visual-root separation.
- Physics must be believable enough for gameplay, but never allowed to destabilize the player controller.
- Save/load and lifecycle pause/resume must be tested.
- The game must run from the exported package, not only inside the editor.
- Performance claims must name the exact phone, OS, driver, game commit, settings, scene and test duration.

## 11. Explicit assumptions and open choices

The following are sensible implementation defaults, not hidden claims of owner approval:
- First-person is the gameplay camera; external camera angles are reserved for authored cutscenes.
- Start at 30 FPS with adaptive resolution/quality and attempt a higher rate only after profiling.
- Build a complete, compact campaign through the forest, perimeter, facility, bunker and substantial basement rather than an unnecessarily vast open world.
- Pre-render the finite dialogue audio during development rather than running a large TTS model in the game.
- Use V-01 for the chair reveal; V-02 is optional elsewhere.

Record material changes to these assumptions in a decision note and update this brief.
