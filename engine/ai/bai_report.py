from __future__ import annotations

from dataclasses import dataclass, field, is_dataclass
from typing import Any, Dict, Iterable, Mapping, MutableMapping

from .bai_models import OperationCandidate, StrategicDirective, TacticalIntent, UnitOrderWrapper, to_bai_payload


ATTACK_ACTIONS = {"attack", "strike", "counterattack"}
HOLD_ACTIONS = {
    "hold",
    "defend",
    "delay",
    "withdraw",
    "reserve",
    "reserve_hold",
    "safe_harbor",
    "escort",
    "cap",
    "loiter",
    "refit",
    "rest",
    "shorten_line",
}


@dataclass
class BAIReport:
    posture: str | None = None
    main_objective: Any = None
    chosen_operation: str | OperationCandidate | Mapping[str, Any] | None = None
    reserve_level: Any = None
    timing_breakdown: Dict[str, Any] = field(default_factory=dict)
    strategic_directive: StrategicDirective | Mapping[str, Any] | None = None
    tactical_intents: list[TacticalIntent | Mapping[str, Any]] = field(default_factory=list)
    unit_orders: list[UnitOrderWrapper | Mapping[str, Any]] = field(default_factory=list)
    attack_reason_summaries: list[str] = field(default_factory=list)
    hold_reason_summaries: list[str] = field(default_factory=list)
    summary_lines: list[str] = field(default_factory=list)
    report_version: str = "bai_report_v1"
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        chosen_operation = _to_payload(self.chosen_operation)
        main_objective = _to_payload(self.main_objective)
        strategic_directive = _to_payload(self.strategic_directive)
        tactical_intents = [_to_payload(item) for item in self.tactical_intents]
        unit_orders = [_to_payload(item) for item in self.unit_orders]
        reserve_level = _resolve_reserve_level(self.reserve_level, chosen_operation, self.extra)
        attack_reason_summaries, hold_reason_summaries = _resolve_reason_summaries(
            explicit_attack=self.attack_reason_summaries,
            explicit_hold=self.hold_reason_summaries,
            tactical_intents=tactical_intents,
            unit_orders=unit_orders,
            chosen_operation=chosen_operation,
            posture=self.posture,
            reserve_level=reserve_level,
            main_objective=main_objective,
        )
        summary_lines = _resolve_summary_lines(
            explicit=self.summary_lines,
            posture=self.posture,
            main_objective=main_objective,
            chosen_operation=chosen_operation,
            reserve_level=reserve_level,
            timing_breakdown=self.timing_breakdown,
            attack_reason_summaries=attack_reason_summaries,
            hold_reason_summaries=hold_reason_summaries,
        )
        payload: Dict[str, Any] = {
            "report_version": self.report_version,
            "posture": self.posture,
            "main_objective": main_objective,
            "chosen_operation": chosen_operation,
            "reserve_level": reserve_level,
            "timing_breakdown": dict(self.timing_breakdown),
            "strategic_directive": strategic_directive,
            "tactical_intents": tactical_intents,
            "unit_orders": unit_orders,
            "attack_reason_summaries": attack_reason_summaries,
            "hold_reason_summaries": hold_reason_summaries,
            "summary_lines": summary_lines,
        }
        normalized = dict(to_bai_payload(payload))
        if self.extra:
            normalized.update(dict(to_bai_payload(dict(self.extra))))
        normalized["report_version"] = self.report_version or "bai_report_v1"
        normalized["posture"] = self.posture
        normalized["main_objective"] = main_objective
        normalized["chosen_operation"] = chosen_operation
        normalized["reserve_level"] = reserve_level
        normalized["timing_breakdown"] = dict(self.timing_breakdown)
        normalized["attack_reason_summaries"] = list(attack_reason_summaries)
        normalized["hold_reason_summaries"] = list(hold_reason_summaries)
        normalized["summary_lines"] = list(summary_lines)
        return normalized


def _coerce_report(report: BAIReport | Mapping[str, Any] | None) -> Dict[str, Any]:
    if report is None:
        return {}
    if isinstance(report, BAIReport):
        return report.to_dict()
    return dict(to_bai_payload(dict(report)))


def _coerce_sequence(items: Iterable[Any] | None) -> list[Any]:
    return list(items or [])


def _to_payload(value: Any) -> Any:
    if value is None:
        return None
    return to_bai_payload(value)


def _to_mapping(value: Any) -> Dict[str, Any] | None:
    if value is None:
        return None
    if is_dataclass(value):
        value = _to_payload(value)
    if isinstance(value, Mapping):
        return {str(key): item for key, item in dict(value).items()}
    if hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        mapped = value.to_dict()
        if isinstance(mapped, Mapping):
            return {str(key): item for key, item in dict(mapped).items()}
    return None


def _is_present(value: Any) -> bool:
    return value not in (None, "", [], {})


def _first_present(mapping: Mapping[str, Any] | None, *keys: str) -> Any:
    if not isinstance(mapping, Mapping):
        return None
    for key in keys:
        value = mapping.get(key)
        if _is_present(value):
            return value
    return None


