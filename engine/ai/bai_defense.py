from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

from .bai_eval import location_strength
from .bai_models import OperationCandidate, StrategicDirective


DEFENSIVE_OPERATION_TYPES = {
    "hold_line",
    "reinforce_sector",
    "withdraw_stronger_terrain",
    "counterattack_local_breach",
}


@dataclass
class DefenseAssessment:
    active: bool = False
    main_objective: str = ""
    fallback_anchor: str | None = None
    collapse_risk: str = "LOW"
    key_terrain_locations: List[str] = field(default_factory=list)
    threatened_locations: List[str] = field(default_factory=list)
    exposed_locations: List[str] = field(default_factory=list)
    encirclement_risk_locations: List[str] = field(default_factory=list)
    counterattack_locations: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def assess_defensive_situation(
    snapshot: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    runtime_profile: Mapping[str, Any] | None,
    profiles: Mapping[str, Mapping[str, Any]],
) -> DefenseAssessment:
    main_objective = str(operation.target_objective or directive.main_objective or "")
    if not _is_defensive_mode(directive, operation):
        return DefenseAssessment(
            active=False,
            main_objective=main_objective,
            rationale="Current directive is not running a defensive behavior pack.",
        )

    side = str(getattr(snapshot, "side", "") or "")
    friendly_units = list(getattr(snapshot, "friendly_units", []) or [])
    enemy_units = list(getattr(snapshot, "enemy_units", []) or [])
    objectives = list(getattr(snapshot, "objectives", []) or [])
    thresholds = dict((runtime_profile or {}).get("thresholds") or {})

    key_terrain_locations = _key_terrain_locations(
        profiles=profiles,
        main_objective=main_objective,
    )
    fallback_anchor = _fallback_anchor(
        profiles=profiles,
        key_terrain_locations=key_terrain_locations,
        main_objective=main_objective,
    )
    threatened_locations = _threatened_locations(
        side=side,
        objectives=objectives,
        profiles=profiles,
        main_objective=main_objective,
    )
    exposed_locations = _exposed_locations(
        profiles=profiles,
        side=side,
        threatened_locations=threatened_locations,
    )
    encirclement_risk_locations = _encirclement_risk_locations(
        profiles=profiles,
        exposed_locations=exposed_locations,
        threatened_locations=threatened_locations,
        fallback_anchor=fallback_anchor,
    )
    counterattack_locations = _counterattack_locations(
        main_objective=main_objective,
        operation=operation,
        profiles=profiles,
        fallback_anchor=fallback_anchor,
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        attack_supply_floor=float(thresholds.get("attack_supply_floor", 45) or 45),
    )
    collapse_risk = _collapse_risk(
        threatened_locations=threatened_locations,
        encirclement_risk_locations=encirclement_risk_locations,
        main_objective=main_objective,
    )
    notes = _notes(
        key_terrain_locations=key_terrain_locations,
        fallback_anchor=fallback_anchor,
        threatened_locations=threatened_locations,
        encirclement_risk_locations=encirclement_risk_locations,
        counterattack_locations=counterattack_locations,
    )

    return DefenseAssessment(
        active=True,
        main_objective=main_objective,
        fallback_anchor=fallback_anchor,
        collapse_risk=collapse_risk,
        key_terrain_locations=key_terrain_locations,
        threatened_locations=threatened_locations,
        exposed_locations=exposed_locations,
        encirclement_risk_locations=encirclement_risk_locations,
        counterattack_locations=counterattack_locations,
        notes=notes,
        rationale=_rationale(
            collapse_risk=collapse_risk,
            fallback_anchor=fallback_anchor,
            threatened_locations=threatened_locations,
            counterattack_locations=counterattack_locations,
        ),
    )


