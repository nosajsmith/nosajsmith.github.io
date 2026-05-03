from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

from server.objectives.control_v1 import compute_objective_state, compute_objective_status
from server.politics.clock_v2 import compute_supply_aware_objective_pressure


VIEW_SNAPSHOT_CONTRACT = "view.snapshot"
VIEW_SNAPSHOT_VERSION = 1


def _object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _canonical_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower().removesuffix(".json")).strip("_")


def _unique_strings(values: Iterable[Any]) -> List[str]:
    seen: set[str] = set()
    rows: List[str] = []
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


def merge_weather_payload(engine_weather: Any, authored_weather: Any) -> Dict[str, Any] | None:
    authored = _object(authored_weather)
    authored_condition = authored.get("condition")
    condition = (
        authored_condition
        if isinstance(authored_condition, str) and authored_condition.strip()
        else engine_weather
    )
    if not condition and not authored:
        return None
    payload = dict(authored)
    if condition:
        payload["condition"] = str(condition)
    return payload


def merge_live_units(live_units: List[Any], authored_units: List[Any]) -> List[Dict[str, Any]]:
    authored_by_id = {
        str(unit.get("id") or unit.get("unit_id") or unit.get("name") or ""): unit
        for unit in authored_units
        if isinstance(unit, dict)
    }
    merged: List[Dict[str, Any]] = []
    for unit in live_units:
        row = _object(unit)
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


def authored_pressure_payload(authored: Mapping[str, Any]) -> Dict[str, Any]:
    local_areas = _list(authored.get("local_pressure_areas"))
    area_labels = _unique_strings(_object(area).get("label") for area in local_areas)
    reasons = _unique_strings(
        reason
        for area in local_areas
        for reason in (_object(area).get("pressure_reasons") or [])
    )

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


def _objective_key(side: str, location_id: str) -> str:
    return f"{side}:{location_id}"


def _state_from_truth(status: str, controller_side: Any) -> str:
    if status == "contested":
        return "contested"
    if status == "held" and controller_side:
        return f"held_{str(controller_side).lower()}"
    return "unheld"


def _snapshot_scenario(authored: Mapping[str, Any], units: List[Dict[str, Any]]) -> Dict[str, Any]:
    scenario = dict(authored)
    scenario["units"] = units
    scenario["objectives"] = _list(authored.get("objectives"))
    return scenario


def _objectives_with_truth(
    authored_objectives: List[Any],
    objective_status: Dict[str, Dict[str, Any]],
    objective_pressure: Dict[str, Any],
) -> List[Dict[str, Any]]:
    pressure_by_objective = _object(objective_pressure.get("by_objective"))
    rows: List[Dict[str, Any]] = []
    for index, objective in enumerate(authored_objectives):
        if not isinstance(objective, dict):
            continue
        side = str(objective.get("side", "")).upper().strip()
        location_id = str(objective.get("location_id", "")).upper().strip()
        key = _objective_key(side, location_id) if side and location_id else ""
        truth = _object(objective_status.get(key))
        pressure = _object(pressure_by_objective.get(key))
        status = str(truth.get("status") or "unknown")
        controller_side = truth.get("controller_side")

        row = dict(objective)
        if "id" not in row or not row.get("id"):
            row["id"] = key or f"objective_{index + 1}"
        row["authored_state"] = objective.get("state")
        row["state"] = _state_from_truth(status, controller_side)
        row["truth_state"] = status
        row["objective_status"] = status
        row["controller_side"] = controller_side
        row["held"] = status == "held"
        row["contested"] = status == "contested"
        row["objective_truth_key"] = key
        row["pressure_state"] = pressure.get("pressure_state", "none")
        row["pressure_score"] = pressure.get("pressure_score", 0.0)
        row["pressure"] = {
            "state": pressure.get("pressure_state", "none"),
            "score": pressure.get("pressure_score", 0.0),
            "nearby_unit_count": pressure.get("nearby_unit_count", 0),
            "contributing_unit_count": pressure.get("contributing_unit_count", 0),
            "low_supply_unit_count": pressure.get("low_supply_unit_count", 0),
            "suppressed_unit_count": pressure.get("suppressed_unit_count", 0),
        }
        rows.append(row)
    return rows


def _report_title(log: Mapping[str, Any]) -> str:
    src = str(log.get("src") or "").strip()
    phase = str(log.get("phase") or "").strip()
    if src and phase:
        return f"{src} {phase}"
    return src or phase or "Status"


def reports_from_logs(logs: Iterable[Any], *, limit: int = 8) -> Dict[str, Any]:
    rows = [dict(log) for log in logs if isinstance(log, dict)]
    recent = []
    for index, log in enumerate(rows[-limit:]):
        recent.append(
            {
                "id": f"log-{max(0, len(rows) - limit) + index + 1}",
                "kind": str(log.get("phase") or "status"),
                "title": _report_title(log),
                "summary": str(log.get("message") or "Operational update."),
                "severity": "info",
                "time": log.get("turn"),
                "sender_label": str(log.get("src") or "ENGINE"),
            }
        )
    return {"pending_count": None, "recent": recent}


