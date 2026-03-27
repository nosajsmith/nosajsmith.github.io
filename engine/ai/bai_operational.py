from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .bai_models import OperationCandidate, StrategicDirective
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


@dataclass
class OperationalPlan:
    primary_operation: OperationCandidate
    candidates: List[OperationCandidate] = field(default_factory=list)
    support_actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_operation": asdict(self.primary_operation),
            "candidates": [asdict(item) for item in self.candidates],
            "support_actions": [dict(item) for item in self.support_actions],
        }


def plan_operational_layer(
    snapshot: Any,
    directive: StrategicDirective,
    runtime_profile: Mapping[str, Any] | None,
) -> OperationalPlan:
    profile = dict(runtime_profile or {})
    axis = dict(profile.get("axis") or {})
    thresholds = dict(profile.get("thresholds") or {})
    weights = dict(profile.get("weights") or {})
    side = str(getattr(snapshot, "side", "") or "")
    day = int(getattr(snapshot, "day", 1) or 1)
    phase = str(getattr(snapshot, "phase", "day") or "day")
    main_objective = str(directive.main_objective or "") or _fallback_location(snapshot)
    posture = str(directive.posture or "CONTAIN").upper().strip()
    reserve_fraction = float((directive.metadata or {}).get("reserve_fraction", thresholds.get("reserve_target_fraction", 0.25)) or 0.25)

    friendly_units = list(getattr(snapshot, "friendly_units", []) or [])
    enemy_units = list(getattr(snapshot, "enemy_units", []) or [])
    known_locations = list(getattr(snapshot, "known_locations", []) or [])
    game_map = getattr(snapshot, "game_map", None)
    control_by_location = _control_map(friendly_units, enemy_units, known_locations, side)

    avg_supply = _average_units(friendly_units, "supply", 50)
    avg_readiness = _average_units(friendly_units, "readiness", 50)
    avg_fatigue = _average_units(friendly_units, "fatigue", 0)
    reserve_level = _reserve_level_from_fraction(reserve_fraction, len(friendly_units))

    own_objective_breach = _is_own_objective_breach(snapshot, side, control_by_location)
    stronger_terrain_location = _find_stronger_terrain_location(game_map, friendly_units, known_locations, main_objective)
    convoy_anchor = _best_supply_anchor(friendly_units, known_locations)
    objective_friendly_strength = location_strength(friendly_units, main_objective)
    objective_enemy_strength = location_strength(enemy_units, main_objective)
    objective_value = sum(
        float(objective.get("value", 0) or 0)
        for objective in list(getattr(snapshot, "objectives", []) or [])
        if isinstance(objective, Mapping) and str(objective.get("location_id", "")).strip() == main_objective
    )

    candidates: List[OperationCandidate] = []
    hold_eval = _evaluate_hold_line(
        game_map=game_map,
        location_id=main_objective,
        objective_value=objective_value,
        posture=posture,
        control=control_by_location.get(main_objective),
        avg_supply=avg_supply,
        avg_readiness=avg_readiness,
        friendly_strength=objective_friendly_strength,
        enemy_strength=objective_enemy_strength,
        contested_weight=float(weights.get("contested_objective", 1.0)),
        reserve_fraction=reserve_fraction,
        caution_bias=float(axis.get("caution_bias", 0.5)),
    )
    candidates.append(
        _candidate(
            side=side,
            day=day,
            operation_type="hold_line",
            name=f"Hold line at {main_objective}",
            posture=posture,
            target_objective=main_objective,
            score=hold_eval.total,
            reserve_level=reserve_level,
            phase=phase,
            rationale=[
                f"Maintain operational cohesion around {main_objective}.",
                f"Directive front priority is {(directive.metadata or {}).get('front_priority', 'SCREEN')}.",
                *hold_eval.reasons[:1],
            ],
            metadata={
                "plan_role": "candidate",
                "operation_family": "line_management",
                "evaluation": hold_eval.to_dict(),
            },
        )
    )

    if main_objective:
        attack_eval = _evaluate_attack_objective(
            game_map=game_map,
            location_id=main_objective,
            posture=posture,
            control=control_by_location.get(main_objective),
            avg_supply=avg_supply,
            avg_readiness=avg_readiness,
            avg_fatigue=avg_fatigue,
            friendly_strength=objective_friendly_strength,
            enemy_strength=objective_enemy_strength,
            objective_value=objective_value,
            reserve_fraction=reserve_fraction,
            thresholds=thresholds,
            enemy_objective_weight=float(weights.get("enemy_objective", 1.0)),
            risk_acceptance=float(weights.get("risk_acceptance", 1.0)),
            aggression=float(axis.get("aggression", 0.5)),
        )
        if attack_eval.total > 0.18:
            candidates.append(
                _candidate(
                    side=side,
                    day=day,
                    operation_type="attack_objective",
                    name=f"Attack objective {main_objective}",
                    posture=posture,
                    target_objective=main_objective,
                    score=attack_eval.total,
                    reserve_level=reserve_level,
                    phase=phase,
                    rationale=[
                        f"{main_objective} remains a viable offensive aim under the current strategic directive.",
                        f"Enemy-objective weight is {float(weights.get('enemy_objective', 1.0)):.2f}.",
                        *attack_eval.reasons[:1],
                    ],
                    metadata={
                        "plan_role": "candidate",
                        "operation_family": "offense",
                        "evaluation": attack_eval.to_dict(),
                    },
                )
            )

    if len(friendly_units) > 1 and main_objective:
        reinforce_eval = _evaluate_reinforce_sector(
            game_map=game_map,
            location_id=main_objective,
            posture=posture,
            control=control_by_location.get(main_objective),
            own_objective_breach=own_objective_breach,
            reserve_fraction=reserve_fraction,
            friendly_strength=objective_friendly_strength,
            enemy_strength=objective_enemy_strength,
            objective_value=objective_value,
            avg_supply=avg_supply,
            caution_bias=float(axis.get("caution_bias", 0.5)),
        )
        candidates.append(
            _candidate(
                side=side,
                day=day,
                operation_type="reinforce_sector",
                name=f"Reinforce sector {main_objective}",
                posture=posture,
                target_objective=main_objective,
                score=reinforce_eval.total,
                reserve_level=reserve_level,
                phase=phase,
                rationale=[
                    f"Shift combat power toward {main_objective} to support the main effort.",
                    f"Reserve fraction is {reserve_fraction:.2f}.",
                    *reinforce_eval.reasons[:1],
                ],
                metadata={
                    "plan_role": "candidate",
                    "operation_family": "maneuver_support",
                    "evaluation": reinforce_eval.to_dict(),
                },
            )
        )

    if stronger_terrain_location and stronger_terrain_location != main_objective:
        withdraw_eval = _evaluate_withdraw(
            game_map=game_map,
            main_objective=main_objective,
            stronger_terrain_location=stronger_terrain_location,
            posture=posture,
            avg_supply=avg_supply,
            avg_fatigue=avg_fatigue,
            friendly_strength=location_strength(friendly_units, stronger_terrain_location),
            enemy_strength=location_strength(enemy_units, main_objective),
            reserve_fraction=reserve_fraction,
            caution_bias=float(axis.get("caution_bias", 0.5)),
        )
        if withdraw_eval.total > 0.2:
            candidates.append(
                _candidate(
                    side=side,
                    day=day,
                    operation_type="withdraw_stronger_terrain",
                    name=f"Withdraw to {stronger_terrain_location}",
                    posture=posture,
                    target_objective=stronger_terrain_location,
                    score=withdraw_eval.total,
                    reserve_level=reserve_level,
                    phase=phase,
                    rationale=[
                        f"{stronger_terrain_location} offers stronger defensive ground than {main_objective}.",
                        f"Average fatigue {avg_fatigue:.1f} and supply {avg_supply:.1f} justify a fallback option.",
                        *withdraw_eval.reasons[:1],
                    ],
                    metadata={
                        "plan_role": "candidate",
                        "operation_family": "survivability",
                        "evaluation": withdraw_eval.to_dict(),
                    },
                )
            )

    convoy_eval = _evaluate_convoy(
        game_map=game_map,
        convoy_anchor=convoy_anchor,
        avg_supply=avg_supply,
        reserve_fraction=reserve_fraction,
        friendly_strength=location_strength(friendly_units, convoy_anchor or ""),
        enemy_strength=location_strength(enemy_units, convoy_anchor or ""),
        logistics_weight=float(weights.get("logistics", 1.0)),
        posture=posture,
    )
    if convoy_anchor and convoy_eval.total > 0.2:
        candidates.append(
            _candidate(
                side=side,
                day=day,
                operation_type="convoy_resupply",
                name=f"Convoy and resupply {convoy_anchor}",
                posture=posture,
                target_objective=convoy_anchor,
                score=convoy_eval.total,
                reserve_level=reserve_level,
                phase=phase,
                rationale=[
                    f"Supply posture at {convoy_anchor} improves the force's next-turn options.",
                    f"Logistics weight is {float(weights.get('logistics', 1.0)):.2f}.",
                    *convoy_eval.reasons[:1],
                ],
                metadata={
                    "plan_role": "candidate",
                    "operation_family": "sustainment",
                    "evaluation": convoy_eval.to_dict(),
                },
            )
        )

    if own_objective_breach:
        breach_location = _primary_breach_location(snapshot, side, control_by_location, main_objective)
        counterattack_eval = _evaluate_counterattack(
            game_map=game_map,
            breach_location=breach_location,
            avg_readiness=avg_readiness,
            avg_supply=avg_supply,
            friendly_strength=location_strength(friendly_units, breach_location),
            enemy_strength=location_strength(enemy_units, breach_location),
            reserve_fraction=reserve_fraction,
            counterattack_bias=float(axis.get("counterattack_bias", 0.5)),
            risk_acceptance=float(weights.get("risk_acceptance", 1.0)),
            posture=posture,
        )
        if counterattack_eval.total > 0.2:
            candidates.append(
                _candidate(
                    side=side,
                    day=day,
                    operation_type="counterattack_local_breach",
                    name=f"Counterattack breach at {breach_location}",
                    posture=posture,
                    target_objective=breach_location,
                    score=counterattack_eval.total,
                    reserve_level=reserve_level,
                    phase=phase,
                    rationale=[
                        f"{breach_location} is under pressure and merits a local counterstroke.",
                        f"Counterattack bias is {float(axis.get('counterattack_bias', 0.5)):.2f}.",
                        *counterattack_eval.reasons[:1],
                    ],
                    metadata={
                        "plan_role": "candidate",
                        "operation_family": "counterstroke",
                        "evaluation": counterattack_eval.to_dict(),
                    },
                )
            )

    ranked = _rank_candidates(candidates)[:5]
    if len(ranked) < 2 and main_objective:
        ranked.append(
            _candidate(
                side=side,
                day=day,
                operation_type="reinforce_sector",
                name=f"Reinforce sector {main_objective}",
                posture=posture,
                target_objective=main_objective,
                score=0.25,
                reserve_level=reserve_level,
                phase=phase,
                rationale=["Fallback support candidate to ensure multiple operational options."],
                metadata={"plan_role": "candidate", "operation_family": "fallback"},
            )
        )
        ranked = _rank_candidates(ranked)[:5]

    primary = _select_primary(ranked)
    support_actions = _support_actions_for_plan(ranked, primary)

    return OperationalPlan(
        primary_operation=primary,
        candidates=ranked,
        support_actions=support_actions,
    )


