from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Mapping


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def to_bai_payload(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)

    if isinstance(value, Mapping):
        payload: Dict[str, Any] = {}
        for key, item in value.items():
            normalized = to_bai_payload(item)
            if _is_empty(normalized):
                continue
            payload[str(key)] = normalized
        return payload

    if isinstance(value, list):
        payload = [to_bai_payload(item) for item in value]
        return [item for item in payload if not _is_empty(item)]

    return value


@dataclass
class StrategicDirective:
    directive_id: str
    side: str = ""
    posture: str = ""
    main_objective: Any = None
    supporting_objectives: List[Any] = field(default_factory=list)
    reserve_policy: str = ""
    desired_end_state: str = ""
    horizon_turns: int | None = None
    operation_window: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(to_bai_payload(self))


@dataclass
class OperationCandidate:
    operation_id: str
    name: str = ""
    operation_type: str = ""
    posture: str = ""
    target_objective: Any = None
    score: float | None = None
    priority: int | None = None
    reserve_level: Any = None
    timing_breakdown: Dict[str, Any] = field(default_factory=dict)
    rationale: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    selected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(to_bai_payload(self))


@dataclass
class TacticalIntent:
    intent_id: str
    unit_id: str
    action: str
    posture: str = ""
    target_location_id: str | None = None
    target_unit_id: str | None = None
    objective_id: str | None = None
    priority: int | None = None
    supporting_unit_ids: List[str] = field(default_factory=list)
    timing: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(to_bai_payload(self))


@dataclass
class UnitOrderWrapper:
    unit_id: str
    action: str
    posture: str = ""
    target_location_id: str | None = None
    target_unit_id: str | None = None
    objective_id: str | None = None
    intent_id: str | None = None
    operation_id: str | None = None
    directive_id: str | None = None
    priority: int | None = None
    source: str = "bai"
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(to_bai_payload(self))


__all__ = [
    "OperationCandidate",
    "StrategicDirective",
    "TacticalIntent",
    "UnitOrderWrapper",
    "to_bai_payload",
]
