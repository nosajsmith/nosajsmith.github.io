from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .bai_models import StrategicDirective
from .bai_eval import (
    build_evaluation,
    doctrinal_bias_component,
    enemy_threat_component,
    force_ratio_component,
    location_strength,
    objective_value_component,
    reserve_requirement_component,
    supply_feasibility_component,
    terrain_value_component,
)


STRATEGIC_POSTURES = {"OFFENSIVE", "DEFENSIVE", "CONTAIN"}


@dataclass
class StrategicMemory:
    side: str = ""
    posture: str = "CONTAIN"
    main_objective: str | None = None
    reserve_fraction: float = 0.25
    front_priority: str = "SCREEN"
    theater_priority: str = "STABILIZE"
    sticky_until_day: int = 0
    explanation: str = ""
    posture_rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_value(cls, value: Any) -> "StrategicMemory | None":
        if value is None:
            return None
        if isinstance(value, StrategicMemory):
            return value
        if not isinstance(value, Mapping):
            return None
        return cls(
            side=str(value.get("side") or ""),
            posture=_normalize_posture(value.get("posture") or "CONTAIN"),
            main_objective=_coerce_optional_text(value.get("main_objective")),
            reserve_fraction=_clamp_float(value.get("reserve_fraction"), 0.25, 0.05, 0.60),
            front_priority=str(value.get("front_priority") or "SCREEN"),
            theater_priority=str(value.get("theater_priority") or "STABILIZE"),
            sticky_until_day=int(value.get("sticky_until_day", 0) or 0),
            explanation=str(value.get("explanation") or ""),
            posture_rationale=str(value.get("posture_rationale") or ""),
        )


def plan_strategic_directive(
    snapshot: Any,
    runtime_profile: Mapping[str, Any] | None,
    previous_memory: StrategicMemory | Mapping[str, Any] | None = None,
) -> tuple[StrategicDirective, StrategicMemory]:
    profile = dict(runtime_profile or {})
    axis = dict(profile.get("axis") or {})
    thresholds = dict(profile.get("thresholds") or {})
    weights = dict(profile.get("weights") or {})
    memory = StrategicMemory.from_value(previous_memory)

    context = _build_context(snapshot, axis, thresholds, weights)
    sticky_days = 1 + int(round((1.0 - _fraction(axis.get("adaptation_rate"), 0.5)) * 2.0))

    recommended_posture, posture_rationale = _recommend_posture(context)
    recommended_objective, objective_explanation = _select_objective(context, recommended_posture)
    reserve_fraction = _reserve_fraction_for_posture(context, recommended_posture)
    front_priority = _front_priority(recommended_posture, recommended_objective)
    theater_priority = _theater_priority(recommended_posture)

    sticky_reason = ""
    if memory is not None and _should_keep_previous(memory, context, sticky_days):
        chosen_posture = memory.posture
        chosen_objective = memory.main_objective if memory.main_objective in context["known_locations"] else recommended_objective
        chosen_reserve_fraction = memory.reserve_fraction
        chosen_front_priority = memory.front_priority
        chosen_theater_priority = memory.theater_priority
        objective_explanation = memory.explanation or objective_explanation
        posture_rationale = memory.posture_rationale or posture_rationale
        sticky_reason = (
            f"Maintaining strategic direction through day {memory.sticky_until_day} "
            f"to avoid posture whiplash."
        )
    else:
        chosen_posture = recommended_posture
        chosen_objective = recommended_objective
        chosen_reserve_fraction = reserve_fraction
        chosen_front_priority = front_priority
        chosen_theater_priority = theater_priority
        sticky_reason = (
            f"New strategic directive established with {sticky_days}-day stickiness "
            f"based on adaptation rate {_fraction(axis.get('adaptation_rate'), 0.5):.2f}."
        )

    day = int(context["day"])
    chosen_objective = chosen_objective or _fallback_objective(context)

    directive = StrategicDirective(
        directive_id=f"{context['side'].lower()}_strategic_day_{day}",
        side=str(context["side"]),
        posture=chosen_posture,
        main_objective=chosen_objective,
        supporting_objectives=_supporting_objectives(context, chosen_objective),
        reserve_policy=f"retain_{chosen_reserve_fraction:.2f}_reserve",
        desired_end_state=_desired_end_state(chosen_posture, chosen_objective, day),
        horizon_turns=max(2, sticky_days),
        operation_window={"day": day, "phase": str(context["phase"]), "sticky_days": sticky_days},
        assumptions=[
            "Strategic AI Lite evaluates posture on a 10-90 day horizon.",
            "Directive changes are sticky unless the situation forces a shift.",
        ],
        notes=[
            f"Posture rationale: {posture_rationale}",
            f"Objective rationale: {objective_explanation}",
            f"Stickiness: {sticky_reason}",
        ],
        metadata={
            "front_priority": chosen_front_priority,
            "theater_priority": chosen_theater_priority,
            "reserve_fraction": chosen_reserve_fraction,
            "objective_explanation": objective_explanation,
            "posture_rationale": posture_rationale,
            "sticky_reason": sticky_reason,
            "candidate_scores": list(context["candidate_summaries"]),
        },
    )

    updated_memory = StrategicMemory(
        side=str(context["side"]),
        posture=chosen_posture,
        main_objective=chosen_objective,
        reserve_fraction=chosen_reserve_fraction,
        front_priority=chosen_front_priority,
        theater_priority=chosen_theater_priority,
        sticky_until_day=day + sticky_days,
        explanation=objective_explanation,
        posture_rationale=posture_rationale,
    )
    return directive, updated_memory


