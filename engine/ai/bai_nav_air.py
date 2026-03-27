from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .bai_eval import (
    EvaluationScore,
    build_evaluation,
    doctrinal_bias_component,
    enemy_threat_component,
    force_ratio_component,
    location_strength,
    objective_value_component,
    supply_feasibility_component,
    terrain_value_component,
    terrain_value_for_location,
)
from .bai_models import OperationCandidate, StrategicDirective, TacticalIntent, UnitOrderWrapper


AIR_TYPE = "AIR"
NAVAL_TYPE = "NAVAL"


@dataclass
class NavAirDecision:
    unit_id: str
    current_location: str
    target_location: str
    action: str
    posture: str
    priority_score: float
    rationale: str
    evaluation: EvaluationScore
    decision_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["evaluation"] = self.evaluation.to_dict()
        return payload


@dataclass
class NavAirSupportPlan:
    orders: List[Dict[str, Any]] = field(default_factory=list)
    intents: List[TacticalIntent] = field(default_factory=list)
    wrapped_orders: List[UnitOrderWrapper] = field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "orders": list(self.orders),
            "intents": [intent.to_dict() for intent in self.intents],
            "wrapped_orders": [wrapped.to_dict() for wrapped in self.wrapped_orders],
            "diagnostics": [dict(item) for item in self.diagnostics],
        }


def plan_nav_air_support(
    snapshot: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    runtime_profile: Mapping[str, Any] | None,
) -> NavAirSupportPlan:
    side = str(getattr(snapshot, "side", "") or "")
    known_locations = list(getattr(snapshot, "known_locations", []) or [])
    game_map = getattr(snapshot, "game_map", None)
    objectives = list(getattr(snapshot, "objectives", []) or [])
    supply_sources = list(getattr(snapshot, "supply_sources", []) or [])
    friendly_units = list(getattr(snapshot, "friendly_units", []) or [])
    enemy_units = list(getattr(snapshot, "enemy_units", []) or [])
    support_units = [unit for unit in friendly_units if _unit_type(unit) in {AIR_TYPE, NAVAL_TYPE}]

    if not support_units:
        return NavAirSupportPlan()

    profiles = _build_location_profiles(
        known_locations=known_locations,
        game_map=game_map,
        side=side,
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        objectives=objectives,
        supply_sources=supply_sources,
    )
    decisions = [
        _choose_support_decision(
            unit=unit,
            directive=directive,
            operation=operation,
            profiles=profiles,
            runtime_profile=runtime_profile,
        )
        for unit in _sort_support_units(support_units)
    ]

    intents: List[TacticalIntent] = []
    wrapped_orders: List[UnitOrderWrapper] = []
    orders: List[Dict[str, Any]] = []

    for priority, decision in enumerate(decisions, start=1):
        intent = TacticalIntent(
            intent_id=f"intent_{decision.unit_id}_{getattr(snapshot, 'day', 1)}_{decision.decision_type}",
            unit_id=decision.unit_id,
            action=decision.action,
            posture=decision.posture,
            target_location_id=decision.target_location,
            objective_id=str(directive.main_objective or decision.target_location),
            priority=priority,
            rationale=decision.rationale,
            metadata={
                "evaluation": decision.evaluation.to_dict(),
                "decision_type": decision.decision_type,
                "support_domain": _decision_domain(decision.unit_id, support_units),
                **dict(decision.metadata or {}),
            },
        )
        intents.append(intent)

        wrapped_orders.append(
            UnitOrderWrapper(
                unit_id=decision.unit_id,
                action=decision.action,
                posture=decision.posture,
                target_location_id=decision.target_location,
                objective_id=str(directive.main_objective or decision.target_location),
                intent_id=intent.intent_id,
                operation_id=operation.operation_id,
                directive_id=directive.directive_id,
                priority=priority,
                notes=f"Support {decision.decision_type}.",
                metadata={
                    "evaluation": decision.evaluation.to_dict(),
                    "decision_type": decision.decision_type,
                    **dict(decision.metadata or {}),
                },
            )
        )

        orders.append(
            {
                "type": "move",
                "unit_id": decision.unit_id,
                "target": decision.target_location,
                "posture": decision.posture,
            }
        )

    return NavAirSupportPlan(orders=orders, intents=intents, wrapped_orders=wrapped_orders)


