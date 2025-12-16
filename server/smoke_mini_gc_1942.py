"""
Quick smoke test for the Mini Guadalcanal 1942 scenario.

Usage (from a CMD window):

    cd C:\MWE\server
    python smoke_mini_gc_1942.py
"""

from engine.engine_api import EngineAPI


def main() -> None:
    # 1) Create API and load scenario
    api = EngineAPI()
    meta = api.load_scenario("mini_gc_1942")
    print("Loaded scenario meta:")
    print(meta)

    # 2) Start the game and show initial state
    state0 = api.start_game()
    print("\nInitial game state:", state0["game"])
    print("Initial unit count:", len(state0["units"]))
    print("-" * 60)

    # 3) Turn 1 — player orders US-1MAR to attack TULAGI
    print("Issuing player order: US-1MAR -> TULAGI (ATTACK)")
    result = api.apply_player_action(
        {
            "type": "move",
            "unit_id": "US-1MAR",
            "target": "TULAGI",
            "posture": "ATTACK",
        }
    )
    print("apply_player_action result:", result)
    print("-" * 60)

    # 4) Run 3 turns and print the time track
    print("Advancing 3 turns...\n")
    for i in range(3):
        state = api.process_turn()
        t = state["game"]["time"]
        print(
            f"Turn {i+1}: Day {t['day']} / Phase {t['phase']} / "
            f"Weather {t['weather']}"
        )

    # 5) Dump staff logs (heart of the engine)
    print("\n--- Staff Logs ---")
    for log in api.get_logs():
        print(f"[{log['src']} T{log['turn']} {log['phase']}] {log['message']}")


if __name__ == "__main__":
    main()
