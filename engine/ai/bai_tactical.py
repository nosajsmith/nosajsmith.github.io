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
    reserve_requirement_component,
    supply_feasibility_component,
    terrain_value_component,
    terrain_value_for_location,
)
from .bai_defense import (
    DefenseAssessment,
    assess_defensive_situation,
    hold_decision_type,
    hold_priority_bonus,
    is_counterattack_location,
    is_encirclement_risk,
    is_exposed_line,
    preferred_defensive_fallback,
    should_allow_defensive_attack,
    should_shorten_line,
)
from .bai_models import OperationCandidate, StrategicDirective, TacticalIntent, UnitOrderWrapper
from .bai_nav_air import NavAirSupportPlan, plan_nav_air_support


GROUND_EXCLUDED_TYPES = {"NAVAL", "AIR"}


@dataclass
class GroundTacticalPlan:
    orders: List[Dict[str, Any]] = field(default_factory=list)
    intents: List[TacticalIntent] = field(default_factory=list)
    wrapped_orders: List[UnitOrderWrapper] = field(default_factory=list)
    diagnostics: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "orders": list(self.orders),
            "intents": [intent.to_dict() for intent in self.intents],
            "wrapped_orders": [wrapped.to_dict() for wrapped in self.wrapped_orders],
            "diagnostics": [dict(item) for item in self.diagnostics],
            "metadata": dict(self.metadata),
        }


def plan_tactical_layer(
    snapshot: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    runtime_profile: Mapping[str, Any] | None,
    *,
    reserve_ids: Sequence[str] = (),
) -> GroundTacticalPlan:
    ground_plan = plan_ground_tactical(
        snapshot,
        directive,
        operation,
        runtime_profile,
        reserve_ids=reserve_ids,
    )
    nav_air_plan = plan_nav_air_support(snapshot, directive, operation, runtime_profile)
    return _merge_tactical_plans(ground_plan, nav_air_plan)


@dataclass
class TacticalDecision:
    unit_id: str
    current_location: str
    target_location: str
    action: str
    posture: str
    priority_score: float
    rationale: str
    evaluation: EvaluationScore
    decision_type: str
    reserve: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["evaluation"] = self.evaluation.to_dict()
        return payload


