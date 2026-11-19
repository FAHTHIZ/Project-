# Campaign Structure and Cinematic Cutscenes

**Direction:** first-person, single-player, cinematic shooter campaign  
**Orientation:** landscape  
**Primary target:** Infinix Hot 10S, 6 GB RAM variant  
**Status:** design handoff; implementation and VICTUS capability checks are still required

## 1. Core direction

SPECIAL OPS is a complete first-person shooter campaign built as a showcase for VICTUS. Exploration, story, characters and environmental detail matter, but the player must also experience a real, satisfying shooter loop. Do not turn the project into a walking simulator or a collection of disconnected environment demos.

Gameplay is first-person throughout ordinary play. The player sees the world through the character's eyes, including the first-person arms and current weapon/tool presentation. Authored story cinematics may deliberately move to external cameras, show the squad, reveal the scale of an area or frame a character moment. Those cinematic camera changes do not change the gameplay camera direction.

The campaign is built around a recurring full squad: the first-person player plus three or four allied operators who travel together wherever mission staging allows. The player remains first-person during gameplay; external cinematic cameras reveal the team as a group. Teammates are active companions with authored reactions, navigation and dialogue, not radio-only voices or background extras. The campaign should have the production ambition and storytelling rhythm of a polished military-action game campaign, with original characters, story, level layouts, art direction, dialogue, music and cinematography. Call of Duty is a quality and pacing reference only. Do not reproduce its missions, characters, maps, scripts, logos, signature shots or distinctive assets.

## 2. Campaign route and operation structure

The route below is the required broad journey. Treat operations as playable mission chapters that may contain multiple connected spaces. Research and document each location before final art production. The exact mission count and detailed layout may be refined after the agent inspects VICTUS and develops the story, but the full route and V-01 reveal must remain.

| Chapter / operation | Main spaces | Dramatic purpose |
|---|---|---|
| Prologue — Briefing / deployment | Short briefing space and transition into the field | Establish the complete recurring squad, player role, team chemistry and tone |
| Operation 01 — Forest approach | Dense forest, narrow trails, clearings and route landmarks | Introduce first-person movement, aiming, basic encounters, environmental clues and the first cinematic reveal |
| Operation 02 — Perimeter | Outer boundary, access structures and transition spaces | Raise the stakes and introduce the facility's presence |
| Operation 03 — Facility approach | Exterior service areas, yards, entry halls and connecting corridors | Shift from natural environments to authored industrial architecture |
| Operation 04 — Facility interior | Operations rooms, laboratories or workspaces, service corridors and character encounter spaces | Deliver story information, combat encounters, exploration and operator/squad moments |
| Operation 05 — Bunker | Main bunker spaces, command/utility areas and connecting corridors | Deepen the mystery and build toward the lower levels |
| Operation 06 — Lower basement | A substantial lower level with its own layout, lighting identity, props and gameplay beats | Make the basement a distinct playable area, not a short hallway attached to the bunker |
| Operation 07 — VICTUS chamber / ending | Final approach, chair area and the V-01 dummy reveal | Deliver the deliberately mundane, funny reveal and a proper ending |

Do not compress the perimeter, facility, bunker and basement into one generic corridor. Give each a distinct visual identity, playable route, story purpose, lighting palette, soundscape, encounter rhythm and at least one memorable landmark.

### Operation design template

Every operation brief must define:
- Narrative purpose and a short player-facing premise.
- Entry and exit points, route diagram and connected sub-areas.
- Objectives and optional discoveries.
- First-person gameplay actions and encounter beats.
- Full squad presence, operator/NPC appearances, squad-to-squad dialogue and player-facing dialogue.
- Cinematic beats and their triggers.
- Environmental art direction, hero props and landmark shots.
- Audio/ambience/music plan.
- Save/checkpoint placement and transitions.
- Expected asset, animation, memory and performance budgets.
- Research references, license/provenance and unresolved decisions.

## 3. First-person gameplay requirements