def _choose_support_decision(
    *,
    unit: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    profiles: Mapping[str, Dict[str, Any]],
    runtime_profile: Mapping[str, Any] | None,
) -> NavAirDecision:
    unit_kind = _unit_type(unit)
    if unit_kind == AIR_TYPE:
        return _choose_air_decision(unit=unit, directive=directive, operation=operation, profiles=profiles, runtime_profile=runtime_profile)
    return _choose_naval_decision(unit=unit, directive=directive, operation=operation, profiles=profiles, runtime_profile=runtime_profile)


def _choose_air_decision(
    *,
    unit: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    profiles: Mapping[str, Dict[str, Any]],
    runtime_profile: Mapping[str, Any] | None,
) -> NavAirDecision:
    strike_target = _best_exposed_strike_target(unit=unit, profiles=profiles, runtime_profile=runtime_profile, prefer_objective=True)
    cap_asset = _best_cap_asset(profiles)
    safe_airfield = _best_airfield(profiles)

    if _should_air_strike(unit=unit, strike_target=strike_target, directive=directive, operation=operation, runtime_profile=runtime_profile):
        return _strike_decision(unit=unit, target_profile=strike_target, runtime_profile=runtime_profile, domain="air")
    if cap_asset is not None:
        return _cap_decision(unit=unit, asset_profile=cap_asset, runtime_profile=runtime_profile)
    if safe_airfield is not None:
        return _loiter_decision(unit=unit, target_profile=safe_airfield, runtime_profile=runtime_profile, decision_type="air_loiter")
    return _loiter_decision(unit=unit, target_profile=_profile_for_location(profiles, _unit_location(unit)), runtime_profile=runtime_profile, decision_type="air_loiter")


def _choose_naval_decision(
    *,
    unit: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    profiles: Mapping[str, Dict[str, Any]],
    runtime_profile: Mapping[str, Any] | None,
) -> NavAirDecision:
    strike_target = _best_exposed_strike_target(unit=unit, profiles=profiles, runtime_profile=runtime_profile, prefer_objective=False)
    escort_anchor = _best_convoy_anchor(profiles)
    safe_harbor = _best_safe_harbor(unit=unit, profiles=profiles)

    if _should_naval_strike(unit=unit, strike_target=strike_target, directive=directive, operation=operation, runtime_profile=runtime_profile):
        return _strike_decision(unit=unit, target_profile=strike_target, runtime_profile=runtime_profile, domain="naval")
    if escort_anchor is not None:
        return _escort_decision(unit=unit, anchor_profile=escort_anchor, runtime_profile=runtime_profile)
    if safe_harbor is not None:
        return _safe_harbor_decision(unit=unit, harbor_profile=safe_harbor, runtime_profile=runtime_profile)
    return _loiter_decision(unit=unit, target_profile=_profile_for_location(profiles, _unit_location(unit)), runtime_profile=runtime_profile, decision_type="naval_loiter")