def plan_ground_tactical(
    snapshot: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    runtime_profile: Mapping[str, Any] | None,
    *,
    reserve_ids: Sequence[str] = (),
) -> GroundTacticalPlan:
    side = str(getattr(snapshot, "side", "") or "")
    target_location = _safe_location(
        str(operation.target_objective or directive.main_objective or ""),
        list(getattr(snapshot, "known_locations", []) or []),
    )
    objectives = list(getattr(snapshot, "objectives", []) or [])
    game_map = getattr(snapshot, "game_map", None)
    friendly_units = [unit for unit in list(getattr(snapshot, "friendly_units", []) or []) if _is_ground_unit(unit)]
    enemy_units = [unit for unit in list(getattr(snapshot, "enemy_units", []) or []) if _is_ground_unit(unit)]
    reserve_id_set = {str(unit_id) for unit_id in reserve_ids}

    if not friendly_units:
        return GroundTacticalPlan(
            diagnostics=[
                {
                    "level": "warn",
                    "code": "tactical.no_ground_units",
                    "message": f"No ground units available for side {side}.",
                }
            ]
        )

    profiles = _build_location_profiles(
        snapshot,
        side=side,
        game_map=game_map,
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        objectives=objectives,
    )
    defense_assessment = assess_defensive_situation(
        snapshot,
        directive,
        operation,
        runtime_profile,
        profiles,
    )
    attack_odds_threshold = _attack_odds_threshold(runtime_profile)
    decisions = [
        _choose_unit_decision(
            snapshot=snapshot,
            side=side,
            unit=unit,
            directive=directive,
            operation=operation,
            target_location=target_location,
            profiles=profiles,
            runtime_profile=runtime_profile,
            defense_assessment=defense_assessment,
            reserve=(_unit_id(unit) in reserve_id_set),
            attack_odds_threshold=attack_odds_threshold,
        )
        for unit in _sort_units(friendly_units)
    ]

    ranked = sorted(
        decisions,
        key=lambda item: (
            item.reserve,
            -float(item.priority_score),
            item.current_location != item.target_location,
            item.unit_id,
        ),
    )

    intents: List[TacticalIntent] = []
    wrapped_orders: List[UnitOrderWrapper] = []
    orders: List[Dict[str, Any]] = []

    for priority, decision in enumerate(ranked, start=1):
        intent = TacticalIntent(
            intent_id=f"intent_{decision.unit_id}_{getattr(snapshot, 'day', 1)}",
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
                "operation_type": operation.operation_type,
                "reserve": decision.reserve,
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
                notes="Reserve preserved." if decision.reserve else f"Tactical {decision.decision_type}.",
                metadata={
                    "evaluation": decision.evaluation.to_dict(),
                    "decision_type": decision.decision_type,
                    "reserve": decision.reserve,
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

    return GroundTacticalPlan(
        orders=orders,
        intents=intents,
        wrapped_orders=wrapped_orders,
        metadata={"defense_assessment": defense_assessment.to_dict()},
    )


def _merge_tactical_plans(*plans: GroundTacticalPlan | NavAirSupportPlan) -> GroundTacticalPlan:
    orders: List[Dict[str, Any]] = []
    intents: List[TacticalIntent] = []
    wrapped_orders: List[UnitOrderWrapper] = []
    diagnostics: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}

    for plan in plans:
        orders.extend(list(plan.orders))
        intents.extend(list(plan.intents))
        wrapped_orders.extend(list(plan.wrapped_orders))
        diagnostics.extend(list(plan.diagnostics))
        metadata.update(dict(getattr(plan, "metadata", {}) or {}))

    for priority, intent in enumerate(intents, start=1):
        intent.priority = priority
    for priority, wrapped in enumerate(wrapped_orders, start=1):
        wrapped.priority = priority

    return GroundTacticalPlan(
        orders=orders,
        intents=intents,
        wrapped_orders=wrapped_orders,
        diagnostics=diagnostics,
        metadata=metadata,
    )


def _choose_unit_decision(
    *,
    snapshot: Any,
    side: str,
    unit: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    target_location: str,
    profiles: Mapping[str, Dict[str, Any]],
    runtime_profile: Mapping[str, Any] | None,
    defense_assessment: DefenseAssessment | None,
    reserve: bool,
    attack_odds_threshold: float,
) -> TacticalDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    thresholds = dict((runtime_profile or {}).get("thresholds") or {})
    unit_id = _unit_id(unit)
    current_location = _unit_location(unit)
    current_profile = dict(profiles.get(current_location) or _empty_profile(current_location))
    target_profile = dict(profiles.get(target_location) or _empty_profile(target_location))
    best_fallback = _best_withdraw_location(
        profiles=profiles,
        current_location=current_location,
        target_location=target_location,
        side=side,
    )
    defensive_fallback = preferred_defensive_fallback(
        current_location=current_location,
        profiles=profiles,
        assessment=defense_assessment,
    )
    if defensive_fallback != current_location:
        best_fallback = defensive_fallback
    fallback_profile = dict(profiles.get(best_fallback) or _empty_profile(best_fallback))

    candidates: List[TacticalDecision] = []
    counterattack_window = is_counterattack_location(target_location, defense_assessment) and str(operation.operation_type or "") == "counterattack_local_breach"

    if reserve:
        reserve_decision = _reserve_decision(
            unit=unit,
            current_profile=current_profile,
            directive=directive,
            runtime_profile=runtime_profile,
        )
        candidates.append(reserve_decision)
        hold_as_reserve = _hold_decision(
            unit=unit,
            location=current_location,
            profile=current_profile,
            directive=directive,
            runtime_profile=runtime_profile,
            base_bonus=-0.04,
            decision_type="reserve_hold",
        )
        candidates.append(hold_as_reserve)
    else:
        attack_candidate = _attack_decision(
            unit=unit,
            directive=directive,
            operation=operation,
            target_location=target_location,
            target_profile=target_profile,
            current_profile=current_profile,
            runtime_profile=runtime_profile,
            attack_odds_threshold=attack_odds_threshold,
        )
        if attack_candidate is not None and should_allow_defensive_attack(
            target_location=target_location,
            operation=operation,
            directive=directive,
            assessment=defense_assessment,
            attack_odds=float(attack_candidate.metadata.get("attack_odds", 0.0) or 0.0),
            attack_odds_threshold=attack_odds_threshold,
        ):
            if is_counterattack_location(target_location, defense_assessment):
                attack_candidate.decision_type = "counterattack"
                attack_candidate.priority_score = round(float(attack_candidate.priority_score) + 0.40, 3)
                attack_candidate.rationale = (
                    f"Selective counterattack at {target_location}. "
                    f"{attack_candidate.evaluation.dominant_reason}"
                )
                attack_candidate.metadata["counterattack_window"] = True
            candidates.append(attack_candidate)

        if should_shorten_line(current_location=current_location, assessment=defense_assessment):
            candidates.append(
                _shorten_line_decision(
                    unit=unit,
                    current_profile=current_profile,
                    fallback_profile=fallback_profile,
                    runtime_profile=runtime_profile,
                    target_location=best_fallback,
                    defense_assessment=defense_assessment,
                )
            )

        if _should_withdraw(
            unit=unit,
            current_profile=current_profile,
            fallback_profile=fallback_profile,
            best_fallback=best_fallback,
            attack_odds_threshold=attack_odds_threshold,
            runtime_profile=runtime_profile,
            defense_assessment=defense_assessment,
        ):
            candidates.append(
                _withdraw_decision(
                    unit=unit,
                    current_profile=current_profile,
                    fallback_profile=fallback_profile,
                    directive=directive,
                    runtime_profile=runtime_profile,
                    target_location=best_fallback,
                )
            )

        if _can_move_toward_target(
            current_location=current_location,
            target_location=target_location,
            target_profile=target_profile,
            unit=unit,
            attack_odds_threshold=attack_odds_threshold,
            thresholds=thresholds,
        ):
            candidates.append(
                _move_decision(
                    unit=unit,
                    directive=directive,
                    operation=operation,
                    target_location=target_location,
                    target_profile=target_profile,
                    runtime_profile=runtime_profile,
                )
            )

        if not is_encirclement_risk(current_location, defense_assessment) and not (
            counterattack_window and current_location == target_location
        ):
            candidates.append(
                _hold_decision(
                    unit=unit,
                    location=current_location,
                    profile=current_profile,
                    directive=directive,
                    runtime_profile=runtime_profile,
                    base_bonus=(0.08 if _holds_valuable_terrain(current_profile) else 0.0) + hold_priority_bonus(current_location, defense_assessment),
                    decision_type=hold_decision_type(current_location, defense_assessment),
                )
            )

        if _needs_delay(unit=unit, current_profile=current_profile, target_profile=target_profile):
            candidates.append(
                _delay_decision(
                    unit=unit,
                    current_profile=current_profile,
                    directive=directive,
                    runtime_profile=runtime_profile,
                )
            )

    best = sorted(
        candidates,
        key=lambda item: (
            -float(item.priority_score),
            item.decision_type,
            item.target_location,
            item.unit_id,
        ),
    )[0]
    return best


def _attack_decision(
    *,
    unit: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    target_location: str,
    target_profile: Mapping[str, Any],
    current_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
    attack_odds_threshold: float,
) -> TacticalDecision | None:
    if not target_location:
        return None

    unit_strength = _unit_strength(unit)
    target_enemy_strength = float(target_profile.get("enemy_strength", 0.0) or 0.0)
    if target_enemy_strength <= 0:
        return None

    attack_odds = _attack_odds(unit, target_enemy_strength)
    thresholds = dict((runtime_profile or {}).get("thresholds") or {})
    if (
        attack_odds < attack_odds_threshold
        or _unit_supply(unit) < int(thresholds.get("attack_supply_floor", 45))
        or _unit_readiness(unit) < int(thresholds.get("attack_readiness_floor", 45))
    ):
        return None

    axis = dict((runtime_profile or {}).get("axis") or {})
    weights = dict((runtime_profile or {}).get("weights") or {})
    objective_value = float(target_profile.get("enemy_objective_value", target_profile.get("objective_value", 0.0)) or 0.0)
    evaluation = build_evaluation(
        f"tactical_attack::{_unit_id(unit)}",
        base=0.12 if operation.operation_type in {"attack_objective", "counterattack_local_breach"} else 0.04,
        components=[
            objective_value_component(
                objective_value,
                weight=0.24 * float(weights.get("enemy_objective", 1.0)),
                label=f"Enemy objective value at {target_location}",
            ),
            terrain_value_component(
                target_profile.get("game_map"),
                target_location,
                weight=-0.12,
                label="Terrain resistance to the attack",
            ),
            force_ratio_component(
                _attack_power(unit),
                target_enemy_strength,
                weight=0.30,
                label=f"Attack odds at {target_location}",
            ),
            supply_feasibility_component(
                min(_unit_supply(unit), _unit_readiness(unit)),
                floor=int(thresholds.get("attack_supply_floor", 45)),
                weight=0.22,
                label="Attack readiness and supply",
            ),
            enemy_threat_component(
                target_enemy_strength,
                unit_strength,
                contested=True,
                weight=-0.14,
                label="Threat of the defending force",
            ),
            reserve_requirement_component(
                float((directive.metadata or {}).get("reserve_fraction", thresholds.get("reserve_target_fraction", 0.25)) or 0.25),
                0.0,
                weight=-0.08,
                label="Reserve cost of committing this unit",
            ),
            doctrinal_bias_component(
                max(float(axis.get("aggression", 0.5) or 0.5), float(weights.get("risk_acceptance", 1.0) or 1.0) / 2.0),
                weight=0.16,
                label="Doctrinal support for attack",
            ),
        ],
    )
    return TacticalDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=target_location,
        action="attack",
        posture="ATTACK",
        priority_score=evaluation.total,
        rationale=f"Attack {target_location} with favorable odds {attack_odds:.2f}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="attack",
        metadata={"attack_odds": round(attack_odds, 3)},
    )


