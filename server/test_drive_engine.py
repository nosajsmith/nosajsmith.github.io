from __future__ import annotations

import sys

if "pytest" in sys.modules:  # pragma: no cover - legacy manual driver only
    import pytest

    pytest.skip(
        "server/test_drive_engine.py is a legacy manual drive script, not an automated pytest target.",
        allow_module_level=True,
    )

from engine.core.time_system import TimeSystem
from engine.core.unit_model import Side, Posture
from engine.scenario_loader import load_scenario

# Staff sections
from engine.staff.g1_personnel import G1Personnel
from engine.staff.g2_intel import G2Intelligence
from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g5_plans import G5Plans
from engine.staff.g6_signals import G6Signals
from engine.staff.g7_reinforcements import G7Reinforcements
from engine.staff.g8_objectives import G8Objectives


def main() -> None:
    # ----------------------------------------------------------------------
    # Load Scenario
    # ----------------------------------------------------------------------
    start_time, game_map, units, meta = load_scenario("mini_gc_1942")

    ts = TimeSystem()
    ts.time.day = start_time.day
    ts.time.phase = start_time.phase

    # ----------------------------------------------------------------------
    # Initialize Staff Sections
    # ----------------------------------------------------------------------
    g1 = G1Personnel(units)
    g2 = G2Intelligence(units, enemy_side=Side.AXIS)
    g3 = G3Operations(units, game_map)
    g4 = G4Logistics(units, meta.get("supply_sources", []))
    g5 = G5Plans(
        units,
        game_map,
        g3=g3,
        mode="advisor",          # try "semi_auto" or "full_auto"
        personality="macarthur", # or "nimitz", "slim", etc.
    )
    g6 = G6Signals(units, g3)
    g7 = G7Reinforcements(units, meta.get("reinforcements", []))
    g8 = G8Objectives(units, meta.get("objectives", []))

    # Register staff with the TimeSystem (order matters conceptually)
    ts.register_listener("g1", g1)
    ts.register_listener("g2", g2)
    ts.register_listener("g5", g5)  # planning before signals
    ts.register_listener("g6", g6)  # command delay before ops
    ts.register_listener("g7", g7)  # reinforcements before ops
    ts.register_listener("g3", g3)  # movement + combat
    ts.register_listener("g4", g4)  # logistics
    ts.register_listener("g8", g8)  # objectives & VP

    # ----------------------------------------------------------------------
    # Scenario Info
    # ----------------------------------------------------------------------
    print(f"Loaded scenario: {meta['name']}")
    print(f"Description: {meta['description']}")
    print(f"Start Day: {ts.time.day}")

    print("\nScenario Extras:")
    print("  Weather:", meta.get("weather", "?"))

    print("  Supply Sources:")
    for src in meta.get("supply_sources", []):
        print(
            f"    {src['side']:6} at {src['location_id']:7} "
            f"+{src['daily_supply']} per day"
        )

    print("  Objectives:")
    for obj in meta.get("objectives", []):
        print(
            f"    {obj['side']:6} {obj['location_id']:7} "
            f"Value={obj['value']:3} - {obj.get('description','')}"
        )

    print("  Reinforcements:")
    for r in meta.get("reinforcements", []):
        print(
            f"    Day {r['arrival_day']:2}: {r['id']} "
            f"({r['name']}) enters at {r['entry_location_id']}"
        )

    # ----------------------------------------------------------------------
    # Initial Unit Status
    # ----------------------------------------------------------------------
    print("\nInitial unit status:")
    for u in units.all_units():
        print(
            f"  {u.id:8} {u.name:24} "
            f"Loc={u.location_id:7} Str={u.strength:3} Sup={u.supply:3} "
            f"Fat={u.fatigue:3} Mor={u.morale:3} Read={u.readiness:3}"
        )

    # ----------------------------------------------------------------------
    # Initial Order via G-6 (with command delay)
    # ----------------------------------------------------------------------
    g6.issue_delayed_move_order(
        "US-1MAR",
        "TULAGI",
        Posture.ATTACK,
        t=ts.time,
        via_hq_id=None,
        notes="Initial assault order via G-6",
    )

    # ----------------------------------------------------------------------
    # Run Engine for N Days
    # ----------------------------------------------------------------------
    days_to_run = 5
    for _ in range(days_to_run):
        ts.advance_one_day()

    # ----------------------------------------------------------------------
    # Final Unit Status
    # ----------------------------------------------------------------------
    print(f"\nAfter {days_to_run} days:")
    for u in units.all_units():
        print(
            f"  {u.id:8} {u.name:24} "
            f"Loc={u.location_id:7} Str={u.strength:3} Sup={u.supply:3} "
            f"Fat={u.fatigue:3} Mor={u.morale:3} Read={u.readiness:3}"
        )

    # ----------------------------------------------------------------------
    # Battles
    # ----------------------------------------------------------------------
    if g3.last_battles:
        print("\nBattles:")
        for br in g3.last_battles:
            print(" ", br.summary)
            for rnd in br.rounds:
                print(
                    f"    Round {rnd.round_index}: "
                    f"Allied loss {rnd.allied_loss}, Axis loss {rnd.axis_loss} "
                    f"({rnd.notes})"
                )
    else:
        print("\nNo battles recorded.")

    # ----------------------------------------------------------------------
    # G-2 Intel Report
    # ----------------------------------------------------------------------
    print("\nG-2 Enemy SITREP (Axis):")
    for status in g2.get_enemy_sitrep():
        levels = ["Unseen", "Presence", "Identified", "Well-known"]
        print(
            f"  {status.unit_id}: Level={status.level} ({levels[status.level]}) "
            f"Last seen D+{status.last_seen_day}"
        )

    # ----------------------------------------------------------------------
    # G-5 Planning Briefing + Portrait
    # ----------------------------------------------------------------------
    print("\n" + g5.last_briefing)
    print("G-5 Portrait Path:", g5.portrait_path)

    # ----------------------------------------------------------------------
    # G-6 Signals Log
    # ----------------------------------------------------------------------
    print("\nG-6 Signals Log:")
    for line in g6.last_log:
        print(" ", line)

    # ----------------------------------------------------------------------
    # G-7 Reinforcement Log
    # ----------------------------------------------------------------------
    print("\nG-7 Reinforcement Log:")
    for line in g7.arrived_log:
        print(" ", line)

    # ----------------------------------------------------------------------
    # G-8 Objectives / Victory Status
    # ----------------------------------------------------------------------
    print("\nG-8 Objectives / Victory:")
    print(f"  Allied VP: {g8.vp.get(Side.ALLIED, 0)}")
    print(f"  Axis VP:   {g8.vp.get(Side.AXIS, 0)}")

    if g8.events:
        print("  Events:")
        for ev in g8.events:
            print("   ", ev)
    else:
        print("  No objective events yet.")


if __name__ == "__main__":
    main()
