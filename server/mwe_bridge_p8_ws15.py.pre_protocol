"""
mwe_bridge_p8_ws15.py — Phase 8 Bridge Service (WS + healthz)

WS: ws://127.0.0.1:8766
HTTP health: http://127.0.0.1:8770/healthz

Protocol v1.0 request:
{
  "id": "string",
  "proto": "1.0",
  "cmd": "string",
  "args": {}
}

Response:
OK:
{ "id": "...", "proto": "1.0", "cmd": "...", "status": "ok", "data": {...} }

ERR:
{ "id": "...", "proto": "1.0", "cmd": "...", "status": "error",
  "error": {"code":"...", "message":"...", "details":{...}} }
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Set, Optional

import websockets
from aiohttp import web

from scenario_store import (
    list_scenarios,
    read_scenario,
    write_scenario,
    DEFAULT_SCENARIO_DIR,
)

PROTO = "1.0"
WS_HOST = "127.0.0.1"
WS_PORT = 8766

HTTP_HOST = "127.0.0.1"
HTTP_PORT = 8770

clients: Set[object] = set()

# ---------------- Engine state ----------------

@dataclass
class EngineClock:
    turn_number: int = 1

@dataclass
class EngineKPIs:
    supply_pct: int = 90
    readiness_pct: int = 85
    morale_pct: int = 88

class EngineState:
    def __init__(self) -> None:
        self.clock = EngineClock()
        self.kpis = EngineKPIs()

ENGINE = EngineState()

# ---------------- Helpers ----------------

def jerr(req_id: str, cmd: str, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "id": req_id,
        "proto": PROTO,
        "cmd": cmd,
        "status": "error",
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }

def jok(req_id: str, cmd: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "id": req_id,
        "proto": PROTO,
        "cmd": cmd,
        "status": "ok",
        "data": data or {},
    }

def require(cond: bool, code: str, msg: str, details: Optional[Dict[str, Any]] = None):
    if not cond:
        raise ValueError(json.dumps({"code": code, "msg": msg, "details": details or {}}))

def safe_json_loads(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception as e:
        raise ValueError(json.dumps({"code": "bad_request", "msg": f"Invalid JSON: {e}", "details": {}}))

def normalize_scenario_name(name: str) -> str:
    # Keep this intentionally conservative. You can harden more later.
    name = name.strip()
    return name

# ---------------- Command handlers ----------------

async def handle_cmd(req: Dict[str, Any]) -> Dict[str, Any]:
    req_id = str(req.get("id", "")).strip()
    cmd = str(req.get("cmd", "")).strip()
    proto = req.get("proto", None)
    args = req.get("args", {})
    if args is None:
        args = {}

    # Envelope validation
    require(req_id != "", "bad_request", "Missing/empty id")
    require(cmd != "", "bad_request", "Missing/empty cmd")
    require(proto == PROTO, "bad_request", f"Unsupported proto: {proto}", {"expected": PROTO})
    require(isinstance(args, dict), "bad_request", "args must be an object")

    # Commands
    if cmd == "ping":
        return jok(req_id, cmd, {"pong": True})

    if cmd == "get_state":
        return jok(req_id, cmd, {
            "clock": {"turn_number": ENGINE.clock.turn_number},
            "kpis": {
                "supply_pct": ENGINE.kpis.supply_pct,
                "readiness_pct": ENGINE.kpis.readiness_pct,
                "morale_pct": ENGINE.kpis.morale_pct,
            }
        })

    if cmd == "list_scenarios":
        names = list_scenarios()
        # ensure JSON-friendly
        names = [str(x) for x in (names or [])]
        return jok(req_id, cmd, {"scenarios": names})

    if cmd == "load_scenario":

    if cmd == "move_unit":
        args = msg.get("args") or {}
        name = args.get("name", "")
        unit_id = args.get("unit_id", "")
        q = args.get("q", None)
        r = args.get("r", None)

        require(name != "", "bad_request", "move_unit requires args.name")
        require(unit_id != "", "bad_request", "move_unit requires args.unit_id")
        require(isinstance(q, int) and isinstance(r, int), "bad_request", "move_unit requires int args.q/args.r")

        from server.scenario_store import move_unit
        scn = move_unit(name, unit_id, q, r)
        require(scn is not None, "not_found", "scenario or unit not found")

        return ok(msg_id, {"scenario": scn})
        name = normalize_scenario_name(str(args.get("name", "") or ""))
        require(name != "", "bad_request", "load_scenario requires args.name")
        data = read_scenario(name)

        # Expected by protocol: "scenario" must be a JSON object
        if data is None:
            return jerr(req_id, cmd, "not_found", f"Scenario not found: {name}", {})
        if not isinstance(data, dict):
            return jerr(req_id, cmd, "internal", "Scenario store returned non-dict scenario", {"type": str(type(data))})

        return jok(req_id, cmd, {"name": name, "scenario": data})

    if cmd == "save_scenario":
        name = normalize_scenario_name(str(args.get("name", "") or ""))
        scenario = args.get("scenario", None)
        require(name != "", "bad_request", "save_scenario requires args.name")
        require(isinstance(scenario, dict), "bad_request", "save_scenario requires args.scenario object")

        ok = write_scenario(name, scenario)
        # write_scenario may return bool or None; treat truthy as ok
        return jok(req_id, cmd, {"saved": bool(ok) or True, "name": name})

    return jerr(req_id, cmd, "bad_request", f"Unknown cmd: {cmd}", {})

# ---------------- WS server ----------------

async def ws_handler(ws):
    clients.add(ws)
    peer = getattr(ws, "remote_address", None)
    logging.info("WS connected peer=%s", peer)
    try:
        async for raw in ws:
            req = safe_json_loads(raw)
            if not isinstance(req, dict):
                # cannot infer proper envelope; send generic
                await ws.send(json.dumps(jerr("", "", "bad_request", "Request must be a JSON object", {})))
                continue

            req_id = str(req.get("id", "")).strip()
            cmd = str(req.get("cmd", "")).strip()

            try:
                resp = await handle_cmd(req)
            except ValueError as ve:
                # our "require" throws ValueError with JSON payload
                try:
                    payload = json.loads(str(ve))
                    resp = jerr(req_id or "", cmd or "", payload.get("code","bad_request"), payload.get("msg","Bad request"), payload.get("details", {}))
                except Exception:
                    resp = jerr(req_id or "", cmd or "", "bad_request", str(ve), {})
            except Exception as e:
                logging.exception("WS handler error")
                resp = jerr(req_id or "", cmd or "", "internal", "Unhandled exception", {"error": str(e)})

            await ws.send(json.dumps(resp))
    finally:
        clients.discard(ws)
        logging.info("WS disconnected")

# ---------------- healthz ----------------

async def healthz(_request):
    return web.json_response({"status": "ok", "clients": len(clients)})

async def start_http_app():
    app = web.Application()
    app.router.add_get("/healthz", healthz)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
    await site.start()
    logging.info("Healthz running on http://%s:%d/healthz", HTTP_HOST, HTTP_PORT)

# ---------------- main ----------------

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # Ensure scenario dir exists
    os.makedirs(DEFAULT_SCENARIO_DIR, exist_ok=True)
    logging.info("Scenario dir: %s", DEFAULT_SCENARIO_DIR)

    await start_http_app()

    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        logging.info("Bridge P8 listening on ws://%s:%d", WS_HOST, WS_PORT)
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