def _move_decision(
    *,
    unit: Any,
    directive: StrategicDirective,
    operation: OperationCandidate,
    target_location: str,
    target_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
) -> TacticalDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    objective_value = float(target_profile.get("objective_value", 0.0) or 0.0)
    evaluation = build_evaluation(
        f"tactical_move::{_unit_id(unit)}",
        base=0.04 if operation.operation_type in {"reinforce_sector", "convoy_resupply"} else 0.0,
        components=[
            objective_value_component(
                objective_value,
                weight=0.18,
                label=f"Operational value at {target_location}",
            ),
            terrain_value_component(
                target_profile.get("game_map"),
                target_location,
                weight=0.08,
                label="Terrain value at the destination",
            ),
            supply_feasibility_component(
                _unit_supply(unit),
                floor=30.0,
                weight=0.10,
                label="Mobility support from supply",
            ),
            enemy_threat_component(
                float(target_profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=False,
                weight=-0.10,
                label="Threat along the intended move",
            ),
            doctrinal_bias_component(
                axis.get("breakthrough_focus", axis.get("aggression", 0.5)),
                weight=0.12,
                label="Doctrinal support for maneuver",
            ),
        ],
    )
    return TacticalDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=target_location,
        action="move",
        posture="MOVE",
        priority_score=evaluation.total,
        rationale=f"Move toward {target_location} to support the main effort. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="move_to_objective",
    )