def _strike_decision(
    *,
    unit: Any,
    target_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
    domain: str,
) -> NavAirDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    weights = dict((runtime_profile or {}).get("weights") or {})
    location_id = str(target_profile.get("location_id", "") or "")
    enemy_strength = float(target_profile.get("enemy_strength", 0.0) or 0.0)
    evaluation = build_evaluation(
        f"{domain}_strike::{_unit_id(unit)}",
        base=0.10,
        components=[
            objective_value_component(
                float(target_profile.get("enemy_objective_value", target_profile.get("objective_value", 0.0)) or 0.0),
                weight=0.24 * float(weights.get("enemy_objective", 1.0)),
                label=f"High-value target at {location_id}",
            ),
            terrain_value_component(
                target_profile.get("game_map"),
                location_id,
                weight=-0.06,
                label="Terrain resistance to the strike",
            ),
            force_ratio_component(
                _support_attack_power(unit),
                enemy_strength,
                weight=0.26,
                label=f"{domain.title()} strike ratio at {location_id}",
            ),
            supply_feasibility_component(
                min(_unit_supply(unit), _unit_readiness(unit)),
                floor=40.0,
                weight=0.16,
                label=f"{domain.title()} readiness for strike",
            ),
            enemy_threat_component(
                enemy_strength,
                _unit_strength(unit),
                contested=True,
                weight=-0.12 if domain == "air" else -0.20,
                label="Threat at the strike target",
            ),
            doctrinal_bias_component(
                max(float(axis.get("aggression", 0.5) or 0.5), float(weights.get("risk_acceptance", 1.0) or 1.0) / 2.0),
                weight=0.14,
                label=f"Doctrinal support for {domain} strike",
            ),
        ],
    )
    return NavAirDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=location_id,
        action="strike",
        posture="ATTACK",
        priority_score=evaluation.total,
        rationale=f"{domain.title()} strike on {location_id}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type=f"{domain}_strike",
        metadata={"strike_target": location_id},
    )


def _cap_decision(
    *,
    unit: Any,
    asset_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
) -> NavAirDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    location_id = str(asset_profile.get("location_id", "") or "")
    evaluation = build_evaluation(
        f"air_cap::{_unit_id(unit)}",
        base=0.12,
        components=[
            objective_value_component(
                float(asset_profile.get("friendly_objective_value", asset_profile.get("objective_value", 0.0)) or 0.0),
                weight=0.22,
                label=f"Friendly asset value at {location_id}",
            ),
            supply_feasibility_component(
                _unit_supply(unit),
                floor=35.0,
                weight=0.12,
                label="Air support endurance",
            ),
            enemy_threat_component(
                float(asset_profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=bool(asset_profile.get("enemy_strength", 0.0)),
                weight=0.20,
                label="Threat to the protected asset",
            ),
            doctrinal_bias_component(
                axis.get("caution_bias", 0.5),
                weight=0.10,
                label="Doctrinal support for CAP",
            ),
        ],
    )
    return NavAirDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=location_id,
        action="cap",
        posture="DEFEND",
        priority_score=evaluation.total,
        rationale=f"Provide CAP over {location_id}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="cap",
    )


def _escort_decision(
    *,
    unit: Any,
    anchor_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
) -> NavAirDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    location_id = str(anchor_profile.get("location_id", "") or "")
    evaluation = build_evaluation(
        f"naval_escort::{_unit_id(unit)}",
        base=0.12,
        components=[
            objective_value_component(
                float(anchor_profile.get("friendly_supply", 0.0) or 0.0) + float(anchor_profile.get("friendly_objective_value", 0.0) or 0.0),
                weight=0.22,
                label=f"Convoy/port value at {location_id}",
            ),
            terrain_value_component(
                anchor_profile.get("game_map"),
                location_id,
                weight=0.10,
                label="Escort anchor terrain",
            ),
            enemy_threat_component(
                float(anchor_profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=bool(anchor_profile.get("enemy_strength", 0.0)),
                weight=0.14,
                label="Threat to the convoy anchor",
            ),
            doctrinal_bias_component(
                axis.get("logistics_emphasis", 0.5),
                weight=0.18,
                label="Doctrinal support for escort duty",
            ),
        ],
    )
    return NavAirDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=location_id,
        action="escort",
        posture="DEFEND",
        priority_score=evaluation.total,
        rationale=f"Escort convoy and sea lines near {location_id}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="escort",
    )


def _safe_harbor_decision(
    *,
    unit: Any,
    harbor_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
) -> NavAirDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    location_id = str(harbor_profile.get("location_id", "") or "")
    evaluation = build_evaluation(
        f"naval_safe_harbor::{_unit_id(unit)}",
        base=0.14,
        components=[
            terrain_value_component(
                harbor_profile.get("game_map"),
                location_id,
                weight=0.10,
                label="Port safety and shelter",
            ),
            enemy_threat_component(
                float(harbor_profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=False,
                weight=-0.16,
                label="Threat avoided by safe harbor",
            ),
            doctrinal_bias_component(
                axis.get("caution_bias", 0.5),
                weight=0.16,
                label="Doctrinal support for preserving naval assets",
            ),
        ],
    )
    return NavAirDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=location_id,
        action="safe_harbor",
        posture="DEFEND",
        priority_score=evaluation.total,
        rationale=f"Keep major naval elements clear of danger at {location_id}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="safe_harbor",
    )


