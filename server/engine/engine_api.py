from __future__ import annotations

import os
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .core.map_model import GameMap
from .core.time_system import GameTime
from .core.unit_model import Posture, Side, UnitRepository, UnitState, UnitType
from .scenario_loader import load_scenario


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    from engine.ai import BAIController
except Exception:  # pragma: no cover - fail-soft import path for older tools
    BAIController = None


LEGAL_POSTURES = {"HOLD", "MOVE", "ATTACK", "DEFEND", "REST", "REFIT"}
MOVEMENT_SEMANTICS_VERSION = "movement_semantics_v1"
MOVE_DESTINATION_FIELD = "target"


class EngineAPI:
    """
    Minimal headless engine API with optional BAI turn control.

    The API remains usable without any UI surface:
      - load scenario
      - optionally configure one AI-controlled side
      - submit player actions directly
      - process turns headlessly
    """

    def __init__(
        self,
        *,
        ai_enabled: bool = False,
        ai_side: str | None = None,
        engine_config: Mapping[str, Any] | None = None,
    ) -> None:
        self.time: Optional[GameTime] = None
        self.game_map: Optional[GameMap] = None
        self.units: Optional[UnitRepository] = None
        self.meta: Optional[Dict[str, Any]] = None

        self._logs: List[Dict[str, Any]] = []
        self._orders: List[Dict[str, Any]] = []
        self._control_by_loc: Dict[str, Optional[Side]] = {}
        self._vp: Dict[Side, int] = {Side.ALLIED: 0, Side.AXIS: 0}
        self._spawned_reinforcement_ids: set[str] = set()

        self._controller = BAIController() if BAIController is not None else None
        self._ai_requested_enabled = bool(ai_enabled)
        self._ai_enabled = False
        self._ai_side: Optional[Side] = _coerce_side(ai_side)
        self.engine_config: Dict[str, Any] = dict(engine_config or {})
        self._last_ai_result: Dict[str, Any] = {}
        self._last_bai_payload: Dict[str, Any] = {}

    # ------------------------------------------------------------ internal

    def _log(self, src: str, phase: str, message: str) -> None:
        turn = getattr(self.time, "turn", getattr(self.time, "day", 0)) if self.time else 0
        self._logs.append({"src": src, "turn": turn, "phase": phase, "message": message})

    def _ensure_ready(self) -> None:
        if self.time is None or self.game_map is None or self.units is None or self.meta is None:
            raise RuntimeError("EngineAPI not initialized. Call load_scenario() first.")

    def _known_location_ids(self) -> List[str]:
        if self.game_map is None:
            return []
        return [str(location_id) for location_id in self.game_map.tile_ids()]

    def _movement_error(
        self,
        code: str,
        message: str,
        *,
        action_type: str,
        unit_id: str = "",
        raw_target: Any = "",
        from_location_id: str | None = None,
    ) -> Dict[str, Any]:
        return {
            "status": "error",
            "code": code,
            "error": message,
            "movement": {
                "semantics": MOVEMENT_SEMANTICS_VERSION,
                "resolved": False,
                "action_type": action_type,
                "unit_id": unit_id,
                "from_location_id": from_location_id,
                "destination": {
                    "field": MOVE_DESTINATION_FIELD,
                    "raw": "" if raw_target is None else str(raw_target).strip(),
                },
            },
        }

    def _resolve_move_destination(self, raw_target: Any) -> Optional[str]:
        target = "" if raw_target is None else str(raw_target).strip()
        if not target:
            return None

        known_locations = self._known_location_ids()
        for location_id in known_locations:
            if target == location_id:
                return location_id

        normalized = target.upper()
        for location_id in known_locations:
            if normalized == location_id.upper():
                return location_id

        return None

    def _time_to_dict(self) -> Dict[str, Any]:
        self._ensure_ready()
        assert self.time is not None
        if hasattr(self.time, "to_dict") and callable(getattr(self.time, "to_dict")):
            return dict(self.time.to_dict())
        return {
            "day": int(getattr(self.time, "day", 1)),
            "phase": str(getattr(self.time, "phase", "day")),
            "weather": str(getattr(self.time, "weather", "Clear")),
        }

    def _reset_runtime_state(self) -> None:
        self._logs.clear()
        self._orders.clear()
        self._control_by_loc.clear()
        self._vp = {Side.ALLIED: 0, Side.AXIS: 0}
        self._spawned_reinforcement_ids.clear()
        self._last_ai_result = {}
        self._last_bai_payload = {}

    def _resolve_ai_defaults(
        self,
        *,
        ai_enabled: bool | None,
        ai_side: str | None,
        engine_config: Mapping[str, Any] | None,
    ) -> None:
        scenario_ai = dict((self.meta or {}).get("ai") or {})

        if engine_config is not None:
            self.engine_config = dict(engine_config)

        run_cfg = dict(self.engine_config.get("run") or {})
        side_value = (
            ai_side
            or self.engine_config.get("ai_side")
            or run_cfg.get("ai_side")
            or scenario_ai.get("side")
            or (self._ai_side.value if self._ai_side else None)
        )
        self._ai_side = _coerce_side(side_value)

        if ai_enabled is None:
            if "enabled" in self.engine_config:
                ai_enabled = bool(self.engine_config.get("enabled"))
            elif "enabled" in scenario_ai:
                ai_enabled = bool(scenario_ai.get("enabled"))
            else:
                ai_enabled = bool(self._ai_requested_enabled or self._ai_side is not None)

        self._ai_requested_enabled = bool(ai_enabled)
        self._ai_enabled = bool(self._ai_requested_enabled and self._ai_side is not None and self._controller is not None)

        if self._ai_requested_enabled and self._controller is None:
            self._log("ENGINE", "ai", "BAI requested but controller import is unavailable; continuing without AI.")
        elif self._ai_requested_enabled and self._ai_side is None:
            self._log("ENGINE", "ai", "BAI requested without a valid side; continuing without AI.")
        elif self._ai_enabled:
            self._log("ENGINE", "ai", f"BAI enabled for side {self._ai_side.value}.")
        else:
            self._log("ENGINE", "ai", "BAI disabled; engine will run without AI orders.")

    def _apply_order(self, action: Mapping[str, Any], *, source: str) -> Dict[str, Any]:
        self._ensure_ready()
        assert self.units is not None

        action_type = str(action.get("type", "") or "").strip().lower()
        raw_target = action.get(MOVE_DESTINATION_FIELD)
        if action_type != "move":
            return self._movement_error(
                "unsupported_action_type",
                "Unsupported action type",
                action_type=action_type,
                raw_target=raw_target,
            )

        unit_id = str(action.get("unit_id", "")).strip()
        posture_raw = str(action.get("posture", "HOLD")).upper().strip()

        if not unit_id:
            return self._movement_error(
                "missing_unit_id",
                "Missing unit_id",
                action_type=action_type,
                raw_target=raw_target,
            )

        unit = self.units.get(unit_id)
        if unit is None:
            return self._movement_error(
                "unknown_unit",
                f"Unknown unit {unit_id}",
                action_type=action_type,
                unit_id=unit_id,
                raw_target=raw_target,
            )

        before = unit.location_id

        target = self._resolve_move_destination(raw_target)
        if target is None:
            code = (
                "missing_target"
                if raw_target is None or str(raw_target).strip() == ""
                else "unknown_target"
            )
            message = (
                "Missing target"
                if code == "missing_target"
                else f"Unknown target {str(raw_target).strip()}"
            )
            return self._movement_error(
                code,
                message,
                action_type=action_type,
                unit_id=unit_id,
                raw_target=raw_target,
                from_location_id=before,
            )

        if posture_raw not in LEGAL_POSTURES:
            return self._movement_error(
                "invalid_posture",
                f"Invalid posture {posture_raw}",
                action_type=action_type,
                unit_id=unit_id,
                raw_target=raw_target,
                from_location_id=before,
            )

        unit.location_id = target
        unit.posture = Posture(posture_raw)

        order_record = dict(action)
        order_record.update(
            {"type": "move", "unit_id": unit_id, "target": target, "posture": unit.posture.value}
        )
        order_record.setdefault("source", source)
        self._orders.append(order_record)
        self._log(source, "orders", f"Order: {unit_id} {before}->{target}, posture={unit.posture.value}")
        return {
            "status": "ok",
            "movement": {
                "semantics": MOVEMENT_SEMANTICS_VERSION,
                "resolved": True,
                "action_type": "move",
                "unit_id": unit_id,
                "from_location_id": before,
                "to_location_id": target,
                "destination": {
                    "field": MOVE_DESTINATION_FIELD,
                    "raw": "" if raw_target is None else str(raw_target).strip(),
                    "location_id": target,
                },
                "posture": unit.posture.value,
                "moved": before != target,
                "source": source,
            },
        }

    def _determine_control(self, location_id: str) -> Optional[Side]:
        assert self.units is not None
        allied_present = False
        axis_present = False
        for unit in self.units.all_units():
            if unit.location_id != location_id:
                continue
            if unit.side == Side.ALLIED:
                allied_present = True
            elif unit.side == Side.AXIS:
                axis_present = True

        if allied_present and not axis_present:
            return Side.ALLIED
        if axis_present and not allied_present:
            return Side.AXIS
        return None

    def _spawn_reinforcements(self) -> None:
        self._ensure_ready()
        assert self.units is not None and self.meta is not None and self.time is not None

        for reinforcement in self.meta.get("reinforcements", []):
            rid = str(reinforcement.get("id", "")).strip()
            arrival_day = int(reinforcement.get("arrival_day", 0) or 0)
            if not rid or rid in self._spawned_reinforcement_ids or self.units.get(rid) is not None:
                continue
            if self.time.day < arrival_day:
                continue

            unit = UnitState(
                id=rid,
                name=str(reinforcement.get("name", rid)),
                side=_coerce_side(reinforcement.get("side")) or Side.ALLIED,
                unit_type=_coerce_unit_type(reinforcement.get("unit_type")),
                strength=int(reinforcement.get("strength", 100)),
                fatigue=int(reinforcement.get("fatigue", 0)),
                morale=int(reinforcement.get("morale", 50)),
                supply=int(reinforcement.get("supply", 100)),
                readiness=int(reinforcement.get("readiness", 50)),
                location_id=str(reinforcement.get("entry_location_id", "UNKNOWN")),
                posture=Posture.DEFEND,
                hq_unit_id=reinforcement.get("hq_unit_id"),
            )
            self.units.add(unit)
            self._spawned_reinforcement_ids.add(rid)
            self._log("G7", "reinforcements", f"Reinforcement arrived: {unit.id} at {unit.location_id}")

    def _run_bai_turn(self) -> None:
        self._ensure_ready()
        assert self.time is not None

        self._last_ai_result = {}
        self._last_bai_payload = {}

        if not self._ai_enabled or self._ai_side is None or self._controller is None:
            return

        result = self._controller.plan_turn(
            self,
            side=self._ai_side.value,
            time_budget_ms=_extract_time_budget(self.engine_config),
            engine_config=self.engine_config,
        )
        self._last_ai_result = result.to_dict()
        self._last_bai_payload = dict(result.report)

        for order in result.orders:
            outcome = self._apply_order(order, source="BAI")
            if outcome.get("status") != "ok":
                self._log("BAI", "orders", f"Rejected AI order for {order.get('unit_id')}: {outcome.get('error')}")

        self._log(
            "BAI",
            "turn",
            (
                f"BAI planned {result.legal_order_count} legal order(s) for {result.side}; "
                f"budget_exceeded={result.budget_exceeded}"
            ),
        )

    def _resolve_battles(self) -> None:
        self._ensure_ready()
        assert self.units is not None

        by_location: Dict[str, Dict[Side, List[UnitState]]] = {}
        for unit in self.units.all_units():
            by_location.setdefault(unit.location_id, {}).setdefault(unit.side, []).append(unit)

        for location_id, grouped in by_location.items():
            allied_units = grouped.get(Side.ALLIED, [])
            axis_units = grouped.get(Side.AXIS, [])
            if not allied_units or not axis_units:
                continue

            defense_bonus = 0
            if self.game_map is not None:
                tile = self.game_map.get_tile(location_id)
                defense_bonus = int(getattr(tile, "defense_bonus", 0) or 0) if tile is not None else 0

            allied_strength = sum(unit.strength for unit in allied_units)
            axis_strength = sum(unit.strength for unit in axis_units)
            allied_effective = allied_strength + (defense_bonus if _defending_side(allied_units) else 0)
            axis_effective = axis_strength + (defense_bonus if _defending_side(axis_units) else 0)

            if allied_effective >= axis_effective:
                winner = Side.ALLIED
                losers = axis_units
            else:
                winner = Side.AXIS
                losers = allied_units

            for unit in losers:
                unit.strength = max(0, unit.strength - 10)
                unit.morale = max(0, unit.morale - 5)
                unit.readiness = max(0, unit.readiness - 5)
                unit.fatigue = min(100, unit.fatigue + 5)

            self._log(
                "G3",
                "combat",
                (
                    f"Battle at {location_id}: winner={winner.value} "
                    f"(ALLIED {allied_effective} vs AXIS {axis_effective})"
                ),
            )

    def _update_objectives(self) -> None:
        self._ensure_ready()
        assert self.meta is not None and self.time is not None

        for objective in self.meta.get("objectives", []):
            location_id = str(objective.get("location_id", "")).strip()
            desired_side = _coerce_side(objective.get("side"))
            if not location_id or desired_side is None:
                continue

            previous_control = self._control_by_loc.get(location_id)
            current_control = self._determine_control(location_id)
            if previous_control == current_control:
                continue

            self._control_by_loc[location_id] = current_control
            if current_control == desired_side:
                value = int(objective.get("value", 0) or 0)
                self._vp[desired_side] = self._vp.get(desired_side, 0) + value
                self._log(
                    "G8",
                    "objectives",
                    f"Day {self.time.day}: {desired_side.value} secured {location_id} (+{value} VP).",
                )

    def _apply_logistics(self) -> None:
        self._ensure_ready()
        assert self.units is not None and self.meta is not None and self.time is not None

        for unit in self.units.all_units():
            consumption = 1
            if unit.posture == Posture.ATTACK:
                consumption += 2
            elif unit.posture in {Posture.MOVE, Posture.DEFEND}:
                consumption += 1

            before = unit.supply
            unit.supply = max(0, unit.supply - consumption)
            self._log("G4", "logistics", f"{unit.id} consumed {consumption}, supply {before}->{unit.supply}")

        weather = str(getattr(self.time, "weather", "Clear"))
        weather_efficiency = {"Clear": 1.0, "Rain": 0.9, "Storm": 0.75}.get(weather, 0.6)
        for source in self.meta.get("supply_sources", []):
            location_id = str(source.get("location_id", "")).strip()
            side = _coerce_side(source.get("side"))
            daily_supply = int(source.get("daily_supply", 0) or 0)
            if not location_id or side is None or daily_supply <= 0:
                continue

            units_here = [unit for unit in self.units.all_units() if unit.location_id == location_id and unit.side == side]
            if not units_here:
                continue

            base_per_unit = max(1, daily_supply // len(units_here))
            per_unit = max(1, int(round(base_per_unit * weather_efficiency)))
            for unit in units_here:
                before_supply = unit.supply
                unit.supply = min(100, unit.supply + per_unit)
                unit.readiness = min(100, unit.readiness + 2)
                if unit.fatigue > 0:
                    unit.fatigue = max(0, unit.fatigue - 2)
                self._log(
                    "G4",
                    "logistics",
                    f"{unit.id} resupplied +{per_unit} at {location_id} ({weather}) {before_supply}->{unit.supply}",
                )

    def _ai_status(self) -> Dict[str, Any]:
        side_value = self._ai_side.value if self._ai_side else None
        return {
            "requested": self._ai_requested_enabled,
            "enabled": self._ai_enabled,
            "controller_available": self._controller is not None,
            "side": side_value,
            "engine_received_settings": bool(self.engine_config),
            "profile_selection": dict(self.engine_config.get("profile_selection") or {}),
            "last_orders": int(self._last_ai_result.get("legal_order_count", 0) or 0),
            "budget_exceeded": bool(self._last_ai_result.get("budget_exceeded", False)),
        }

    # ------------------------------------------------------------ public API

    def configure_ai(
        self,
        *,
        enabled: bool | None = None,
        side: str | None = None,
        engine_config: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._resolve_ai_defaults(ai_enabled=enabled, ai_side=side, engine_config=engine_config)
        return self._ai_status()

    def load_scenario(
        self,
        scenario_id: str,
        *,
        ai_enabled: bool | None = None,
        ai_side: str | None = None,
        engine_config: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._reset_runtime_state()
        start_time, game_map, units_repo, meta = load_scenario(scenario_id)

        self.time = start_time
        self.game_map = game_map
        self.units = units_repo
        self.meta = meta

        self._resolve_ai_defaults(ai_enabled=ai_enabled, ai_side=ai_side, engine_config=engine_config)
        self._log("ENGINE", "load", f"Loaded scenario {scenario_id}")
        return meta

    def start_game(self) -> Dict[str, Any]:
        self._ensure_ready()
        assert self.meta is not None
        self._log("ENGINE", "start", f"Game started for scenario {self.meta['id']}")
        return self.get_game_state()

    def get_game_state(self) -> Dict[str, Any]:
        self._ensure_ready()
        assert self.meta is not None and self.units is not None

        return {
            "game": {
                "time": self._time_to_dict(),
                "scenario": self.meta["name"],
                "vp": {
                    "ALLIED": int(self._vp.get(Side.ALLIED, 0)),
                    "AXIS": int(self._vp.get(Side.AXIS, 0)),
                },
                "ai": self._ai_status(),
            },
            "units": self.units.to_list(),
            "bai_report": dict(self._last_bai_payload.get("bai_report") or {}),
        }

    def apply_player_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        return self._apply_order(action, source="PLAYER")

    def process_turn(self) -> Dict[str, Any]:
        self._ensure_ready()
        assert self.time is not None

        self._spawn_reinforcements()
        self._run_bai_turn()
        self._resolve_battles()
        self._update_objectives()
        self._apply_logistics()

        processed_day = self.time.day
        self.time.advance()
        self._log("ENGINE", "turn", f"Processed Day {processed_day}; now Day {self.time.day}")
        return self.get_game_state()

    def get_logs(self) -> List[Dict[str, Any]]:
        return list(self._logs)


def _coerce_side(value: Any) -> Optional[Side]:
    if value is None or value == "":
        return None
    if isinstance(value, Side):
        return value
    try:
        return Side(str(value).upper().strip())
    except Exception:
        return None


def _coerce_unit_type(value: Any) -> UnitType:
    if isinstance(value, UnitType):
        return value
    try:
        return UnitType(str(value).upper().strip())
    except Exception:
        return UnitType.INFANTRY


def _defending_side(units: Iterable[UnitState]) -> bool:
    postures = {unit.posture for unit in units}
    return bool(postures & {Posture.DEFEND, Posture.HOLD})


def _extract_time_budget(engine_config: Mapping[str, Any]) -> int | None:
    run_cfg = engine_config.get("run")
    if isinstance(run_cfg, Mapping) and run_cfg.get("time_budget_ms") is not None:
        return int(run_cfg.get("time_budget_ms"))
    if engine_config.get("time_budget_ms") is not None:
        return int(engine_config.get("time_budget_ms"))
    return None


__all__ = ["EngineAPI"]
