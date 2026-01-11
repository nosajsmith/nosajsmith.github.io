"""
mwe_bridge_p8_ws15.py — Phase 8 Bridge Service (WebSockets v15 + aiohttp healthz)

Protocol v1 (minimal):
Request:  {"cmd": "...", "args": {...optional...}}
Response: {"status":"ok", ...}  OR  {"status":"error","error":"...","detail":{...}}

WS:     ws://127.0.0.1:8766
Health: http://127.0.0.1:8770/healthz
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

import websockets
from aiohttp import web

from scenario_store import (
    list_scenarios,
    read_scenario,
    write_scenario,
    DEFAULT_SCENARIO_DIR,
)

LOG = logging.getLogger("mwe-bridge")


# ---------- helpers ----------
def j_ok(**extra) -> str:
    payload = {"status": "ok", **extra}
    return json.dumps(payload)


def j_err(msg: str, **detail) -> str:
    payload = {"status": "error", "error": msg}
    if detail:
        payload["detail"] = detail
    return json.dumps(payload)


def safe_json_loads(raw: str) -> Optional[Dict[str, Any]]:
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return None
        return obj
    except Exception:
        return None


def get_scenario_dir() -> str:
    # keep your existing behavior: scenario dir is repo/scenarios by default
    return os.environ.get("MWE_SCENARIO_DIR", DEFAULT_SCENARIO_DIR)


# ---------- WS command handlers ----------
async def handle_cmd(cmd: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a dict that will be wrapped as {"status":"ok", ...} or error.
    """
    scen_dir = get_scenario_dir()

    if cmd == "ping":
        return {}

    if cmd == "help":
        return {
            "commands": [
                "ping",
                "help",
                "list_scenarios",
                "load_scenario",
                "save_scenario",
            ]
        }

    if cmd == "list_scenarios":
        items = list_scenarios(scen_dir)
        return {"scenarios": items}

    if cmd == "load_scenario":
        name = args.get("name")
        if not name or not isinstance(name, str):
            raise ValueError("load_scenario requires args.name (string)")
        scen = read_scenario(scen_dir, name)
        return {"scenario": scen}

    if cmd == "save_scenario":
        name = args.get("name")
        scenario = args.get("scenario")
        if not name or not isinstance(name, str):
            raise ValueError("save_scenario requires args.name (string)")
        if scenario is None or not isinstance(scenario, dict):
            raise ValueError("save_scenario requires args.scenario (object)")
        write_scenario(scen_dir, name, scenario)
        return {}

    raise KeyError(f"Unknown cmd: {cmd}")


async def ws_handler(ws):
    """
    websockets v15 server handler signature: ws_handler(connection)
    """
    LOG.info("connection open")
    try:
        async for raw in ws:
            msg = safe_json_loads(raw)
            if msg is None:
                await ws.send(j_err("Invalid JSON message (expected object)"))
                continue

            cmd = msg.get("cmd")
            args = msg.get("args") or {}
            if not isinstance(cmd, str) or not cmd:
                await ws.send(j_err("Missing/invalid cmd"))
                continue
            if not isinstance(args, dict):
                await ws.send(j_err("args must be an object"))
                continue

            try:
                data = await handle_cmd(cmd, args)
                await ws.send(j_ok(**data))
            except KeyError as e:
                await ws.send(j_err(str(e)))
            except ValueError as e:
                await ws.send(j_err(str(e)))
            except Exception as e:
                LOG.exception("Unhandled error")
                await ws.send(j_err("Internal error", exception=str(e)))
    finally:
        LOG.info("connection closed")


# ---------- healthz (aiohttp) ----------
async def healthz(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "clients": 0})


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    scen_dir = get_scenario_dir()
    LOG.info("Scenario dir: %s", scen_dir)

    host = "127.0.0.1"
    ws_port = int(os.environ.get("MWE_WS_PORT", "8766"))
    health_port = int(os.environ.get("MWE_HEALTH_PORT", "8770"))

    # Health server
    app = web.Application()
    app.router.add_get("/healthz", healthz)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, health_port)
    await site.start()
    LOG.info("Healthz running on http://%s:%d/healthz", host, health_port)

    # WebSocket server
    async with websockets.serve(ws_handler, host, ws_port):
        LOG.info("Bridge P8 listening on ws://%s:%d", host, ws_port)
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
