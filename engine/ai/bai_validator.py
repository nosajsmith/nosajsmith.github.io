from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence


LEGAL_POSTURES = {"HOLD", "MOVE", "ATTACK", "DEFEND", "REST", "REFIT"}
LEGAL_ORDER_TYPES = {"move"}


@dataclass
class OrderValidationContext:
    friendly_ids: set[str] = field(default_factory=set)
    current_locations: Dict[str, str] = field(default_factory=dict)
    known_locations: List[str] = field(default_factory=list)
    fallback_unit_id: str = ""
    fallback_location: str = ""

    @classmethod
    def from_snapshot(cls, snapshot: Any) -> "OrderValidationContext":
        friendly_units = list(getattr(snapshot, "friendly_units", []) or [])
        current_locations = {
            _unit_value(unit, "id", ""): _unit_value(unit, "location_id", "")
            for unit in friendly_units
            if _unit_value(unit, "id", "")
        }
        fallback_unit = _sort_units(friendly_units)[0] if friendly_units else None
        return cls(
            friendly_ids={unit_id for unit_id in current_locations if unit_id},
            current_locations=current_locations,
            known_locations=list(getattr(snapshot, "known_locations", []) or []),
            fallback_unit_id=_unit_value(fallback_unit, "id", "") if fallback_unit is not None else "",
            fallback_location=_unit_value(fallback_unit, "location_id", "") if fallback_unit is not None else "",
        )


@dataclass
class OrderValidationResult:
    orders: List[Dict[str, Any]] = field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def validate_orders(
    orders: Sequence[Mapping[str, Any]] | Sequence[Any],
    context: OrderValidationContext,
) -> OrderValidationResult:
    valid_locations = set(str(location) for location in context.known_locations if str(location))
    accepted_signatures: Dict[str, tuple[str, str]] = {}
    validated: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []

    for raw_order in orders:
        if not isinstance(raw_order, Mapping) or _is_empty_action(raw_order):
            diagnostics.append(
                {
                    "level": "warn",
                    "code": "order.empty_action",
                    "message": "Dropped empty or malformed action object.",
                }
            )
            continue

        order_type = str(raw_order.get("type", "move") or "move").strip().lower()
        if order_type not in LEGAL_ORDER_TYPES:
            diagnostics.append(
                {
                    "level": "warn",
                    "code": "order.unsupported_type",
                    "message": f"Dropped unsupported order type {order_type or '<empty>'}.",
                }
            )
            continue

        unit_id = str(raw_order.get("unit_id", "") or "").strip()
        if unit_id not in context.friendly_ids:
            diagnostics.append(
                {
                    "level": "warn",
                    "code": "order.unknown_or_wrong_side_unit",
                    "message": f"Dropped order for non-friendly unit {unit_id}.",
                }
            )
            continue

        target = str(raw_order.get("target", "") or "").strip() or context.current_locations.get(unit_id, "")
        if target not in valid_locations:
            diagnostics.append(
                {
                    "level": "warn",
                    "code": "order.unknown_target",
                    "message": f"Dropped order for {unit_id} with unknown target {target}.",
                }
            )
            continue

        posture = str(raw_order.get("posture", "HOLD") or "HOLD").upper().strip()
        if posture not in LEGAL_POSTURES:
            diagnostics.append(
                {
                    "level": "warn",
                    "code": "order.invalid_posture",
                    "message": f"Normalized invalid posture for {unit_id} to HOLD.",
                }
            )
            posture = "HOLD"

        signature = (target, posture)
        existing = accepted_signatures.get(unit_id)
        if existing is not None:
            code = "order.duplicate_redundant" if existing == signature else "order.conflicting_duplicate"
            message = (
                f"Dropped duplicate order for {unit_id}."
                if existing == signature
                else f"Dropped conflicting duplicate order for {unit_id}; kept the first validated order."
            )
            diagnostics.append({"level": "warn", "code": code, "message": message})
            continue

        accepted_signatures[unit_id] = signature
        validated.append(
            {
                "type": "move",
                "unit_id": unit_id,
                "target": target,
                "posture": posture,
            }
        )

    if not validated and context.fallback_unit_id and context.fallback_location:
        validated.append(
            {
                "type": "move",
                "unit_id": context.fallback_unit_id,
                "target": context.fallback_location,
                "posture": "HOLD",
            }
        )
        diagnostics.append(
            {
                "level": "warn",
                "code": "order.fallback_hold_generated",
                "message": f"Generated fallback HOLD order for {context.fallback_unit_id}.",
            }
        )

    return OrderValidationResult(orders=validated, diagnostics=diagnostics)


def _is_empty_action(order: Mapping[str, Any]) -> bool:
    keys = ("type", "unit_id", "target", "posture", "action")
    return not any(str(order.get(key, "") or "").strip() for key in keys)


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _unit_value(unit: Any, key: str, default: Any = None) -> Any:
    value = _get_value(unit, key, default)
    return getattr(value, "value", value)


def _sort_units(units: Iterable[Any]) -> List[Any]:
    return sorted(
        list(units),
        key=lambda unit: (
            -float(_unit_value(unit, "readiness", 0) or 0),
            -float(_unit_value(unit, "supply", 0) or 0),
            -float(_unit_value(unit, "strength", 0) or 0),
            str(_unit_value(unit, "id", "")),
        ),
    )


__all__ = [
    "LEGAL_ORDER_TYPES",
    "LEGAL_POSTURES",
    "OrderValidationContext",
    "OrderValidationResult",
    "validate_orders",
]
