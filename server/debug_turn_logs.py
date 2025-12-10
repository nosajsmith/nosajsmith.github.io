"""
Quick log inspector for MWE EngineAPI.

Usage:
    cd C:\MWE\server
    python debug_turn_logs.py
"""

from __future__ import annotations
import json

from engine.engine_api import EngineAPI


def print_state_summary(state: dict) -> None:
    game = state["game"]
    time = game["time"]
    print(f"\n=== GAME STATE SUMMARY ===")
    print(f"Day {time['day']} ({time['phase']}), Weather={time['weather']}")
    print(f"Scenario: {game['scenario']}")
    vp = game.get("vp", {})
    print(f"VP: Allied={vp.get('ALLIED', 0)}, Axis={vp.get('AXIS', 0)}")
    print(f"Units: {len(state['units'])}")


def print_logs(logs: list[dict]) -> None:
    if not logs:
        print("\n(no logs this turn)")
        return

    print("\n=== TURN LOGS ===")
    for entry in logs:
        src = entry["src"]
        turn = entry["turn"]
        phase = entry["phase"]
        msg = entry["message"]
        print(f"[{src} T{turn} {phase}] {msg}")


def main() -> None:
    api = EngineAPI()

    # 1) Load scenario
    meta = api.load_scenario("mini_gc_1942")
    print("Loaded scenario meta:")
    print(json.dumps(meta, indent=2))

    # 2) Start game
    state0 = api.start_game()
    print_state_summary(state0)

    # 3) Example player action: US-1MAR attacks TULAGI
    api.apply_player_action(
        {
            "type": "move",
            "unit_id": "US-1MAR",
            "target": "TULAGI",
            "posture": "ATTACK",
        }
    )

    # 4) Process a few turns and show logs
    for i in range(1, 4):
        state = api.process_turn()
        print_state_summary(state)
        logs = api.get_logs()
        print_logs(logs)


if __name__ == "__main__":
    main()
