"""
mwe_bridge_p8.py — Phase 8 Bridge Service with Scenario load/save/list
"""

import asyncio, json, logging, os
from dataclasses import dataclass
from typing import Any, Dict, Set
import websockets
from websockets.server import WebSocketServerProtocol
from aiohttp import web
from scenario_store import (
    list_scenarios, read_scenario, write_scenario,
    Scenario, Unit, DEFAULT_SCENARIO_DIR
)

# ---------------- Core engine skeleton ----------------

@dataclass
class EngineClock: turn_number: int = 1
@dataclass
class EngineKPIs:
    supply_pct: int = 90
    readiness_pct: int = 85
    morale_pct: int = 88

class EngineState:
    def __init__(self):
        self.clock = EngineClock()
        self.kpis = EngineKPIs()

class GameWorld:
    def __init__(self):
        self.engine = EngineState()
        self.blue = {"units": [], "objectives": []}
        self.red = {"units": []}

    def snapshot(self) -> Dict[str, Any]:
        return {
            "engine": {
                "clock": {"turn_number": self.engine.clock.turn_number},
                "kpis": {
                    "supply_pct": self.engine.kpis.supply_pct,
                    "readiness_pct": self.engine.kpis.readiness_pct,
                    "morale_pct": self.engine.kpis.morale_pct,
                },
            },
            "blue": self.blue,
            "red": self.red,
        }

    # --- Phase 8 hooks ---
    def apply_scenario(self, scn: Scenario):
        self.engine.clock.turn_number = scn.start_turn
        self.blue["units"] = [asdict(u) for u in scn.blue_units]
        self.red["units"] = [asdict(u) for u in scn.red_units]
        self.blue["objectives"] = scn.objectives

    def export_scenario(self, name: str) -> Scenario:
        def _u(d: Dict[str, Any]) -> Unit:
            return Unit(
                id=str(d["id"]), name=str(d["name"]), type=str(d["type"]),
                strength=int(d.get("strength", 100)), fatigue=int(d.get("fatigue", 0)),
                hq=str(d.get("hq", "")), pos=tuple(d.get("pos", [0, 0]))
            )
        return Scenario(
            name=name,
            metadata={"exported_by": "MWE Bridge P8"},
            blue_units=[_u(u) for u in self.blue["units"]],
            red_units=[_u(u) for u in self.red["units"]],
            objectives=[tuple(o) for o in self.blue["objectives"]],
            start_turn=self.engine.clock.turn_number,
        )

# ---------------- Bridge server ----------------

CLIENTS: Set[WebSocketServerProtocol] = set()
LOGGER = logging.getLogger("MWE-P8")

def msg_json(t: str, data: Any) -> str:
    return json.dumps({"type": t, "data": data})

async def send_snapshot(ws, world):
    await ws.send(msg_json("snapshot", world.snapshot()))

async def handle(ws, path, world, scen_dir):
    CLIENTS.add(ws)
    try:
        await send_snapshot(ws, world)
        async for raw in ws:
            try: msg = json.loads(raw)
            except Exception:
                await ws.send(msg_json("error", {"code":"bad_json"}))
                continue
            cmd = msg.get("cmd")

            if cmd == "ping":
                await ws.send(msg_json("pong", {}))
            elif cmd == "auto_execute":
                await ws.send(msg_json("movement_report", {"movements": []}))
                await ws.send(msg_json("combat_report", {"combats": []}))
            elif cmd == "next_turn":
                world.engine.clock.turn_number += 1
                await ws.send(msg_json("turn_advanced", {"turn": world.engine.clock.turn_number}))
                await send_snapshot(ws, world)
            # ----- Phase 8 commands -----
            elif cmd == "list_scenarios":
                files = list_scenarios(scen_dir)
                await ws.send(msg_json("scenario_list", {"files": files}))
            elif cmd == "load_scenario":
                name = msg.get("name")
                try:
                    scn = read_scenario(name, scen_dir)
                    world.apply_scenario(scn)
                    await ws.send(msg_json("scenario_loaded", {"name": scn.name}))
                    await send_snapshot(ws, world)
                except Exception as e:
                    await ws.send(msg_json("error", {"code":"load_failed","message":str(e)}))
            elif cmd == "save_scenario":
                name = msg.get("name") or "export"
                try:
                    scn = world.export_scenario(name)
                    path = write_scenario(scn, f"{name}.json", scen_dir)
                    await ws.send(msg_json("scenario_saved", {"name":scn.name,"path":path}))
                except Exception as e:
                    await ws.send(msg_json("error", {"code":"save_failed","message":str(e)}))
            else:
                await ws.send(msg_json("error", {"code":"unknown_cmd","message":f"Unknown {cmd}"}))
    finally:
        CLIENTS.discard(ws)

# ---- Healthz ----
async def healthz(_req): return web.json_response({"status":"ok","clients":len(CLIENTS)})

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    world = GameWorld()
    host, port, health_port = "localhost", 8766, 8770
    scen_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "scenarios"))
    os.makedirs(scen_dir, exist_ok=True)
    LOGGER.info(f"Scenario dir: {scen_dir}")

    app = web.Application(); app.router.add_get("/healthz", healthz)
    runner = web.AppRunner(app); await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", health_port); await site.start()
    LOGGER.info(f"Healthz running on http://127.0.0.1:{health_port}/healthz")

    async with websockets.serve(lambda ws, p: handle(ws, p, world, scen_dir), host, port):
        LOGGER.info(f"Bridge P8 listening on ws://{host}:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
