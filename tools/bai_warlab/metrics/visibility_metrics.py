from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _unique_strings(values: Iterable[Any]) -> List[str]:
    seen: set[str] = set()
    items: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(text)
    return items


def _authored_pressure_payload(scenario_payload: Dict[str, Any]) -> Dict[str, Any]:
    local_areas = scenario_payload.get("local_pressure_areas")
    if not isinstance(local_areas, list):
        local_areas = []
    labels = _unique_strings(
        (dict(area).get("label") for area in local_areas if isinstance(area, dict))
    )
    reasons = _unique_strings(
        reason
        for area in local_areas
        if isinstance(area, dict)
        for reason in (area.get("pressure_reasons") or [])
    )

    summary = None
    if len(labels) == 1:
        summary = f"Pressure centers on {labels[0]}."
    elif len(labels) == 2:
        summary = f"Pressure spans {labels[0]} and {labels[1]}."
    elif len(labels) > 2:
        summary = f"Pressure spans {labels[0]}, {labels[1]}, and {len(labels) - 2} more sectors."

    return {
        "active": bool(local_areas or reasons),
        "summary": summary,
        "reasons": reasons,
        "details": {
            "areas": labels,
            "count": len(local_areas),
        },
    }


def _hours_elapsed(tick: int, dt_hours: int) -> int:
    return max(0, tick) * max(0, dt_hours)


def _score_reason_by_day(objective_events: List[str]) -> Dict[int, str]:
    reasons: Dict[int, List[str]] = {}
    for event in objective_events:
        text = str(event or "").strip()
        if not text.startswith("Day "):
            continue
        day_token = text.split(":", 1)[0].replace("Day", "").strip()
        try:
            day = int(day_token)
        except Exception:
            continue
        reasons.setdefault(day, []).append(text)
    return {day: " | ".join(messages) for day, messages in reasons.items()}


def compute_score_visibility(context: Dict[str, Any]) -> Dict[str, Any]:
    snapshots = list(context.get("snapshots") or [])
    dt_hours = _to_int(context.get("dt_hours"), 0)
    objective_events = list(context.get("objective_events") or [])
    reasons_by_day = _score_reason_by_day(objective_events)

    timeline: List[Dict[str, Any]] = []
    changes: List[Dict[str, Any]] = []
    previous_allied = 0
    previous_axis = 0

    for index, snapshot in enumerate(snapshots, start=1):
        day = _to_int(snapshot.get("day"))
        allied = _to_int(snapshot.get("vp_allied"))
        axis = _to_int(snapshot.get("vp_axis"))
        margin = allied - axis
        changed = index == 1 or allied != previous_allied or axis != previous_axis
        reason = reasons_by_day.get(day)
        timeline.append(
            {
                "tick": index,
                "day": day,
                "hours_elapsed": _hours_elapsed(index, dt_hours),
                "score_allied": allied,
                "score_axis": axis,
                "score_margin_allied": margin,
                "changed": changed,
                "reason": reason,
            }
        )
        if changed:
            changes.append(
                {
                    "tick": index,
                    "day": day,
                    "hours_elapsed": _hours_elapsed(index, dt_hours),
                    "from_allied": previous_allied,
                    "to_allied": allied,
                    "from_axis": previous_axis,
                    "to_axis": axis,
                    "delta_allied": allied - previous_allied,
                    "delta_axis": axis - previous_axis,
                    "reason": reason,
                }
            )
        previous_allied = allied
        previous_axis = axis

    final = timeline[-1] if timeline else {
        "tick": 0,
        "day": _to_int(context.get("start_day"), 0),
        "hours_elapsed": 0,
        "score_allied": 0,
        "score_axis": 0,
        "score_margin_allied": 0,
        "changed": False,
        "reason": None,
    }
    summaries = [
        (
            f"score changed at T+{item['hours_elapsed']}h because {item['reason']}"
            if item.get("reason")
            else f"score changed at T+{item['hours_elapsed']}h."
        )
        for item in changes
        if item["tick"] > 0 and (item["delta_allied"] or item["delta_axis"])
    ]

    return {
        "available": bool(snapshots),
        "timeline": timeline,
        "changes": changes,
        "final": final,
        "summary_lines": summaries[:5],
    }


def _objective_control_counts(controls: Dict[str, Any]) -> Dict[str, int]:
    allied = sum(1 for value in controls.values() if value == "ALLIED")
    axis = sum(1 for value in controls.values() if value == "AXIS")
    contested = sum(1 for value in controls.values() if value not in {"ALLIED", "AXIS"})
    return {
        "allied_controlled": allied,
        "axis_controlled": axis,
        "contested": contested,
    }


