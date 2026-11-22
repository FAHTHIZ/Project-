# Installing Special Ops on an Android phone

Target: Infinix Hot 10S (Helio G85, Mali-G52 MC2, Android 11, 4/6 GB RAM). Any arm64 phone on
Android 9 or newer with Vulkan 1.1 or OpenGL ES 3.0 is supported by the engine.

## Install

1. Download `SpecialOps-1.0.0-067b086.apk` from the [android-v1.0.1 release](https://github.com/FAHTHIZ/Project-/releases/tag/android-v1.0.1) (592 MB). The older [android-v1.0.0](https://github.com/FAHTHIZ/Project-/releases/tag/android-v1.0.0) build is 2.0 GB.
2. Free at least 1.5 GB on the phone: the APK holds the 590 MB game pack, and on first launch the
   engine copies that pack to the app's internal storage once (VICTUS `install_bundled_pack`).
   1.0.1 installs over 1.0.0 (same key, higher versionCode).
3. Open the APK and allow "Install unknown apps" for the browser or file manager when asked.
4. First launch shows a black screen while the pack is copied (eMMC 5.1: expect several seconds
   to half a minute). Later launches start straight away.

The APK is signed with the project's sideload key (`tools/android/specialops-sideload.keystore`,
password `specialops`). It is a development key kept in the repository on purpose so that any
rebuild can update an installed copy. Do not use it for a store release.

## What is in the phone build

- Engine: VICTUS built by its own Gradle project (`platforms/android`, NDK r29, arm64-v8a, Release).
- Game pack: `victus export --target android` (VICTUS ADR-0149) ships every texture as ASTC only
  above 64 px, capped at 1024 px, with no BC7 or full RGBA8 copies: 590 MB against 2.29 GB for
  the desktop export.
- Rendering: `rendering.mobile_quality = auto`, `mobile_target_fps = 30` (AGENTS.md: start at a measured 30; 30 paces
  evenly on the 90 Hz panel, every third refresh) with dynamic resolution down to 0.55 (`game/victus.project`).

## Rebuild

```sh
export PATH=/path/to/VICTUS/build/rel/bin:$PATH      # desktop victus CLI
sh tools/android/build_apk.sh /path/to/VICTUS build/SpecialOps.apk
```

Needs JDK 17, Gradle 9.6+, Android SDK platform 36, build-tools 36.0.0, CMake 3.31.6 and
NDK 29.0.14206865 (VICTUS `docs/ANDROID.md`). Peak disk use is about 1.5 GB plus the native build.

## Not yet verified

No phone or arm64 emulator was available on the build machine. The APK passed the engine's
`tools/android/check_apk.sh` (entries, SDL_main export, 16 KB ELF and zip alignment),
`zipalign -c -P 16 4` and `apksigner verify` (v3), but it has not been installed or run on a device.
Frame time, memory, thermals and touch feel on the Hot 10S are still to be measured.
