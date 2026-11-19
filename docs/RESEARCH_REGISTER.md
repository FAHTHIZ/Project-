# Research Register — Sources, Licensing and Open Questions

**Last updated:** 2026-11-19  
**Purpose:** Preserve the evidence used in this project handoff. URLs are research sources, not blanket permission to redistribute every asset found there.

## 1. Device target — Infinix Hot 10S

### Manufacturer announcement

**Source:** Infinix launch announcement distributed through AP Multimedia Newsroom  
**URL:** https://www.apmultimedianewsroom.com/multimedia-newsroom/infinix-launches-all-new-hot-10s-the-ultimate-smartphone-entertainment-experience  
**Accessed:** 2026-11-19  
**Supports:** Helio G85 SoC, 6.82-inch HD+ screen, 90 Hz display, 180 Hz touch sampling, 6000 mAh battery for the standard Hot 10S, CPU core specification.  
**Caveat:** It is a launch announcement from 2021. It does not prove the currently installed Android version, GPU driver or Vulkan compatibility of the owner's exact handset.

### Device specification reference

**Source:** Device Specs API — Infinix Hot 10S  
**URL:** https://ds.gtgroup.dev/specs/infinix/hot-10s  
**Accessed:** 2026-11-19  
**Supports:** Hot 10S family has 4 GB and 6 GB configurations; lists Helio G85, Mali-G52 MC2, Android 11 factory OS and 64/128 GB storage variants.  
**Caveat:** Secondary normalized device data. The owner's exact SKU and storage size still need direct device inspection.

### Independent display/device reference

**Source:** Notebookcheck — Infinix Hot 10S  
**URL:** https://www.notebookcheck.net/Infinix-Hot-10S.545431.0.html  
**Accessed:** 2026-11-19  
**Supports:** 720 × 1640, 90 Hz, 6.82-inch display and Mali-G52 MP2 GPU.  
**Caveat:** Review sample and model configuration may differ from the owner's exact unit. Treat the GPU naming as a family-level reference until Android reports the renderer/device.

### Device questions still open

- Exact model suffix (for example X689 / X689B / X689D).
- Storage variant.
- Android API/build currently installed.
- Current Mali driver version.
- Actual Vulkan API/device extensions and VICTUS initialization success.
- Available RAM/free storage when the game runs.
- Thermal behaviour after sustained play.
- Real touch latency and physical display safe-area behaviour.

The agent must record these using the actual handset. No performance claims can be inferred from specifications alone.

## 2. Android controls and device guidance

### Android controller design

**Source:** Android Developers — Essential game-controller design considerations  
**URL:** https://developer.android.com/games/sdk/game-controller/essential-design-considerations  
**Accessed:** 2026-11-19  
**Supports:** Full gamepad navigation, updating control prompts, separating gameplay/UI input and hiding virtual touch controls when a gamepad is active.

### Android multi-form-factor input

**Source:** Android Developers — Enable natural input on all form factors  
**URL:** https://developer.android.com/games/develop/multiplatform/enable-natural-input-on-all-form-factors  
**Accessed:** 2026-11-19  
**Supports:** Respond to active input type, switch hints/controls when input changes and support touch/gamepad/keyboard across form factors.

### Android Game Mode

**Source:** Android Developers — Game Mode API  
**URL:** https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api  
**Accessed:** 2026-11-19  
**Supports:** Game Mode exists on selected Android 12 devices and Android 13+; availability is device/OEM dependent.  
**Caveat:** Do not build a core gameplay dependency on it; the owner's OS version and OEM implementation must be checked.

## 3. VICTUS engine — owner's source of truth

**Repository:** https://github.com/FAHTHIZ/VICTUS  
**Historical main commit inspected:** `31457931542d52c0572970139d161a73428c21bd`  
**Date:** 2026-11-19

Key sources:
- README: https://github.com/FAHTHIZ/VICTUS/blob/main/README.md
- Autonomous agent rules: https://github.com/FAHTHIZ/VICTUS/blob/main/AGENTS.md
- Character inventory: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/CHARACTERS.md
- Android pipeline: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/ANDROID.md
- Platform proof matrix: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/PLATFORM_SUPPORT.md
- Subsystem limitations: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/KNOWN_LIMITATIONS.md
- Engineering status: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/STATUS.md
- Animation: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/ANIMATION.md
- Rendering spec: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/RENDERING_SPEC.md
- Performance strategy: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/PERFORMANCE_STRATEGY.md
- Third-party dependencies/licenses: https://github.com/FAHTHIZ/VICTUS/blob/main/docs/THIRD_PARTY_AND_LICENSES.md

Verified handoff facts:
- V-01 and V-02 are original robot models with a shared 21-joint skeleton and seven locomotion/action clips.
- Rendering supports HDR PBR, shadows, SSAO, IBL, atmosphere, reflection probes, fog, LOD, culling, instancing, decals and temporal post-processing.
- 3D physics uses Jolt; 2D physics uses Box2D.
- Animation supports skeletal clips, blend controllers, IK, layers, retargeting and morph target weights.
- Audio uses miniaudio, including spatial playback and buses.
- AI/navigation includes behavior trees, perception, navmesh and agents.
- Game UI exists, but no virtual mobile sticks/buttons are built in according to the Android guide.
- Android packaging exists, but the audited platform matrix says no physical Android device/emulator was run.
- The audited Android graphics path requires Vulkan 1.1; no GLES fallback is documented.
- Ragdolls have no automatic get-up/root/capsule follow.
- Morph targets currently use CPU deformation and changed-vertex upload.
- SDL_GPU does not expose GPU timestamp queries in the audited renderer.