def _build_context(
    snapshot: Any,
    axis: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    weights: Mapping[str, Any],
) -> Dict[str, Any]:
    side = str(getattr(snapshot, "side", "") or "")
    day = int(getattr(snapshot, "day", 1) or 1)
    phase = str(getattr(snapshot, "phase", "day") or "day")
    friendly_units = list(getattr(snapshot, "friendly_units", []) or [])
    enemy_units = list(getattr(snapshot, "enemy_units", []) or [])
    known_locations = list(getattr(snapshot, "known_locations", []) or [])
    game_map = getattr(snapshot, "game_map", None)

    avg_supply = _average_units(friendly_units, "supply", 50)
    avg_readiness = _average_units(friendly_units, "readiness", 50)
    avg_fatigue = _average_units(friendly_units, "fatigue", 0)

    control_by_location = _control_map(friendly_units, enemy_units, known_locations, side)
    candidates = _build_location_candidates(
        side=side,
        objectives=list(getattr(snapshot, "objectives", []) or []),
        control_by_location=control_by_location,
        game_map=game_map,
        friendly_units=friendly_units,
        enemy_units=enemy_units,
        thresholds=thresholds,
        axis=axis,
        avg_supply=avg_supply,
        weights=weights,
    )

    own_objective_under_pressure = any(
        candidate["own_value"] > 0 and candidate["control"] != side for candidate in candidates.values()
    )
    enemy_objective_held = any(
        candidate["enemy_value"] > 0 and candidate["control"] == "ENEMY" for candidate in candidates.values()
    )

    return {
        "side": side,
        "day": day,
        "phase": phase,
        "friendly_units": friendly_units,
        "enemy_units": enemy_units,
        "known_locations": known_locations,
        "game_map": game_map,
        "axis": dict(axis),
        "thresholds": dict(thresholds),
        "weights": dict(weights),
        "avg_supply": avg_supply,
        "avg_readiness": avg_readiness,
        "avg_fatigue": avg_fatigue,
        "control_by_location": control_by_location,
        "candidates": candidates,
        "candidate_summaries": [
            {
                "location_id": location_id,
                "offensive_score": round(candidate["offensive_score"], 3),
                "defensive_score": round(candidate["defensive_score"], 3),
                "contain_score": round(candidate["contain_score"], 3),
                "control": candidate["control"],
                "offensive_reason": candidate["offensive_eval"]["dominant_reason"],
                "defensive_reason": candidate["defensive_eval"]["dominant_reason"],
                "contain_reason": candidate["contain_eval"]["dominant_reason"],
            }
            for location_id, candidate in sorted(candidates.items())
        ],
        "own_objective_under_pressure": own_objective_under_pressure,
        "enemy_objective_held": enemy_objective_held,
    }


