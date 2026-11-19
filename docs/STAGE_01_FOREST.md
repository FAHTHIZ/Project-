# Stage 01 — Forest Visual and Playable Environment Brief

**Source set:** four user-supplied videos, inspected in upload order on 2026-11-19.  
**Recorded media properties:** each is 720 × 1280, 30 fps; durations approximately 14.07 s, 16.11 s, 11.14 s and 13.12 s.  
**Important:** the clips are portrait captures. The game must be a native landscape composition. The design descriptions below are observations of the supplied clips, not claims about the capture source or the software used to make them.

## 1. Visual target in one paragraph

A dense, wet-looking woodland with a narrow, natural dirt path that leads the eye forward. Layered trees form a roof over the path. Ferns, shrubs, grasses and broad-leaf ground plants crowd the foreground. The middle distance fades into cool, pale mist. The nearest vegetation remains detailed and saturated enough to read, while the far forest becomes soft and low-contrast. The palette is mostly deep forest green, wet earth brown, muted bark and cool grey-green atmosphere. Brightness comes from diffuse light filtering through gaps in the canopy rather than a clear blue sky or strong desert sunlight.

The mood is quiet, curious and isolated. It is not a horror mood: no gore, scare staging or aggressive visual effects are needed.

## 2. Reference-by-reference observations

### Reference 01 — misty trunks and fern-lined path

- A large dark tree trunk anchors the foreground, slightly off-centre.
- A horizontal branch creates a strong near-camera silhouette.
- Layered trees recede into a pale, mist-filled background.
- The forest floor and path are dark brown, with visible damp/organic texture.
- Low plants and fern-like leaves cluster along the path edges.
- The light is diffuse and cool; visibility decreases gradually with distance.
- The frame has several depth planes: foreground trunk/branch, shrubs, mid-distance trunks, distant fog.

**Translate into game content:** create a foreground tree/branch framing element, a readable path, several shrub/fern clusters, a tall-tree backdrop and depth fog. Keep the player's forward route legible even where the ground is dark.

### Reference 02 — enclosed foliage tunnel

- A narrow path enters a more enclosed section of the woods.
- The canopy and thick broad-leaf foliage form a dark arch around the path.
- Brightness is concentrated in a pale opening beyond the vegetation.
- The foreground foliage is dark and dense; the path remains visible as a slightly lighter central strip.
- This reference has the strongest feeling of a tunnel through the trees.

**Translate into game content:** build a short, enclosed path segment with layered overhead branches and side foliage. Use the brighter opening as the visual destination, not a flashing objective marker. Keep a low but readable exposure in the shaded section; do not crush the ground into black.

### Reference 03 — fern and undergrowth detail

- The foreground contains large, easily readable fern fronds.
- More open woodland is visible behind the ferns, with many thin tree trunks and broken gaps in the canopy.
- Light is brighter and more even than the enclosed-path references.
- Leaves overlap at several scales, creating strong depth and an impression of dense vegetation.
- The nearest ferns are a major visual feature, not just a flat green carpet.

**Translate into game content:** make this the most vegetation-rich showcase clearing. Put a few large fern silhouettes close to the camera, medium shrubs behind them and instanced small plants in the middle distance. Use a limited number of hero plants with clear silhouettes and a repeated, cheaper vegetation set for volume.

### Reference 04 — dark, narrow green corridor

- A path continues through dense vegetation with branches and leaves meeting above it.
- The corridor is darker and more enclosed than reference 03.
- The ground path is central and recedes into the scene.
- Small brighter gaps in the canopy provide direction and depth.
- Dark greens dominate, but the path and tree edges still separate from each other.

**Translate into game content:** use this as the final forest corridor before the perimeter transition. The path should remain navigable and contrast against nearby foliage. Use the darker canopy to transition naturally toward built structures.

## 3. Landscape translation

Do not rotate a portrait image, simply crop it, or reproduce a tall portrait composition. Reconstruct the environment for a wide screen:

- Keep the route visible through the horizontal centre or slightly below centre.
- Place foreground trunks and branches near the left/right edges as framing layers, not as walls that obscure the route.
- Add lateral depth: trees and plant clusters should extend across the width so the wide camera does not reveal empty edges.
- Use a wider distribution of canopy gaps and bright distant landmarks.
- Preserve enough space on the lower left and lower right for touch controls.
- Keep the central play area clear of persistent HUD clutter.
- Account for a very wide 20.5:9-class phone panel in landscape; test the camera and UI at the actual phone aspect ratio, not only 16:9.

