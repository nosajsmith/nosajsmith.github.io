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

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Set

import websockets
from aiohttp import web

from engine.engine_api import EngineAPI

try:
    from scenario_store import (  # type: ignore
        list_scenarios as list_bridge_scenarios,
        read_scenario as read_bridge_scenario,
        write_scenario,
        DEFAULT_SCENARIO_DIR,
    )
except ImportError:  # pragma: no cover - module import path under pytest/module execution
    from server.scenario_store import (
        list_scenarios as list_bridge_scenarios,
        read_scenario as read_bridge_scenario,
        write_scenario,
        DEFAULT_SCENARIO_DIR,
    )

PROTO = "1.0"
DEFAULT_WS_HOST = os.environ.get("MWE_BRIDGE_HOST", "127.0.0.1")
DEFAULT_WS_PORT = int(os.environ.get("MWE_BRIDGE_PORT", "8766"))
DEFAULT_HTTP_HOST = os.environ.get("MWE_HEALTH_HOST", "127.0.0.1")
DEFAULT_HTTP_PORT = int(os.environ.get("MWE_HEALTH_PORT", "8770"))

clients: Set[object] = set()


def _rules_scenario_dir() -> Path:
    return Path(__file__).resolve().parent / "rules" / "scenarios"


@dataclass
class BridgeRuntime:
    engine: EngineAPI = field(default_factory=EngineAPI)
    scenario_name: str | None = None
    scenario_id: str | None = None
    scenario_data: Dict[str, Any] | None = None
    started: bool = False


RUNTIME = BridgeRuntime()


def reset_runtime() -> BridgeRuntime:
    global RUNTIME
    RUNTIME = BridgeRuntime()
    return RUNTIME


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


def require(cond: bool, code: str, msg: str, details: Optional[Dict[str, Any]] = None) -> None:
    if not cond:
        raise ValueError(json.dumps({"code": code, "msg": msg, "details": details or {}}))


def safe_json_loads(raw: str) -> Any:
    try:
        return json.loads(raw)
    except Exception as exc:  # pragma: no cover - defensive transport path
        raise ValueError(json.dumps({"code": "bad_request", "msg": f"Invalid JSON: {exc}", "details": {}}))


def to_object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def canonical_scenario_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower().removesuffix(".json")).strip("_")


def merge_weather_payload(engine_weather: Any, authored_weather: Any) -> Dict[str, Any] | None:
    authored = to_object(authored_weather)
    authored_condition = authored.get("condition")
    condition = authored_condition if isinstance(authored_condition, str) and authored_condition.strip() else engine_weather
    if not condition and not authored:
        return None
    payload = dict(authored)
    if condition:
        payload["condition"] = str(condition)
    return payload


def unique_strings(values: list[Any]) -> list[str]:
    seen: Set[str] = set()
    rows: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


def derive_pressure_payload(authored: Dict[str, Any]) -> Dict[str, Any]:
    local_areas = authored.get("local_pressure_areas") if isinstance(authored.get("local_pressure_areas"), list) else []
    area_labels = unique_strings([
        to_object(area).get("label")
        for area in local_areas
    ])
    reasons = unique_strings([
        reason
        for area in local_areas
        for reason in (to_object(area).get("pressure_reasons") or [])
    ])

    summary = None
    if len(area_labels) == 1:
        summary = f"Pressure centers on {area_labels[0]}."
    elif len(area_labels) == 2:
        summary = f"Pressure spans {area_labels[0]} and {area_labels[1]}."
    elif len(area_labels) > 2:
        summary = f"Pressure spans {area_labels[0]}, {area_labels[1]}, and {len(area_labels) - 2} more sectors."

    return {
        "active": bool(local_areas or reasons),
        "summary": summary,
        "reasons": reasons,
        "details": {
            "areas": area_labels,
            "count": len(local_areas),
        },
    }


def merge_live_units(live_units: list[Any], authored_units: list[Any]) -> list[Dict[str, Any]]:
    authored_by_id = {
        str(unit.get("id") or unit.get("unit_id") or unit.get("name") or ""): unit
        for unit in authored_units
        if isinstance(unit, dict)
    }
    merged: list[Dict[str, Any]] = []
    for unit in live_units:
        row = to_object(unit)
        unit_id = str(row.get("id") or row.get("unit_id") or row.get("name") or "")
        authored = authored_by_id.get(unit_id, {})
        same_location = str(authored.get("location_id") or "") == str(row.get("location_id") or "")
        next_row = dict(row)
        for key in ("map_label", "label_priority", "label_offset_x", "label_offset_y", "label_anchor"):
            if key not in next_row and key in authored:
                next_row[key] = authored[key]
        if same_location:
            if next_row.get("x") is None and isinstance(authored.get("x"), (int, float)):
                next_row["x"] = authored["x"]
            if next_row.get("y") is None and isinstance(authored.get("y"), (int, float)):
                next_row["y"] = authored["y"]
            if "position" not in next_row and isinstance(authored.get("position"), list):
                next_row["position"] = list(authored["position"])
        merged.append(next_row)
    return merged


