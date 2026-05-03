#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

pkill -f mwe_bridge_allinone_p6.py || true
fuser -k 8766/tcp 8770/tcp 2>/dev/null || true
sleep 1

python server/mwe_bridge_allinone_p6.py &
BRIDGE_PID=$!

sleep 2

(
  cd ui
  ELECTRON_OZONE_PLATFORM_HINT=x11 \
  ELECTRON_DISABLE_GPU=1 \
  LIBGL_ALWAYS_SOFTWARE=1 \
  npm run electron
)

wait $BRIDGE_PID