The reference videos provide atmosphere and vegetation shape. They do not define the finished game's exact map, geometry, camera lens or resolution.

## 4. Proposed playable layout

Build a compact authored route, not a huge open world. Suggested order:

1. **Entry path:** begin beneath taller trees, with a clear forward route and sparse close ferns.
2. **Trunk-framed bend:** use a strong foreground trunk/branch silhouette and a shallow bend to reveal depth.
3. **Fern clearing:** open the canopy slightly, show hero ferns in the near field, and place the first inspectable environmental clue.
4. **Enclosed green corridor:** narrow the route under heavy canopy; let the light beyond pull the player onward.
5. **Perimeter hint:** introduce distant man-made details through the foliage (fence line, marker light, path material change or structure silhouette). This is a transition hint, not a full facility stage.

The agent may adapt route length and exact landmarks after prototyping. Keep each segment distinct enough to demonstrate one rendering/interaction feature without feeling like a benchmark gallery.

## 5. Environment asset plan

### Hero assets

Create or source a small group of high-quality, reusable hero assets:
- Several distinguishable tree silhouettes (trunks, branch structure, canopy).
- Fern variants with strong frond silhouettes.
- Broad-leaf shrub variants.
- Ground cover and small grasses.
- Fallen branch/log and damp soil/rock props.
- A few authored points of interest: trail marker, weathered sign, abandoned field item, sensor/panel or other non-weapon environmental object.

Hero assets should withstand close camera viewing. Use original procedural modelling or verified redistributable assets. A repeated tree with a different scale is useful for fill but should not be the only silhouette.

### Repeated vegetation

Use instancing where VICTUS supports it. Avoid placing hundreds of unique entities just to make the screenshot look dense. Divide vegetation into spatial groups/chunks so distant groups can have less detail and fewer active instances. Keep near-path collision selective; do not make every leaf a physics collider.

Foliage alpha cutouts can become overdraw-heavy, especially when viewed through overlapping canopy layers. Profile visible alpha-tested draws, triangles and fill cost. Use alpha-coverage-preserving mips where supported by the importer.

### Terrain and ground

Use a compact terrain/mesh route with:
- a visibly readable path surface;
- varied damp earth, leaves, moss and occasional exposed roots;
- subtle height variation to make walking feel grounded;
- no excessive geometry under foliage that fully hides it;
- stable collision at the path edges.

VICTUS has terrain and heightfield workflows, but its foliage limitations must be considered. Use the smallest terrain workflow that satisfies the authored route; do not create a large terrain world just because a terrain tool exists.

## 6. Lighting and atmosphere recipe

The intention is layered, restrained outdoor light. Do not make all light sources equally bright.

### Base lighting

- One principal directional daylight source with a soft, overcast character.
- Environment/sky contribution that keeps shaded leaves and the player's clothing readable.
- PBR materials with controlled roughness; wet ground can be slightly shinier than bark, but should not become a mirror.
- Use the engine's physical sky/environment image-based lighting workflow where appropriate, but bake or reuse environment data rather than performing repeated expensive work at runtime.

### Canopy and shadows

- Tree trunks, larger branches and selected foliage clusters should cast the shadows that make the forest feel layered.
- Do not make every tiny grass card a shadow caster.
- Use the lowest shadow resolution/cascade count that preserves a readable frame on the device.
- Prevent high-contrast shadow patterns from hiding the path or the player.
- Validate alpha cutout shadow behaviour and mip coverage with the real foliage textures.

### Fog

- Use atmosphere/fog to separate foreground, middle distance and far trees.
- The first prototype should compare a low-cost distance/height fog setup with volumetric fog.
- VICTUS documents volumetric fog as Medium-tier-or-higher, bounded by a 160 × 90 column grid, with no volumetric self-shadowing. It can be too expensive or too coarse on the target Mali GPU; do not depend on it until measured.
- Fog should be pale grey-green, not opaque white. The path and nearby plants must remain visible.
- Use local fog volumes only for a specific authored transition, not as overlapping fog boxes everywhere.

### Light shafts and bright openings

Use composition and the existing renderer's tested atmosphere/lighting first. If a volumetric shaft effect is too expensive, create the same visual impression with layered fog and controlled bright gaps in the canopy. Do not add a screen-wide post effect just to simulate every ray of sunlight.

### Colour and exposure

- Keep the overall image cool green/grey, with enough warm earth tones to anchor the ground.
- Maintain texture detail in the darkest leaves.
- Avoid neon greens, strong teal/orange grading, excessive bloom and heavy vignettes.
- Let exposure settle consistently; rapid brightness pumping is unacceptable.
- Compare Low/Medium/High captures at matching camera positions.

