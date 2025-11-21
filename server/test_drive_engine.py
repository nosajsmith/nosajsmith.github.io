from engine.core.time_system import TimeSystem
from engine.scenario_loader import load_scenario
from engine.staff.g4_logistics import G4Logistics


def main() -> None:
    # Load scenario
    start_time, game_map, units, meta = load_scenario("mini_gc_1942")

    # Create time system and align to scenario start
    ts = TimeSystem()
    ts.time.day = start_time.day
    ts.time.phase = start_time.phase

    # Hook up G-4
    g4 = G4Logistics(units)
    ts.register_listener("g4", g4)

    print(f"Loaded scenario: {meta['name']}")
    print(f"Description: {meta['description']}")
    print(f"Start Day: {ts.time.day}")
    print("\nInitial unit status:")
    for u in units.all_units():
        print(f"  {u.id} {u.name} @ {u.location_id} - Supply {u.supply}")

    # Advance 3 days
    for _ in range(3):
        ts.advance_one_day()

    print("\nAfter 3 days of logistics processing:")
    for u in units.all_units():
        print(f"  {u.id} {u.name} - Supply {u.supply}")


if __name__ == "__main__":
    main()