def _loiter_decision(
    *,
    unit: Any,
    target_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
    decision_type: str,
) -> NavAirDecision:
    location_id = str(target_profile.get("location_id", "") or _unit_location(unit))
    evaluation = build_evaluation(
        f"{decision_type}::{_unit_id(unit)}",
        base=0.04,
        components=[
            supply_feasibility_component(
                _unit_supply(unit),
                floor=35.0,
                weight=0.08,
                label="Support unit sustainability",
            ),
        ],
    )
    return NavAirDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=location_id,
        action="hold",
        posture="HOLD",
        priority_score=evaluation.total,
        rationale=f"Loiter at {location_id} until a better support mission appears.",
        evaluation=evaluation,
        decision_type=decision_type,
    )


def _should_air_strike(
    *,
    unit: Any,
    strike_target: Mapping[str, Any] | None,
    directive: StrategicDirective,
    operation: OperationCandidate,
    runtime_profile: Mapping[str, Any] | None,
) -> bool:
    if not strike_target:
        return False
    if float(strike_target.get("enemy_strength", 0.0) or 0.0) <= 0:
        return False
    aggression = float(dict((runtime_profile or {}).get("axis") or {}).get("aggression", 0.5) or 0.5)
    odds = _support_attack_odds(unit, float(strike_target.get("enemy_strength", 0.0) or 0.0))
    offensive = directive.posture == "OFFENSIVE" or operation.operation_type in {"attack_objective", "counterattack_local_breach"}
    return offensive and odds >= max(0.95, 1.15 - (aggression * 0.25))


def _should_naval_strike(
    *,
    unit: Any,
    strike_target: Mapping[str, Any] | None,
    directive: StrategicDirective,
    operation: OperationCandidate,
    runtime_profile: Mapping[str, Any] | None,
) -> bool:
    if not strike_target:
        return False
    enemy_strength = float(strike_target.get("enemy_strength", 0.0) or 0.0)
    if enemy_strength <= 0:
        return False
    odds = _support_attack_odds(unit, enemy_strength)
    if _is_major_naval(unit) and enemy_strength > _support_attack_power(unit) * 0.75:
        return False
    offensive = directive.posture == "OFFENSIVE" or operation.operation_type in {"attack_objective", "counterattack_local_breach"}
    return offensive and odds >= 1.10


def _best_cap_asset(profiles: Mapping[str, Dict[str, Any]]) -> Mapping[str, Any] | None:
    candidates = [
        profile
        for profile in profiles.values()
        if profile.get("friendly_objective_value", 0.0) > 0
        or profile.get("friendly_supply", 0.0) > 0
        or profile.get("is_airfield")
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda profile: (
            float(profile.get("friendly_objective_value", 0.0) or 0.0)
            + float(profile.get("friendly_supply", 0.0) or 0.0)
            + (25.0 if profile.get("is_airfield") else 0.0)
            + (15.0 if profile.get("is_port") else 0.0)
            + (float(profile.get("enemy_strength", 0.0) or 0.0) * 0.35),
            profile.get("location_id", ""),
        ),
        reverse=True,
    )[0]


def _best_convoy_anchor(profiles: Mapping[str, Dict[str, Any]]) -> Mapping[str, Any] | None:
    candidates = [
        profile
        for profile in profiles.values()
        if profile.get("friendly_supply", 0.0) > 0 or profile.get("is_port")
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda profile: (
            float(profile.get("friendly_supply", 0.0) or 0.0)
            + (20.0 if profile.get("is_port") else 0.0)
            + float(profile.get("friendly_objective_value", 0.0) or 0.0)
            + (float(profile.get("enemy_strength", 0.0) or 0.0) * 0.30),
            profile.get("location_id", ""),
        ),
        reverse=True,
    )[0]