- Responsive first-person look and movement with tunable field of view, sensitivity, acceleration and camera motion.
- Stable head/camera rig that does not visibly clip through walls or floors.
- First-person arms and hand/weapon viewmodels with clean alignment and readable framing.
- Separate animation/state logic for weapon presentation, utility-tool presentation, interactions and cutscene ownership.
- Consistent reticle and aim feedback, with options for size, opacity, sensitivity and motion comfort.
- Gameplay camera must return to the same valid first-person state after any cinematic, pause, reload, scene transition or checkpoint restore.
- External third-person camera rigs are cutscene-only unless the owner explicitly changes the direction.

## 4. Cinematic cutscene ambition

Cutscenes are a major part of the intended experience, not an optional bonus. Plan for frequent, purposeful cinematics across the campaign. Use a mix of longer story scenes and shorter in-engine cinematic beats so the game feels authored and film-like without interrupting every minute of gameplay.

### Required cinematic beats

At minimum, plan and implement:
1. Opening title / mission setup and deployment.
2. First forest arrival and the reveal of the route ahead.
3. First important encounter with an operator or NPC.
4. Forest-to-perimeter transition.
5. Perimeter-to-facility reveal.
6. Facility entry and first major interior reveal.
7. One or more squad/operator character moments that establish personalities and stakes.
8. Bunker discovery and descent.
9. Lower-basement entrance and a distinct reveal of its scale/purpose.
10. Major discovery before the final room.
11. The V-01 chair reveal, with deliberate timing and visual composition.
12. Ending scene and credits/epilogue handoff.

Add additional short cinematic moments when justified by story events: a mission completion, a new location, a major discovery, a character entrance or an important change in the environment. Do not pad the game with repetitive camera pans.

### Quality bar

Each cinematic should be storyboarded and reviewed for:
- Clear dramatic intention and readable staging.
- Deliberate shot sizes, camera movement, screen direction and edit rhythm.
- Convincing full-squad blocking, eye-lines, gestures, body language and listener reactions; every operator should have a clear place in the scene.
- Visible facial performance for the whole speaking cast: eye direction, blinks, brows, expressions, jaw and synchronized mouth shapes.
- Good lighting and environment composition, including readable faces on a phone.
- Voice performance, spatial audio, music and sound effects mixed as one scene; squad members speak to each other as well as to the player.
- Accurate subtitles, speaker identification and timing.
- Clean transitions into and out of gameplay.
- Appropriate duration and pacing; let important reveals breathe without dragging.
- Performance and memory behaviour on the actual target device.

Avoid relying only on dialogue boxes over a static camera. Use camera choreography, character animation, environmental action, sound and editing to communicate.

## 5. Environment art and rendering quality

The goal is a beautiful, coherent, cinematic game world—not a technically correct greybox. Each operation must have a visual target sheet and a reviewed in-engine result.

### Global art direction
- Use a consistent material language, palette and lighting philosophy across the campaign, while giving each location its own identity.
- Compose spaces with clear foreground, middle-ground and background layers, strong silhouettes, believable scale and purposeful landmarks.
- Use physically based materials with convincing roughness, normal detail, edge wear and restrained emissive accents. Avoid excessive gloss, flat colour blocks and visibly repeated textures.
- Pay attention to contact shadows, grounded props, believable surface transitions, atmospheric perspective, exposure and colour grading.
- Use environmental storytelling: signs of prior activity, purposeful prop placement, wear patterns and light/sound cues that guide attention without cluttering the scene.

