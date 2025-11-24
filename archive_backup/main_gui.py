# -*- coding: utf-8 -*-
from turn_engine import TurnEngine
import time

def on_event(e):
    print(f"[EVENT] {e['type']}: {e}")

def main():
    engine = TurnEngine(days_per_turn=2)
    engine.on(on_event)

    print("Starting MWE Turn Engine simulation...")
    for _ in range(3):
        engine.advance_one_turn()
        time.sleep(1.0)

if __name__ == "__main__":
    main()
