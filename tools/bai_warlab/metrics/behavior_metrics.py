from __future__ import annotations

from typing import Any, Dict, Iterable, List


RESERVE_POSTURES = {"HOLD", "REST", "REFIT", "DEFEND"}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_ratio(numerator: float, denominator: float) -> float:
    base = denominator if denominator > 0 else 1.0
    return round(float(numerator) / float(base), 3)


def _sum_strength(units: Iterable[Dict[str, Any]]) -> int:
    return sum(_to_int(unit.get("strength")) for unit in units)


def _objective_hold_metrics(objectives: List[Dict[str, Any]], snapshots: List[Dict[str, Any]]) -> Dict[str, int]:
    allied_hold_turns = 0
    axis_hold_turns = 0
    contested_turns = 0
    for snapshot in snapshots:
        controls = dict(snapshot.get("objective_control") or {})
        for objective in objectives:
            control = controls.get(objective["id"])
            desired_side = objective["side"]
            if control is None:
                contested_turns += 1
            if control == desired_side == "ALLIED":
                allied_hold_turns += 1
            elif control == desired_side == "AXIS":
                axis_hold_turns += 1
    return {
        "objective_hold_turns_allied": allied_hold_turns,
        "objective_hold_turns_axis": axis_hold_turns,
        "contested_objective_turns": contested_turns,
    }


def _reserve_preservation(context: Dict[str, Any]) -> Dict[str, Any]:
    ai_report = dict(context.get("ai_report") or {})
    reserve_level = ai_report.get("reserve_level")
    initial_units = list(context.get("initial_units") or [])
    final_units = list(context.get("final_units") or [])
    battle_history = list(context.get("battle_history") or [])
    contested_locations = {str(battle.get("location_id", "")) for battle in battle_history}

    if reserve_level in (None, ""):
        return {
            "reserve_preservation_available": False,
            "reserve_level": None,
            "reserve_units_identified": 0,
            "reserve_preservation_ratio": None,
        }

    reserve_candidates = [
        unit
        for unit in initial_units
        if str(unit.get("posture", "")).upper() in RESERVE_POSTURES
        and str(unit.get("location_id", "")) not in contested_locations
    ]
    if not reserve_candidates:
        return {
            "reserve_preservation_available": False,
            "reserve_level": reserve_level,
            "reserve_units_identified": 0,
            "reserve_preservation_ratio": None,
        }

    final_by_id = {str(unit.get("id", "")): unit for unit in final_units}
    initial_strength = _sum_strength(reserve_candidates)
    final_strength = sum(_to_int(final_by_id.get(str(unit.get("id", "")), {}).get("strength")) for unit in reserve_candidates)
    return {
        "reserve_preservation_available": True,
        "reserve_level": reserve_level,
        "reserve_units_identified": len(reserve_candidates),
        "reserve_preservation_ratio": _safe_ratio(final_strength, initial_strength),
    }


def compute_behavior_metrics(context: Dict[str, Any]) -> Dict[str, Any]:
    initial_strength = dict(context.get("initial_strength") or {})
    final_strength = dict(context.get("final_strength") or {})
    battle_history = list(context.get("battle_history") or [])
    objectives = list(context.get("objectives") or [])
    snapshots = list(context.get("snapshots") or [])

    allied_losses = max(0, _to_int(initial_strength.get("ALLIED")) - _to_int(final_strength.get("ALLIED")))
    axis_losses = max(0, _to_int(initial_strength.get("AXIS")) - _to_int(final_strength.get("AXIS")))
    failed_attack_count = sum(
        1
        for battle in battle_history
        if battle.get("attacker") == "ALLIED" and not bool(battle.get("attack_success", battle.get("winner") == "ALLIED"))
    )

    metrics = {
        "available": True,
        "allied_casualties": allied_losses,
        "axis_casualties": axis_losses,
        "casualty_ratio_allied": _safe_ratio(axis_losses, allied_losses),
        "casualty_ratio_axis": _safe_ratio(allied_losses, axis_losses),
        "failed_attack_count": failed_attack_count,
    }
    metrics.update(_objective_hold_metrics(objectives, snapshots))
    metrics.update(_reserve_preservation(context))
    return metrics


__all__ = ["compute_behavior_metrics"]