def _compact_label(value: Any) -> str:
    if not _is_present(value):
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    mapping = _to_mapping(value)
    if mapping is None:
        return str(value)
    for key in (
        "name",
        "id",
        "label",
        "title",
        "main_objective",
        "objective_id",
        "target_objective",
        "target_location_id",
        "location_id",
        "operation_id",
        "value",
    ):
        candidate = mapping.get(key)
        if _is_present(candidate):
            return str(candidate)
    return str(mapping)


def _normalize_reason_text(value: Any) -> str:
    if not _is_present(value):
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, list):
        parts = [_normalize_reason_text(item) for item in value]
        return "; ".join(part for part in parts if part)
    return _compact_label(value)


def _extract_reason(mapping: Mapping[str, Any]) -> str:
    metadata = _to_mapping(mapping.get("metadata")) or {}
    evaluation = _to_mapping(metadata.get("evaluation")) or {}
    for candidate in (
        mapping.get("rationale"),
        mapping.get("notes"),
        metadata.get("summary"),
        metadata.get("rationale"),
        metadata.get("reason"),
        evaluation.get("dominant_reason"),
        evaluation.get("reasons"),
    ):
        text = _normalize_reason_text(candidate)
        if text:
            return text
    return ""


def _classify_reason_bucket(mapping: Mapping[str, Any]) -> str | None:
    metadata = _to_mapping(mapping.get("metadata")) or {}
    action = str(_first_present(mapping, "action", "type") or "").strip().lower()
    posture = str(mapping.get("posture") or "").strip().upper()
    decision_type = str(metadata.get("decision_type") or "").strip().lower()

    if action in ATTACK_ACTIONS or decision_type in ATTACK_ACTIONS or posture == "ATTACK":
        return "attack"
    if action in HOLD_ACTIONS or decision_type in HOLD_ACTIONS or posture in {"DEFEND", "HOLD", "REST", "REFIT"}:
        return "hold"
    return None


def _format_reason_summary(mapping: Mapping[str, Any], *, bucket: str) -> str:
    actor = _compact_label(_first_present(mapping, "unit_id", "intent_id"))
    action = str(_first_present(mapping, "action", "type") or bucket).replace("_", " ").strip()
    target = _compact_label(
        _first_present(mapping, "target_location_id", "target_unit_id", "objective_id")
    )
    reason = _extract_reason(mapping)

    parts = [part for part in (actor, action, target) if part]
    prefix = " ".join(parts).strip()
    if reason and prefix:
        return f"{prefix}: {reason}"
    if reason:
        return reason
    return prefix


