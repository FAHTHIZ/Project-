# Operators, Costumes and Fictional Shooter Design

**Direction:** original operator cast and a real first-person shooter gameplay loop  
**Status:** art/game-design research brief; no real-world weapon instruction or functional design

## 1. Visual identity and cast

Create a small, memorable ensemble rather than a crowd of interchangeable masked characters. Research and propose a compact cast with distinct silhouettes, clothing palettes, voices, personalities and story roles. At minimum consider:
- The player character / mission protagonist.
- A recurring full squad of the first-person player plus three or four allied operators, all present in gameplay and cinematics where mission staging allows.
- A facility/security group with a clearly different visual identity.
- One or two named speaking characters who carry important story information.

The number of fully animated characters present at once must be chosen from measured device performance, not from desktop assumptions. Use distant/background characters sparingly.

For every named character, document:
- Story role, personality, dialogue style and relationship to the player.
- Silhouette and recognizable visual feature.
- Face visibility, headwear and hair/face design.
- Main clothing layers, palette, materials and condition.
- Gloves, footwear, protective-looking costume pieces, communication accessories and carried props as visual art-direction elements.
- Idle, walk, run, turn, gesture, talk, listen, interaction and cinematic animation needs.
- First-person visibility needs: hands/arms if the character is the player; full body/face when visible to other characters or in cinematics.
- Voice casting/recording rights, subtitles and facial/lip-sync requirements.
- Model/texture/rig provenance and redistribution license.

## 2. Clothing and costume direction

Aim for a believable, contemporary fictional field-team appearance with strong visual readability on a small landscape screen. Clothing should look layered, worn by the environment and individually tailored to each character rather than like identical stock uniforms.

Potential visual elements to research and combine:
- Base layer: field shirt or fitted long-sleeve top.
- Outer layer: lightweight field jacket, overshirt or weather shell, depending on the location.
- Lower-body silhouette: practical trousers with visible fabric folds and restrained reinforcement shapes.
- Footwear: durable boots with a readable sole and believable movement deformation.
- Hands: gloves or exposed hands as appropriate for character identity and close-up animation.
- Costume silhouette: a restrained vest/carrier-like outer shape, straps, utility pouches and a compact pack where it serves the character design.
- Head and communication styling: cap, beanie, helmet-like headwear, headset or ear protection only where it suits the character; do not make every character wear the same full-face mask.
- Small identity details: original fictional patches, colored tabs, unit marks, fabric repairs and personal items. Never use real unit insignia or copy another game's distinctive marks.

Make variants for the environment: dry forest, rain/wet foliage, indoor facility lighting and basement dust/grime. Changes should be authored art details, not a requirement to simulate expensive cloth physics. Use texture/material variants where possible.

The protagonist's hands, sleeves and first-person arms are hero assets. Give special attention to proportions, wrist transitions, glove seams, sleeve materials, believable grip poses as a visual animation, lighting response and clipping at the screen edge. Keep the viewmodel stable and avoid obstructing the centre of the screen.

## 3. Fictional weapon art and gameplay scope

The game must actually play as a shooter. Implement a small, polished set of **original fictional game weapons** rather than leaving the player with only a scanner. The first implementation should be limited to a primary weapon and a secondary option; add another special-purpose game weapon only if the campaign has a clear need and the device budget allows it.

Research should focus on game-development concerns:
- Original silhouette and fictional naming.
- Colour/material language and readability at first-person screen scale.
- Clear distinction between primary and secondary choices.
- First-person viewmodel proportions and screen placement.
- State transitions and animation quality: equipped, idle, aim, fire, reload, switch, inspect and stow.
- Distinct fictional sound identity and mix.
- Muzzle/impact visual effects that are readable but not visually overwhelming.
- Reticle, ammunition and weapon-state UI.
- Abstract game balance: damage class, fire cadence, range bands, spread, reload duration and ammunition economy as invented tuning values.
- Accessibility: adjustable aim sensitivity, camera shake, reticle options and input alternatives.
- Performance: mesh LODs, texture budget, animation cost, particle count and audio memory.