### Location-specific visual targets
- **Forest:** dense layered canopy, varied tree silhouettes, fern/undergrowth foreground, readable dirt trail, damp earth, natural diffuse light, brighter canopy openings, depth haze and restrained mist. Preserve the mood of the supplied references in a wide landscape composition.
- **Perimeter:** a clear visual transition from organic forest to controlled infrastructure; strong scale cues, layered boundary elements, weathering and readable approach routes.
- **Facility:** distinctive exterior massing and interior architecture, practical lighting, believable workspaces, prop storytelling, material variation and strong reveal compositions.
- **Bunker:** heavier structural forms, compressed spaces opening into larger chambers, purposeful practical lights, signage/wayfinding and a distinct sound/lighting identity.
- **Lower basement:** a genuinely separate visual chapter with its own architectural language, vertical scale, material condition, lighting palette, hero props and memorable reveal—not a recoloured bunker corridor.
- **Final chamber:** carefully controlled composition and lighting that support the V-01 chair reveal and comedic timing without turning the room into a horror set.

### Renderer and mobile proof
- Recheck current VICTUS renderer capabilities before relying on a feature. Use PBR, IBL, shadows, atmosphere, fog, reflections, decals, LOD, instancing and post-processing only where verified and visually useful.
- Profile foliage, shadow-casting lights, transparent materials, particles, volumetric effects, reflections and post-processing on the target phone. Prefer a beautiful stable frame over expensive effects that cause stutter.
- Produce matched screenshots/captures at each quality tier and compare actual visual differences. Record frame pacing, memory, thermal behaviour and quality settings from real tests.
- Inspect every major space in motion, not only as a still screenshot. Look for texture shimmer, foliage popping, shadow acne, temporal ghosting, clipping, exposure pumping and visible LOD transitions.
- Do not call a scene finished until the packaged build matches the approved reference captures at its supported quality tier.

## 6. Implementation and VICTUS research

Before implementation, inspect the current VICTUS main branch and its agent instructions. Research the actual scene sequencing, animation, camera, audio, subtitle/UI and save/checkpoint APIs. The historical engine audit is not proof that a current cinematic sequencer exists.

Preferred implementation order:
1. Use an existing, verified VICTUS sequencer/timeline if it genuinely supports the required scene, camera, actor and audio events.
2. Otherwise, implement a small game-owned cinematic timeline using documented VICTUS primitives: timestamped camera transforms, actor animation states, dialogue/audio cues, subtitle events, environment events and input ownership.
3. Keep cinematic data separate from mission logic so scenes are editable and testable.
4. Prefer real-time in-engine cutscenes to large pre-rendered videos for package size and visual continuity. Use pre-rendered media only when necessary, licensed and proven to decode smoothly on the target phone.
5. Preload or stage assets safely; prevent scene transitions from causing long stalls or memory spikes.

Do not add a second camera/animation framework if VICTUS already provides a suitable system. Do not claim a sequencer feature exists until the live API and a working sample prove it.

## 7. Cutscene behaviour and accessibility

- Provide skip controls after a short initial input grace period. Skipping must never skip a required mission flag, item grant, checkpoint or story state transition.
- Provide subtitle size/background controls and speaker labels.
- Respect master, dialogue, ambience, music and effects volume.
- Pause/resume and app backgrounding must not leave a cinematic half-owned camera or duplicated audio.
- Save/checkpoint logic must define whether a cinematic replays, resumes or is skipped after loading.
- Ensure all essential mission information is also available in objectives, dialogue logs or captions.
- Offer replay for key cinematics from a suitable menu or extras screen when practical.
- Add a setting to reduce camera shake and intense camera motion.

## 8. Verification gates

A cutscene is complete only when it:
- Triggers from the correct campaign state and plays exactly once unless replayed.
- Shows the intended camera/actor sequence in the exported game.
- Plays the correct voice, music and effects with synchronized subtitles.
- Shows the complete squad with readable blocking, eye-lines, facial animation and visible reactions.
- Preserves every squad member's identity and continuity between gameplay and cinematics.
- Can be skipped without breaking the mission.
- Can be paused/resumed and survives app lifecycle changes.
- Returns control to first-person gameplay with input and camera state restored.
- Passes on desktop and the physical phone when available.
- Has asset and performance evidence recorded in the build/test log.

The campaign is not complete until all required operations, all key cinematic beats, the basement and the final V-01 reveal are playable and verified.