def _recommend_posture(context: Mapping[str, Any]) -> tuple[str, str]:
    avg_supply = float(context["avg_supply"])
    avg_readiness = float(context["avg_readiness"])
    avg_fatigue = float(context["avg_fatigue"])
    thresholds = dict(context["thresholds"])
    axis = dict(context["axis"])
    weights = dict(context["weights"])

    attack_supply_floor = int(thresholds.get("attack_supply_floor", 45))
    attack_readiness_floor = int(thresholds.get("attack_readiness_floor", 45))
    defend_supply_floor = int(thresholds.get("defend_supply_floor", 35))
    rest_supply_floor = int(thresholds.get("rest_supply_floor", 25))
    rest_fatigue_floor = int(thresholds.get("rest_fatigue_floor", 65))

    aggression = _fraction(axis.get("aggression"), 0.5)
    caution_bias = _fraction(axis.get("caution_bias"), 0.5)
    risk_acceptance = float(weights.get("risk_acceptance", 1.0))

    if avg_supply < rest_supply_floor or avg_fatigue > rest_fatigue_floor:
        return "DEFENSIVE", "Combat power is degraded enough that the theater must stabilize first."
    if context["own_objective_under_pressure"]:
        return "DEFENSIVE", "A friendly objective is not securely held, so the theater priority shifts to defense."
    if avg_supply < defend_supply_floor or avg_readiness < defend_supply_floor:
        return "DEFENSIVE", "Supply/readiness is below the defensive floor, so a conservative posture is required."
    if caution_bias >= 0.72:
        return "DEFENSIVE", "Personality caution bias favors preserving the line over pushing forward."
    if (
        context["enemy_objective_held"]
        and aggression >= 0.55
        and risk_acceptance >= 0.95
        and avg_supply >= attack_supply_floor
        and avg_readiness >= attack_readiness_floor
        and avg_fatigue <= 55
    ):
        return "OFFENSIVE", "Enemy-held objectives remain viable and current combat power supports offensive action."
    return "CONTAIN", "The force can pressure the enemy, but the situation does not justify a full offensive shift."


def _select_objective(context: Mapping[str, Any], posture: str) -> tuple[str | None, str]:
    candidates = dict(context["candidates"])
    if not candidates:
        return _fallback_objective(context), "No objective list was available, so the current line is treated as the main objective."

    posture_key = posture.lower()
    score_key = f"{posture_key}_score"
    ranked = sorted(
        candidates.items(),
        key=lambda item: (float(item[1].get(score_key, 0.0)), float(item[1].get("offensive_score", 0.0))),
        reverse=True,
    )
    location_id, candidate = ranked[0]
    explanation = _objective_explanation(posture, location_id, candidate)
    return location_id, explanation


def _reserve_fraction_for_posture(context: Mapping[str, Any], posture: str) -> float:
    base = _clamp_float(context["thresholds"].get("reserve_target_fraction"), 0.25, 0.10, 0.60)
    axis = dict(context["axis"])
    reserve_commitment = _fraction(axis.get("reserve_commitment"), 0.5)
    reserve_preservation = _fraction(axis.get("reserve_preservation_bias"), 0.5)

    if posture == "OFFENSIVE":
        return round(max(0.08, base - (reserve_commitment * 0.12) + (reserve_preservation * 0.03) - 0.04), 3)
    if posture == "DEFENSIVE":
        return round(min(0.60, base + (reserve_preservation * 0.10) + 0.06), 3)
    return round(min(0.50, max(0.12, base + (reserve_preservation - reserve_commitment) * 0.05)), 3)