def _hold_decision(
    *,
    unit: Any,
    location: str,
    profile: Mapping[str, Any],
    directive: StrategicDirective,
    runtime_profile: Mapping[str, Any] | None,
    base_bonus: float,
    decision_type: str,
) -> TacticalDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    thresholds = dict((runtime_profile or {}).get("thresholds") or {})
    posture = "DEFEND" if _holds_valuable_terrain(profile) or directive.posture == "DEFENSIVE" else "HOLD"
    evaluation = build_evaluation(
        f"tactical_hold::{_unit_id(unit)}",
        base=0.06 + base_bonus,
        components=[
            objective_value_component(
                float(profile.get("friendly_objective_value", profile.get("objective_value", 0.0)) or 0.0),
                weight=0.24,
                label=f"Friendly value held at {location}",
            ),
            terrain_value_component(
                profile.get("game_map"),
                location,
                weight=0.22,
                label="Terrain value for holding",
            ),
            force_ratio_component(
                float(profile.get("friendly_strength", 0.0) or 0.0),
                max(1.0, float(profile.get("enemy_strength", 0.0) or 0.0)),
                weight=-0.10,
                label=f"Local balance at {location}",
            ),
            supply_feasibility_component(
                _unit_supply(unit),
                floor=int(thresholds.get("defend_supply_floor", 35)),
                weight=0.12,
                label="Supply support for holding",
            ),
            enemy_threat_component(
                float(profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=bool(profile.get("enemy_strength", 0.0)),
                weight=0.24,
                label="Enemy pressure on the position",
            ),
            doctrinal_bias_component(
                axis.get("caution_bias", 0.5),
                weight=0.14,
                label="Doctrinal support for defense",
            ),
        ],
    )
    return TacticalDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=location,
        action="hold",
        posture=posture,
        priority_score=evaluation.total,
        rationale=f"Hold {location} and preserve control. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type=decision_type,
    )


