from __future__ import annotations

from typing import Any, Dict, Iterable


LOW_SUPPLY_THRESHOLD = 30


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_ratio(numerator: float, denominator: float) -> float:
    base = denominator if denominator > 0 else 1.0
    return round(float(numerator) / float(base), 3)


def _mean_supply(units: Iterable[Dict[str, Any]], side: str) -> float:
    supplies = [_to_int(unit.get("supply")) for unit in units if unit.get("side") == side]
    if not supplies:
        return 0.0
    return round(sum(supplies) / len(supplies), 3)


def compute_logistics_metrics(context: Dict[str, Any]) -> Dict[str, Any]:
    snapshots = list(context.get("snapshots") or [])
    final_units = list(context.get("final_units") or [])

    low_supply_turns_allied = sum(1 for snapshot in snapshots if _to_int(dict(snapshot.get("low_supply_counts") or {}).get("ALLIED")) > 0)
    low_supply_turns_axis = sum(1 for snapshot in snapshots if _to_int(dict(snapshot.get("low_supply_counts") or {}).get("AXIS")) > 0)
    low_supply_unit_turns_allied = sum(_to_int(dict(snapshot.get("low_supply_counts") or {}).get("ALLIED")) for snapshot in snapshots)
    low_supply_unit_turns_axis = sum(_to_int(dict(snapshot.get("low_supply_counts") or {}).get("AXIS")) for snapshot in snapshots)
    total_unit_turns_allied = sum(_to_int(dict(snapshot.get("unit_counts") or {}).get("ALLIED")) for snapshot in snapshots)
    total_unit_turns_axis = sum(_to_int(dict(snapshot.get("unit_counts") or {}).get("AXIS")) for snapshot in snapshots)

    return {
        "available": bool(snapshots),
        "low_supply_threshold": LOW_SUPPLY_THRESHOLD,
        "low_supply_turns_allied": low_supply_turns_allied,
        "low_supply_turns_axis": low_supply_turns_axis,
        "low_supply_unit_turns_allied": low_supply_unit_turns_allied,
        "low_supply_unit_turns_axis": low_supply_unit_turns_axis,
        "low_supply_unit_turn_ratio_allied": _safe_ratio(low_supply_unit_turns_allied, total_unit_turns_allied),
        "low_supply_unit_turn_ratio_axis": _safe_ratio(low_supply_unit_turns_axis, total_unit_turns_axis),
        "average_end_supply_allied": _mean_supply(final_units, "ALLIED"),
        "average_end_supply_axis": _mean_supply(final_units, "AXIS"),
    }


__all__ = ["LOW_SUPPLY_THRESHOLD", "compute_logistics_metrics"]
