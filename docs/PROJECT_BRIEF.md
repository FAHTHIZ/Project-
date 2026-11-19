# Project Brief — SPECIAL OPS / VICTUS Field Demonstration

**Document date:** 2026-11-19  
**Game orientation:** Landscape  
**Primary device:** Infinix Hot 10S, 6 GB RAM variant  
**Engine:** VICTUS, live main branch  
**Genre:** Third-person exploration / field investigation / environmental interaction  
**Working title:** SPECIAL OPS (title can be reconsidered after a playable build)

## 1. Product purpose

This game is a real, playable demonstration of VICTUS. It should show that the engine can deliver a coherent 3D experience on a budget-class Android phone: attractive outdoor lighting, dense vegetation, fog, convincing materials, responsive character animation, physical reactions, voiced dialogue, interactive props, stable controls, loading, save/restore, and a complete packaged game.

It is not a renderer screenshot scene. The player must have meaningful control, discover the route, interact with the environment and characters, reach a conclusion, and be able to play it again.

The game should be recognizable as a product even to someone who has never heard of VICTUS. Engine demonstrations should happen naturally during gameplay rather than interrupting the experience with a technical checklist.

## 2. Player experience

The player enters a secluded forest and follows a faint route toward a remote underground facility. The first stage is quiet and visually rich. The player notices environmental details, inspects points of interest with a field utility device, encounters at least one speaking character, and gradually discovers signs of the facility.

The tone is grounded, curious and cinematic. The forest can feel mysterious, isolated and atmospheric, but this is not intended to be a horror game. Do not build the experience around jump scares, gore or disturbing imagery.

At the end of the bunker sequence, the player discovers the VICTUS dummy: an ordinary Vanguard V-01 robot awkwardly positioned behind a chair. It is a deliberately mundane, funny reveal. The dummy is not secretly intelligent, a mastermind, a final boss or a supercomputer. The joke works because the preceding presentation has made the facility feel important, only for the final discovery to be a harmless dummy.

## 3. Camera and player embodiment

Use a **third-person camera** as the default. This is a deliberate showcase decision: it lets the player see the character's full locomotion, foot contact, physical reactions, falls, interaction animations and silhouette while moving through the forest.

Requirements:
- Responsive follow camera with smoothing that does not feel delayed.
- Obstruction handling that avoids clipping through trees, walls and door frames.
- Sensible collision and camera distance in narrow interiors.
- Optional close follow distance only if it remains readable and stable.
- Camera-relative movement with a clear and predictable relationship between the left stick and camera-look region.
- Keep camera presentation separate from player movement and physics.
- Camera must reframe for conversations and the final reveal without losing player orientation.
- Test the unusually wide landscape aspect ratio of the phone; do not assume a standard 16:9 viewport.

A first-person presentation is not the default. Do not switch the game to first-person merely because it is common in tactical games; that would hide much of the character animation that this demo is intended to showcase.

## 4. Core gameplay loop

1. Move along the forest route.
2. Notice a visual, audio or environmental clue.
3. Approach and inspect it.
4. Use the field utility device to illuminate or scan a designated point of interest.
5. Read a short contextual response, hear a character or environment reaction, or trigger a simple world-state change.
6. Continue toward the next landmark.
7. Reach the perimeter and later facility/bunker stages.
8. Meet and speak with characters.
9. Reach the V-01 dummy behind the chair and complete the stage.

Interaction design must be clear on touch and gamepad. A highlighted object should not require pixel-perfect tapping. Context prompts should explain what action is available.

## 5. The field utility device

Create an original **non-weapon field utility device** as the player's main active tool. It can combine:
- A focused light for inspecting dark corners and surfaces.
- A scan mode that reveals or labels authored points of interest.
- A simple interaction pulse/confirmation effect for environment objects.
- Clear on-screen feedback and a short, polished equip/use/holster-style presentation only in the sense of presenting and stowing an ordinary utility gadget.

This tool must not become a parallel combat system. Its purpose is exploration, inspection and environmental storytelling. Keep its mesh, effects, animation and UI mobile-friendly.

## 6. Alert and objective feedback

The game needs an alert system, but it should support exploration rather than combat. Use an authored **facility-awareness / objective-alert state** such as:
- Calm: no active event.
- Noticed: a clue, sensor or character has reacted.
- Investigating: the current objective or a nearby character is responding.
- Resolved: the player completed the interaction.

Do not build real-world tactical guidance or combat behaviour. The player should understand why the state changed and what safe, ordinary interaction is available next.

HUD should include:
- Current objective (one short sentence).
- Contextual interaction prompt.
- Utility-tool status.
- Compact alert/awareness state.
- Optional subtitle and speaker name.
- Pause/settings.
- Optional performance overlay for demonstration builds, disabled by default.

## 7. Existing characters and intended use

VICTUS already ships two original robot models in its project data:

- **Vanguard V-01**: the broader, angular version. Use this as the VICTUS dummy in the final chair reveal.
- **Vanguard V-02**: the narrower, tapered version. It may appear as a secondary facility character or background presence.

Both variants share the same documented 21-joint skeleton, material family, sockets, and seven animation clips. They are useful assets, not a substitute for human-looking NPCs if the story needs expressive human faces.

For a human protagonist or speaking NPC, create or source original/redistributable models and verify their actual rig, materials, facial geometry, animation clips, and licensing. Do not pretend V-01/V-02 have human faces: their heads use a visor with two eye indicators.

## 8. Stage structure

Only Stage 01's visual direction is fixed by the supplied videos. Later stages are a research task for the coding agent; see the agent contract and production plan.

| Stage | Purpose | Current direction |
|---|---|---|
| 01 — Forest approach | Establish atmosphere, movement and environment interaction | Directly grounded in the four supplied forest videos |
| 02 — Perimeter | Transition from natural environment to a human-built boundary | Research references and propose an original layout before asset production |
| 03 — Facility exterior / service areas | Demonstrate modular architecture, materials, practical lights, doors and interactions | Research and document independently |
| 04 — Bunker interior | Demonstrate interior lighting, spatial audio, dialogue, props and character behaviour | Research and document independently |
| 05 — Dummy reveal | Pay off the setup with the V-01 dummy behind a chair | Use existing V-01 asset; keep the gag simple and readable |

The agent may propose a better sequence after researching later-stage references, but must preserve the forest-to-facility-to-bunker direction and the V-01 reveal unless the owner explicitly changes it.

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
- Third-person is the default camera because it best showcases character motion.
- Start at 30 FPS with adaptive resolution/quality and attempt a higher rate only after profiling.
- Build a compact, carefully authored forest route rather than a vast open world.
- Pre-render the finite dialogue audio during development rather than running a large TTS model in the game.
- Use V-01 for the chair reveal; V-02 is optional elsewhere.

Record material changes to these assumptions in a decision note and update this brief.