def _withdraw_decision(
    *,
    unit: Any,
    current_profile: Mapping[str, Any],
    fallback_profile: Mapping[str, Any],
    directive: StrategicDirective,
    runtime_profile: Mapping[str, Any] | None,
    target_location: str,
) -> TacticalDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    evaluation = build_evaluation(
        f"tactical_withdraw::{_unit_id(unit)}",
        base=0.10,
        components=[
            terrain_value_component(
                fallback_profile.get("game_map"),
                target_location,
                weight=0.30,
                label="Terrain gained by withdrawal",
            ),
            force_ratio_component(
                float(current_profile.get("friendly_strength", 0.0) or 0.0),
                max(1.0, float(current_profile.get("enemy_strength", 0.0) or 0.0)),
                weight=-0.18,
                label=f"Pressure at {_unit_location(unit)}",
            ),
            supply_feasibility_component(
                _unit_supply(unit),
                floor=45.0,
                weight=-0.18,
                label="Supply stress arguing for withdrawal",
            ),
            enemy_threat_component(
                float(current_profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=True,
                weight=0.22,
                label="Enemy threat to the salient",
            ),
            doctrinal_bias_component(
                axis.get("caution_bias", 0.5),
                weight=0.18,
                label="Doctrinal support for pulling back",
            ),
        ],
    )
    return TacticalDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=target_location,
        action="withdraw",
        posture="DEFEND",
        priority_score=evaluation.total,
        rationale=f"Withdraw from {_unit_location(unit)} to stronger ground at {target_location}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="withdraw",
    )