def preferred_defensive_fallback(
    *,
    current_location: str,
    profiles: Mapping[str, Mapping[str, Any]],
    assessment: DefenseAssessment | None,
) -> str:
    if assessment is None or not assessment.active:
        return current_location
    if current_location in assessment.key_terrain_locations and current_location not in assessment.encirclement_risk_locations:
        return current_location
    if (
        assessment.fallback_anchor
        and assessment.fallback_anchor != current_location
        and (
            current_location in assessment.exposed_locations
            or current_location in assessment.encirclement_risk_locations
            or (assessment.collapse_risk == "HIGH" and current_location not in assessment.key_terrain_locations)
        )
    ):
        return str(assessment.fallback_anchor)
    return current_location


def hold_priority_bonus(location: str, assessment: DefenseAssessment | None) -> float:
    if assessment is None or not assessment.active:
        return 0.0
    if location in assessment.key_terrain_locations:
        return 0.14
    if location == assessment.main_objective:
        return 0.08
    return 0.0


def hold_decision_type(location: str, assessment: DefenseAssessment | None) -> str:
    if assessment is not None and assessment.active and location in assessment.key_terrain_locations:
        return "defend_key_terrain"
    return "hold_ground"


def should_shorten_line(
    *,
    current_location: str,
    assessment: DefenseAssessment | None,
) -> bool:
    if assessment is None or not assessment.active:
        return False
    if assessment.fallback_anchor in (None, "", current_location):
        return False
    return current_location in assessment.exposed_locations or current_location in assessment.encirclement_risk_locations


def should_allow_defensive_attack(
    *,
    target_location: str,
    operation: OperationCandidate,
    directive: StrategicDirective,
    assessment: DefenseAssessment | None,
    attack_odds: float,
    attack_odds_threshold: float,
) -> bool:
    if assessment is None or not assessment.active:
        return True
    if directive.posture != "DEFENSIVE" and str(operation.operation_type or "") not in DEFENSIVE_OPERATION_TYPES:
        return True
    if target_location not in assessment.counterattack_locations:
        return False
    extra_margin = 0.0 if str(operation.operation_type or "") == "counterattack_local_breach" else 0.10
    return attack_odds >= attack_odds_threshold + extra_margin


def is_counterattack_location(target_location: str, assessment: DefenseAssessment | None) -> bool:
    return bool(assessment and assessment.active and target_location in assessment.counterattack_locations)


def is_encirclement_risk(location: str, assessment: DefenseAssessment | None) -> bool:
    return bool(assessment and assessment.active and location in assessment.encirclement_risk_locations)


def is_exposed_line(location: str, assessment: DefenseAssessment | None) -> bool:
    return bool(assessment and assessment.active and location in assessment.exposed_locations)


def _is_defensive_mode(directive: StrategicDirective, operation: OperationCandidate) -> bool:
    return str(directive.posture or "").upper().strip() == "DEFENSIVE" or str(operation.operation_type or "") in DEFENSIVE_OPERATION_TYPES


def _key_terrain_locations(
    *,
    profiles: Mapping[str, Mapping[str, Any]],
    main_objective: str,
) -> List[str]:
    ranked = sorted(
        profiles.values(),
        key=lambda profile: (
            float(profile.get("friendly_objective_value", 0.0) or 0.0) * 2.0
            + float(profile.get("terrain_value", 0.0) or 0.0) * 25.0
            + (20.0 if str(profile.get("location_id", "") or "") == main_objective else 0.0)
            + (8.0 if float(profile.get("friendly_strength", 0.0) or 0.0) > 0 else 0.0)
            - float(profile.get("enemy_strength", 0.0) or 0.0) * 0.1,
            str(profile.get("location_id", "") or ""),
        ),
        reverse=True,
    )
    keys = [
        str(profile.get("location_id", "") or "")
        for profile in ranked
        if (
            float(profile.get("friendly_objective_value", 0.0) or 0.0) > 0
            or float(profile.get("terrain_value", 0.0) or 0.0) >= 1.2
            or str(profile.get("location_id", "") or "") == main_objective
        )
    ]
    return [location_id for location_id in keys if location_id][:3]


