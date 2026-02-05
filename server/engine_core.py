"""
engine_core.py — Phase 6
All game logic lives here. The bridge just validates transport + routes commands.

Engine responses are JSON-serializable dicts.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, asdict, is_dataclass
from typing import Any, Dict

from scenario_store import (
    list_scenarios,
    read_scenario,
    write_scenario,
    DEFAULT_SCENARIO_DIR,
)

from bridge_protocol import (
    CMD_GET_STATE,
    CMD_LIST_SCENARIOS,
    CMD_LOAD_SCENARIO,
    CMD_PING,
    CMD_SAVE_SCENARIO,
)

PROTO = "1.0"

# ---------------- Engine state (starter) ----------------

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clock": asdict(self.clock),
            "kpis": asdict(self.kpis),
        }

# ---------------- Helpers ----------------

def _to_jsonable(obj: Any) -> Any:
    """Best-effort conversion to JSON-safe types (dict/list/str/int/float/bool/None)."""
    if obj is None:
        return None
    if is_dataclass(obj):
        return {k: _to_jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    # last resort: string it
    return str(obj)

# ---------------- Core Engine ----------------

class EngineCore:
    def __init__(self, scenario_dir: str | None = None) -> None:
        self.state = EngineState()
        self.scenario_dir = os.path.abspath(scenario_dir or DEFAULT_SCENARIO_DIR)
        self._handlers = {
            CMD_PING: self._handle_ping,
            CMD_GET_STATE: self._handle_get_state,
            CMD_LIST_SCENARIOS: self._handle_list_scenarios,
            CMD_LOAD_SCENARIO: self._handle_load_scenario,
            CMD_SAVE_SCENARIO: self._handle_save_scenario,
        }

    def apply(self, cmd: str | None, args: Dict[str, Any] | None) -> Dict[str, Any]:
        """
        Returns ONLY the 'data' payload for an OK response.
        On error, returns {"ok": False, "error": {...}}.
        """
        args = args or {}

        try:
            cmd_name = str(cmd or "").strip()
            if not cmd_name:
                raise EngineError("bad_request", "Missing cmd", {})

            handler = self._handlers.get(cmd_name)
            if handler is None:
                raise EngineError("unknown_cmd", f"Unknown cmd: {cmd_name}", {"cmd": cmd_name})

            return handler(args)
        except EngineError as exc:
            return {"ok": False, "error": exc.to_error()}
        except Exception as exc:
            return {
                "ok": False,
                "error": {
                    "code": "internal",
                    "message": "Unhandled exception",
                    "details": {"error": str(exc)},
                },
            }

    def _handle_ping(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"pong": True}

    def _handle_get_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.state.to_dict()

    def _handle_list_scenarios(self, args: Dict[str, Any]) -> Dict[str, Any]:
        names = list_scenarios(self.scenario_dir)
        # normalize
        if not isinstance(names, list):
            raise EngineError("internal", "Scenario store returned non-list scenarios", {"type": str(type(names))})
        return {"scenarios": [str(x) for x in names]}

    def _handle_load_scenario(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = str(args.get("name", "")).strip()
        if not name:
            raise EngineError("bad_request", "Missing args.name", {})
        data = read_scenario(name, self.scenario_dir)
        if data is None:
            raise EngineError("not_found", f"Scenario not found: {name}", {})
        # ensure dict-like for UI friendliness
        if is_dataclass(data):
            data = asdict(data)
        if not isinstance(data, dict):
            raise EngineError("internal", "Scenario store returned non-dict scenario", {"type": str(type(data))})
        return {"name": name, "scenario": _to_jsonable(data)}

    def _handle_save_scenario(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = str(args.get("name", "")).strip()
        scenario = args.get("scenario", None)
        if not name:
            raise EngineError("bad_request", "Missing args.name", {})
        if not isinstance(scenario, dict):
            raise EngineError(
                "bad_request",
                "Missing/invalid args.scenario (must be object)",
                {"type": str(type(scenario))},
            )
        # write_scenario may accept dict; that's what our current bridge flow relies on.
        write_scenario(name, scenario, self.scenario_dir)
        return {"saved": True, "name": name}

class EngineError(Exception):
    def __init__(self, code: str, message: str, details: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_error(self) -> Dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}