## 7. Animation and player movement in this stage

- Gameplay uses a first-person camera. Prioritize responsive head/camera motion and polished first-person arms/hands/weapon viewmodels; do not use a third-person follow camera for ordinary play. Full-body character animation is for authored cutscenes and other characters' views.
- Keep ordinary walking as the dominant traversal movement; sprinting is a short optional traversal action, not the only way to move.
- First-person hands/arms must remain stable, avoid clipping and stay out of the centre of the view during movement and combat.
- Add first-person viewmodel transitions for ready/idle, aim, firing, reload and weapon switch using the original fictional game weapon designs.
- Use full-body operator/NPC performances for authored cinematic moments; keep their costumes and animation consistent with the later facility/bunker scenes.
- Blend starts/stops and turns smoothly.
- Add subtle idle breathing and head/upper-body look-at responses where the rig supports them.
- Use terrain-aware foot placement only if existing IK can be configured reliably; otherwise author a stable animation and avoid uneven ground that causes obvious floating.
- A small number of authored trip/fall events can demonstrate physical response. Keep falls safe, non-graphic and predictable, and always return to normal movement cleanly.
- Do not let a physics demonstration interrupt normal control or cause the player to become stuck.

## 8. Audio target

The forest should sound alive but not busy:
- layered tree/leaf ambience;
- soft wind/air movement;
- distant birds/insects at restrained levels;
- footsteps differentiated by ground surface;
- occasional nearby environmental events;
- restrained low-frequency atmosphere that does not become a horror drone;
- clear dialogue when the player is near a speaking character.

Use positional audio and the engine's Ambient, SFX, Voice and UI buses. No audio asset is ready merely because it downloads: listen to it, check clipping/noise, confirm rights and test on the phone speaker/headphones.

## 9. First-stage demonstration beats

The following beats should be demonstrated naturally:

| Beat | Engine capability exercised | Player-visible result |
|---|---|---|
| Enter the forest | First-person player controller/camera, 3D PBR, environment lighting | Stable first-person movement under a layered canopy |
| Pass close vegetation | Asset LOD, alpha-tested materials, instancing, culling | Plants remain detailed nearby without overwhelming the frame |
| Walk into mist | Atmosphere/fog, directional light, shadows | Clear depth separation without hiding the path |
| Inspect a point of interest | UI prompt, touch input, script/event, field-tool presentation | Simple readable interaction |
| Hear a nearby character/event | Audio bus, spatial playback, subtitles | A voice or sound belongs to a world location |
| Play the first shooter encounter | First-person viewmodel, fictional weapon actions, enemy AI, HUD, game audio/effects | A complete, readable, non-graphic shooter encounter with working aim/fire/reload/switch actions |
| Experience a cinematic reveal | Camera sequencing, character blocking, dialogue, music/SFX and subtitles | A polished authored scene that returns cleanly to first-person gameplay |
| Experience an authored stumble | Animation/physics integration, recovery state | Safe physical response and immediate return to control |
| Approach perimeter | Scene transition or authored zone progression | The forest leads naturally into the next stage |

## 10. Performance-specific scene budget

Do not set final geometry counts from guesses. Establish a reproducible benchmark scene and collect measurements. Practical rules:
- Use instancing for repeated static vegetation.
- Use distance-based grouping and LOD.
- Minimize transparent layers and overlapping alpha cards.
- Keep high-detail collision to the playable path and interactable props.
- Avoid dozens of independently shadowed local lights.
- Avoid high-frequency particles in every forest segment.
- Stream/load only the upcoming area; do not hold all later stages resident.
- Keep the number of animated characters and active facial morphs small.
- Prefer precomputed environment data where possible.
- Keep a representative camera capture for each segment so visual regressions can be compared.

## 11. Acceptance criteria for Stage 01

Stage 01 is ready only when:
- the full route is playable in landscape;
- all four references have a recognizable influence on the art direction;
- the wide phone aspect ratio has no empty-world edges or obstructed route;
- lighting remains readable at the target device quality;
- foliage does not cause unacceptable overdraw, memory pressure or frame-time spikes;
- the player can move, turn, interact and recover from authored movement reactions;
- audio and subtitles function in the exported Android game;
- touch controls and gamepad controls both work;
- the stage has start, completion, save/restore and a route to Stage 02;
- visual captures, logs and measured performance are retained in the repository.
