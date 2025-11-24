from game_state import GameState
from order_system import OrderDispatcher
from order_persistence import OrderStorage
from order_execution import OrderExecutor
from scenario_loader import load_units_from_file

TURN = 0
game_state = GameState()
units = load_units_from_file("scenario.json")
for u in units:
    game_state.add_unit(u)

dispatcher = OrderDispatcher()
executor = OrderExecutor(game_state)

while True:
    print(f"\n=== TURN {TURN} ===")
    for unit in game_state.all_units():
        print(f"{unit.name} at {unit.position} | Fatigue: {unit.fatigue}, Supply: {unit.supply}")

    cmd = input("Command (run/next/quit): ").strip().lower()
    if cmd == "run":
        executor.execute_orders(dispatcher)
        OrderStorage(f"orders_turn{TURN}.json").save(dispatcher.active_orders)
    elif cmd == "next":
        game_state.advance_turn()
        TURN += 1
    elif cmd == "quit":
        break
    else:
        print("Unknown command.")
