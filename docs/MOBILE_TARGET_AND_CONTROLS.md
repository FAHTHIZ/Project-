# Mobile Target and Controls — Infinix Hot 10S

**Date researched:** 2026-11-19  
**Owner-provided device:** Infinix Hot 10S, 6 GB RAM variant  
**Required game orientation:** Landscape

## 1. Device facts and uncertainty

The Hot 10S launch announcement identifies the MediaTek Helio G85, 6.82-inch HD+ display, 90 Hz refresh rate, 180 Hz touch-sampling rate and 6000 mAh battery. The device family includes 6 GB RAM configurations. Published specification references identify the GPU as Mali-G52 MC2 and the panel resolution as 720 × 1640 (portrait), making the landscape panel approximately 1640 × 720.

| Item | Working device reference | Evidence / caveat |
|---|---|---|
| Phone | Infinix Hot 10S | Owner-confirmed model |
| RAM | 6 GB | Owner-confirmed variant |
| SoC | MediaTek Helio G85 | Manufacturer launch announcement |
| CPU | 2 × Cortex-A75 up to 2.0 GHz + 6 × Cortex-A55 up to 1.8 GHz | Manufacturer launch announcement |
| GPU | Mali-G52 MC2 | Device-spec reference; verify on actual SKU |
| Display | 6.82-inch HD+, 720 × 1640 portrait | Manufacturer announcement and independent spec reference |
| Landscape dimensions | About 1640 × 720 | Derived by rotating the panel orientation |
| Refresh | 90 Hz | Manufacturer launch announcement |
| Touch sampling | 180 Hz | Manufacturer launch announcement |
| Battery | 6000 mAh for the standard Hot 10S (NFC model differs) | Manufacturer launch announcement |
| Android build | Unknown on the owner's exact phone | Read from device; do not assume it is still the factory OS |
| Vulkan driver | Unknown on the owner's exact phone | Must be verified on the device |
| Storage size | Unknown | Do not infer from RAM variant |

Sources are listed in [RESEARCH_REGISTER.md](RESEARCH_REGISTER.md). The exact Hot 10S model suffix, storage size, Android update level, GPU driver revision and available RAM at runtime are not known from the owner message. The 6 GB installed memory is shared by Android, drivers and apps; it is not a 6 GB game allocation.

## 2. Compatibility gate — do this before building the whole game

The audited VICTUS Android path requires Android arm64 and Vulkan 1.1. The project documentation says SDL_GPU has no OpenGL ES backend and that Vulkan is required. The real Hot 10S must therefore be checked before the agent invests in a large scene.

Required device inspection:
- Record manufacturer, model string, Android version/API level, security patch, build fingerprint and storage capacity.
- Confirm ABI is `arm64-v8a`.
- Inspect Vulkan instance/device availability and reported API version with a Vulkan-capability diagnostic that actually runs on the device.
- Record GPU renderer/device name and driver version.
- Install and launch a minimal VICTUS exported Android project.
- Exercise resume/pause, audio, touch, rendering and repeated scene reload.
- Save logcat and the device report in `docs/device-tests/`.

Do not write "Vulkan supported" based only on a third-party spec page. The VICTUS requirement is runtime compatibility with the installed driver.

If the exact device cannot initialize VICTUS's Vulkan backend, record the failure and the full driver logs. Continue desktop development, but do not claim Hot 10S support until the incompatibility is resolved by a verified, supportable engine path.

## 3. Performance target

Initial target: **stable 30 FPS**, with adaptive rendering resolution and capability-based quality. 90 Hz panel support does not mean the game should attempt 90 FPS. A stable frame cadence, predictable touch response and sustained performance are more important than a high short-lived FPS spike.

Suggested initial settings to test, not guaranteed final settings:
- Android orientation: landscape / sensorLandscape, as supported by the VICTUS Gradle configuration.
- Mobile quality: begin at Medium and compare against Low; retain the visually best setting that passes sustained device tests.
- Mobile target FPS: 30.
- Dynamic resolution: enabled, with a measured floor and ceiling chosen after captures.
- Resolution output: native panel resolution where the platform surface permits; render internally at an adaptive lower scale when necessary.
- Fog: compare non-volumetric fog against volumetric fog; keep the latter only if it provides clear value without destabilizing frame time.
- Shadows: limit cascades, local shadow-casting lights, shadow resolution and foliage casters to what the device sustains.
- Textures: use the engine's ASTC mobile compression path and sensible source dimensions. Avoid large uncompressed assets.
- Foliage: instance repeated plants, use distance groups/LODs and control alpha overdraw.
- Animated characters: keep the number of fully animated and morph-updated characters low.
- Particles: small bounded effects; avoid continuous dense emitters across the whole level.