def list_runtime_scenarios() -> list[str]:
    names = {str(item) for item in (list_bridge_scenarios() or [])}
    rules_dir = _rules_scenario_dir()
    if rules_dir.exists():
        names.update(path.name for path in rules_dir.glob("*.json") if path.is_file())
    return sorted(name for name in names if name)


def read_rules_scenario(filename: str) -> Dict[str, Any] | None:
    path = _rules_scenario_dir() / filename
    if not path.exists() or not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def resolve_requested_scenario(args: Dict[str, Any]) -> tuple[str, str, Dict[str, Any]] | None:
    requested_values = []
    for key in ("name", "id"):
        value = str(args.get(key, "") or "").strip()
        if value:
            requested_values.append(value)

    seen = set()
    candidates: list[tuple[str, str]] = []
    for value in requested_values:
        canonical = canonical_scenario_id(value)
        raw_name = value if value.endswith(".json") else f"{value}.json"
        canonical_name = f"{canonical}.json" if canonical else ""
        for filename in (raw_name, canonical_name):
            if not filename or filename in seen:
                continue
            seen.add(filename)
            candidates.append((canonical or canonical_scenario_id(filename), filename))

    for scenario_id, filename in candidates:
        payload = read_bridge_scenario(filename) or read_rules_scenario(filename)
        if payload:
            resolved_id = str(payload.get("id") or scenario_id or canonical_scenario_id(filename))
            return resolved_id, filename, payload
    return None


def build_view_snapshot() -> Dict[str, Any]:
    require(RUNTIME.started and RUNTIME.scenario_data is not None, "not_ready", "Scenario is not active yet.")

    state = RUNTIME.engine.get_game_state()
    game = to_object(state.get("game"))
    game_time = to_object(game.get("time"))
    authored = RUNTIME.scenario_data or {}
    authored_weather = authored.get("weather")
    authored_units = authored.get("units") if isinstance(authored.get("units"), list) else []
    day_value = int(game_time.get("day") or 1)
    pressure_payload = derive_pressure_payload(authored)

    return {
        "scenario": {
            "id": authored.get("id") or RUNTIME.scenario_id,
            "name": authored.get("name") or game.get("scenario") or RUNTIME.scenario_name,
            "theater_id": authored.get("theater_id"),
            "map_package": authored.get("map_package"),
        },
        "time": {
            "turn": int(game_time.get("turn") or day_value),
            "current_hours": max(0, (day_value - 1) * 24),
            "phase": game_time.get("phase"),
        },
        "weather": merge_weather_payload(game_time.get("weather"), authored_weather),
        "campaign": {
            "status": "active",
            "score_by_side": game.get("vp") or {},
        },
        "pressure": pressure_payload,
        "reports": {
            "pending_count": None,
            "recent": [],
        },
        "staff": {
            "summary": to_object(authored.get("grease_board")).get("staff_notes"),
        },
        "ai": game.get("ai") or {},
        "bai_report": state.get("bai_report") or {},
        "grease_board": authored.get("grease_board"),
        "map_presentation": authored.get("map_presentation"),
        "local_pressure_areas": authored.get("local_pressure_areas") or [],
        "named_features": authored.get("named_features") or [],
        "airfields": authored.get("airfields") or [],
        "ports": authored.get("ports") or [],
        "naval_support_windows": authored.get("naval_support_windows") or [],
        "objectives": authored.get("objectives") or [],
        "units": merge_live_units(state.get("units") or [], authored_units),
        "logs": RUNTIME.engine.get_logs(),
        "capabilities": {
            "can_save_snapshot": False,
            "can_load_snapshot": False,
            "can_export_replay": False,
        },
    }


