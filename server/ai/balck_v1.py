from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


SUPPORTED_BALCK_KINDS = {"attack", "support", "withdraw"}
BALCK_SEMANTICS_VERSION = "balck_ai_v2"


def _infer_side(unit: Dict[str, Any]) -> str:
    side = str(unit.get("side", "")).strip().upper()
    if side:
        return side
    uid = str(unit.get("id") or unit.get("unit_id") or "").strip().upper()
    if uid.startswith("US-") or uid.startswith("ALL-"):
        return "ALLIED"
    if uid.startswith("JP-") or uid.startswith("AX-"):
        return "AXIS"
    return "UNKNOWN"


def _objective_key(side: str, location_id: str) -> str:
    return f"{side}:{location_id}"


def _unit_id(unit: Dict[str, Any]) -> str:
    return str(unit.get("id") or unit.get("unit_id") or "")


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


class BalckAIV2:
    """
    Narrow one-intent Balck behavior for the Harding kernel.

    Balck v2 consumes objective truth and supply-aware objective pressure, then
    emits at most one supported operational event: attack, support, or withdraw.
    """

    def __init__(self, side: str = "AXIS") -> None:
        self.side = str(side or "AXIS").upper()

    def decide_orders(self, state: Dict[str, Any], now: int) -> List[Dict[str, Any]]:
        scenario = state.get("scenario") if isinstance(state, dict) else {}
        if not isinstance(scenario, dict):
            scenario = {}

        candidate = self._select_objective(state, scenario)
        if candidate is None:
            return []

        unit = self._select_unit(candidate, scenario)
        kind, intent = self._choose_kind_and_intent(candidate, unit)
        if kind not in SUPPORTED_BALCK_KINDS:
            return []

        return [
            {
                "kind": kind,
                "intent": intent,
                "unit_id": _unit_id(unit) if unit is not None else None,
                "objective_id": candidate["objective_id"],
                "target_location_id": candidate["location_id"],
                "eta_hours": 6,
                "metadata": {
                    "semantics": BALCK_SEMANTICS_VERSION,
                    "objective_status": candidate["objective_status"],
                    "pressure_state": candidate["pressure_state"],
                    "pressure_score": candidate["pressure_score"],
                    "priority_score": candidate["priority_score"],
                },
            }
        ]

    def _select_objective(
        self,
        state: Dict[str, Any],
        scenario: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        objectives = scenario.get("objectives", [])
        if not isinstance(objectives, list):
            return None

        objective_status = state.get("objective_status", {})
        if not isinstance(objective_status, dict):
            objective_status = {}

        objective_pressure = state.get("objective_pressure", {})
        pressure_by_objective = {}
        if isinstance(objective_pressure, dict):
            pressure_by_objective = objective_pressure.get("by_objective", {})
        if not isinstance(pressure_by_objective, dict):
            pressure_by_objective = {}

        candidates: List[Dict[str, Any]] = []
        for index, objective in enumerate(objectives):
            if not isinstance(objective, dict):
                continue
            side = str(objective.get("side", "")).strip().upper()
            if side != self.side:
                continue
            location_id = str(objective.get("location_id", "")).strip().upper()
            if not location_id:
                continue

            key = _objective_key(self.side, location_id)
            status_payload = objective_status.get(key, {})
            if not isinstance(status_payload, dict):
                status_payload = {}
            pressure_payload = pressure_by_objective.get(key, {})
            if not isinstance(pressure_payload, dict):
                pressure_payload = {}

            objective_status_value = str(status_payload.get("status", "neutral") or "neutral")
            objective_status_value = objective_status_value.lower()
            pressure_state = str(pressure_payload.get("pressure_state", "none") or "none").lower()
            pressure_score = float(pressure_payload.get("pressure_score", 0.0) or 0.0)
            value = _to_int(objective.get("value"), 50)
            tier = _to_int(objective.get("importance_tier"), 0)

            status_priority = {
                "contested": 120,
                "neutral": 60,
                "held": 20,
            }.get(objective_status_value, 0)
            pressure_priority = {
                "sustained": 30,
                "degraded": 15,
                "suppressed": -20,
                "none": -10,
            }.get(pressure_state, 0)
            priority_score = value + (tier * 10) + status_priority + pressure_priority

            candidates.append(
                {
                    "index": index,
                    "key": key,
                    "objective_id": str(objective.get("id") or key),
                    "location_id": location_id,
                    "value": value,
                    "importance_tier": tier,
                    "objective_status": objective_status_value,
                    "pressure_state": pressure_state,
                    "pressure_score": pressure_score,
                    "pressure": pressure_payload,
                    "priority_score": priority_score,
                }
            )

        if not candidates:
            return None

        return sorted(
            candidates,
            key=lambda item: (
                -float(item["priority_score"]),
                -float(item["pressure_score"]),
                str(item["location_id"]),
                int(item["index"]),
            ),
        )[0]

    def _select_unit(
        self,
        candidate: Dict[str, Any],
        scenario: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        units = scenario.get("units", [])
        if not isinstance(units, list):
            return None

        units_by_id = {
            _unit_id(unit): unit
            for unit in units
            if isinstance(unit, dict) and _unit_id(unit)
        }
        contributors = candidate.get("pressure", {}).get("contributors", [])
        if isinstance(contributors, list) and contributors:
            ordered_contributors = sorted(
                [item for item in contributors if isinstance(item, dict)],
                key=lambda item: (
                    -float(item.get("contribution", 0.0) or 0.0),
                    -_to_int(item.get("supply"), 0),
                    str(item.get("unit_id") or ""),
                ),
            )
            for contributor in ordered_contributors:
                unit = units_by_id.get(str(contributor.get("unit_id") or ""))
                if isinstance(unit, dict):
                    return unit

        side_units = [unit for unit in units if isinstance(unit, dict) and _infer_side(unit) == self.side]
        if not side_units:
            return None
        return sorted(
            side_units,
            key=lambda unit: (
                -_to_int(unit.get("strength"), 0),
                -_to_int(unit.get("supply"), 0),
                -_to_int(unit.get("readiness"), 0),
                _unit_id(unit),
            ),
        )[0]

    def _choose_kind_and_intent(
        self,
        candidate: Dict[str, Any],
        unit: Optional[Dict[str, Any]],
    ) -> Tuple[str, str]:
        pressure_state = str(candidate.get("pressure_state", "none") or "none")
        objective_status = str(candidate.get("objective_status", "neutral") or "neutral")
        supply = _to_int(unit.get("supply"), 0) if isinstance(unit, dict) else 0
        readiness = _to_int(unit.get("readiness"), 0) if isinstance(unit, dict) else 0

        if pressure_state == "suppressed" or supply < 10 or readiness < 25:
            return "withdraw", "recover_supply_before_pressure"

        if pressure_state == "degraded" or supply < 30 or readiness < 40:
            return "support", "delay_and_rebuild_pressure"

        if objective_status in {"contested", "neutral"} and pressure_state == "sustained":
            return "attack", "press_objective"

        if objective_status == "held":
            return "support", "hold_objective"

        return "support", "probe_without_overcommitment"


BalckAIV1 = BalckAIV2


__all__ = ["BALCK_SEMANTICS_VERSION", "SUPPORTED_BALCK_KINDS", "BalckAIV1", "BalckAIV2"]