def _shorten_line_decision(
    *,
    unit: Any,
    current_profile: Mapping[str, Any],
    fallback_profile: Mapping[str, Any],
    runtime_profile: Mapping[str, Any] | None,
    target_location: str,
    defense_assessment: DefenseAssessment | None,
) -> TacticalDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    evaluation = build_evaluation(
        f"tactical_shorten_line::{_unit_id(unit)}",
        base=0.14,
        components=[
            terrain_value_component(
                fallback_profile.get("game_map"),
                target_location,
                weight=0.24,
                label="Terrain gained by shortening the line",
            ),
            objective_value_component(
                float(fallback_profile.get("friendly_objective_value", fallback_profile.get("objective_value", 0.0)) or 0.0),
                weight=0.18,
                label=f"Ground value preserved at {target_location}",
            ),
            enemy_threat_component(
                float(current_profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=True,
                weight=0.18,
                label="Pressure on the exposed line",
            ),
            doctrinal_bias_component(
                axis.get("caution_bias", 0.5),
                weight=0.16,
                label="Doctrinal support for compact defense",
            ),
        ],
    )
    return TacticalDecision(
        unit_id=_unit_id(unit),
        current_location=_unit_location(unit),
        target_location=target_location,
        action="withdraw",
        posture="DEFEND",
        priority_score=evaluation.total,
        rationale=(
            f"Shorten the line from {_unit_location(unit)} to {target_location}. "
            f"{(defense_assessment.rationale + ' ') if defense_assessment and defense_assessment.rationale else ''}"
            f"{evaluation.dominant_reason}"
        ).strip(),
        evaluation=evaluation,
        decision_type="shorten_line",
        metadata={"fallback_anchor": target_location},
    )


def _delay_decision(
    *,
    unit: Any,
    current_profile: Mapping[str, Any],
    directive: StrategicDirective,
    runtime_profile: Mapping[str, Any] | None,
) -> TacticalDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    current_location = _unit_location(unit)
    evaluation = build_evaluation(
        f"tactical_delay::{_unit_id(unit)}",
        base=0.04,
        components=[
            terrain_value_component(
                current_profile.get("game_map"),
                current_location,
                weight=0.18,
                label="Terrain helping a delay",
            ),
            enemy_threat_component(
                float(current_profile.get("enemy_strength", 0.0) or 0.0),
                _unit_strength(unit),
                contested=True,
                weight=0.26,
                label="Enemy pressure requiring a delay",
            ),
            supply_feasibility_component(
                _unit_supply(unit),
                floor=35.0,
                weight=0.08,
                label="Supply support for delaying action",
            ),
            doctrinal_bias_component(
                axis.get("caution_bias", 0.5),
                weight=0.12,
                label="Doctrinal support for delay",
            ),
        ],
    )
    return TacticalDecision(
        unit_id=_unit_id(unit),
        current_location=current_location,
        target_location=current_location,
        action="delay",
        posture="DEFEND" if directive.posture == "DEFENSIVE" else "HOLD",
        priority_score=evaluation.total,
        rationale=f"Delay in place at {current_location}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="delay",
    )


def _reserve_decision(
    *,
    unit: Any,
    current_profile: Mapping[str, Any],
    directive: StrategicDirective,
    runtime_profile: Mapping[str, Any] | None,
) -> TacticalDecision:
    axis = dict((runtime_profile or {}).get("axis") or {})
    current_location = _unit_location(unit)
    reserve_fraction = float((directive.metadata or {}).get("reserve_fraction", 0.25) or 0.25)
    evaluation = build_evaluation(
        f"tactical_reserve::{_unit_id(unit)}",
        base=0.14,
        components=[
            objective_value_component(
                float(current_profile.get("friendly_objective_value", 0.0) or 0.0),
                weight=0.12,
                label=f"Position value while in reserve at {current_location}",
            ),
            terrain_value_component(
                current_profile.get("game_map"),
                current_location,
                weight=0.12,
                label="Terrain protecting the reserve",
            ),
            reserve_requirement_component(
                reserve_fraction,
                0.0,
                weight=0.30,
                label="Reserve requirement for the operation",
            ),
            doctrinal_bias_component(
                axis.get("reserve_preservation_bias", 0.5),
                weight=0.20,
                label="Doctrinal support for preserving a reserve",
            ),
        ],
    )
    posture = "DEFEND" if directive.posture == "DEFENSIVE" or _holds_valuable_terrain(current_profile) else "HOLD"
    return TacticalDecision(
        unit_id=_unit_id(unit),
        current_location=current_location,
        target_location=current_location,
        action="hold",
        posture=posture,
        priority_score=evaluation.total,
        rationale=f"Keep {_unit_id(unit)} in reserve at {current_location}. {evaluation.dominant_reason}",
        evaluation=evaluation,
        decision_type="reserve",
        reserve=True,
    )


def _build_location_profiles(
    snapshot: Any,
    *,
    side: str,
    game_map: Any,
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    objectives: Sequence[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    known_locations = sorted(set(str(location) for location in list(getattr(snapshot, "known_locations", []) or [])))
    profiles: Dict[str, Dict[str, Any]] = {}
    for location_id in known_locations:
        friendly_strength = location_strength(friendly_units, location_id)
        enemy_strength = location_strength(enemy_units, location_id)
        friendly_objective_value = _objective_value_for_location(objectives, location_id, side_filter=side)
        enemy_objective_value = _objective_value_for_location(objectives, location_id, side_filter=None) - friendly_objective_value
        control = side if friendly_strength > 0 and enemy_strength <= 0 else ("ENEMY" if enemy_strength > 0 and friendly_strength <= 0 else None)
        profiles[location_id] = {
            "location_id": location_id,
            "game_map": game_map,
            "friendly_strength": friendly_strength,
            "enemy_strength": enemy_strength,
            "friendly_objective_value": friendly_objective_value,
            "enemy_objective_value": max(0.0, enemy_objective_value),
            "objective_value": friendly_objective_value + max(0.0, enemy_objective_value),
            "terrain_value": terrain_value_for_location(game_map, location_id),
            "control": control,
        }
    return profiles


def _best_withdraw_location(
    *,
    profiles: Mapping[str, Dict[str, Any]],
    current_location: str,
    target_location: str,
    side: str,
) -> str:
    current_profile = dict(profiles.get(current_location) or _empty_profile(current_location))
    ranked = sorted(
        profiles.values(),
        key=lambda profile: (
            float(profile.get("control") == side),
            float(profile.get("enemy_strength", 0.0) == 0.0),
            float(profile.get("terrain_value", 0.0)),
            float(profile.get("friendly_objective_value", 0.0)),
            -float(profile.get("enemy_strength", 0.0)),
            profile.get("location_id", ""),
        ),
        reverse=True,
    )
    for profile in ranked:
        location_id = str(profile.get("location_id", "") or "")
        if not location_id or location_id == current_location:
            continue
        if float(profile.get("terrain_value", 0.0)) <= float(current_profile.get("terrain_value", 0.0)):
            continue
        if float(profile.get("enemy_strength", 0.0) or 0.0) > 0 and location_id != target_location:
            continue
        return location_id
    return current_location


def _should_withdraw(
    *,
    unit: Any,
    current_profile: Mapping[str, Any],
    fallback_profile: Mapping[str, Any],
    best_fallback: str,
    attack_odds_threshold: float,
    runtime_profile: Mapping[str, Any] | None,
    defense_assessment: DefenseAssessment | None,
) -> bool:
    if best_fallback == _unit_location(unit):
        return False
    axis = dict((runtime_profile or {}).get("axis") or {})
    caution_bias = float(axis.get("caution_bias", 0.5) or 0.5)
    enemy_pressure = float(current_profile.get("enemy_strength", 0.0) or 0.0)
    unit_power = _attack_power(unit)
    current_odds = unit_power / max(1.0, enemy_pressure) if enemy_pressure > 0 else 9.0
    return (
        enemy_pressure > 0
        and (
            is_encirclement_risk(_unit_location(unit), defense_assessment)
            or is_exposed_line(_unit_location(unit), defense_assessment)
            or
            current_odds < attack_odds_threshold
            or _unit_supply(unit) < 40
            or _unit_fatigue(unit) > 55
            or caution_bias >= 0.7
        )
        and float(current_profile.get("terrain_value", 0.0)) < float(fallback_profile.get("terrain_value", current_profile.get("terrain_value", 0.0)))
    )


def _can_move_toward_target(
    *,
    current_location: str,
    target_location: str,
    target_profile: Mapping[str, Any],
    unit: Any,
    attack_odds_threshold: float,
    thresholds: Mapping[str, Any],
) -> bool:
    if not target_location or current_location == target_location:
        return False
    enemy_strength = float(target_profile.get("enemy_strength", 0.0) or 0.0)
    if enemy_strength <= 0:
        return True
    if _unit_supply(unit) < int(thresholds.get("attack_supply_floor", 45)) or _unit_readiness(unit) < int(thresholds.get("attack_readiness_floor", 45)):
        return False
    return _attack_odds(unit, enemy_strength) >= attack_odds_threshold


def _holds_valuable_terrain(profile: Mapping[str, Any]) -> bool:
    return (
        float(profile.get("friendly_objective_value", 0.0) or 0.0) > 0
        or float(profile.get("terrain_value", 0.0) or 0.0) >= 1.25
    )


def _needs_delay(
    *,
    unit: Any,
    current_profile: Mapping[str, Any],
    target_profile: Mapping[str, Any],
) -> bool:
    enemy_pressure = float(current_profile.get("enemy_strength", 0.0) or 0.0)
    return (
        enemy_pressure > 0
        and enemy_pressure >= (_unit_strength(unit) * 0.85)
        and float(target_profile.get("enemy_strength", 0.0) or 0.0) >= enemy_pressure
    )


def _attack_odds_threshold(runtime_profile: Mapping[str, Any] | None) -> float:
    axis = dict((runtime_profile or {}).get("axis") or {})
    weights = dict((runtime_profile or {}).get("weights") or {})
    aggression = float(axis.get("aggression", 0.5) or 0.5)
    caution_bias = float(axis.get("caution_bias", 0.5) or 0.5)
    risk_acceptance = float(weights.get("risk_acceptance", 1.0) or 1.0)
    threshold = 1.20 + (caution_bias * 0.35) - (aggression * 0.25) - ((risk_acceptance - 1.0) * 0.20)
    return max(0.9, min(1.65, round(threshold, 3)))


def _attack_odds(unit: Any, enemy_strength: float) -> float:
    return round(_attack_power(unit) / max(1.0, enemy_strength), 3)


def _attack_power(unit: Any) -> float:
    strength = _unit_strength(unit)
    readiness = _unit_readiness(unit)
    supply = _unit_supply(unit)
    fatigue = _unit_fatigue(unit)
    readiness_factor = 0.55 + (readiness / 150.0)
    supply_factor = 0.55 + (supply / 150.0)
    fatigue_drag = max(0.50, 1.0 - (fatigue / 200.0))
    return round(strength * readiness_factor * supply_factor * fatigue_drag, 3)


def _sort_units(units: Iterable[Any]) -> List[Any]:
    return sorted(
        list(units),
        key=lambda unit: (
            -_unit_readiness(unit),
            -_unit_supply(unit),
            -_unit_strength(unit),
            _unit_id(unit),
        ),
    )


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


def _is_ground_unit(unit: Any) -> bool:
    return _unit_type(unit) not in GROUND_EXCLUDED_TYPES


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


def _safe_location(location_id: str | None, known_locations: Sequence[str]) -> str:
    if location_id and location_id in known_locations:
        return location_id
    return str(known_locations[0]) if known_locations else ""


def _empty_profile(location_id: str) -> Dict[str, Any]:
    return {
        "location_id": location_id,
        "game_map": None,
        "friendly_strength": 0.0,
        "enemy_strength": 0.0,
        "friendly_objective_value": 0.0,
        "enemy_objective_value": 0.0,
        "objective_value": 0.0,
        "terrain_value": 0.0,
        "control": None,
    }


__all__ = ["GroundTacticalPlan", "TacticalDecision", "plan_ground_tactical", "plan_tactical_layer"]
