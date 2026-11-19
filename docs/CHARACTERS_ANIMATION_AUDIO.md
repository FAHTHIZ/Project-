# Characters, Animation and Dialogue Audio

**Goal:** make characters feel present and readable on a budget phone without overwhelming the engine or inventing capabilities it does not currently have.

## 1. Existing VICTUS characters

Two original Vanguard robot variants are already included in the VICTUS project data:

### V-01 — the reveal dummy

- Broader shoulders, angular split chest shell and squared head crown.
- Pearl ceramic shell, graphite structure, titanium accents and a dark visor with two cyan-white indicators.
- About 20.6k triangles at highest LOD and about 10.5k vertices.
- Four material slots.
- Shared 21-joint skeleton.
- Existing clips: Idle, Walk, Run, Jump, Fall, Land and Interact.
- Named attachment nodes on head, hands, back and root.

**Use V-01 for the VICTUS dummy behind the chair in the final reveal.** It should look like an ordinary physical dummy, not a boss, sentient machine or AI entity. A slightly awkward pose and a quiet room are enough for the gag.

### V-02 — secondary variant

V-02 has a narrower, more tapered silhouette but shares the same rig and animation controller. Use only if a second robot character contributes something to the story. It is not necessary to force both models into Stage 01.

Read the current [VICTUS character guide](https://github.com/FAHTHIZ/VICTUS/blob/main/docs/CHARACTERS.md) and inspect the actual GLB files before use. Never duplicate a copy of the robot assets inside the game repo when the normal VICTUS template/project asset workflow can provide them.

## 2. Human character needs

The story and reference direction call for readable expressions and voiced character interactions. The Vanguard models are robots and do not supply human faces. If human characters are required, create or acquire a small original, redistributable cast:
- One player/explorer model.
- One principal speaking NPC for Stage 01.
- Optionally one secondary NPC later if a researched stage needs them.

Avoid a large crowd on the first phone target. More characters mean more draw calls, animation evaluation, skinning, audio voices and memory.

Character art requirements:
- Clear silhouette at gameplay camera distance.
- A face that reads at the actual phone screen resolution.
- Sensible topology around shoulders, elbows, hips, knees, neck and jaw.
- A shared, documented rig where possible.
- Textures and materials that use the existing PBR importer.
- Normalized scale and facing axis.
- Explicit skeleton/root/collider separation.
- GLB export tested through VICTUS's normal importer, not just Blender preview.

Model provenance and license must be documented before the asset enters the final package. Do not grab a model from an arbitrary asset dump or infer permission from a preview page.

## 3. Animation coverage

Create a small, polished animation library rather than dozens of low-quality one-off clips.

### Movement

- Idle, with subtle breathing and occasional head/eye attention.
- Walk with clear heel/toe contact and opposite arm swing.
- Faster locomotion if the route needs it.
- Start, stop and turn transitions.
- Short step-up/step-down or slope adaptation only if the character controller and animation support them reliably.
- Jump/fall/land only if the stage actually needs those actions.
- Controlled stumble and recover for a staged engine demonstration.

### Interaction

- Inspect a point of interest.
- Reach to a panel or object.
- Open/close a simple environmental door or hatch.
- Use the field utility scanner/light.
- Talk/listen idle.
- React to a sound or discovery.
- Turn toward a nearby point of interest.

### Physical reaction

Use a layered approach:
1. Ordinary locomotion and short reaction animations should cover most normal movement.
2. A safe trip can interrupt locomotion, blend to a controlled fall and transition into a recovery animation.
3. Use a full physics ragdoll only for a deliberate, bounded demonstration where it has a clear purpose.
4. Preserve the gameplay capsule/root separately and restore a stable locomotion state only after the character is safe and grounded.

The audited VICTUS ragdoll system does not currently provide automatic get-up or gameplay-root/capsule follow. The game must not mark ragdoll recovery complete until it has built and tested the full state transition. Test on uneven ground, slopes and near walls. Prevent a character from being launched, trapped, or stuck in a physics state.

## 4. Facial animation

VICTUS's audited glTF path supports morph-target weights and their animation. The current morph deformation is CPU-side; when morph weights change, the engine updates a vertex copy for the affected entity. This is a real cost and should shape the design.

For one or two close-up speaking human characters, author a compact face-shape set such as:
- Blink left/right (or a shared blink if the mesh/rig design permits).
- Jaw open.
- Mouth wide.
- Mouth rounded.
- Smile / soft positive expression.
- Concern or brow raise.

Keep the count low and test the quality of the result at the real output size. Expressions should be subtle and believable, not exaggerated. A character who is far from the camera can rely more on head turns, posture and audio than expensive facial deformation.

The final names and number of morph targets must match the actual exported GLB target names and the game-side lookup. Do not assume the names above already exist in VICTUS assets.

Facial acceptance:
- Shapes combine without cracks or bad normals.
- Neutral weight returns cleanly after speech.
- Blinks do not stay stuck.
- Audio and mouth timing agree.
- Face animation does not produce unacceptable CPU spikes.
- Face animation on one hero is tested before adding more simultaneously animated faces.

## 5. Dialogue and audio architecture

VICTUS already supplies normal audio playback through miniaudio:
- WAV, Ogg Vorbis, MP3 and FLAC.
- Spatial AudioSource/AudioListener.
- Ambient, Voice, SFX, UI, Music and Master buses.
- Distance attenuation and streaming.

VICTUS does **not** itself generate a natural spoken voice. Treat voice generation/recording as an offline content-authoring step. The shipped game should play ordinary licensed audio assets through VICTUS.

Recommended pipeline:
1. Write short dialogue lines in the game script.
2. Choose a voice source with rights suitable for the intended distribution.
3. Generate or record the final line.
4. Listen to every line; fix pronunciation, pacing, breaths, noise and clipping.
5. Save the clean source master and a game-ready compressed copy.
6. Generate lip-sync cue data from the final audio file.
7. Review the result manually against the actual character face.
8. Package the audio, subtitle text and cue data as associated game assets.
9. Test with phone speaker and headphones.

For the first stage, prioritize a small number of clear, well-performed lines rather than long unedited monologues. Provide subtitles and a way to skip/replay dialogue. Do not make comprehension depend on hearing a quiet background line.

## 6. Offline speech synthesis candidates — research, not automatic approval

The owner prefers free/open tooling and does not want a recurring subscription dependency. These are candidate authoring tools; the agent must verify the exact version, license, voice model, dataset lineage and redistribution obligations before use.

### Kokoro

The 82-million-parameter Kokoro model has an Apache-2.0 model release for the specific model repository. Its inference ecosystem has multiple implementations and dependencies with their own licenses. The voice packs and any community voices must be checked individually; do not assume every file found under a related project has the same license.

Candidate use:
- Generate finite dialogue lines offline on a development computer.
- Compare voices for naturalness, pronunciation and emotional range.
- Store final audio, not the speech model, in the mobile game unless there is a compelling reason to bundle it.

Research references:
- [Kokoro model card](https://huggingface.co/hexgrad/Kokoro-82M)
- [Kokoro inference project](https://github.com/hexgrad/kokoro)

### Piper

The older `rhasspy/piper` repository is archived. Development moved to `OHF-Voice/piper1-gpl`, whose engine code is GPL-3.0-or-later. More importantly, the Piper project states that voice model rights depend on each model's recordings and training chain. The model card must be read all the way back to its base model; some common voices have non-commercial or other restrictions.

Do not select a Piper voice because it is popular or easy to download. Only consider a particular voice after documenting the exact model file, model card, upstream/base model chain and license obligations. The engine's GPL license also needs to be evaluated if the tool is bundled or distributed.

Research references:
- [Current Piper project](https://github.com/OHF-Voice/piper1-gpl)
- [Voice licensing](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md)
- [Reviewed commercial-use voice list](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md)

### Recorded voice

A human-recorded line can be an excellent option for a small cast. Obtain clear permission for the recording, performance, editing, use in the game and distribution. Keep the agreement/provenance with the source audio. Do not clone or imitate a real person's voice without permission.

## 7. Lip-sync cue generation

Rhubarb Lip Sync is a possible offline cue-generation tool. It is MIT-licensed. It analyzes a finished voice recording and outputs timed mouth cues; it is not a voice generator and does not animate a character by itself.

Suggested use:
- Run the tool on the final dialogue audio during content production.
- Convert its mouth cue timings into a small game-owned data file.
- Map cues to the exact face morph targets present in the GLB.
- Interpolate between mouth states to avoid abrupt popping.
- Add eye blinks and subtle head motion independently.
- Preserve the original audio timeline as the timing source.

Review:
- [Rhubarb Lip Sync repository](https://github.com/DanielSWolf/rhubarb-lip-sync)
- [Rhubarb license](https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md)

The exact output format, supported language/recognition mode and current compatibility must be tested against the dialogue material. Do not assume its cue labels map one-to-one to the character's face shapes.

## 8. Animation and dialogue runtime state

Implement a small game-owned dialogue state machine:
- Idle / available.
- Interaction started.
- Speaker turn.
- Player response / listening.
- Dialogue finished or skipped.
- Return to gameplay.

Requirements:
- Trigger each audio line once.
- Track line duration and subtitle timing.
- Only animate the current speaking character's mouth.
- Blend to a neutral mouth state at line end or skip.
- Add short natural pauses; do not speak every line back-to-back.
- Dialogue UI blocks movement/interaction where required.
- Character movement and audio stop/pause/resume predictably when app lifecycle events occur.
- Avoid starting overlapping copies of the same voice line.
- Respect audio bus volume and master mute.
- Make subtitles readable and accessible.

Do not introduce runtime TTS just to avoid recording assets. The story uses a finite set of lines and pre-rendered audio is simpler, faster to load predictably and easier to test on the phone.

## 9. Voice performance and asset budgeting

- Prefer short lines and stream longer dialogue where supported.
- Use compressed game-ready audio; preserve original masters outside the runtime package.
- Avoid excessive simultaneous ambience loops or voice instances.
- Use the Voice bus for spoken dialogue, Ambient for forest/facility beds, SFX for interaction effects and UI for interface feedback.
- Use distance attenuation only where it improves spatial clarity.
- Test that dialogue remains intelligible under ambience.
- Store speaker metadata, subtitle text, cue files and audio paths together.
- Measure package-size impact and audio memory behaviour.

## 10. Character acceptance checklist

- Player controller and visual rig stay aligned.
- Walk/run transitions show no obvious snapping or foot sliding.
- Turns and stops look responsive.
- Interaction animations match object positions.
- Safe fall/recovery returns cleanly to control.
- Ragdoll is not enabled on the player unless the complete root/capsule recovery flow has passed.
- V-01 uses the existing shared Vanguard controller and clips.
- V-01 dummy is visible, static/idle as intended, behind the chair, and reachable at the end of the route.
- Human character morphs and dialogue are tested at phone resolution.
- Voice file rights and model provenance are recorded.
- Subtitles, skip, pause/resume and lip-sync timing all work in the exported package.
