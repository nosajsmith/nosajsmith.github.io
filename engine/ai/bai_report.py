from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping


@dataclass
class BAIReport:
    posture: str | None = None
    main_objective: Any = None
    chosen_operation: str | None = None
    reserve_level: Any = None
    timing_breakdown: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if self.posture is not None:
            payload["posture"] = self.posture
        if self.main_objective is not None:
            payload["main_objective"] = self.main_objective
        if self.chosen_operation is not None:
            payload["chosen_operation"] = self.chosen_operation
        if self.reserve_level is not None:
            payload["reserve_level"] = self.reserve_level
        if self.timing_breakdown:
            payload["timing_breakdown"] = dict(self.timing_breakdown)
        if self.extra:
            payload.update(dict(self.extra))
        return payload


def _coerce_report(report: BAIReport | Mapping[str, Any] | None) -> Dict[str, Any]:
    if report is None:
        return {}
    if isinstance(report, BAIReport):
        return report.to_dict()
    return {str(key): value for key, value in dict(report).items()}


def build_bai_report(
    *,
    posture: str | None = None,
    main_objective: Any = None,
    chosen_operation: str | None = None,
    reserve_level: Any = None,
    timing_breakdown: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    report = BAIReport(
        posture=posture,
        main_objective=main_objective,
        chosen_operation=chosen_operation,
        reserve_level=reserve_level,
        timing_breakdown=dict(timing_breakdown or {}),
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
