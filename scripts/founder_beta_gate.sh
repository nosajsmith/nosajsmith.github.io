#!/usr/bin/env bash
set -euo pipefail

pytest -q --ignore=server/test_drive_engine.py
pytest --collect-only -q >/dev/null
python server/tools/smoke_test_engine_api.py >/dev/null
node --test ui/tests/view_snapshot_bridge_state.test.js ui/tests/launcher_flow.test.js ui/tests/live_entry_path.test.js >/dev/null