All weapon names, silhouettes, visuals, sounds, animation timing and gameplay statistics must be original fictional content. Do not reproduce an exact real firearm or provide real-world specifications, construction information, operational instructions, maintenance guidance, aiming/handling lessons or tactical doctrine. No real-world weapon training or realistic combat simulator is intended. Model firing, recoil, spread, damage, reload timing and ammunition entirely as game systems with invented values.

Keep shooter interactions responsive and fair:
- A clear fire action with immediate audiovisual feedback.
- An aim/alternate-view action with a readable and stable sight picture.
- A reload action with clear start/completion feedback and interruption rules.
- A weapon-switch action with a predictable transition.
- Sensible hit confirmation and enemy reaction cues.
- Encounters built around readable game spaces, authored pacing, cover as a level-design feature and fair enemy telegraphs.
- Non-graphic impact and defeat presentation; do not add gore.

Do not create weapons as static props. The player must be able to use the shipped game weapons in the actual mission flow, with input, animation, HUD, sound, effects, AI response and checkpoint state all connected.

## 4. Opposing characters and encounter readability

Opposing personnel should have an original faction identity that is visually distinct from allied operators and facility workers. Differentiate them by broad palette, silhouette, clothing condition, face visibility and fictional insignia. Avoid copied real-world uniforms or identifiable military branding.

Enemy characters are game AI actors, not tactical training examples. Their behaviour should be tuned for clarity, fairness, performance and authored drama. Use readable state changes and telegraphs. Keep groups small enough for the phone to animate and render reliably. Avoid graphic injury/death content.

## 5. Research workflow

The autonomous agent must conduct research before locking character or weapon visuals:
1. Collect a range of visual references from legitimate sources: professional game-art breakdowns, character-design portfolios, licensed asset previews, animation breakdowns and material references.
2. Separate observations from design proposals. Record what a reference contributes: silhouette, fabric/material treatment, colour, lighting, proportions, animation or visual storytelling.
3. Use references to inform an original design; do not trace or reproduce copyrighted costumes, weapons, characters, game screenshots or distinctive compositions.
4. For game weapons, focus strictly on fictional art direction and game presentation rather than functional real-world weapon information.
5. Record author/provider, exact asset/page URL, license, attribution and redistribution rights for every asset used.
6. Prefer original models or assets with explicit redistribution terms compatible with the game's release.
7. Prototype the first-person arms and weapon viewmodel early; test at the actual landscape phone resolution before producing the full cast.
8. Verify the assets through the live VICTUS importer and runtime. A Blender or browser preview is not proof of engine compatibility.

## 6. Production order

1. Establish the first-person camera, movement, touch/gamepad/keyboard input and viewmodel framing.
2. Create one complete first-person weapon loop using an original fictional model and invented game parameters.
3. Build the complete allied squad roster: every member gets a finished face, costume, voice, personality, animation identity and mission role. Implement them as companions, not just cutscene extras.
4. Add companion navigation, regroup/wait/follow states, contextual squad chatter, spatial dialogue and radio communication.
5. Add one opposing character with distinct costume and readable animation.
4. Integrate one complete shooter encounter into the actual mission, including AI, HUD, audio, effects and checkpoint behaviour.
5. Validate the slice on desktop and the target phone before expanding the cast or weapon inventory.
6. Add the remaining operator designs and weapon variants only as required by the campaign and measured performance.
7. Integrate the operators into the campaign cutscenes; ensure models, voices, animation and cinematic lighting match gameplay assets.

## 7. Completion checks

- The campaign contains a recurring full squad of the player plus three or four original, visually distinct allied operators and a distinct opposing cast.
- Squad members appear together in playable missions and cinematics, communicate naturally, react to one another and retain continuity between operations.
- The player character has a polished first-person arms/hand presentation.
- A usable primary and secondary fictional game weapon exist and are integrated into missions.
- Aim, fire, reload, switch, effects, sounds, HUD and enemy reactions all work in the exported game.
- No placeholder weapon panels, non-functional props or empty interaction stubs remain.
- Costume, weapon, voice, animation and audio provenance is recorded.
- All combat presentation is non-graphic and the systems remain game abstractions rather than real-world instruction.
- Operator appearances and weapons remain consistent between gameplay, dialogue scenes and cinematics.