Do not hard-code a numerical memory ceiling before measuring device process memory. Track peak and steady-state app memory, GPU/cache budgets, asset loading peaks and Android low-memory behaviour. VICTUS's `asset_budget_mb` covers only cache-owned textures/models; its docs explicitly say it does not include render targets, environment maps or particles, so it is not a total memory cap.

## 4. Performance validation protocol

The final report must use the actual Hot 10S, not an emulator, and include:
- Exact phone model/SKU and 6 GB variant.
- Android build/API, GPU driver and Vulkan version.
- Game commit SHA, VICTUS commit SHA and APK hash.
- Scene/route, quality preset, render scale and target frame rate.
- Display refresh setting, battery level, battery saver state and brightness.
- Ambient conditions and whether the device began cool or warm.
- Cold-start and warm-start observations.
- Frame-time / frame pacing data at start and after 5, 10 and 20 minutes.
- Memory peak and steady-state readings.
- Thermal state before and after the run, using an Android-supported diagnostic available on that build.
- Loading stalls, crashes, audio dropouts, missed touch input and UI issues.
- Repeat the same route more than once and keep raw logs.

An emulator is useful for deterministic functional tests and a range of screen sizes. It cannot establish actual GPU performance, battery drain, thermal throttling, physical touch latency, device-driver behaviour or sustained memory pressure. Do not present emulator performance as a Hot 10S benchmark.

VICTUS's current renderer does not expose GPU timestamp queries. If GPU pass timings are unavailable, say so. Use an external Android profiling tool only after verifying it works on this device/OS and documenting the method.

## 5. Landscape composition and responsive UI

The game must be landscape by default. Use the device's real wide aspect ratio in layout and camera tests. Some desktop emulator windows will be 16:9; the game must not depend on this exact ratio.

- Reserve safe margins for rounded corners, status/navigation bars and cutouts.
- Keep the centre of the frame readable for aiming, targets, characters and environmental clues; avoid excessive HUD clutter.
- Place touch controls near the lower left/right corners, without overlapping core interactions.
- Use screen-scaled UI anchors and safe areas, not fixed pixel positions that only fit one emulator.
- Keep the objective and alert state near the top corners or another non-obstructive area.
- Subtitles should sit above the lower control cluster and remain readable.
- Use a restrained first-person reticle during gameplay, with adjustable size/opacity and appropriate hide/show behaviour in menus and cutscenes.
- Add UI scaling and opacity options for comfort.

## 6. Virtual touch controls — required implementation

VICTUS documents low-level touch APIs but no built-in on-screen virtual joystick/buttons. Implement a reusable game-level control layer.

### Left movement stick

- A circular, semi-transparent base near the lower-left safe area.
- A thumb knob that follows the active pointer.
- The stick outputs a normalized 2D movement vector with a configurable dead zone.
- Clamp output magnitude to 1; avoid abrupt jumps at the dead-zone edge.
- Pointer ownership is fixed from touch-down to touch-up/cancel. A second finger must not steal the movement pointer.
- Touching outside the base should only engage if the chosen UX intentionally supports a floating stick; decide once and test it.
- Releasing or cancelling the pointer returns movement to neutral immediately.
- The stick drives camera-relative movement through the player input abstraction.

### Right first-person look/aim surface

- A large right-side touch region for first-person look/aim.
- A distinct pointer id from the left movement stick.
- Scale first-person look sensitivity by screen size and frame delta; clamp extreme touch jumps.
- Never rotate the camera when the user presses an on-screen button or drags a modal.
- Provide sensitivity and inversion settings.
- Avoid pitch ranges that invert the view or cause disorienting motion. Provide sensitivity, inversion and motion-comfort options.

### Contextual interaction button

- Appears only when the player is near an authored interactable, or remains as a disabled/low-emphasis button with a clear state.
- Shows the current action with a short icon/label such as "Inspect", "Talk" or "Open".
- A single tap produces one action. Debounce accidental double activation.
- On success, provide feedback through animation, UI and sound.
- If the target moves out of range or becomes unavailable, the prompt must update.

### Shooter action buttons

The game is a first-person shooter, so touch combat actions must be usable without interfering with movement or look:
- Fire: a clearly separated, reachable action button with reliable press/hold semantics chosen by the game design.
- Aim: an optional hold/toggle action that adjusts the first-person presentation and reticle feedback.
- Reload: a dedicated action with clear unavailable/in-progress feedback.
- Weapon switch: a compact, predictable control for the available fictional primary/secondary game weapons.
- Keep controls visually distinct from interaction and field-tool actions.
- Support simultaneous movement, look/aim and a combat action without pointer ownership conflicts.
- Offer button size, opacity, repositioning and left-handed layout options.
- All timing, recoil, spread, ammunition and damage values are fictional game tuning. The UI is not a real-world weapon training interface.