def _fallback_anchor(
    *,
    profiles: Mapping[str, Mapping[str, Any]],
    key_terrain_locations: Sequence[str],
    main_objective: str,
) -> str | None:
    candidates: List[Mapping[str, Any]] = []
    for location_id in key_terrain_locations:
        profile = profiles.get(location_id)
        if profile is None:
            continue
        if float(profile.get("enemy_strength", 0.0) or 0.0) > 0 and str(profile.get("location_id", "") or "") != main_objective:
            continue
        candidates.append(profile)
    if not candidates:
        candidates = list(profiles.values())
    if not candidates:
        return None
    best = sorted(
        candidates,
        key=lambda profile: (
            float(profile.get("enemy_strength", 0.0) or 0.0) <= 0.0,
            float(profile.get("terrain_value", 0.0) or 0.0),
            float(profile.get("friendly_objective_value", 0.0) or 0.0),
            float(profile.get("friendly_strength", 0.0) or 0.0),
            -float(profile.get("enemy_strength", 0.0) or 0.0),
            str(profile.get("location_id", "") or ""),
        ),
        reverse=True,
    )[0]
    location_id = str(best.get("location_id", "") or "")
    return location_id or None


def _threatened_locations(
    *,
    side: str,
    objectives: Sequence[Mapping[str, Any]],
    profiles: Mapping[str, Mapping[str, Any]],
    main_objective: str,
) -> List[str]:
    threatened: List[str] = []
    for objective in objectives:
        location_id = str(objective.get("location_id", "") or "")
        if not location_id:
            continue
        if str(objective.get("side", "") or "").upper().strip() != side:
            continue
        profile = dict(profiles.get(location_id) or {})
        friendly_strength = float(profile.get("friendly_strength", 0.0) or 0.0)
        enemy_strength = float(profile.get("enemy_strength", 0.0) or 0.0)
        if enemy_strength <= 0:
            continue
        if enemy_strength >= max(1.0, friendly_strength * 0.9) or location_id == main_objective:
            threatened.append(location_id)
    if main_objective and main_objective not in threatened:
        profile = dict(profiles.get(main_objective) or {})
        if float(profile.get("enemy_strength", 0.0) or 0.0) > 0:
            threatened.append(main_objective)
    return sorted(set(threatened))


def _exposed_locations(
    *,
    profiles: Mapping[str, Mapping[str, Any]],
    side: str,
    threatened_locations: Sequence[str],
) -> List[str]:
    exposed: List[str] = []
    threatened_set = set(threatened_locations)
    for location_id, profile in profiles.items():
        friendly_strength = float(profile.get("friendly_strength", 0.0) or 0.0)
        enemy_strength = float(profile.get("enemy_strength", 0.0) or 0.0)
        if friendly_strength <= 0 or enemy_strength <= 0:
            continue
        if location_id in threatened_set:
            continue
        if (
            float(profile.get("terrain_value", 0.0) or 0.0) <= 1.0
            and float(profile.get("friendly_objective_value", 0.0) or 0.0) <= 0.0
            and enemy_strength >= friendly_strength
        ):
            exposed.append(location_id)
    return sorted(set(exposed))


def _encirclement_risk_locations(
    *,
    profiles: Mapping[str, Mapping[str, Any]],
    exposed_locations: Sequence[str],
    threatened_locations: Sequence[str],
    fallback_anchor: str | None,
) -> List[str]:
    if not fallback_anchor:
        return []
    fallback_terrain = float(dict(profiles.get(fallback_anchor) or {}).get("terrain_value", 0.0) or 0.0)
    risks: List[str] = []
    for location_id in sorted(set(exposed_locations) | set(threatened_locations)):
        profile = dict(profiles.get(location_id) or {})
        friendly_strength = float(profile.get("friendly_strength", 0.0) or 0.0)
        enemy_strength = float(profile.get("enemy_strength", 0.0) or 0.0)
        if (
            enemy_strength >= max(1.0, friendly_strength * 1.25)
            and float(profile.get("terrain_value", 0.0) or 0.0) < fallback_terrain
        ):
            risks.append(location_id)
    return sorted(set(risks))