async def handle_cmd(req: Dict[str, Any]) -> Dict[str, Any]:
    req_id = str(req.get("id", "")).strip()
    cmd = str(req.get("cmd", "")).strip()
    proto = req.get("proto", None)
    args = req.get("args", {})
    if args is None:
        args = {}

    require(req_id != "", "bad_request", "Missing/empty id")
    require(cmd != "", "bad_request", "Missing/empty cmd")
    require(proto == PROTO, "bad_request", f"Unsupported proto: {proto}", {"expected": PROTO})
    require(isinstance(args, dict), "bad_request", "args must be an object")

    if cmd == "ping":
        return jok(req_id, cmd, {"pong": True})

    if cmd == "engine_status":
        return jok(req_id, cmd, {
            "started": RUNTIME.started,
            "scenario_id": RUNTIME.scenario_id,
            "scenario_name": RUNTIME.scenario_name,
            "ai": build_view_snapshot().get("ai") if RUNTIME.started and RUNTIME.scenario_data else {},
        })

    if cmd == "get_state":
        return jok(req_id, cmd, build_view_snapshot())

    if cmd == "list_scenarios":
        return jok(req_id, cmd, {"scenarios": list_runtime_scenarios()})

    if cmd == "load_scenario":
        resolved = resolve_requested_scenario(args)
        require(resolved is not None, "not_found", "Scenario not found.")
        scenario_id, filename, authored = resolved
        meta = RUNTIME.engine.load_scenario(scenario_id)
        RUNTIME.scenario_id = scenario_id
        RUNTIME.scenario_name = str(authored.get("name") or meta.get("name") or scenario_id)
        RUNTIME.scenario_data = authored
        RUNTIME.started = False
        return jok(req_id, cmd, {
            "id": scenario_id,
            "name": filename,
            "scenario": authored,
        })

    if cmd == "start_game":
        require(RUNTIME.scenario_id is not None, "not_ready", "No scenario loaded.")
        state = RUNTIME.engine.start_game()
        RUNTIME.started = True
        return jok(req_id, cmd, state)

    if cmd == "view.snapshot":
        return jok(req_id, cmd, build_view_snapshot())

    if cmd == "end_turn":
        require(RUNTIME.started, "not_ready", "Scenario is not active yet.")
        state = RUNTIME.engine.process_turn()
        return jok(req_id, cmd, {"state": state, "dt_hours": args.get("dt_hours")})

    if cmd == "process_turn":
        require(RUNTIME.started, "not_ready", "Scenario is not active yet.")
        state = RUNTIME.engine.process_turn()
        return jok(req_id, cmd, state)

    if cmd == "ai.enable":
        enabled = bool(args.get("enabled", True))
        status = RUNTIME.engine.configure_ai(enabled=enabled)
        return jok(req_id, cmd, status)

    if cmd == "save_scenario":
        name = str(args.get("name", "") or "").strip()
        scenario = args.get("scenario")
        require(name != "", "bad_request", "save_scenario requires args.name")
        require(isinstance(scenario, dict), "bad_request", "save_scenario requires args.scenario object")
        ok = write_scenario(name, scenario)
        return jok(req_id, cmd, {"saved": bool(ok), "name": name})

    return jerr(req_id, cmd, "bad_request", f"Unknown cmd: {cmd}", {})


async def dispatch_request(req: Dict[str, Any]) -> Dict[str, Any]:
    req_id = str(req.get("id", "")).strip()
    cmd = str(req.get("cmd", "")).strip()
    try:
        return await handle_cmd(req)
    except ValueError as exc:
        try:
            payload = json.loads(str(exc))
            return jerr(
                req_id or "",
                cmd or "",
                payload.get("code", "bad_request"),
                payload.get("msg", "Bad request"),
                payload.get("details", {}),
            )
        except Exception:
            return jerr(req_id or "", cmd or "", "bad_request", str(exc), {})
    except Exception as exc:  # pragma: no cover - transport-level guard
        logging.exception("WS handler error")
        return jerr(req_id or "", cmd or "", "internal", "Unhandled exception", {"error": str(exc)})


async def ws_handler(ws) -> None:
    clients.add(ws)
    peer = getattr(ws, "remote_address", None)
    logging.info("WS connected peer=%s", peer)
    try:
        async for raw in ws:
            req = safe_json_loads(raw)
            if not isinstance(req, dict):
                await ws.send(json.dumps(jerr("", "", "bad_request", "Request must be a JSON object", {})))
                continue

            req_id = str(req.get("id", "")).strip()
            cmd = str(req.get("cmd", "")).strip()
            resp = await dispatch_request(req)
            await ws.send(json.dumps(resp))
    finally:
        clients.discard(ws)
        logging.info("WS disconnected")


async def healthz(_request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "clients": len(clients), "started": RUNTIME.started})


async def start_http_app(host: str, port: int) -> None:
    app = web.Application()
    app.router.add_get("/healthz", healthz)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logging.info("Healthz running on http://%s:%d/healthz", host, port)


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MWE Phase 8 websocket bridge.")
    parser.add_argument("--host", default=DEFAULT_WS_HOST, help="Bridge websocket host")
    parser.add_argument("--port", type=int, default=DEFAULT_WS_PORT, help="Bridge websocket port")
    parser.add_argument("--health-host", default=DEFAULT_HTTP_HOST, help="Health endpoint host")
    parser.add_argument("--health-port", type=int, default=DEFAULT_HTTP_PORT, help="Health endpoint port")
    return parser.parse_args()


async def main() -> None:
    args = parse_cli_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    os.makedirs(DEFAULT_SCENARIO_DIR, exist_ok=True)
    logging.info("Scenario dir: %s", DEFAULT_SCENARIO_DIR)
    logging.info("Rules scenario dir: %s", _rules_scenario_dir())

    await start_http_app(args.health_host, args.health_port)

    async with websockets.serve(ws_handler, args.host, args.port):
        logging.info("Bridge P8 listening on ws://%s:%d", args.host, args.port)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
