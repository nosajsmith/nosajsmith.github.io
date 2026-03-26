from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, Mapping


REPORT_CONTAINER_KEYS = (
    "bai_report",
    "ai_report",
    "reasoning",
    "report",
    "ai",
    "bai",
    "decision",
    "summary",
)


def empty_ai_report() -> Dict[str, Any]:
    fields = ("posture", "main_objective", "chosen_operation", "reserve_level", "timing_breakdown")
    return {
        "available": False,
        "posture": None,
        "main_objective": None,
        "chosen_operation": None,
        "reserve_level": None,
        "timing_breakdown": {},
        "missing_fields": list(fields),
    }


def _to_mapping(value: Any) -> Dict[str, Any] | None:
    if value is None:
        return None
    if is_dataclass(value):
        value = asdict(value)
    elif isinstance(value, Mapping):
        value = dict(value)
    elif hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        mapped = value.to_dict()
        if isinstance(mapped, Mapping):
            value = dict(mapped)
        else:
            return None
    elif hasattr(value, "__dict__"):
        value = {key: item for key, item in vars(value).items() if not key.startswith("_")}
    else:
        return None
    return {str(key): item for key, item in value.items()}


def _is_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _iter_candidate_mappings(payloads: Iterable[Any]) -> Iterable[Dict[str, Any]]:
    queue = list(payloads)
    while queue:
        current = queue.pop(0)
        mapping = _to_mapping(current)
        if mapping is None:
            continue
        yield mapping
        for key in REPORT_CONTAINER_KEYS:
            nested = mapping.get(key)
            if isinstance(nested, list):
                queue.extend(nested)
            elif nested is not None:
                queue.append(nested)


def _first_value(candidates: Iterable[Dict[str, Any]], aliases: Iterable[str]) -> Any:
    alias_list = tuple(aliases)
    for mapping in candidates:
        for alias in alias_list:
            value = mapping.get(alias)
            if _is_present(value):
                return value
    return None


def _first_selected_item(candidates: Iterable[Dict[str, Any]], keys: Iterable[str]) -> Any:
    key_list = tuple(keys)
    for mapping in candidates:
        for key in key_list:
            items = mapping.get(key)
            if not isinstance(items, list):
                continue
            selected = []
            for item in items:
                item_mapping = _to_mapping(item)
                if item_mapping is None:
                    continue
                if any(bool(item_mapping.get(flag)) for flag in ("selected", "chosen", "primary", "main")):
                    selected.append(item_mapping)
            if selected:
                return selected[0]
            if items:
                return items[0]
    return None


def _compact_label(value: Any) -> Any:
    if not _is_present(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    mapping = _to_mapping(value)
    if mapping is None:
        return value
    for key in ("name", "id", "label", "title", "objective_id", "operation", "level", "type", "value"):
        candidate = mapping.get(key)
        if _is_present(candidate):
            return candidate
    return mapping


def _normalize_timing_breakdown(value: Any) -> Dict[str, Any]:
    if not _is_present(value):
        return {}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"total": value}
    mapping = _to_mapping(value)
    if mapping is not None:
        return {key: item for key, item in mapping.items() if _is_present(item)}
    return {"raw": value}


def normalize_ai_report(*payloads: Any) -> Dict[str, Any]:
    candidates = list(_iter_candidate_mappings(payloads))
    if not candidates:
        return empty_ai_report()

    posture = _compact_label(
        _first_value(candidates, ("posture", "stance", "selected_posture", "recommended_posture"))
    )
    main_objective = _compact_label(
        _first_value(
            candidates,
            (
                "main_objective",
                "mainObjective",
                "primary_objective",
                "selected_objective",
                "objective",
                "objective_id",
            ),
        )
        or _first_selected_item(candidates, ("objectives", "objective_candidates"))
    )
    chosen_operation = _compact_label(
        _first_value(
            candidates,
            (
                "chosen_operation",
                "chosenOperation",
                "selected_operation",
                "operation",
                "operation_name",
                "main_effort",
            ),
        )
        or _first_selected_item(candidates, ("operations", "operation_options"))
    )
    reserve_level = _compact_label(
        _first_value(
            candidates,
            ("reserve_level", "reserveLevel", "reserve", "reserves", "reserve_commitment"),
        )
    )
    timing_breakdown = _normalize_timing_breakdown(
        _first_value(
            candidates,
            (
                "timing_breakdown",
                "timingBreakdown",
                "timing",
                "timings",
                "timing_ms",
                "duration_ms",
                "latency_ms",
            ),
        )
    )

    missing_fields = []
    if posture is None:
        missing_fields.append("posture")
    if main_objective is None:
        missing_fields.append("main_objective")
    if chosen_operation is None:
        missing_fields.append("chosen_operation")
    if reserve_level is None:
        missing_fields.append("reserve_level")
    if not timing_breakdown:
        missing_fields.append("timing_breakdown")

    available = any(
        value is not None
        for value in (posture, main_objective, chosen_operation, reserve_level)
    ) or bool(timing_breakdown)

    return {
        "available": available,
        "posture": posture,
        "main_objective": main_objective,
        "chosen_operation": chosen_operation,
        "reserve_level": reserve_level,
        "timing_breakdown": timing_breakdown,
        "missing_fields": missing_fields,
    }


capture_ai_report = normalize_ai_report


__all__ = ["capture_ai_report", "empty_ai_report", "normalize_ai_report"]
