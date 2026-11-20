# Installing Special Ops on an Android phone

Target: Infinix Hot 10S (Helio G85, Mali-G52 MC2, Android 11, 4/6 GB RAM). Any arm64 phone on
Android 9 or newer with Vulkan 1.1 or OpenGL ES 3.0 is supported by the engine.

## Install

1. Download `SpecialOps-1.0.0-android.apk` from the [android-v1.0.0 release](https://github.com/FAHTHIZ/Project-/releases/tag/android-v1.0.0) (about 2.0 GB).
2. Free at least 4.5 GB on the phone: the APK holds the 1.97 GB game pack, and on first launch the
   engine copies that pack to the app's internal storage once (VICTUS `install_bundled_pack`).
3. Open the APK and allow "Install unknown apps" for the browser or file manager when asked.
4. First launch shows a black screen while the pack is copied (eMMC 5.1: expect roughly half a
   minute to a minute). Later launches start straight away.

The APK is signed with the project's sideload key (`tools/android/specialops-sideload.keystore`,
password `specialops`). It is a development key kept in the repository on purpose so that any
rebuild can update an installed copy. Do not use it for a store release.

## What is in the phone build

- Engine: VICTUS built by its own Gradle project (`platforms/android`, NDK r29, arm64-v8a, Release).
- Game pack: `tools/android/mobile_pack.py` cooks every texture ASTC only (4x4 for characters and
  weapons, 6x6 for the world) plus the RGBA8 fallback. The desktop export also carries BC7,
  which phones never sample (2.29 GB vs 1.97 GB).
- Rendering: `rendering.mobile_quality = auto`, `mobile_target_fps = 60` with dynamic resolution
  down to 0.55 (`game/victus.project`).

## Rebuild

```sh
export PATH=/path/to/VICTUS/build/rel/bin:$PATH      # desktop victus CLI
sh tools/android/build_apk.sh /path/to/VICTUS build/SpecialOps.apk
```

Needs JDK 17, Gradle 9.6+, Android SDK platform 36, build-tools 36.0.0, CMake 3.31.6 and
NDK 29.0.14206865 (VICTUS `docs/ANDROID.md`). Peak disk use is about 6 GB.

## Not yet verified

No phone or arm64 emulator was available on the build machine. The APK passed the engine's
`tools/android/check_apk.sh` (entries, SDL_main export, 16 KB ELF and zip alignment),
`zipalign -c -P 16 4` and `apksigner verify` (v3), but it has not been installed or run on a device.
Frame time, memory, thermals and touch feel on the Hot 10S are still to be measured.
