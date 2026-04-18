from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple


def _infer_side(unit: Dict[str, Any]) -> str:
    side = str(unit.get("side", "")).upper()
    if side:
        return side
    uid = str(unit.get("id") or unit.get("unit_id") or "").upper()
    if uid.startswith("US-") or uid.startswith("ALL-"):
        return "ALLIED"
    if uid.startswith("JP-") or uid.startswith("AX-"):
        return "AXIS"
    return "UNKNOWN"


def _pos(unit: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    if "x" in unit and "y" in unit:
        return (int(unit["x"]), int(unit["y"]))
    pos = unit.get("position")
    if not pos:
        pos = unit.get("pos")
    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
        return (int(pos[0]), int(pos[1]))
    return None


def _objective_pos(objective: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    if "x" in objective and "y" in objective:
        return (int(objective["x"]), int(objective["y"]))
    pos = objective.get("position")
    if not pos:
        pos = objective.get("pos")
    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
        return (int(pos[0]), int(pos[1]))
    return None


def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _objective_key(side: str, location_id: str) -> str:
    return f"{side}:{location_id}"


def _opposing_side(designated_side: str) -> Optional[str]:
    if designated_side == "ALLIED":
        return "AXIS"
    if designated_side == "AXIS":
        return "ALLIED"
    return None


def _side_in_range(
    units: Iterable[Dict[str, Any]],
    *,
    side: Optional[str],
    target: Tuple[int, int],
    radius: int,
    exclude_side: Optional[str] = None,
) -> bool:
    for unit in units:
        if not isinstance(unit, dict):
            continue
        unit_side = _infer_side(unit)
        if exclude_side is not None:
            if not unit_side or unit_side in {exclude_side, "UNKNOWN"}:
                continue
        elif unit_side != side:
            continue
        unit_pos = _pos(unit)
        if unit_pos is None:
            continue
        if _dist(target, unit_pos) <= radius:
            return True
    return False


def compute_objective_status(
    scenario: Dict[str, Any],
    radius: int = 1,
) -> Dict[str, Dict[str, Any]]:
    objs = scenario.get("objectives", []) if isinstance(scenario, dict) else []
    units = scenario.get("units", []) if isinstance(scenario, dict) else []

    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(objs, list) or not isinstance(units, list):
        return out

    for objective in objs:
        if not isinstance(objective, dict):
            continue
        side = str(objective.get("side", "")).upper()
        location_id = str(objective.get("location_id", "")).upper()
        if not side or not location_id:
            continue

        objective_pos = _objective_pos(objective)
        key = _objective_key(side, location_id)
        designated_side_in_range = False
        opposing_side_in_range = False
        if objective_pos is not None:
            designated_side_in_range = _side_in_range(
                units,
                side=side,
                target=objective_pos,
                radius=radius,
            )
            opposing_side = _opposing_side(side)
            if opposing_side is not None:
                opposing_side_in_range = _side_in_range(
                    units,
                    side=opposing_side,
                    target=objective_pos,
                    radius=radius,
                )
            else:
                opposing_side_in_range = _side_in_range(
                    units,
                    side=None,
                    target=objective_pos,
                    radius=radius,
                    exclude_side=side,
                )

        if designated_side_in_range and not opposing_side_in_range:
            status = "held"
            controller_side: Optional[str] = side
        elif designated_side_in_range and opposing_side_in_range:
            status = "contested"
            controller_side = None
        else:
            status = "neutral"
            controller_side = None

        out[key] = {
            "side": side,
            "location_id": location_id,
            "status": status,
            "designated_side_in_range": designated_side_in_range,
            "opposing_side_in_range": opposing_side_in_range,
            "controller_side": controller_side,
        }

    return out


def compute_objective_truth(
    scenario: Dict[str, Any],
    radius: int = 1,
) -> Dict[str, Dict[str, Any]]:
    return compute_objective_status(scenario, radius=radius)


def compute_objective_state(
    scenario: Dict[str, Any],
    radius: int = 1,
) -> Dict[str, bool]:
    status_by_objective = compute_objective_status(scenario, radius=radius)
    return {
        key: value.get("status") == "held"
        for key, value in status_by_objective.items()
    }