def compute_objective_visibility(context: Dict[str, Any]) -> Dict[str, Any]:
    snapshots = list(context.get("snapshots") or [])
    objectives = list(context.get("objectives") or [])
    dt_hours = _to_int(context.get("dt_hours"), 0)
    objective_meta = {
        str(objective.get("id")): {
            "location_id": str(objective.get("location_id") or ""),
            "side": str(objective.get("side") or ""),
            "description": str(objective.get("description") or ""),
        }
        for objective in objectives
        if isinstance(objective, dict)
    }

    timeline: List[Dict[str, Any]] = []
    changes: List[Dict[str, Any]] = []
    previous_controls: Dict[str, Any] = {}

    for index, snapshot in enumerate(snapshots, start=1):
        controls = dict(snapshot.get("objective_control") or {})
        counts = _objective_control_counts(controls)
        timeline.append(
            {
                "tick": index,
                "day": _to_int(snapshot.get("day")),
                "hours_elapsed": _hours_elapsed(index, dt_hours),
                "controls": controls,
                **counts,
            }
        )
        for objective_id, current_value in controls.items():
            previous_value = previous_controls.get(objective_id)
            if index == 1 or current_value != previous_value:
                meta = objective_meta.get(str(objective_id), {})
                changes.append(
                    {
                        "tick": index,
                        "day": _to_int(snapshot.get("day")),
                        "objective_id": str(objective_id),
                        "location_id": meta.get("location_id", ""),
                        "from": previous_value,
                        "to": current_value,
                        "expected_side": meta.get("side", ""),
                        "description": meta.get("description", ""),
                    }
                )
        previous_controls = controls

    final = timeline[-1] if timeline else {
        "tick": 0,
        "day": _to_int(context.get("start_day"), 0),
        "hours_elapsed": 0,
        "controls": {},
        "allied_controlled": 0,
        "axis_controlled": 0,
        "contested": 0,
    }
    summaries = [
        f"objective control changed for {item['location_id'] or item['objective_id']} to {item['to'] or 'CONTESTED'} at day {item['day']}."
        for item in changes
        if item["tick"] > 0 and item.get("from") != item.get("to")
    ]

    return {
        "available": bool(objectives or snapshots),
        "timeline": timeline,
        "changes": changes,
        "final": final,
        "summary_lines": summaries[:5],
    }


def _pressure_components_for_day(
    *,
    day: int,
    snapshot: Dict[str, Any],
    battle_history: List[Dict[str, Any]],
    authored_pressure: Dict[str, Any],
) -> Tuple[float, Dict[str, Any]]:
    battle_count = sum(1 for battle in battle_history if _to_int(battle.get("day")) == day)
    low_supply_counts = dict(snapshot.get("low_supply_counts") or {})
    low_supply_units = _to_int(low_supply_counts.get("ALLIED")) + _to_int(low_supply_counts.get("AXIS"))
    controls = dict(snapshot.get("objective_control") or {})
    contested_objectives = sum(1 for value in controls.values() if value not in {"ALLIED", "AXIS"})
    authored_pressure_areas = _to_int(dict(authored_pressure.get("details") or {}).get("count"))
    pressure_score = round(
        (battle_count * 2.0)
        + (contested_objectives * 1.5)
        + (low_supply_units * 0.5)
        + float(authored_pressure_areas),
        3,
    )
    details = {
        "battle_count": battle_count,
        "contested_objectives": contested_objectives,
        "low_supply_units": low_supply_units,
        "authored_pressure_areas": authored_pressure_areas,
    }
    return pressure_score, details


def compute_pressure_visibility(context: Dict[str, Any]) -> Dict[str, Any]:
    snapshots = list(context.get("snapshots") or [])
    battle_history = list(context.get("battle_history") or [])
    scenario_payload = dict(context.get("scenario_payload") or {})
    dt_hours = _to_int(context.get("dt_hours"), 0)
    authored_pressure = _authored_pressure_payload(scenario_payload)

    timeline: List[Dict[str, Any]] = []
    for index, snapshot in enumerate(snapshots, start=1):
        day = _to_int(snapshot.get("day"))
        pressure_score, details = _pressure_components_for_day(
            day=day,
            snapshot=snapshot,
            battle_history=battle_history,
            authored_pressure=authored_pressure,
        )
        timeline.append(
            {
                "tick": index,
                "day": day,
                "hours_elapsed": _hours_elapsed(index, dt_hours),
                "pressure_score": pressure_score,
                "active": bool(pressure_score > 0 or authored_pressure.get("active")),
                "summary": authored_pressure.get("summary"),
                "reasons": list(authored_pressure.get("reasons") or []),
                **details,
            }
        )

    peak = max(timeline, key=lambda item: (float(item.get("pressure_score") or 0.0), -int(item.get("tick") or 0)), default=None)
    final = timeline[-1] if timeline else {
        "tick": 0,
        "day": _to_int(context.get("start_day"), 0),
        "hours_elapsed": 0,
        "pressure_score": 0.0,
        "active": authored_pressure.get("active", False),
        "summary": authored_pressure.get("summary"),
        "reasons": list(authored_pressure.get("reasons") or []),
        "battle_count": 0,
        "contested_objectives": 0,
        "low_supply_units": 0,
        "authored_pressure_areas": _to_int(dict(authored_pressure.get("details") or {}).get("count")),
    }
    summaries: List[str] = []
    if peak is not None:
        summaries.append(
            "pressure peak at "
            f"T+{peak['hours_elapsed']}h with score {peak['pressure_score']} "
            f"(battles={peak['battle_count']}, contested={peak['contested_objectives']}, low_supply_units={peak['low_supply_units']})."
        )
    if authored_pressure.get("summary"):
        summaries.append(str(authored_pressure["summary"]))

    return {
        "available": bool(snapshots or authored_pressure.get("active")),
        "derived": True,
        "source": "scenario_authored_plus_runtime_snapshots",
        "timeline": timeline,
        "peak": peak,
        "final": final,
        "authored": authored_pressure,
        "summary_lines": summaries[:5],
    }


def compute_visibility_metrics(context: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        "score_visibility": compute_score_visibility(context),
        "pressure_visibility": compute_pressure_visibility(context),
        "objective_visibility": compute_objective_visibility(context),
    }


__all__ = [
    "compute_objective_visibility",
    "compute_pressure_visibility",
    "compute_score_visibility",
    "compute_visibility_metrics",
]
