from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .bai_eval import location_strength
from .bai_models import OperationCandidate, StrategicDirective


GROUND_EXCLUDED_TYPES = {"AIR", "NAVAL"}


@dataclass
class ReservePlan:
    target_fraction: float
    target_count: int
    held_count: int
    available_ground_units: int
    reserve_level: str
    commitment_state: str
    held_reserve_ids: List[str] = field(default_factory=list)
    committed_reserve_ids: List[str] = field(default_factory=list)
    candidate_reserve_ids: List[str] = field(default_factory=list)
    triggers: Dict[str, bool] = field(default_factory=dict)
    rationale: str = ""
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def plan_reserves(
    snapshot: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    runtime_profile: Mapping[str, Any] | None,
    *,
    default_fraction: float = 0.25,
    minimum_reserve_units: int = 1,
) -> ReservePlan:
    thresholds = dict((runtime_profile or {}).get("thresholds") or {})
    friendly_units = [unit for unit in list(getattr(snapshot, "friendly_units", []) or []) if _is_ground_unit(unit)]
    enemy_units = [unit for unit in list(getattr(snapshot, "enemy_units", []) or []) if _is_ground_unit(unit)]
    objectives = list(getattr(snapshot, "objectives", []) or [])
    side = str(getattr(snapshot, "side", "") or "")
    main_objective = str(operation.target_objective or directive.main_objective or "")

    if len(friendly_units) <= 1:
        return ReservePlan(
            target_fraction=0.0,
            target_count=0,
            held_count=0,
            available_ground_units=len(friendly_units),
            reserve_level="NONE",
            commitment_state="NO_RESERVE_AVAILABLE",
            rationale="Insufficient ground units to hold a separate reserve.",
        )

    target_fraction = float(
        (directive.metadata or {}).get(
            "reserve_fraction",
            thresholds.get("reserve_target_fraction", default_fraction),
        )
        or default_fraction
    )
    target_fraction = _clamp(target_fraction, 0.10, 0.60, default_fraction)

    target_count = int(round(len(friendly_units) * target_fraction))
    target_count = max(int(minimum_reserve_units), target_count)
    target_count = min(target_count, max(0, len(friendly_units) - 1))

    sorted_units = _sort_units(friendly_units)
    candidate_reserve_ids = [_unit_id(unit) for unit in sorted_units[:target_count]]

    objective_is_critical = _objective_is_critical(
        side=side,
        main_objective=main_objective,
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        objectives=objectives,
    )
    line_is_collapsing = _line_is_collapsing(
        side=side,
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        objectives=objectives,
    )
    counterattack_window = _counterattack_window_is_favorable(
        main_objective=main_objective,
        operation=operation,
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        runtime_profile=runtime_profile,
    )

    triggers = {
        "objective_critical": objective_is_critical,
        "line_collapsing": line_is_collapsing,
        "counterattack_window": counterattack_window,
    }

    release_count = _reserve_release_count(
        reserve_count=target_count,
        unit_count=len(friendly_units),
        triggers=triggers,
    )
    held_count = max(0, target_count - release_count)

    committed_reserve_ids = candidate_reserve_ids[:release_count]
    held_reserve_ids = candidate_reserve_ids[release_count:target_count]

    if line_is_collapsing:
        commitment_state = "EMERGENCY_COMMIT"
        rationale = (
            f"Line collapse indicators forced reserve commitment: released {release_count} of "
            f"{target_count} reserve units to stabilize threatened positions."
        )
    elif counterattack_window:
        commitment_state = "COUNTERATTACK_COMMIT"
        rationale = (
            f"Counterattack window is favorable near {main_objective or 'the breach'}, so {release_count} "
            f"reserve unit(s) were released for exploitation."
        )
    elif objective_is_critical:
        commitment_state = "CRITICAL_OBJECTIVE_COMMIT"
        rationale = (
            f"Main objective {main_objective or 'CURRENT_LINE'} is critical, so {release_count} reserve "
            f"unit(s) were committed while {held_count} remained back."
        )
    else:
        commitment_state = "HOLDING_RESERVE"
        rationale = (
            f"Holding {held_count} reserve unit(s) out of {len(friendly_units)} ground units to preserve "
            f"a target reserve fraction of {target_fraction:.2f}."
        )

    return ReservePlan(
        target_fraction=round(target_fraction, 3),
        target_count=target_count,
        held_count=held_count,
        available_ground_units=len(friendly_units),
        reserve_level=_reserve_level(held_count, len(friendly_units)),
        commitment_state=commitment_state,
        held_reserve_ids=held_reserve_ids,
        committed_reserve_ids=committed_reserve_ids,
        candidate_reserve_ids=candidate_reserve_ids,
        triggers=triggers,
        rationale=rationale,
    )


