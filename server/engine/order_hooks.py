import os
from order_persistence import OrderStorage
from order_execution import OrderExecutor
from order_system import OrderDispatcher

def get_order_file_for_turn(turn):
    return f"orders_turn{turn}.json"

def load_orders_for_turn(turn, dispatcher: OrderDispatcher):
    path = get_order_file_for_turn(turn)
    storage = OrderStorage(path)
    dispatcher.active_orders = storage.load()

def execute_and_update_orders(dispatcher: OrderDispatcher, executor: OrderExecutor):
    print("[ORDER EXECUTION] Running all pending orders...")
    executor.execute_orders(dispatcher)
    print("[ORDER EXECUTION] All executable orders processed.")

def save_orders_for_turn(turn, dispatcher: OrderDispatcher):
    path = get_order_file_for_turn(turn)
    storage = OrderStorage(path)
    storage.save(dispatcher.active_orders)