def _ai_picture(game_ai: Mapping[str, Any], bai_report: Mapping[str, Any]) -> Dict[str, Any]:
    ai = dict(game_ai)
    chosen_operation = _object(bai_report.get("chosen_operation"))
    last_intent = chosen_operation.get("name")
    if not last_intent and bai_report.get("main_objective"):
        last_intent = str(bai_report.get("main_objective"))
    ai.setdefault("last_intent", last_intent)
    return ai


def _read_first(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    reports = _object(snapshot.get("reports"))
    recent = _list(reports.get("recent"))
    objectives = _list(snapshot.get("objectives"))
    pressure = _object(snapshot.get("pressure"))
    time = _object(snapshot.get("time"))
    campaign = _object(snapshot.get("campaign"))
    scenario = _object(snapshot.get("scenario"))
    return {
        "scenario": scenario.get("name") or scenario.get("id"),
        "turn": time.get("turn"),
        "phase": time.get("phase"),
        "campaign_status": campaign.get("status"),
        "key_objective": _object(objectives[0]).get("name") if objectives else None,
        "pressure_summary": pressure.get("summary"),
        "latest_report": _object(recent[-1]).get("title") if recent else None,
    }


def build_view_snapshot(
    *,
    scenario_id: str | None,
    scenario_name: str | None,
    authored_scenario: Mapping[str, Any],
    engine_state: Mapping[str, Any],
    engine_logs: Iterable[Any] = (),
) -> Dict[str, Any]:
    game = _object(engine_state.get("game"))
    game_time = _object(game.get("time"))
    authored = _object(authored_scenario)
    authored_units = _list(authored.get("units"))
    live_units = _list(engine_state.get("units"))
    merged_units = merge_live_units(live_units, authored_units)
    snapshot_scenario = _snapshot_scenario(authored, merged_units)
    objective_status = compute_objective_status(snapshot_scenario)
    objective_state = compute_objective_state(snapshot_scenario)
    objective_pressure = compute_supply_aware_objective_pressure(
        snapshot_scenario,
        objective_status,
    )
    authored_pressure = authored_pressure_payload(authored)
    day_value = int(game_time.get("day") or 1)
    bai_report = _object(engine_state.get("bai_report"))
    score_by_side = _object(game.get("vp"))
    campaign = {
        "status": "active",
        "score_by_side": score_by_side,
        "win_score": None,
    }
    time = {
        "turn": int(game_time.get("turn") or day_value),
        "day": day_value,
        "current_hours": max(0, (day_value - 1) * 24),
        "time_remaining_hours": None,
        "phase": game_time.get("phase"),
    }
    pressure = {
        **authored_pressure,
        "active": bool(authored_pressure.get("active") or objective_pressure.get("total_pressure_score", 0) > 0),
        "objective_pressure": objective_pressure,
        "by_objective": objective_pressure.get("by_objective", {}),
        "total_pressure_score": objective_pressure.get("total_pressure_score", 0.0),
        "semantics": objective_pressure.get("semantics"),
    }

    snapshot: Dict[str, Any] = {
        "contract": {
            "id": VIEW_SNAPSHOT_CONTRACT,
            "version": VIEW_SNAPSHOT_VERSION,
            "source": "backend_read_model",
        },
        "scenario": {
            "id": authored.get("id") or scenario_id or _canonical_id(game.get("scenario")),
            "name": authored.get("name") or game.get("scenario") or scenario_name,
            "theater_id": authored.get("theater_id"),
            "map_package": authored.get("map_package"),
        },
        "operation": {
            "id": authored.get("id") or scenario_id,
            "name": authored.get("name") or scenario_name or game.get("scenario"),
            "theater_id": authored.get("theater_id"),
        },
        "time": time,
        "weather": merge_weather_payload(game_time.get("weather"), authored.get("weather")),
        "campaign": campaign,
        "score": {
            "score_by_side": score_by_side,
            "win_score": campaign["win_score"],
        },
        "objective_truth": objective_status,
        "objective_state": objective_state,
        "pressure": pressure,
        "reports": reports_from_logs(engine_logs),
        "staff": {
            "summary": _object(authored.get("grease_board")).get("staff_notes"),
        },
        "ai": _ai_picture(_object(game.get("ai")), bai_report),
        "bai_report": bai_report,
        "grease_board": authored.get("grease_board"),
        "map_presentation": authored.get("map_presentation"),
        "local_pressure_areas": authored.get("local_pressure_areas") or [],
        "named_features": authored.get("named_features") or [],
        "airfields": authored.get("airfields") or [],
        "ports": authored.get("ports") or [],
        "naval_support_windows": authored.get("naval_support_windows") or [],
        "objectives": _objectives_with_truth(
            _list(authored.get("objectives")),
            objective_status,
            objective_pressure,
        ),
        "units": merged_units,
        "logs": list(engine_logs),
        "capabilities": {
            "can_save_snapshot": False,
            "can_load_snapshot": False,
            "can_export_replay": False,
        },
    }
    snapshot["read_first"] = _read_first(snapshot)
    return snapshot


__all__ = [
    "VIEW_SNAPSHOT_CONTRACT",
    "VIEW_SNAPSHOT_VERSION",
    "build_view_snapshot",
    "merge_live_units",
    "merge_weather_payload",
    "reports_from_logs",
]