def _best_airfield(profiles: Mapping[str, Dict[str, Any]]) -> Mapping[str, Any] | None:
    candidates = [profile for profile in profiles.values() if profile.get("is_airfield")]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda profile: (
            float(profile.get("friendly_objective_value", 0.0) or 0.0)
            + float(profile.get("friendly_supply", 0.0) or 0.0)
            - float(profile.get("enemy_strength", 0.0) or 0.0),
            profile.get("location_id", ""),
        ),
        reverse=True,
    )[0]


def _best_safe_harbor(unit: Any, profiles: Mapping[str, Dict[str, Any]]) -> Mapping[str, Any] | None:
    candidates = [profile for profile in profiles.values() if profile.get("is_port") or profile.get("friendly_supply", 0.0) > 0]
    if not candidates:
        return _profile_for_location(profiles, _unit_location(unit))
    return sorted(
        candidates,
        key=lambda profile: (
            (20.0 if profile.get("is_port") else 0.0)
            + float(profile.get("friendly_supply", 0.0) or 0.0)
            - (float(profile.get("enemy_strength", 0.0) or 0.0) * 0.50)
            + float(profile.get("terrain_value", 0.0) or 0.0),
            profile.get("location_id", ""),
        ),
        reverse=True,
    )[0]


def _best_exposed_strike_target(
    *,
    unit: Any,
    profiles: Mapping[str, Dict[str, Any]],
    runtime_profile: Mapping[str, Any] | None,
    prefer_objective: bool,
) -> Mapping[str, Any] | None:
    candidates = []
    for profile in profiles.values():
        enemy_strength = float(profile.get("enemy_strength", 0.0) or 0.0)
        enemy_value = float(profile.get("enemy_objective_value", 0.0) or 0.0)
        if enemy_strength <= 0 and enemy_value <= 0:
            continue
        attack_odds = _support_attack_odds(unit, enemy_strength)
        exposure = attack_odds - 0.9
        score = (
            enemy_value * (1.3 if prefer_objective else 1.0)
            + float(profile.get("enemy_supply", 0.0) or 0.0) * 2.0
            + (18.0 if profile.get("is_airfield") else 0.0)
            + (14.0 if profile.get("is_port") else 0.0)
            + (exposure * 25.0)
            - (enemy_strength * (0.20 if _unit_type(unit) == AIR_TYPE else 0.30))
        )
        if attack_odds < 0.9:
            continue
        candidates.append((score, profile))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1].get("location_id", "")), reverse=True)
    return candidates[0][1]


