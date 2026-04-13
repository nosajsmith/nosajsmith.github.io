from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from ..models import to_plain


def _to_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (str, Path)):
        path = Path(value)
        if path.exists() and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, Mapping):
                return dict(payload)
        return {}
    if hasattr(value, "__dict__") or hasattr(value, "metrics") or hasattr(value, "summary"):
        mapped = to_plain(value)
        if isinstance(mapped, Mapping):
            return dict(mapped)
    return {}


def _scenario_name(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    return str(summary.get("scenario_name") or payload.get("scenario") or "")


def _variant_name(payload: Dict[str, Any]) -> str:
    resolved = dict(payload.get("resolved_profile") or {})
    return (
        str(resolved.get("variant_name") or resolved.get("variant_id") or "").strip()
        or str(payload.get("variant_name") or payload.get("variant_id") or payload.get("variant_label") or "").strip()
        or "variant"
    )


def _metrics(payload: Dict[str, Any], block: str) -> Dict[str, Any]:
    return dict(dict(payload.get("metrics") or {}).get(block) or {})


def _timeline(payload: Dict[str, Any], block: str) -> list[Dict[str, Any]]:
    return list(_metrics(payload, block).get("timeline") or [])


def _objective_controls(entry: Mapping[str, Any]) -> Dict[str, Any]:
    return dict(entry.get("controls") or entry.get("objective_control") or {})


def _scalar_diff(
    *,
    left_payload: Dict[str, Any],
    right_payload: Dict[str, Any],
    phase: str,
    field_path: str,
    field: str,
    tick: int | None,
    day: int | None,
    left_value: Any,
    right_value: Any,
) -> Dict[str, Any]:
    return {
        "comparable": True,
        "identical": False,
        "scenario": _scenario_name(left_payload) or _scenario_name(right_payload),
        "left_variant": _variant_name(left_payload),
        "right_variant": _variant_name(right_payload),
        "tick": tick,
        "day": day,
        "phase": phase,
        "field": field,
        "field_path": field_path,
        "left_value": left_value,
        "right_value": right_value,
    }


def _compare_scalar_timelines(
    *,
    left_payload: Dict[str, Any],
    right_payload: Dict[str, Any],
    block: str,
    phase: str,
    fields: Iterable[str],
) -> Dict[str, Any] | None:
    left_timeline = _timeline(left_payload, block)
    right_timeline = _timeline(right_payload, block)
    if not left_timeline and not right_timeline:
        return None
    if len(left_timeline) != len(right_timeline):
        return _scalar_diff(
            left_payload=left_payload,
            right_payload=right_payload,
            phase=phase,
            field_path=f"metrics.{block}.timeline_length",
            field="timeline_length",
            tick=None,
            day=None,
            left_value=len(left_timeline),
            right_value=len(right_timeline),
        )

    for index, (left_entry, right_entry) in enumerate(zip(left_timeline, right_timeline), start=1):
        for field in fields:
            left_value = left_entry.get(field)
            right_value = right_entry.get(field)
            if left_value != right_value:
                return _scalar_diff(
                    left_payload=left_payload,
                    right_payload=right_payload,
                    phase=phase,
                    field_path=f"metrics.{block}.timeline[{index - 1}].{field}",
                    field=field,
                    tick=int(left_entry.get("tick") or right_entry.get("tick") or index),
                    day=int(left_entry.get("day") or right_entry.get("day") or 0),
                    left_value=left_value,
                    right_value=right_value,
                )
    return None


def _compare_objective_timeline(left_payload: Dict[str, Any], right_payload: Dict[str, Any]) -> Dict[str, Any] | None:
    left_timeline = _timeline(left_payload, "objective_visibility")
    right_timeline = _timeline(right_payload, "objective_visibility")
    if not left_timeline and not right_timeline:
        return None
    if len(left_timeline) != len(right_timeline):
        return _scalar_diff(
            left_payload=left_payload,
            right_payload=right_payload,
            phase="objective",
            field_path="metrics.objective_visibility.timeline_length",
            field="timeline_length",
            tick=None,
            day=None,
            left_value=len(left_timeline),
            right_value=len(right_timeline),
        )

    for index, (left_entry, right_entry) in enumerate(zip(left_timeline, right_timeline), start=1):
        left_controls = _objective_controls(left_entry)
        right_controls = _objective_controls(right_entry)
        objective_ids = sorted(set(left_controls) | set(right_controls))
        for objective_id in objective_ids:
            left_value = left_controls.get(objective_id)
            right_value = right_controls.get(objective_id)
            if left_value != right_value:
                return _scalar_diff(
                    left_payload=left_payload,
                    right_payload=right_payload,
                    phase="objective",
                    field_path=f"metrics.objective_visibility.timeline[{index - 1}].controls.{objective_id}",
                    field=f"objective_control:{objective_id}",
                    tick=int(left_entry.get("tick") or right_entry.get("tick") or index),
                    day=int(left_entry.get("day") or right_entry.get("day") or 0),
                    left_value=left_value,
                    right_value=right_value,
                )
    return None


def find_first_divergence(left: Any, right: Any) -> Dict[str, Any]:
    left_payload = _to_mapping(left)
    right_payload = _to_mapping(right)
    if not left_payload or not right_payload:
        return {
            "comparable": False,
            "identical": False,
            "reason": "Missing or unreadable War Lab payload.",
            "left_variant": _variant_name(left_payload),
            "right_variant": _variant_name(right_payload),
        }

    for block, phase, fields in (
        ("score_visibility", "score", ("score_allied", "score_axis", "score_margin_allied")),
        ("pressure_visibility", "pressure", ("pressure_score", "battle_count", "contested_objectives", "low_supply_units")),
    ):
        divergence = _compare_scalar_timelines(
            left_payload=left_payload,
            right_payload=right_payload,
            block=block,
            phase=phase,
            fields=fields,
        )
        if divergence is not None:
            return divergence

    objective_divergence = _compare_objective_timeline(left_payload, right_payload)
    if objective_divergence is not None:
        return objective_divergence

    left_summary = dict(left_payload.get("summary") or {})
    right_summary = dict(right_payload.get("summary") or {})
    for field in ("result", "winning_side", "final_score_margin", "final_pressure_score"):
        if left_summary.get(field) != right_summary.get(field):
            return _scalar_diff(
                left_payload=left_payload,
                right_payload=right_payload,
                phase="summary",
                field_path=f"summary.{field}",
                field=field,
                tick=None,
                day=None,
                left_value=left_summary.get(field),
                right_value=right_summary.get(field),
            )

    return {
        "comparable": True,
        "identical": True,
        "scenario": _scenario_name(left_payload) or _scenario_name(right_payload),
        "left_variant": _variant_name(left_payload),
        "right_variant": _variant_name(right_payload),
    }


def render_first_divergence(divergence: Mapping[str, Any]) -> str:
    payload = dict(divergence or {})
    if not payload.get("comparable"):
        return f"First divergence unavailable: {payload.get('reason') or 'incomparable payloads'}"
    if payload.get("identical"):
        return "Runs are identical across score, pressure, objective, and final summary fields."

    lines = [
        f"first differing {payload.get('phase')} field: {payload.get('field')}",
        f"left: {payload.get('left_value')}",
        f"right: {payload.get('right_value')}",
    ]
    if payload.get("day") is not None:
        lines.insert(0, f"first divergence at day {payload.get('day')}")
    elif payload.get("tick") is not None:
        lines.insert(0, f"first divergence at tick {payload.get('tick')}")
    return "\n".join(lines)


__all__ = ["find_first_divergence", "render_first_divergence"]
