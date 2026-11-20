#!/bin/sh
# Builds the installable Android APK of Special Ops (arm64, Android 9+), e.g. for the Infinix Hot 10S.
#
# Needs: the VICTUS engine checkout (desktop build with `victus` on PATH), JDK 17, Gradle 9.6+,
# Android SDK platform 36 / build-tools 36.0.0 / CMake 3.31.6 and NDK 29.0.14206865
# (see VICTUS docs/ANDROID.md). Peak disk use is about 3x the pack size (~6 GB).
#
# usage: sh tools/android/build_apk.sh /path/to/VICTUS [OUT.apk]
set -eu
ENGINE=$(cd "$1" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
GAME=$(cd "$HERE/../.." && pwd)
OUT=${2:-$GAME/build/SpecialOps.apk}
VERSION=$(git -C "$GAME" describe --always --dirty)
WORK=${TMPDIR:-/tmp}/sops_apk
rm -rf "$WORK"; mkdir -p "$WORK/dummy" "$(dirname "$OUT")"
echo dummy > "$WORK/dummy/game.vpak"

# 1. Phone pack: ASTC-only textures (desktop .meta files are restored afterwards).
python3 "$GAME/tools/android/mobile_pack.py" "$WORK/export"
cp "$WORK/export/THIRD_PARTY_NOTICES.txt" "$WORK/dummy/"

# 2. Engine shell APK (native engine for arm64-v8a + SDL glue) around a dummy pack.
gradle --no-daemon -p "$ENGINE/platforms/android" assembleRelease \
    -Pvictus.game="$WORK/dummy" -Pvictus.applicationId=com.fahthiz.specialops \
    -Pvictus.appName="Special Ops" -Pvictus.versionName="1.0.0-$VERSION" \
    -Pvictus.versionCode="$(git -C "$GAME" rev-list --count HEAD)"
SHELL_APK="$ENGINE/platforms/android/app/build/outputs/apk/release/app-release-unsigned.apk"

# 3. Stream the real pack in (stored, aligned), then sign v2+v3.
python3 "$HERE/inject_pack.py" "$SHELL_APK" "$WORK/export/game/game.vpak" "$WORK/unsigned.apk" "$WORK/export/THIRD_PARTY_NOTICES.txt"
rm -rf "$WORK/export"
BT=$(ls -d "$ANDROID_HOME"/build-tools/* | sort -V | tail -1)
"$BT/apksigner" sign --ks "$HERE/specialops-sideload.keystore" --ks-pass pass:specialops \
    --ks-key-alias specialops --v1-signing-enabled false --v4-signing-enabled false \
    --alignment-preserved true --out "$OUT" "$WORK/unsigned.apk"
rm -f "$WORK/unsigned.apk"
"$BT/apksigner" verify --print-certs "$OUT" | head -3
ls -l "$OUT"; sha256sum "$OUT"
