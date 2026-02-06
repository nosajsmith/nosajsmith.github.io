"""
mwe_bridge_p8_ws15.py — Phase 8 Bridge Service (WebSockets v15 compatible)

Default: ws://127.0.0.1:8766

Commands:
  - ping
  - list_scenarios
  - load_scenario   payload: {"name": "<scenario_name>"}

Protocol:
  Uses server/protocol.py envelopes:
    Request: {"cmd","req_id","payload","v"}
    Response OK: {"ok":true,"req_id","payload","v"}
    Response ERR: {"ok":false,"req_id","error":{"code","message"},"v"}
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from typing import Any, Dict

import websockets

from logging_setup import setup_bridge_logger
from protocol import (
    CMD_LIST_SCENARIOS,
    CMD_LOAD_SCENARIO,
    CMD_PING,
    ERR_BAD_REQUEST,
    ERR_INTERNAL,
    ERR_NOT_FOUND,
    ERR_UNKNOWN_CMD,
    mk_err,
    mk_ok,
    normalize_request,
)

# Keep imports minimal and explicit.
from scenario_store import list_scenarios, load_scenario  # type: ignore


DEFAULT_HOST = os.environ.get("MWE_BRIDGE_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("MWE_BRIDGE_PORT", "8766"))
DEFAULT_SCENARIO_DIR = os.environ.get(
    "MWE_SCENARIO_DIR",
    os.path.join(os.path.dirname(__file__), "scenarios"),
)

log = setup_bridge_logger()


async def dispatch(cmd: str, payload: Dict[str, Any], scenario_dir: str) -> Dict[str, Any]:
    """
    Returns a *payload dict* (not envelope). Envelope is handled by caller.
    """
    if cmd == CMD_PING:
        return {"pong": True, "ts": time.time()}

    if cmd == CMD_LIST_SCENARIOS:
        items = list_scenarios(scenario_dir)
        return {"scenarios": items}

    if cmd == CMD_LOAD_SCENARIO:
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("payload.name must be a non-empty string")
        data = load_scenario(scenario_dir, name.strip())
        # If scenario_store returns None on missing, treat as not_found.
        if data is None:
            raise FileNotFoundError(f"Scenario not found: {name.strip()}")
        return {"scenario": data}

    raise KeyError(f"Unknown cmd: {cmd}")


async def ws_handler(ws) -> None:
    peer = getattr(ws, "remote_address", None)
    log.info("ws_connected peer=%s", peer)

    try:
        async for raw in ws:
            t0 = time.perf_counter()

            # Parse JSON
            try:
                msg = json.loads(raw)
            except Exception as e:
                resp = mk_err("", ERR_BAD_REQUEST, f"Invalid JSON: {e}")
                await ws.send(json.dumps(resp))
                log.warning("bad_json peer=%s err=%s", peer, e)
                continue

            # Validate request envelope
            try:
                req = normalize_request(msg)
            except Exception as e:
                resp = mk_err("", ERR_BAD_REQUEST, f"Invalid request: {e}")
                await ws.send(json.dumps(resp))
                log.warning("bad_request peer=%s err=%s", peer, e)
                continue

            cmd = req["cmd"]
            req_id = req["req_id"]
            payload = req["payload"]

            # Execute
            try:
                out_payload = await dispatch(cmd, payload, DEFAULT_SCENARIO_DIR)
                resp = mk_ok(req_id, out_payload)

            except ValueError as e:
                resp = mk_err(req_id, ERR_BAD_REQUEST, str(e))

            except FileNotFoundError as e:
                resp = mk_err(req_id, ERR_NOT_FOUND, str(e))

            except KeyError as e:
                resp = mk_err(req_id, ERR_UNKNOWN_CMD, str(e))

            except Exception as e:
                resp = mk_err(req_id, ERR_INTERNAL, "Unhandled exception")
                log.exception("internal_error req_id=%s cmd=%s err=%r", req_id, cmd, e)

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            log.info("req_id=%s cmd=%s ok=%s elapsed_ms=%d", req_id, cmd, resp.get("ok"), elapsed_ms)

            await ws.send(json.dumps(resp))

    finally:
        log.info("ws_disconnected peer=%s", peer)


async def main_async(host: str, port: int) -> None:
    async with websockets.serve(ws_handler, host, port):
        log.info("bridge_p8_listening url=ws://%s:%d scenario_dir=%s", host, port, DEFAULT_SCENARIO_DIR)
        await asyncio.Future()  # run forever


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    asyncio.run(main_async(args.host, args.port))


if __name__ == "__main__":
    main()
