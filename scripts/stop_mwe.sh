#!/usr/bin/env bash
set -euo pipefail

pkill -f mwe_bridge_allinone_p6.py || true
fuser -k 8766/tcp 8770/tcp 2>/dev/null || true
pkill -f "electron ./electron/main.js" || true