def _objective_is_critical(
    *,
    side: str,
    main_objective: str,
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    objectives: Sequence[Mapping[str, Any]],
) -> bool:
    if not main_objective:
        return False
    objective_value = _objective_value_for_location(objectives, main_objective, side_filter=side)
    enemy_strength = location_strength(enemy_units, main_objective)
    friendly_strength = location_strength(friendly_units, main_objective)
    objective_contested = enemy_strength > 0 and friendly_strength > 0
    objective_overmatched = enemy_strength > max(1.0, friendly_strength * 1.05)
    objective_exposed = objective_value >= 60.0 and enemy_strength >= max(1.0, friendly_strength * 0.90)
    return objective_contested and (objective_overmatched or objective_exposed)


def _line_is_collapsing(
    *,
    side: str,
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    objectives: Sequence[Mapping[str, Any]],
) -> bool:
    own_objective_locations = sorted(
        {
            str(objective.get("location_id", "") or "")
            for objective in objectives
            if str(objective.get("side", "") or "").upper().strip() == side and str(objective.get("location_id", "") or "")
        }
    )
    if not own_objective_locations:
        return False

    collapsing_count = 0
    for location_id in own_objective_locations:
        friendly_strength = location_strength(friendly_units, location_id)
        enemy_strength = location_strength(enemy_units, location_id)
        if enemy_strength <= 0:
            continue
        if friendly_strength <= 0 or enemy_strength > max(1.0, friendly_strength * 1.25):
            collapsing_count += 1
    return collapsing_count > 1


def _counterattack_window_is_favorable(
    *,
    main_objective: str,
    operation: OperationCandidate,
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    runtime_profile: Mapping[str, Any] | None,
) -> bool:
    thresholds = dict((runtime_profile or {}).get("thresholds") or {})
    if str(operation.operation_type or "") != "counterattack_local_breach":
        return False
    if not main_objective:
        return False

    friendly_strength = location_strength(friendly_units, main_objective)
    enemy_strength = location_strength(enemy_units, main_objective)
    reserve_strength = sum(
        float(_unit_value(unit, "strength", 0) or 0)
        for unit in _sort_units(
            unit for unit in friendly_units if str(_unit_value(unit, "location_id", "") or "") != main_objective
        )[:2]
    )
    effective_friendly_strength = friendly_strength + (reserve_strength * 0.65)
    if effective_friendly_strength <= 0 or enemy_strength <= 0:
        return False

    avg_supply = _average_units(friendly_units, "supply", 50)
    avg_readiness = _average_units(friendly_units, "readiness", 50)
    supply_floor = float(thresholds.get("attack_supply_floor", 45) or 45)
    readiness_floor = float(thresholds.get("attack_readiness_floor", 45) or 45)
    force_ratio = effective_friendly_strength / max(1.0, enemy_strength)

    return force_ratio >= 1.15 and avg_supply >= max(30.0, supply_floor - 10.0) and avg_readiness >= max(30.0, readiness_floor - 10.0)


def _reserve_release_count(
    *,
    reserve_count: int,
    unit_count: int,
    triggers: Mapping[str, bool],
) -> int:
    if reserve_count <= 0:
        return 0
    if triggers.get("line_collapsing"):
        keep_back = 0 if unit_count <= 3 else 1
        return max(1, reserve_count - keep_back)
    if triggers.get("counterattack_window"):
        return max(1, reserve_count // 2 or 1)
    if triggers.get("objective_critical"):
        return max(1, min(reserve_count, (reserve_count + 1) // 2))
    return 0


def _reserve_level(reserve_count: int, total_units: int) -> str:
    if total_units <= 0 or reserve_count <= 0:
        return "NONE"
    ratio = reserve_count / total_units
    if ratio >= 0.4:
        return "HIGH"
    if ratio >= 0.2:
        return "MEDIUM"
    return "LOW"


def _objective_value_for_location(
    objectives: Sequence[Mapping[str, Any]],
    location_id: str,
    *,
    side_filter: str | None,
) -> float:
    total = 0.0
    for objective in objectives:
        if str(objective.get("location_id", "") or "") != str(location_id or ""):
            continue
        objective_side = str(objective.get("side", "") or "").upper().strip()
        if side_filter is not None and objective_side != str(side_filter).upper().strip():
            continue
        total += float(objective.get("value", 0) or 0)
    return round(total, 3)


def _average_units(units: Sequence[Any], field_name: str, default: int) -> float:
    if not units:
        return float(default)
    return sum(float(_unit_value(unit, field_name, default) or default) for unit in units) / len(units)


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


def _clamp(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = default
    return max(minimum, min(maximum, numeric))


def _unit_value(unit: Any, key: str, default: Any = None) -> Any:
    value = unit.get(key, default) if isinstance(unit, Mapping) else getattr(unit, key, default)
    return getattr(value, "value", value)


def _unit_id(unit: Any) -> str:
    return str(_unit_value(unit, "id", "") or "")


def _unit_type(unit: Any) -> str:
    return str(_unit_value(unit, "unit_type", "") or "").upper().strip()


def _is_ground_unit(unit: Any) -> bool:
    return _unit_type(unit) not in GROUND_EXCLUDED_TYPES


__all__ = ["ReservePlan", "plan_reserves"]