def _front_priority(posture: str, objective: str | None) -> str:
    objective_value = str(objective or "CURRENT_LINE")
    if posture == "OFFENSIVE":
        return f"MAIN_EFFORT::{objective_value}"
    if posture == "DEFENSIVE":
        return f"HOLD::{objective_value}"
    return f"SCREEN::{objective_value}"


def _theater_priority(posture: str) -> str:
    if posture == "OFFENSIVE":
        return "DECISIVE_ACTION"
    if posture == "DEFENSIVE":
        return "THEATER_STABILIZATION"
    return "CONTAIN_AND_SHAPE"


def _supporting_objectives(context: Mapping[str, Any], main_objective: str | None) -> List[str]:
    candidates = dict(context["candidates"])
    ranked = sorted(
        (
            (location_id, max(candidate["offensive_score"], candidate["defensive_score"], candidate["contain_score"]))
            for location_id, candidate in candidates.items()
            if location_id != main_objective
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return [location_id for location_id, _score in ranked[:2]]


def _desired_end_state(posture: str, objective: str | None, day: int) -> str:
    target = str(objective or "the current line")
    if posture == "OFFENSIVE":
        return f"Shape the theater for decisive gains against {target} after day {day}."
    if posture == "DEFENSIVE":
        return f"Prevent line collapse and retain control of {target} through day {day}."
    return f"Contain the enemy and preserve options around {target} through day {day}."


def _should_keep_previous(memory: StrategicMemory, context: Mapping[str, Any], sticky_days: int) -> bool:
    day = int(context["day"])
    if memory.main_objective is None:
        return False
    if memory.main_objective not in context["known_locations"]:
        return False
    if day > memory.sticky_until_day:
        return False
    if context["own_objective_under_pressure"] and memory.posture == "OFFENSIVE":
        return False
    if float(context["avg_supply"]) < int(context["thresholds"].get("rest_supply_floor", 25)):
        return memory.posture != "OFFENSIVE"
    return sticky_days >= 1


def _build_location_candidates(
    *,
    side: str,
    objectives: Sequence[Mapping[str, Any]],
    control_by_location: Mapping[str, str | None],
    game_map: Any,
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    thresholds: Mapping[str, Any],
    axis: Mapping[str, Any],
    avg_supply: float,
    weights: Mapping[str, Any],
) -> Dict[str, Dict[str, Any]]:
    objective_value_weight = float(weights.get("objective_value", 1.0))
    contested_weight = float(weights.get("contested_objective", 1.0))
    enemy_weight = float(weights.get("enemy_objective", 1.0))
    infiltration_weight = float(weights.get("infiltration", 1.0))
    reserve_weight = float(weights.get("reserve", 1.0))
    reserve_target_fraction = _clamp_float(thresholds.get("reserve_target_fraction"), 0.25, 0.10, 0.60)
    attack_supply_floor = int(thresholds.get("attack_supply_floor", 45))
    defend_supply_floor = int(thresholds.get("defend_supply_floor", 35))
    aggression = _fraction(axis.get("aggression"), 0.5)
    caution_bias = _fraction(axis.get("caution_bias"), 0.5)
    breakthrough_focus = _fraction(axis.get("breakthrough_focus"), 0.5)
    reserve_preservation = _fraction(axis.get("reserve_preservation_bias"), 0.5)

    candidates: Dict[str, Dict[str, Any]] = {}
    for objective in objectives:
        if not isinstance(objective, Mapping):
            continue
        location_id = str(objective.get("location_id", "")).strip()
        if not location_id:
            continue
        desired_side = str(objective.get("side", "")).upper().strip()
        value = float(objective.get("value", 0) or 0)
        candidate = candidates.setdefault(
            location_id,
            {
                "location_id": location_id,
                "own_value": 0.0,
                "enemy_value": 0.0,
                "control": control_by_location.get(location_id),
                "objective_count": 0,
            },
        )
        candidate["objective_count"] += 1
        if desired_side == side:
            candidate["own_value"] += value
        else:
            candidate["enemy_value"] += value

    for candidate in candidates.values():
        location_id = str(candidate["location_id"])
        control = candidate["control"]
        own_value = float(candidate["own_value"])
        enemy_value = float(candidate["enemy_value"])
        friendly_strength = location_strength(friendly_units, location_id)
        enemy_strength = location_strength(enemy_units, location_id)
        contested = control is None

        offensive_eval = build_evaluation(
            f"offensive::{location_id}",
            base=0.18 if control == "ENEMY" else 0.08,
            components=[
                objective_value_component(
                    enemy_value,
                    weight=objective_value_weight * enemy_weight,
                    label=f"Enemy objective value at {location_id}",
                ),
                terrain_value_component(
                    game_map,
                    location_id,
                    weight=-0.16,
                    label="Defensive terrain resistance",
                ),
                force_ratio_component(
                    friendly_strength,
                    enemy_strength,
                    weight=0.34,
                    label=f"Attack force ratio at {location_id}",
                ),
                supply_feasibility_component(
                    avg_supply,
                    floor=attack_supply_floor,
                    weight=0.30,
                    label="Offensive supply feasibility",
                ),
                enemy_threat_component(
                    enemy_strength,
                    friendly_strength,
                    contested=contested,
                    weight=-0.20,
                    label="Enemy threat to an attack",
                ),
                reserve_requirement_component(
                    reserve_target_fraction,
                    0.0,
                    weight=-0.16 * reserve_weight,
                    label="Reserve retained for offensive reach",
                ),
                doctrinal_bias_component(
                    max(aggression, breakthrough_focus),
                    weight=0.34,
                    label="Offensive doctrinal bias",
                ),
            ],
        )
        defensive_eval = build_evaluation(
            f"defensive::{location_id}",
            base=0.08 if own_value > 0 else 0.0,
            components=[
                objective_value_component(
                    own_value,
                    weight=objective_value_weight * contested_weight,
                    label=f"Friendly objective value at {location_id}",
                ),
                terrain_value_component(
                    game_map,
                    location_id,
                    weight=0.26,
                    label="Defensive terrain value",
                ),
                force_ratio_component(
                    friendly_strength,
                    enemy_strength,
                    weight=-0.18,
                    label=f"Defensive force ratio at {location_id}",
                ),
                supply_feasibility_component(
                    avg_supply,
                    floor=defend_supply_floor,
                    weight=0.14,
                    label="Defensive supply feasibility",
                ),
                enemy_threat_component(
                    enemy_strength,
                    friendly_strength,
                    contested=contested or (own_value > 0 and control != side),
                    weight=0.48,
                    label="Enemy pressure on the line",
                ),
                reserve_requirement_component(
                    reserve_target_fraction,
                    0.0,
                    weight=0.22 * reserve_weight,
                    label="Reserve needed to stabilize the line",
                ),
                doctrinal_bias_component(
                    caution_bias,
                    weight=0.28,
                    label="Defensive doctrinal bias",
                ),
            ],
        )
        contain_eval = build_evaluation(
            f"contain::{location_id}",
            base=0.06,
            components=[
                objective_value_component(
                    own_value + enemy_value,
                    weight=objective_value_weight * 0.65,
                    label=f"Shared objective value at {location_id}",
                ),
                terrain_value_component(
                    game_map,
                    location_id,
                    weight=0.12,
                    label="Terrain anchor value",
                ),
                force_ratio_component(
                    friendly_strength,
                    enemy_strength,
                    weight=0.06,
                    label=f"Contain force ratio at {location_id}",
                ),
                supply_feasibility_component(
                    avg_supply,
                    floor=defend_supply_floor,
                    weight=0.18,
                    label="Containment supply feasibility",
                ),
                enemy_threat_component(
                    enemy_strength,
                    friendly_strength,
                    contested=contested,
                    weight=0.28,
                    label="Enemy pressure shaping the front",
                ),
                reserve_requirement_component(
                    reserve_target_fraction,
                    0.0,
                    weight=0.18 * reserve_weight,
                    label="Reserve needed to preserve options",
                ),
                doctrinal_bias_component(
                    (aggression + caution_bias + reserve_preservation) / 3.0,
                    weight=0.16,
                    label="Containment doctrinal bias",
                ),
                objective_value_component(
                    max(own_value, enemy_value) if contested else 0.0,
                    weight=max(contested_weight, infiltration_weight) * 0.35,
                    label=f"Contested leverage at {location_id}",
                ),
            ],
        )

        candidate["offensive_score"] = offensive_eval.total
        candidate["defensive_score"] = defensive_eval.total
        candidate["contain_score"] = contain_eval.total
        candidate["offensive_eval"] = offensive_eval.to_dict()
        candidate["defensive_eval"] = defensive_eval.to_dict()
        candidate["contain_eval"] = contain_eval.to_dict()

    return candidates


def _objective_explanation(posture: str, location_id: str, candidate: Mapping[str, Any]) -> str:
    control = candidate.get("control")
    own_value = float(candidate.get("own_value", 0.0) or 0.0)
    enemy_value = float(candidate.get("enemy_value", 0.0) or 0.0)
    posture_eval = dict(candidate.get(f"{posture.lower()}_eval", {}) or {})
    dominant_reason = str(posture_eval.get("dominant_reason") or "").strip()

    if posture == "OFFENSIVE":
        if control == "ENEMY":
            return f"{location_id} is enemy-held and carries offensive value {enemy_value:.0f}; {dominant_reason or 'it is the clearest decisive target.'}"
        return f"{location_id} offers the best offensive leverage with score {float(candidate.get('offensive_score', 0.0)):.2f}. {dominant_reason}".strip()
    if posture == "DEFENSIVE":
        if own_value > 0:
            return f"{location_id} protects friendly objective value {own_value:.0f}; {dominant_reason or 'it anchors the defensive plan.'}"
        return f"{location_id} is the most vulnerable sector to stabilize first. {dominant_reason}".strip()
    return (
        f"{location_id} balances pressure and preservation with offensive value {enemy_value:.0f} "
        f"and friendly stake {own_value:.0f}. {dominant_reason}".strip()
    )


def _control_map(
    friendly_units: Sequence[Any],
    enemy_units: Sequence[Any],
    known_locations: Sequence[str],
    side: str,
) -> Dict[str, str | None]:
    control: Dict[str, str | None] = {}
    for location_id in known_locations:
        friendly_present = any(_unit_location(unit) == location_id for unit in friendly_units)
        enemy_present = any(_unit_location(unit) == location_id for unit in enemy_units)
        if friendly_present and not enemy_present:
            control[location_id] = side
        elif enemy_present and not friendly_present:
            control[location_id] = "ENEMY"
        else:
            control[location_id] = None
    return control


def _fallback_objective(context: Mapping[str, Any]) -> str | None:
    friendly_units = list(context.get("friendly_units", []) or [])
    if not friendly_units:
        return None
    for unit in friendly_units:
        location_id = _unit_location(unit)
        if location_id:
            return location_id
    return None


def _average_units(units: Sequence[Any], field_name: str, default: int) -> float:
    if not units:
        return float(default)
    total = 0.0
    for unit in units:
        total += float(getattr(getattr(unit, field_name, default), "value", getattr(unit, field_name, default)) or default)
    return total / len(units)


def _unit_location(unit: Any) -> str:
    return str(getattr(getattr(unit, "location_id", ""), "value", getattr(unit, "location_id", "")) or "")


def _fraction(value: Any, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return max(0.0, min(1.0, numeric))


def _clamp_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return round(max(low, min(high, numeric)), 3)


def _normalize_posture(value: Any) -> str:
    raw = str(value or "CONTAIN").upper().strip()
    return raw if raw in STRATEGIC_POSTURES else "CONTAIN"


def _coerce_optional_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


__all__ = ["STRATEGIC_POSTURES", "StrategicMemory", "plan_strategic_directive"]