### Field-tool button

- Toggles the field utility presentation or triggers its active inspection mode.
- Tool actions are limited to illumination, scanning and environmental inspection.
- Display the active state clearly; avoid making the button look like an attack button.
- Test with the camera-look pointer active at the same time.

### Pause and settings

- A clearly visible pause button opens a modal.
- On modal open, gameplay input is blocked: no movement, camera rotation or interaction can pass through to the world.
- Pause the simulation/audio according to the intended game state.
- Menus must support touch and gamepad navigation.
- Resume returns focus to gameplay without leaving a stuck virtual input active.

## 7. Input unification

Maintain one logical action layer for:
- Touch controls.
- Gamepad.
- Keyboard/mouse (desktop).
- Automated tests/manual input.

The gameplay code should consume logical actions such as move, look, aim, fire, reload, switch weapon, jump/confirm, interact, field tool, pause and menu navigation. It should not need to know whether the action came from a finger, controller stick or keyboard.

When a gamepad becomes active:
- Hide or fade virtual controls to reduce screen clutter.
- Update prompts and button glyphs to match the active input.
- Keep all menus/dialogues navigable by the gamepad.
- Do not require touch to continue or exit a gameplay interaction.
- Restore touch UI when the player touches the screen again.

These rules align with Android's game-controller and multi-form-factor guidance. Avoid input-context leaks: a menu should not accidentally move the player behind it.

## 8. Multitouch correctness checklist

- Move with left stick while looking with right pointer.
- Move/look while tapping the interaction button.
- Move/look while firing; aim while moving; reload or switch weapons without stealing either movement/look pointer.
- Tap field-tool while moving or looking/aiming.
- Open pause while holding movement; movement must stop.
- Receive touch cancellation from system interruption.
- Resume app after backgrounding; all virtual controls must reset to neutral.
- Rotate or resize emulator window; controls must re-anchor without stale pointer state.
- A third/fourth finger must not steal the first two controls.
- Rapid repeated taps must not duplicate one-shot interactions.
- Touch on a subtitle or HUD panel must not also steer the camera.
- No stuck pointer if screen is locked, call/notification overlay appears, or app is paused.

## 9. Accessibility and comfort

- Adjustable stick size and opacity.
- Adjustable camera sensitivity and inversion.
- Reposition controls within safe bounds.
- Optional left-handed layout.
- Subtitle size, background opacity and speaker labels.
- Separate dialogue, ambience, SFX and UI volume controls (where VICTUS buses permit).
- Clear pause/resume and no mandatory rapid repeated touch sequence.
- Support full gamepad operation.

## 10. Android packaging and smoke test

Follow the live VICTUS `docs/ANDROID.md` rather than copying old commands blindly. The audited workflow exports a VICTUS project to `game.vpak` and builds an Android arm64 Gradle APK. The Android orientation property defaults to `sensorLandscape`.

Smoke test on the physical phone:
1. Install APK and launch from a clean install.
2. Confirm landscape orientation and correct safe areas.
3. Play the forest entry and interact with at least one object.
4. Verify simultaneous left/right multitouch.
5. Verify pause/resume and app background/foreground.
6. Hear dialogue, cutscene voice/music and ambience; test phone speaker and headphones if possible.
7. Save, close, relaunch and restore.
8. Complete the full campaign route through the perimeter, facility, bunker and lower basement, and reach the V-01 ending. Repeat this full-route check after major changes.
9. Run a sustained 20-minute session and inspect logs, thermals and memory.
10. Repeat after a device restart.

## 11. References

- Infinix launch announcement: [Hot 10S Series](https://www.apmultimedianewsroom.com/multimedia-newsroom/infinix-launches-all-new-hot-10s-the-ultimate-smartphone-entertainment-experience)
- Device details: [Hot 10S specification sheet](https://ds.gtgroup.dev/specs/infinix/hot-10s)
- Independent panel/resolution reference: [Notebookcheck Hot 10S](https://www.notebookcheck.net/Infinix-Hot-10S.545431.0.html)
- Android controller design: [Essential game-controller design considerations](https://developer.android.com/games/sdk/game-controller/essential-design-considerations)
- Android form-factor/input guidance: [Enable natural input on all form factors](https://developer.android.com/games/develop/multiplatform/enable-natural-input-on-all-form-factors)
- Android Game Mode (availability varies by OS/OEM): [Game Mode API](https://developer.android.com/games/optimize/adpf/gamemode/gamemode-api)
