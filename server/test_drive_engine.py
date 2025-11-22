from engine.core.time_system import TimeSystem
from engine.core.unit_model import Side, Posture
from engine.scenario_loader import load_scenario
from engine.staff.g1_personnel import G1Personnel
from engine.staff.g2_intel import G2Intelligence
from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g5_plans import G5Plans


def main() -> None:
    # Load scenario
    start_time, game_map, units, meta = load_scenario("mini_gc_1942")

    # Time system
    ts = TimeSystem()
    ts.time.day = start_time.day
    ts.time.phase = start_time.phase

    # Staff sections
    g1 = G1Personnel(units)
    g2 = G2Intelligence(units, enemy_side=Side.AXIS)   # assuming Allies = player
    g3 = G3Operations(units, game_map)
    g4 = G4Logistics(units)
    g5 = G5Plans(
        units,
        game_map,
        g3=g3,
        mode="advisor",          # try "semi_auto" or "full_auto" later
        personality="macarthur", # can be "nimitz", "slim", or any modded one
    )

    ts.register_listener("g1", g1)
    ts.register_listener("g2", g2)
    ts.register_listener("g5", g5)
    ts.register_listener("g3", g3)
    ts.register_listener("g4", g4)

    print(f"Loaded scenario: {meta['name']}")
    print(f"Description: {meta['description']}")
    print(f"Start Day: {ts.time.day}\n")

    print("Initial unit status:")
    for u in units.all_units():
        print(
            f"  {u.id:8} {u.name:24} "
            f"Loc={u.location_id:7} Str={u.strength:3} Sup={u.supply:3} "
            f"Fat={u.fatigue:3} Mor={u.morale:3} Read={u.readiness:3}"
        )

    # For this test, we still manually order 1st Marines to attack TULAGI
    g3.issue_move_order("US-1MAR", "TULAGI", Posture.ATTACK, t=ts.time)

    days_to_run = 5
    for _ in range(days_to_run):
        ts.advance_one_day()

    print(f"\nAfter {days_to_run} days:")
    for u in units.all_units():
        print(
            f"  {u.id:8} {u.name:24} "
            f"Loc={u.location_id:7} Str={u.strength:3} Sup={u.supply:3} "
            f"Fat={u.fatigue:3} Mor={u.morale:3} Read={u.readiness:3}"
        )

    # Battles
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

    # G-2 SITREP
    print("\nG-2 Enemy SITREP (Axis):")
    for status in g2.get_enemy_sitrep():
        level_name = {0: "Unseen", 1: "Presence", 2: "Identified", 3: "Well-known"}[
            status.level
        ]
        print(
            f"  Unit {status.unit_id}: Level={status.level} ({level_name}), "
            f"Last seen D+{status.last_seen_day}"
        )

    # G-5 Briefing (MacArthur personality)
    print("\n" + g5.last_briefing)


if __name__ == "__main__":
    main()