def _candidate(
    *,
    side: str,
    day: int,
    operation_type: str,
    name: str,
    posture: str,
    target_objective: str,
    score: float,
    reserve_level: str,
    phase: str,
    rationale: Sequence[str],
    metadata: Mapping[str, Any] | None = None,
) -> OperationCandidate:
    return OperationCandidate(
        operation_id=f"{side.lower()}_{day}_{operation_type}_{str(target_objective or 'line').lower()}",
        name=name,
        operation_type=operation_type,
        posture=posture,
        target_objective=target_objective,
        score=round(float(score), 3),
        priority=1,
        reserve_level=reserve_level,
        timing_breakdown={"phase": phase, "day": day},
        rationale=list(rationale),
        metadata=dict(metadata or {}),
    )


def _rank_candidates(candidates: Sequence[OperationCandidate]) -> List[OperationCandidate]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            -float(item.score or 0.0),
            str(item.operation_type),
            str(item.target_objective or ""),
            str(item.name),
        ),
    )
    deduped: List[OperationCandidate] = []
    seen: set[tuple[str, str]] = set()
    for candidate in ranked:
        key = (candidate.operation_type, str(candidate.target_objective or ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _select_primary(candidates: List[OperationCandidate]) -> OperationCandidate:
    if not candidates:
        raise ValueError("Operational layer requires at least one candidate operation.")
    selected = candidates[0]
    marked: List[OperationCandidate] = []
    for index, candidate in enumerate(candidates, start=1):
        metadata = dict(candidate.metadata or {})
        metadata["plan_role"] = "primary" if candidate is selected else "support_candidate"
        marked.append(
            OperationCandidate(
                operation_id=candidate.operation_id,
                name=candidate.name,
                operation_type=candidate.operation_type,
                posture=candidate.posture,
                target_objective=candidate.target_objective,
                score=candidate.score,
                priority=index,
                reserve_level=candidate.reserve_level,
                timing_breakdown=dict(candidate.timing_breakdown),
                rationale=list(candidate.rationale),
                risks=list(candidate.risks),
                selected=candidate is selected,
                metadata=metadata,
            )
        )
    candidates[:] = marked
    return candidates[0]


def _support_actions_for_plan(
    candidates: Sequence[OperationCandidate],
    primary: OperationCandidate,
) -> List[Dict[str, Any]]:
    support_actions: List[Dict[str, Any]] = []
    for candidate in candidates:
        if candidate.operation_id == primary.operation_id:
            continue
        support_actions.append(
            {
                "action": candidate.operation_type,
                "target": candidate.target_objective,
                "operation_id": candidate.operation_id,
                "reason": candidate.rationale[0] if candidate.rationale else candidate.name,
            }
        )
        if len(support_actions) >= 2:
            break
    return support_actions


def _evaluate_hold_line(
    *,
    game_map: Any,
    location_id: str,
    objective_value: float,
    posture: str,
    control: str | None,
    avg_supply: float,
    avg_readiness: float,
    friendly_strength: float,
    enemy_strength: float,
    contested_weight: float,
    reserve_fraction: float,
    caution_bias: float,
) -> EvaluationScore:
    return build_evaluation(
        f"hold_line::{location_id}",
        base=0.24,
        components=[
            objective_value_component(
                objective_value,
                weight=0.44 * contested_weight,
                scale=120.0,
                label=f"Operational objective value at {location_id}",
            ),
            terrain_value_component(
                game_map,
                location_id,
                weight=0.22,
                label="Line-holding terrain value",
            ),
            force_ratio_component(
                friendly_strength,
                enemy_strength,
                weight=0.12,
                label=f"Hold force ratio at {location_id}",
            ),
            supply_feasibility_component(
                (avg_supply + avg_readiness) / 2.0,
                floor=40.0,
                weight=0.12,
                label="Hold-line sustainment",
            ),
            enemy_threat_component(
                enemy_strength,
                friendly_strength,
                contested=control is None,
                weight=0.28,
                label="Threat pressing the line",
            ),
            reserve_requirement_component(
                reserve_fraction,
                0.0,
                weight=0.14,
                label="Reserve needed behind the line",
            ),
            doctrinal_bias_component(
                caution_bias if posture == "DEFENSIVE" else 0.5,
                weight=0.18 if posture in {"DEFENSIVE", "CONTAIN"} else 0.04,
                label="Doctrinal bias toward preserving the line",
            ),
        ],
    )


def _evaluate_attack_objective(
    *,
    game_map: Any,
    location_id: str,
    posture: str,
    control: str | None,
    avg_supply: float,
    avg_readiness: float,
    avg_fatigue: float,
    friendly_strength: float,
    enemy_strength: float,
    objective_value: float,
    reserve_fraction: float,
    thresholds: Mapping[str, Any],
    enemy_objective_weight: float,
    risk_acceptance: float,
    aggression: float,
) -> EvaluationScore:
    attack_supply_floor = int(thresholds.get("attack_supply_floor", 45))
    attack_readiness_floor = int(thresholds.get("attack_readiness_floor", 45))
    if avg_supply < attack_supply_floor or avg_readiness < attack_readiness_floor:
        return build_evaluation(
            f"attack_objective::{location_id}",
            base=0.12,
            components=[
                supply_feasibility_component(
                    min(avg_supply, avg_readiness),
                    floor=attack_supply_floor,
                    weight=0.05,
                    label="Attack readiness is below threshold",
                ),
            ],
        )
    fatigue_penalty = max(0.0, min(1.0, (avg_fatigue - 40.0) / 30.0))
    return build_evaluation(
        f"attack_objective::{location_id}",
        base=0.06 if control == "ENEMY" else 0.0,
        components=[
            objective_value_component(
                objective_value,
                weight=0.34 * enemy_objective_weight,
                label=f"Enemy objective value at {location_id}",
            ),
            terrain_value_component(
                game_map,
                location_id,
                weight=-0.18,
                label="Terrain resistance to an attack",
            ),
            force_ratio_component(
                friendly_strength,
                enemy_strength,
                weight=0.28,
                label=f"Assault force ratio at {location_id}",
            ),
            supply_feasibility_component(
                min(avg_supply, avg_readiness),
                floor=min(attack_supply_floor, attack_readiness_floor),
                weight=0.28,
                label="Attack supply feasibility",
            ),
            enemy_threat_component(
                enemy_strength,
                friendly_strength,
                contested=control is None,
                weight=-0.16,
                label="Threat that can blunt the attack",
            ),
            reserve_requirement_component(
                reserve_fraction,
                0.0,
                weight=-0.14,
                label="Reserve held back from the assault",
            ),
            doctrinal_bias_component(
                max(aggression, risk_acceptance),
                baseline=0.5,
                weight=0.24,
                label="Doctrinal bias toward attack",
            ),
            doctrinal_bias_component(
                0.5 - fatigue_penalty,
                baseline=0.5,
                weight=0.12,
                label="Fatigue drag on the assault",
            ),
        ],
    )


def _evaluate_reinforce_sector(
    *,
    game_map: Any,
    location_id: str,
    posture: str,
    control: str | None,
    own_objective_breach: bool,
    reserve_fraction: float,
    friendly_strength: float,
    enemy_strength: float,
    objective_value: float,
    avg_supply: float,
    caution_bias: float,
) -> EvaluationScore:
    return build_evaluation(
        f"reinforce_sector::{location_id}",
        base=0.12 if own_objective_breach else 0.04,
        components=[
            objective_value_component(
                objective_value,
                weight=0.26,
                label=f"Objective stake at {location_id}",
            ),
            terrain_value_component(
                game_map,
                location_id,
                weight=0.08,
                label="Terrain worth reinforcing",
            ),
            force_ratio_component(
                friendly_strength,
                enemy_strength,
                weight=-0.24,
                label=f"Current force ratio at {location_id}",
            ),
            supply_feasibility_component(
                avg_supply,
                floor=35.0,
                weight=0.14,
                label="Supply that can support reinforcement",
            ),
            enemy_threat_component(
                enemy_strength,
                friendly_strength,
                contested=control is None or own_objective_breach,
                weight=0.28,
                label="Pressure on the sector",
            ),
            reserve_requirement_component(
                reserve_fraction,
                0.0,
                weight=0.20,
                label="Reserve available to reinforce the sector",
            ),
            doctrinal_bias_component(
                caution_bias,
                weight=0.14 if posture in {"DEFENSIVE", "CONTAIN"} else 0.04,
                label="Doctrinal bias toward reinforcement",
            ),
        ],
    )


def _evaluate_withdraw(
    *,
    game_map: Any,
    main_objective: str,
    stronger_terrain_location: str,
    posture: str,
    avg_supply: float,
    avg_fatigue: float,
    friendly_strength: float,
    enemy_strength: float,
    reserve_fraction: float,
    caution_bias: float,
) -> EvaluationScore:
    terrain_delta = terrain_value_for_location(game_map, stronger_terrain_location) - terrain_value_for_location(game_map, main_objective)
    return build_evaluation(
        f"withdraw::{stronger_terrain_location}",
        base=0.06 if posture == "DEFENSIVE" else 0.0,
        components=[
            objective_value_component(
                max(friendly_strength, enemy_strength),
                weight=0.10,
                scale=120.0,
                label=f"Combat power preserved by withdrawing to {stronger_terrain_location}",
            ),
            terrain_value_component(
                game_map,
                stronger_terrain_location,
                weight=0.34 + max(0.0, terrain_delta * 0.10),
                label="Terrain gained by withdrawal",
            ),
            force_ratio_component(
                friendly_strength,
                enemy_strength,
                weight=-0.12,
                label=f"Pressure forcing withdrawal from {main_objective}",
            ),
            supply_feasibility_component(
                avg_supply,
                floor=45.0,
                weight=-0.24,
                label="Supply stress supporting withdrawal",
            ),
            enemy_threat_component(
                enemy_strength,
                friendly_strength,
                contested=True,
                weight=0.18,
                label="Enemy threat pushing the force back",
            ),
            reserve_requirement_component(
                reserve_fraction,
                0.0,
                weight=0.16,
                label="Reserve preserved by disengaging",
            ),
            doctrinal_bias_component(
                caution_bias,
                weight=0.22,
                label="Doctrinal bias toward withdrawal",
            ),
            doctrinal_bias_component(
                0.5 - max(0.0, min(0.5, (avg_fatigue - 45.0) / 50.0)),
                baseline=0.5,
                weight=-0.14,
                label="Fatigue argues for disengagement",
            ),
        ],
    )


def _evaluate_convoy(
    *,
    game_map: Any,
    convoy_anchor: str | None,
    avg_supply: float,
    reserve_fraction: float,
    friendly_strength: float,
    enemy_strength: float,
    logistics_weight: float,
    posture: str,
) -> EvaluationScore:
    anchor = convoy_anchor or "line"
    return build_evaluation(
        f"convoy::{anchor}",
        base=0.04,
        components=[
            objective_value_component(
                friendly_strength,
                weight=0.08,
                scale=120.0,
                label=f"Force sustained at {anchor}",
            ),
            terrain_value_component(
                game_map,
                anchor,
                weight=0.06,
                label="Terrain around the resupply anchor",
            ),
            force_ratio_component(
                friendly_strength,
                enemy_strength,
                weight=-0.08,
                label=f"Security ratio around {anchor}",
            ),
            supply_feasibility_component(
                avg_supply,
                floor=55.0,
                weight=-0.34,
                label="Poor supply makes convoying more urgent",
            ),
            enemy_threat_component(
                enemy_strength,
                friendly_strength,
                contested=posture == "DEFENSIVE",
                weight=0.10 if posture == "DEFENSIVE" else 0.04,
                label="Threat to the supply route",
            ),
            reserve_requirement_component(
                reserve_fraction,
                0.0,
                weight=0.12,
                label="Reserve coverage needed for convoy security",
            ),
            doctrinal_bias_component(
                logistics_weight,
                baseline=1.0,
                weight=0.18,
                label="Doctrinal bias toward sustainment",
            ),
        ],
    )


def _evaluate_counterattack(
    *,
    game_map: Any,
    breach_location: str,
    avg_readiness: float,
    avg_supply: float,
    friendly_strength: float,
    enemy_strength: float,
    reserve_fraction: float,
    counterattack_bias: float,
    risk_acceptance: float,
    posture: str,
) -> EvaluationScore:
    if avg_readiness < 35 or avg_supply < 35:
        return build_evaluation(
            f"counterattack::{breach_location}",
            base=0.14,
            components=[
                supply_feasibility_component(
                    min(avg_supply, avg_readiness),
                    floor=35.0,
                    weight=0.04,
                    label="Counterattack readiness is below threshold",
                ),
            ],
        )
    return build_evaluation(
        f"counterattack::{breach_location}",
        base=0.08 if posture == "DEFENSIVE" else 0.0,
        components=[
            objective_value_component(
                max(friendly_strength, enemy_strength),
                weight=0.14,
                scale=120.0,
                label=f"Local combat stake at {breach_location}",
            ),
            terrain_value_component(
                game_map,
                breach_location,
                weight=0.10,
                label="Terrain shaping the counterstroke",
            ),
            force_ratio_component(
                friendly_strength,
                enemy_strength,
                weight=0.24,
                label=f"Counterattack force ratio at {breach_location}",
            ),
            supply_feasibility_component(
                min(avg_supply, avg_readiness),
                floor=35.0,
                weight=0.22,
                label="Counterattack sustainment",
            ),
            enemy_threat_component(
                enemy_strength,
                friendly_strength,
                contested=True,
                weight=0.18,
                label="Enemy breach pressure",
            ),
            reserve_requirement_component(
                reserve_fraction,
                0.0,
                weight=-0.10,
                label="Reserve cost of the counterattack",
            ),
            doctrinal_bias_component(
                max(counterattack_bias, risk_acceptance),
                baseline=0.5,
                weight=0.24,
                label="Doctrinal bias toward local counterattack",
            ),
        ],
    )


def _is_own_objective_breach(
    snapshot: Any,
    side: str,
    control_by_location: Mapping[str, str | None],
) -> bool:
    for objective in list(getattr(snapshot, "objectives", []) or []):
        if not isinstance(objective, Mapping):
            continue
        location_id = str(objective.get("location_id", "")).strip()
        objective_side = str(objective.get("side", "")).upper().strip()
        if location_id and objective_side == side and control_by_location.get(location_id) != side:
            return True
    return False


def _primary_breach_location(
    snapshot: Any,
    side: str,
    control_by_location: Mapping[str, str | None],
    fallback: str,
) -> str:
    for objective in list(getattr(snapshot, "objectives", []) or []):
        if not isinstance(objective, Mapping):
            continue
        location_id = str(objective.get("location_id", "")).strip()
        objective_side = str(objective.get("side", "")).upper().strip()
        if location_id and objective_side == side and control_by_location.get(location_id) != side:
            return location_id
    return fallback


def _find_stronger_terrain_location(
    game_map: Any,
    friendly_units: Sequence[Any],
    known_locations: Sequence[str],
    main_objective: str,
) -> str | None:
    if game_map is None:
        return None
    current_score = terrain_value_for_location(game_map, main_objective)
    candidate_locations = {str(getattr(unit, "location_id", "") or "") for unit in friendly_units}
    candidate_locations.update(str(location) for location in known_locations)

    best_location = None
    best_score = current_score
    for location_id in sorted(candidate_locations):
        if not location_id or location_id == main_objective:
            continue
        score = terrain_value_for_location(game_map, location_id)
        if score > best_score:
            best_score = score
            best_location = location_id
    return best_location


def _best_supply_anchor(friendly_units: Sequence[Any], known_locations: Sequence[str]) -> str | None:
    if friendly_units:
        sorted_units = sorted(
            friendly_units,
            key=lambda unit: (
                float(getattr(unit, "supply", 0) or 0),
                float(getattr(unit, "readiness", 0) or 0),
                str(getattr(unit, "location_id", "") or ""),
            ),
        )
        location_id = str(getattr(sorted_units[0], "location_id", "") or "")
        if location_id:
            return location_id
    return str(known_locations[0]) if known_locations else None


def _control_map(
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    known_locations: Sequence[str],
    side: str,
) -> Dict[str, str | None]:
    control: Dict[str, str | None] = {}
    for location_id in known_locations:
        friendly_present = any(str(getattr(unit, "location_id", "") or "") == location_id for unit in friendly_units)
        enemy_present = any(str(getattr(unit, "location_id", "") or "") == location_id for unit in enemy_units)
        if friendly_present and not enemy_present:
            control[location_id] = side
        elif enemy_present and not friendly_present:
            control[location_id] = "ENEMY"
        else:
            control[location_id] = None
    return control


def _average_units(units: Sequence[Any], field_name: str, default: int) -> float:
    if not units:
        return float(default)
    total = 0.0
    for unit in units:
        total += float(getattr(getattr(unit, field_name, default), "value", getattr(unit, field_name, default)) or default)
    return total / len(units)


def _fallback_location(snapshot: Any) -> str:
    for unit in list(getattr(snapshot, "friendly_units", []) or []):
        location_id = str(getattr(unit, "location_id", "") or "")
        if location_id:
            return location_id
    known_locations = list(getattr(snapshot, "known_locations", []) or [])
    return str(known_locations[0]) if known_locations else ""


def _reserve_level_from_fraction(reserve_fraction: float, unit_count: int) -> str:
    if unit_count <= 0 or reserve_fraction <= 0:
        return "NONE"
    if reserve_fraction >= 0.4:
        return "HIGH"
    if reserve_fraction >= 0.2:
        return "MEDIUM"
    return "LOW"


__all__ = ["OperationalPlan", "plan_operational_layer"]
