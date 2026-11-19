#!/bin/sh
# Renders one frame of a scene to a PNG with the software Vulkan driver under a virtual display.
#   tools/test/shot.sh <scene> <frames> <out.png> [width height] [quality]
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
W=${4:-1600}; H=${5:-720}; Q=${6:-high}
export VICTUS_NO_AUDIO=1
timeout 600 xvfb-run -a -s "-screen 0 ${W}x${H}x24" victus run "$ROOT/game" --scene "$1" --frames "$2" \
  --screenshot "$3" --width "$W" --height "$H" --quality "$Q" --saves /tmp/sops_shot_saves --strict > /tmp/sops_shot.log 2>&1 \
  || { tail -20 /tmp/sops_shot.log; exit 1; }
echo "wrote $3"
