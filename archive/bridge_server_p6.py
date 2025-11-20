# -*- coding: utf-8 -*-
"""
bridge_server_p6.py - Phase 6
Adds order execution and reporting to the Phase 5 bridge.

Runs on ws://localhost:8766
Supports:
- next_turn
- auto_execute (plans + executes AI orders)
- execute_orders (UI-provided orders)
Broadcasts:
- movement_report
- combat_report
"""

import asyncio, json, websockets
from typing import Set
from turn_engine import TurnEngine
from ai_planner import AIPlanner
from scenario_state import Scenario, Unit, HQ, serialize
from orders_executor import execute_orders
from reports import movement_report_dict, combat_report_dict

# Connected clients
CLIENTS: Set[websockets.WebSocketServer] = set()

# Initialize engine + AI
engine = TurnEngine(days_per_turn=2)
ai = AIPlanner(rng_seed=9001)

# Demo Blue/Red forces
blue = Scenario(
    id="blue01", name="Blue Force",
    units=[
        Unit(id="b1", name="1/24 Inf", type="inf", strength=85, fatigue=25, pos=(40,30), hq="IX"),
        Unit(id="b2", name="Tank Co A", type="arm", strength=70, fatigue=30, pos=(42,30), hq="IX"),
        Unit(id="b3", name="Eng Bn", type="eng", strength=60, fatigue=20, pos=(39,29), hq="IX"),
    ],
    hqs=[HQ(id="IX", name="IX Corps", tier="regular", stance="balanced")],
    objectives=[(48,30),(46,28)]
)

red_units = [
    {"id": "r1", "name": "NK 1st", "type": "inf", "strength": 75, "fatigue": 20, "pos": (46,30)},
]

# --- Terrain + Environment Helpers ---
def terrain_cost(c):
    # Simple terrain cost mock
    q, r = c
    base = 1.0
    if (q + r) % 11 == 0:
        base = 2.0  # hills
    if r % 5 == 0:
        base *= 0.6  # road
    return base

def terrain_type(c):
    q, r = c
    if (q + r) % 11 == 0:
        return "hills"
    return "clear"

def ground_mod(c):
    g = engine.state["weather"]["ground"]
    if g == "mud":
        return 0.6
    if g == "frozen":
        return 0.2
    return 0.0

# --- Communication Helpers ---
async def broadcast(evt_type, data):
    msg = json.dumps({"type": evt_type, "data": data})
    for c in list(CLIENTS):
        try:
            await c.send(msg)
        except Exception:
            pass

# --- WebSocket Handler ---
async def handle(ws, path):
    CLIENTS.add(ws)

    # Send initial snapshot
    await ws.send(json.dumps({
        "type": "snapshot",
        "data": {
            "engine": engine.state,
            "blue": json.loads(serialize(blue)),
            "red": {"units": red_units},
        }
    }))

    try:
        async for raw in ws:
            m = json.loads(raw)
            cmd = m.get("cmd")
            payload = m.get("payload", {})

            if cmd == "next_turn":
                engine.advance_one_turn()
                await broadcast("turn_advanced", {"turn": engine.state["clock"]["turn_number"]})

            elif cmd == "auto_execute":
                # AI plans and executes automatically
                orders = [vars(o) for o in ai.plan_turn(
                    stance=blue.hqs[0].stance,
                    weather=engine.state["weather"],
                    kpis=engine.state["kpis"],
                    intel={"enemy_frontline":[(47,30),(47,29)], "weakpoints":[(46,30)]},
                    scenario={
                        "units":[vars(u) for u in blue.units],
                        "hqs":[vars(h) for h in blue.hqs],
                        "objectives": blue.objectives
                    }
                )]
                rep = execute_orders(orders, [vars(u) for u in blue.units], red_units,
                                     terrain_cost, terrain_type, ground_mod)
                await broadcast("movement_report", movement_report_dict(rep))
                await broadcast("combat_report", combat_report_dict(rep))

            elif cmd == "execute_orders":
                orders = payload.get("orders", [])
                rep = execute_orders(orders, [vars(u) for u in blue.units], red_units,
                                     terrain_cost, terrain_type, ground_mod)
                await broadcast("movement_report", movement_report_dict(rep))
                await broadcast("combat_report", combat_report_dict(rep))

            else:
                await broadcast("unknown_command", {"cmd": cmd, "payload": payload})

    finally:
        CLIENTS.discard(ws)

# --- Main Entry ---
async def main():
    async with websockets.serve(handle, "localhost", 8766):
        print("Bridge P6 running on ws://localhost:8766")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