def _dedupe_keep_order(items: Iterable[str], *, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        text = " ".join(str(item).split()).strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def _fallback_attack_reasons(
    chosen_operation: Any,
    posture: str | None,
    main_objective: Any,
) -> list[str]:
    operation_mapping = _to_mapping(chosen_operation) or {}
    operation_name = _compact_label(chosen_operation)
    operation_reasons = operation_mapping.get("rationale")
    if isinstance(operation_reasons, list):
        summaries = [
            f"{operation_name}: {_normalize_reason_text(reason)}" if operation_name else _normalize_reason_text(reason)
            for reason in operation_reasons
            if _normalize_reason_text(reason)
        ]
        if summaries:
            return _dedupe_keep_order(summaries)

    if str(posture or "").upper() == "OFFENSIVE":
        objective_label = _compact_label(main_objective) or "the primary objective"
        name = operation_name or "Primary operation"
        return [f"{name} concentrates force against {objective_label}."]
    return []


def _fallback_hold_reasons(
    posture: str | None,
    reserve_level: Any,
    chosen_operation: Any,
) -> list[str]:
    summaries: list[str] = []
    posture_value = str(posture or "").upper()
    operation_name = _compact_label(chosen_operation)
    if posture_value in {"DEFENSIVE", "CONTAIN"}:
        summaries.append(f"Posture {posture_value} prioritizes preserving key terrain and delaying losses.")
    if _is_present(reserve_level):
        summaries.append(f"Reserve posture maintained at {_compact_label(reserve_level)}.")
    if not summaries and operation_name:
        summaries.append(f"{operation_name} emphasizes line stability over opportunistic attacks.")
    return _dedupe_keep_order(summaries)


def _resolve_reason_summaries(
    *,
    explicit_attack: Iterable[str] | None,
    explicit_hold: Iterable[str] | None,
    tactical_intents: Iterable[Any],
    unit_orders: Iterable[Any],
    chosen_operation: Any,
    posture: str | None,
    reserve_level: Any,
    main_objective: Any,
) -> tuple[list[str], list[str]]:
    attack = _dedupe_keep_order(explicit_attack or [])
    hold = _dedupe_keep_order(explicit_hold or [])

    if attack and hold:
        return attack, hold

    candidates = [*_coerce_sequence(tactical_intents), *_coerce_sequence(unit_orders)]
    for item in candidates:
        mapping = _to_mapping(item)
        if mapping is None:
            continue
        bucket = _classify_reason_bucket(mapping)
        if bucket == "attack" and not attack:
            attack = _dedupe_keep_order([*attack, _format_reason_summary(mapping, bucket="attack")])
        elif bucket == "hold" and not hold:
            hold = _dedupe_keep_order([*hold, _format_reason_summary(mapping, bucket="hold")])
        if attack and hold:
            break

    if not attack:
        attack = _fallback_attack_reasons(chosen_operation, posture, main_objective)
    if not hold:
        hold = _fallback_hold_reasons(posture, reserve_level, chosen_operation)
    return attack, hold


def _format_timing_summary(timing_breakdown: Mapping[str, Any] | None) -> str:
    if not timing_breakdown:
        return "Timing: unavailable"
    parts: list[str] = []
    for key in sorted(timing_breakdown):
        value = timing_breakdown.get(key)
        if not _is_present(value):
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            suffix = "" if str(key).endswith("_ms") else "ms"
            parts.append(f"{key}={value}{suffix}")
        else:
            parts.append(f"{key}={value}")
        if len(parts) >= 4:
            break
    if not parts:
        return "Timing: unavailable"
    return "Timing: " + ", ".join(parts)


def _resolve_summary_lines(
    *,
    explicit: Iterable[str] | None,
    posture: str | None,
    main_objective: Any,
    chosen_operation: Any,
    reserve_level: Any,
    timing_breakdown: Mapping[str, Any] | None,
    attack_reason_summaries: Iterable[str],
    hold_reason_summaries: Iterable[str],
) -> list[str]:
    summaries = _dedupe_keep_order(explicit or [], limit=6)
    if summaries:
        return summaries

    lines = [
        f"Posture: {_compact_label(posture) or 'UNSPECIFIED'}",
        f"Main objective: {_compact_label(main_objective) or 'UNSPECIFIED'}",
        f"Chosen operation: {_compact_label(chosen_operation) or 'UNSPECIFIED'}",
        f"Reserve level: {_compact_label(reserve_level) or 'UNKNOWN'}",
    ]
    attack = list(attack_reason_summaries)
    hold = list(hold_reason_summaries)
    if attack:
        lines.append(f"Attack rationale: {attack[0]}")
    if hold:
        lines.append(f"Hold rationale: {hold[0]}")
    lines.append(_format_timing_summary(timing_breakdown))
    return _dedupe_keep_order(lines, limit=7)


def _resolve_reserve_level(
    reserve_level: Any,
    chosen_operation: Any,
    extra: Mapping[str, Any] | None,
) -> Any:
    if _is_present(reserve_level):
        return reserve_level
    operation_mapping = _to_mapping(chosen_operation) or {}
    operation_reserve = operation_mapping.get("reserve_level")
    if _is_present(operation_reserve):
        return operation_reserve
    extra_mapping = dict(extra or {})
    reserve_plan = _to_mapping(extra_mapping.get("reserve_plan")) or {}
    extra_reserve = reserve_plan.get("reserve_level")
    if _is_present(extra_reserve):
        return extra_reserve
    return reserve_level


def build_bai_report(
    *,
    posture: str | None = None,
    main_objective: Any = None,
    chosen_operation: str | OperationCandidate | Mapping[str, Any] | None = None,
    reserve_level: Any = None,
    timing_breakdown: Mapping[str, Any] | None = None,
    strategic_directive: StrategicDirective | Mapping[str, Any] | None = None,
    tactical_intents: Iterable[TacticalIntent | Mapping[str, Any]] | None = None,
    unit_orders: Iterable[UnitOrderWrapper | Mapping[str, Any]] | None = None,
    attack_reason_summaries: Iterable[str] | None = None,
    hold_reason_summaries: Iterable[str] | None = None,
    summary_lines: Iterable[str] | None = None,
    report_version: str = "bai_report_v1",
    extra: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    report = BAIReport(
        posture=posture,
        main_objective=main_objective,
        chosen_operation=chosen_operation,
        reserve_level=reserve_level,
        timing_breakdown=dict(timing_breakdown or {}),
        strategic_directive=strategic_directive,
        tactical_intents=_coerce_sequence(tactical_intents),
        unit_orders=_coerce_sequence(unit_orders),
        attack_reason_summaries=_coerce_sequence(attack_reason_summaries),
        hold_reason_summaries=_coerce_sequence(hold_reason_summaries),
        summary_lines=_coerce_sequence(summary_lines),
        report_version=report_version,
        extra=dict(extra or {}),
    )
    return {"bai_report": report.to_dict()}


def attach_bai_report(
    payload: MutableMapping[str, Any],
    report: BAIReport | Mapping[str, Any] | None,
) -> MutableMapping[str, Any]:
    payload["bai_report"] = _coerce_report(report)
    return payload


__all__ = ["BAIReport", "attach_bai_report", "build_bai_report"]