These are starting facts only. The agent must re-check the current VICTUS main branch before implementing against these details.

## 4. Environment and source assets

### Poly Haven

**Source:** Poly Haven asset license  
**URL:** https://polyhaven.com/license  
**Accessed:** 2026-11-19  
**Supports:** Poly Haven states its HDRIs, textures and 3D models are CC0 and can be used, modified and redistributed, including commercially.  
**Caveat:** Verify that each downloaded asset is actually a Poly Haven asset and preserve source URL/asset name. Do not assume every image shown on the website or every linked external asset is also CC0.

**Useful category landing page:** https://polyhaven.com/

The agent should use original assets or check other libraries one asset at a time. Store the exact asset ID, download page, license, source author and any required attribution in the project register before shipping.

## 5. 3D asset and facial animation format

### Khronos glTF 2.0

**Source:** Khronos glTF 2.0 specification  
**URL:** https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html  
**Accessed:** 2026-11-19  
**Supports:** Portable 3D runtime format with PBR materials, node-transform animation, skeletal skinning and morph-target weights. Morph targets represent deltas to vertex attributes.  
**Relevance:** VICTUS imports glTF/GLB. Author character assets in a format the importer actually supports and test the exported file through VICTUS rather than assuming a DCC preview proves runtime compatibility.

### Blender glTF exporter documentation

**Source:** Blender manual — glTF 2.0 exporter  
**URL:** https://docs.blender.org/manual/en/latest/addons/scene_gltf2.html  
**Accessed:** 2026-11-19  
**Relevance:** Potential authoring/export workflow for original models, skeletons, animation and morph targets. Confirm the exact Blender version and exporter settings used by the agent.

## 6. Offline voice and lip-sync tooling

### Kokoro

**Source:** Kokoro-82M model card  
**URL:** https://huggingface.co/hexgrad/Kokoro-82M  
**Accessed:** 2026-11-19  
**Supports:** Model card declares Apache-2.0 for this specific model release and describes an 82-million-parameter TTS model.  
**Caveats:** Each implementation, dependency, voice pack and community file can have separate terms. Inspect the exact pinned model and runtime package. Do not infer that every voice or third-party voice pack is Apache-2.0. Generate the game's finite lines offline and ship only the resulting audio if the output rights and source model terms have been cleared.

### Piper — current project

**Source:** OHF-Voice Piper  
**URL:** https://github.com/OHF-Voice/piper1-gpl  
**Accessed:** 2026-11-19  
**Supports:** Current project describes a local neural TTS engine. The old `rhasspy/piper` repository is archived and development moved to OHF-Voice.  
**Caveat:** Current engine code is GPL-3.0-or-later; voice model rights depend on voice-specific datasets and training lineage. A voice's `MODEL_CARD` is essential. This is not pre-approved for the game.

### Piper voice licensing

**Source:** Piper licensing guide  
**URL:** https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md  
**Accessed:** 2026-11-19  
**Supports:** Voice rights must be checked through the complete training chain; model files need their model cards preserved when redistributed; some commonly used base voices have restrictive terms.

**Source:** Piper commercial-use review  
**URL:** https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md  
**Accessed:** 2026-11-19  
**Supports:** Identifies some voice models whose documented training chains use recordings permitting commercial use.  
**Caveat:** Re-check the exact file/version and its lineage, not merely the voice name.

### Rhubarb Lip Sync

**Source:** Rhubarb Lip Sync repository  
**URL:** https://github.com/DanielSWolf/rhubarb-lip-sync  
**Accessed:** 2026-11-19  
**License source:** https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/LICENSE.md  
**Supports:** MIT-licensed offline dialogue lip-sync cue generation from an audio file. It is not a TTS system and does not animate the character at runtime by itself.

## 7. Licensing and provenance policy

Before any external asset/tool enters the game:
1. Record its exact name, version or asset ID.
2. Record its canonical source URL and author/provider.
3. Read the actual license and any additional model/data terms.
4. Record attribution, redistribution, modification and commercial-use obligations.
5. Include the required notice/license where the terms require it.
6. Preserve model cards and voice lineage for speech content.
7. Remove the asset if rights are ambiguous and cannot be resolved.

"Free download", "open source" and "no subscription" are not license categories. Source code, model weights, training data, voice recordings and generated output may have different legal treatment. Do not bundle an authoring model/runtime into the game unless the distribution impact is intentional and reviewed.

## 8. Unresolved research tasks for later stages

The agent must research and cite:
- Original perimeter/facility/bunker architecture references.
- Environment modular kit and prop set suitable for a mobile scene.
- Original character models and any required animations.
- Exact audio ambience/footstep source licenses.
- Voice choice and model/recording rights.
- Any additional VICTUS features required for later stage progression.
- Android profiling tooling compatible with the phone's actual OS and GPU driver.

Later stage design is deliberately open. Each stage should have its own brief with image references, observations, design decisions, asset list, licenses, engine fit and mobile performance plan.
