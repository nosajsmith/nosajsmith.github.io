from __future__ import annotations

import os
import sys


def _add_repo_root_to_path() -> None:
    # tools/ -> server/ -> repo root
    here = os.path.dirname(os.path.abspath(__file__))
    server_root = os.path.dirname(here)
    repo_root = os.path.dirname(server_root)
    for path in (repo_root, server_root):
        if path not in sys.path:
            sys.path.insert(0, path)


def main() -> int:
    _add_repo_root_to_path()

    from engine.engine_api import EngineAPI  # noqa: E402

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

    # Dump logs
    for log in api.get_logs():
        print(f"[{log['src']} T{log['turn']} {log['phase']}] {log['message']}")

    print("\nSMOKE TEST: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