def _build_location_profiles(
    *,
    known_locations: Sequence[str],
    game_map: Any,
    side: str,
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    objectives: Sequence[Mapping[str, Any]],
    supply_sources: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    profiles: Dict[str, Dict[str, Any]] = {}
    for location_id in sorted(set(str(location) for location in known_locations)):
        tile = _tile_for_location(game_map, location_id)
        friendly_strength = location_strength(friendly_units, location_id)
        enemy_strength = location_strength(enemy_units, location_id)
        friendly_objective_value = _objective_value_for_location(objectives, location_id, side_filter=side)
        enemy_objective_value = _objective_value_for_location(objectives, location_id, side_filter=None) - friendly_objective_value
        friendly_supply = _supply_value_for_location(supply_sources, location_id, side_filter=side)
        enemy_supply = _supply_value_for_location(supply_sources, location_id, side_filter=None) - friendly_supply
        profiles[location_id] = {
            "location_id": location_id,
            "game_map": game_map,
            "tile": tile,
            "friendly_strength": friendly_strength,
            "enemy_strength": enemy_strength,
            "friendly_objective_value": friendly_objective_value,
            "enemy_objective_value": max(0.0, enemy_objective_value),
            "objective_value": friendly_objective_value + max(0.0, enemy_objective_value),
            "friendly_supply": friendly_supply,
            "enemy_supply": max(0.0, enemy_supply),
            "terrain_value": terrain_value_for_location(game_map, location_id),
            "is_port": bool(getattr(tile, "is_port", False)) if tile is not None else False,
            "is_airfield": bool(getattr(tile, "is_airfield", False)) if tile is not None else False,
        }
    return profiles


def _tile_for_location(game_map: Any, location_id: str) -> Any:
    if not location_id or game_map is None:
        return None
    if hasattr(game_map, "get_tile") and callable(getattr(game_map, "get_tile")):
        return game_map.get_tile(location_id)
    if hasattr(game_map, "get") and callable(getattr(game_map, "get")):
        return game_map.get(location_id)
    if isinstance(game_map, Mapping):
        return game_map.get(location_id)
    return None


def _support_attack_odds(unit: Any, enemy_strength: float) -> float:
    return round(_support_attack_power(unit) / max(1.0, enemy_strength), 3)


def _support_attack_power(unit: Any) -> float:
    strength = _unit_strength(unit)
    readiness = _unit_readiness(unit)
    supply = _unit_supply(unit)
    fatigue = _unit_fatigue(unit)
    domain_bonus = 1.15 if _unit_type(unit) == NAVAL_TYPE else 1.05
    readiness_factor = 0.60 + (readiness / 140.0)
    supply_factor = 0.60 + (supply / 160.0)
    fatigue_drag = max(0.55, 1.0 - (fatigue / 220.0))
    return round(strength * domain_bonus * readiness_factor * supply_factor * fatigue_drag, 3)


def _sort_support_units(units: Iterable[Any]) -> List[Any]:
    return sorted(
        list(units),
        key=lambda unit: (
            _unit_type(unit) != AIR_TYPE,
            -_unit_readiness(unit),
            -_unit_supply(unit),
            -_unit_strength(unit),
            _unit_id(unit),
        ),
    )


def _decision_domain(unit_id: str, units: Sequence[Any]) -> str:
    for unit in units:
        if _unit_id(unit) == unit_id:
            return _unit_type(unit).lower()
    return "support"


def _profile_for_location(profiles: Mapping[str, Dict[str, Any]], location_id: str) -> Mapping[str, Any]:
    return dict(profiles.get(location_id) or {"location_id": location_id, "game_map": None})


def _is_major_naval(unit: Any) -> bool:
    name = str(getattr(getattr(unit, "name", ""), "value", getattr(unit, "name", "")) or "").lower()
    return _unit_strength(unit) >= 100 or any(token in name for token in ("task force", "fleet", "carrier", "battleship", "cruiser"))


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


def _supply_value_for_location(
    supply_sources: Sequence[Mapping[str, Any]],
    location_id: str,
    *,
    side_filter: str | None,
) -> float:
    total = 0.0
    for source in supply_sources:
        if str(source.get("location_id", "") or "") != str(location_id or ""):
            continue
        source_side = str(source.get("side", "") or "").upper().strip()
        if side_filter is not None and source_side != str(side_filter).upper().strip():
            continue
        total += float(source.get("daily_supply", 0) or 0)
    return round(total, 3)


def _unit_id(unit: Any) -> str:
    return str(getattr(getattr(unit, "id", ""), "value", getattr(unit, "id", "")) or "")


def _unit_location(unit: Any) -> str:
    return str(getattr(getattr(unit, "location_id", ""), "value", getattr(unit, "location_id", "")) or "")


def _unit_strength(unit: Any) -> float:
    return float(getattr(getattr(unit, "strength", 0), "value", getattr(unit, "strength", 0)) or 0)


def _unit_supply(unit: Any) -> float:
    return float(getattr(getattr(unit, "supply", 0), "value", getattr(unit, "supply", 0)) or 0)


def _unit_readiness(unit: Any) -> float:
    return float(getattr(getattr(unit, "readiness", 0), "value", getattr(unit, "readiness", 0)) or 0)


def _unit_fatigue(unit: Any) -> float:
    return float(getattr(getattr(unit, "fatigue", 0), "value", getattr(unit, "fatigue", 0)) or 0)


def _unit_type(unit: Any) -> str:
    return str(getattr(getattr(unit, "unit_type", ""), "value", getattr(unit, "unit_type", "")) or "").upper()


__all__ = ["NavAirDecision", "NavAirSupportPlan", "plan_nav_air_support"]