def _counterattack_locations(
    *,
    main_objective: str,
    operation: OperationCandidate,
    profiles: Mapping[str, Mapping[str, Any]],
    fallback_anchor: str | None,
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    attack_supply_floor: float,
) -> List[str]:
    candidates: List[str] = []
    reserve_anchor_strength = location_strength(friendly_units, fallback_anchor or "")
    for location_id, profile in profiles.items():
        enemy_strength = float(profile.get("enemy_strength", 0.0) or 0.0)
        if enemy_strength <= 0:
            continue
        friendly_strength = float(profile.get("friendly_strength", 0.0) or 0.0)
        objective_value = float(profile.get("friendly_objective_value", 0.0) or 0.0)
        avg_local_supply = _average_supply_for_location(friendly_units, location_id)
        effective_strength = friendly_strength + (reserve_anchor_strength * 0.45 if fallback_anchor and fallback_anchor != location_id else 0.0)
        if effective_strength >= enemy_strength * 1.05 and avg_local_supply >= max(30.0, attack_supply_floor - 10.0):
            if location_id == main_objective or objective_value > 0 or str(operation.operation_type or "") == "counterattack_local_breach":
                candidates.append(location_id)
    return sorted(set(candidates))


def _collapse_risk(
    *,
    threatened_locations: Sequence[str],
    encirclement_risk_locations: Sequence[str],
    main_objective: str,
) -> str:
    if len(threatened_locations) >= 2 or len(encirclement_risk_locations) >= 1:
        return "HIGH"
    if threatened_locations or main_objective in threatened_locations:
        return "MEDIUM"
    return "LOW"


def _notes(
    *,
    key_terrain_locations: Sequence[str],
    fallback_anchor: str | None,
    threatened_locations: Sequence[str],
    encirclement_risk_locations: Sequence[str],
    counterattack_locations: Sequence[str],
) -> List[str]:
    notes: List[str] = []
    if key_terrain_locations:
        notes.append(f"Key terrain: {', '.join(key_terrain_locations)}.")
    if fallback_anchor:
        notes.append(f"Fallback anchor: {fallback_anchor}.")
    if threatened_locations:
        notes.append(f"Threatened sectors: {', '.join(threatened_locations)}.")
    if encirclement_risk_locations:
        notes.append(f"Encirclement risk: {', '.join(encirclement_risk_locations)}.")
    if counterattack_locations:
        notes.append(f"Selective counterattack windows: {', '.join(counterattack_locations)}.")
    return notes


def _rationale(
    *,
    collapse_risk: str,
    fallback_anchor: str | None,
    threatened_locations: Sequence[str],
    counterattack_locations: Sequence[str],
) -> str:
    if collapse_risk == "HIGH":
        return (
            f"High collapse risk detected; shorten the line toward {fallback_anchor or 'defensible ground'} "
            f"and only counterattack at {', '.join(counterattack_locations) or 'favorable breach windows'}."
        )
    if threatened_locations:
        return (
            f"Threatened defensive sectors require deliberate defense of key ground around "
            f"{', '.join(threatened_locations)}."
        )
    return "Defensive posture is stable; hold key terrain and preserve a compact line."


def _average_supply_for_location(units: Sequence[Any], location_id: str) -> float:
    local = [
        float(_unit_value(unit, "supply", 0) or 0)
        for unit in units
        if str(_unit_value(unit, "location_id", "") or "") == location_id
    ]
    if not local:
        return 0.0
    return sum(local) / len(local)


def _unit_value(unit: Any, key: str, default: Any = None) -> Any:
    value = unit.get(key, default) if isinstance(unit, Mapping) else getattr(unit, key, default)
    return getattr(value, "value", value)


__all__ = [
    "DefenseAssessment",
    "assess_defensive_situation",
    "hold_decision_type",
    "hold_priority_bonus",
    "is_counterattack_location",
    "is_encirclement_risk",
    "is_exposed_line",
    "preferred_defensive_fallback",
    "should_allow_defensive_attack",
    "should_shorten_line",
]
