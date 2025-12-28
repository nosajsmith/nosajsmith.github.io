from __future__ import annotations

import os
import sys

# Ensure project root (...\server) is on sys.path so "import engine" works
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(THIS_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.engine_api import EngineAPI  # noqa: E402


def main() -> int:
    api = EngineAPI()

    meta = api.load_scenario("mini_gc_1942")
    print("META:", meta)

    state0 = api.start_game()
    print("START:", state0["game"], "units=", len(state0["units"]))

    api.apply_player_action(
        {"type": "move", "unit_id": "US-1MAR", "target": "TULAGI", "posture": "ATTACK"}
    )

    state1 = api.process_turn()
    print("AFTER:", state1["game"]["time"])
    print("LOGS:", len(api.get_logs()))
    for log in api.get_logs():
        print(f"[{log['src']} T{log['turn']} {log['phase']}] {log['message']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
