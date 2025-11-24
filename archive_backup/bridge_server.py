# -*- coding: utf-8 -*-
"""
bridge_server.py (Phase 5 update)
- WebSocket relay for UI <-> Engine/AI
- Adds run/pause auto-advance loop
- Commands: next_turn, run, pause, set_days_per_turn, set_stance, plan_orders
Requires: pip install websockets
"""

import asyncio, json, websockets
from typing import Set, Dict, Any
from turn_engine import TurnEngine
from ai_planner import AIPlanner
from command_api import encode_event, decode_message, Event
from scenario_state import Scenario, Unit, HQ, serialize

CLIENTS: Set[websockets.WebSocketServer] = set()  # future-proof typing
engine = TurnEngine(days_per_turn=2)
ai = AIPlanner(rng_seed=9001)

RUNNING = False
TICK_MS = 1200

# Demo scenario
scenario = Scenario(
    id="demo01",
    name="Phase 5 Demo",
    units=[
        Unit(id="u1", name="1/24 Inf", type="inf", strength=85, fatigue=25, pos=(40,30), hq="IX"),
        Unit(id="u2", name="Tank Co A", type="arm", strength=70, fatigue=30, pos=(42,30), hq="IX"),
        Unit(id="u3", name="Eng Bn", type="eng", strength=60, fatigue=20, pos=(39,29), hq="IX"),
    ],
    hqs=[HQ(id="IX", name="IX Corps", tier="regular", stance="balanced")],
    objectives=[(48,30),(46,28)]
)

def broadcast(evt: Event):
    msg = encode_event(evt)
    for c in list(CLIENTS):
        try:
            asyncio.create_task(c.send(msg))
        except Exception:
            pass

def on_engine_event(e: Dict[str, Any]):
    broadcast(Event(type=e.get("type","event"), data=e))

engine.on(on_engine_event)

async def auto_loop():
    global RUNNING
    while True:
        if RUNNING:
            engine.advance_one_turn()
        await asyncio.sleep(TICK_MS/1000.0)

async def handle(ws, path):
    CLIENTS.add(ws)
    await ws.send(encode_event(Event(type="snapshot", data={
        "engine": engine.state,
        "scenario": json.loads(serialize(scenario)),
    })))

    try:
        async for raw in ws:
            msg = decode_message(raw)
            cmd = msg.get("cmd")
            payload = msg.get("payload", {})

            if cmd == "next_turn":
                engine.advance_one_turn()
            elif cmd == "run":
                global RUNNING
                RUNNING = True
                broadcast(Event(type="run_state", data={"running": True}))
            elif cmd == "pause":
                RUNNING = False
                broadcast(Event(type="run_state", data={"running": False}))
            elif cmd == "set_days_per_turn":
                dpt = int(payload.get("days", engine.state["clock"]["days_per_turn"]))
                engine.state["clock"]["days_per_turn"] = dpt
                broadcast(Event(type="days_per_turn", data={"days": dpt}))
            elif cmd == "set_stance":
                stance = payload.get("stance","balanced")
                for h in scenario.hqs:
                    h.stance = stance
                broadcast(Event(type="stance_updated", data={"stance": stance}))
            elif cmd == "plan_orders":
                orders = ai.plan_turn(
                    stance=scenario.hqs[0].stance,
                    weather=engine.state["weather"],
                    kpis=engine.state["kpis"],
                    intel={"enemy_frontline":[(47,30),(47,29)], "weakpoints":[(46,30)], "minefields":[(45,29)]},
                    scenario={
                        "units":[vars(u) for u in scenario.units],
                        "hqs":[vars(h) for h in scenario.hqs],
                        "objectives": scenario.objectives
                    }
                )
                broadcast(Event(type="ai_orders", data={"orders":[vars(o) for o in orders]}))
            else:
                broadcast(Event(type="unknown_command", data=msg))
    finally:
        CLIENTS.discard(ws)

async def main():
    server = await websockets.serve(handle, "localhost", 8765)
    print("Bridge server listening on ws://localhost:8765")
    await auto_loop()

if __name__ == "__main__":
    asyncio.run(main())
