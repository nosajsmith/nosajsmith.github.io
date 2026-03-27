from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping


DEFAULT_DOCTRINE_AXIS: Dict[str, Any] = {
    "aggression": 0.5,
    "caution_bias": 0.5,
    "counterattack_bias": 0.5,
    "reserve_preservation_bias": 0.5,
    "reserve_commitment": 0.5,
    "adaptation_rate": 0.5,
    "risk_tolerance": 0.5,
    "logistics_emphasis": 0.5,
    "artillery_preparation": 0.5,
    "infiltration_bias": 0.5,
    "objective_discipline": 0.5,
    "breakthrough_focus": 0.5,
    "tempo_bias": "balanced",
}

DEFAULT_DOCTRINE_RUN: Dict[str, Any] = {
    "attack_supply_floor": 45,
    "attack_readiness_floor": 45,
    "rest_supply_floor": 25,
    "rest_fatigue_floor": 65,
    "fallback_posture": "HOLD",
}


def build_doctrine_profile(engine_config: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    config = _coerce_mapping(engine_config)
    doctrine = _coerce_mapping(config.get("doctrine"))
    metadata = _deep_merge(_coerce_mapping(config.get("metadata")), _coerce_mapping(doctrine.get("metadata")))

    axis = _deep_merge(DEFAULT_DOCTRINE_AXIS, _coerce_mapping(doctrine.get("axis")))
    run = _deep_merge(DEFAULT_DOCTRINE_RUN, _coerce_mapping(doctrine.get("run")))

    profile = {
        "axis": _normalize_axis(axis),
        "run": _normalize_run(run),
        "metadata": metadata,
        "profile_selection": dict(_coerce_mapping(config.get("profile_selection"))),
        "sources": {
            "defaults": True,
            "doctrine": bool(doctrine),
        },
        "warnings": [],
    }
    profile.update(derive_behavior_values(profile["axis"], profile["run"]))
    return profile


def derive_behavior_values(axis: Mapping[str, Any], run: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    aggression = _fraction(axis.get("aggression"), 0.5)
    caution_bias = _fraction(axis.get("caution_bias"), 0.5)
    counterattack_bias = _fraction(axis.get("counterattack_bias"), 0.5)
    reserve_preservation_bias = _fraction(axis.get("reserve_preservation_bias"), 0.5)
    reserve_commitment = _fraction(axis.get("reserve_commitment"), 0.5)
    adaptation_rate = _fraction(axis.get("adaptation_rate"), 0.5)
    risk_tolerance = _fraction(axis.get("risk_tolerance"), 0.5)
    logistics_emphasis = _fraction(axis.get("logistics_emphasis"), 0.5)
    artillery_preparation = _fraction(axis.get("artillery_preparation"), 0.5)
    infiltration_bias = _fraction(axis.get("infiltration_bias"), 0.5)
    objective_discipline = _fraction(axis.get("objective_discipline"), 0.5)
    breakthrough_focus = _fraction(axis.get("breakthrough_focus"), 0.5)

    thresholds = {
        "attack_supply_floor": int(
            round(
                _clamp(
                    _int_value(run.get("attack_supply_floor"), 45)
                    + (logistics_emphasis * 8.0)
                    + (caution_bias * 8.0)
                    - (aggression * 10.0)
                    - (risk_tolerance * 6.0),
                    20,
                    80,
                )
            )
        ),
        "attack_readiness_floor": int(
            round(
                _clamp(
                    _int_value(run.get("attack_readiness_floor"), 45)
                    + (caution_bias * 12.0)
                    - (aggression * 10.0)
                    - (adaptation_rate * 4.0),
                    20,
                    90,
                )
            )
        ),
        "defend_supply_floor": int(round(_clamp(28 + (logistics_emphasis * 16.0) + (caution_bias * 10.0), 15, 80))),
        "rest_supply_floor": int(
            round(
                _clamp(
                    _int_value(run.get("rest_supply_floor"), 25)
                    + (caution_bias * 10.0)
                    + (logistics_emphasis * 6.0)
                    - (aggression * 4.0),
                    10,
                    60,
                )
            )
        ),
        "rest_fatigue_floor": int(
            round(
                _clamp(
                    _int_value(run.get("rest_fatigue_floor"), 65)
                    + (reserve_preservation_bias * 12.0)
                    + (caution_bias * 8.0)
                    - (aggression * 8.0),
                    35,
                    95,
                )
            )
        ),
        "reserve_target_fraction": round(
            _clamp(
                0.15 + (reserve_preservation_bias * 0.35) - (reserve_commitment * 0.15),
                0.10,
                0.60,
            ),
            3,
        ),
    }

    weights = {
        "objective_value": round(_clamp(1.0 + (objective_discipline * 1.0), 0.5, 2.5), 3),
        "contested_objective": round(_clamp(1.0 + (counterattack_bias * 0.8) + (caution_bias * 0.2), 0.5, 2.5), 3),
        "enemy_objective": round(_clamp(1.0 + (aggression * 0.8) + (breakthrough_focus * 0.7), 0.5, 2.5), 3),
        "reserve": round(_clamp(1.0 + (reserve_preservation_bias * 0.9) - (reserve_commitment * 0.6), 0.5, 2.5), 3),
        "infiltration": round(_clamp(1.0 + (infiltration_bias * 1.2), 0.5, 2.5), 3),
        "artillery": round(_clamp(1.0 + (artillery_preparation * 0.8), 0.5, 2.0), 3),
        "logistics": round(_clamp(1.0 + (logistics_emphasis * 1.0), 0.5, 2.0), 3),
        "risk_acceptance": round(_clamp(0.8 + (risk_tolerance * 1.2) - (caution_bias * 0.5), 0.4, 2.0), 3),
    }

    return {"thresholds": thresholds, "weights": weights}


def _normalize_axis(raw_axis: Mapping[str, Any]) -> Dict[str, Any]:
    axis = dict(DEFAULT_DOCTRINE_AXIS)
    for key, default in DEFAULT_DOCTRINE_AXIS.items():
        value = raw_axis.get(key, default)
        if isinstance(default, str):
            axis[key] = str(value or default).strip() or default
        else:
            axis[key] = _fraction(value, default)
    return axis


def _normalize_run(raw_run: Mapping[str, Any]) -> Dict[str, Any]:
    run = dict(DEFAULT_DOCTRINE_RUN)
    for key, default in DEFAULT_DOCTRINE_RUN.items():
        value = raw_run.get(key, default)
        if isinstance(default, str):
            normalized = str(value or default).upper().strip()
            run[key] = normalized if normalized in {"HOLD", "MOVE", "ATTACK", "DEFEND", "REST", "REFIT"} else default
        else:
            run[key] = _int_value(value, default)
    return run


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(dict(merged[key]), value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _fraction(value: Any, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float(default)
    return round(_clamp(numeric, 0.0, 1.0), 3)


def _int_value(value: Any, default: int) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return int(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


__all__ = ["DEFAULT_DOCTRINE_AXIS", "DEFAULT_DOCTRINE_RUN", "build_doctrine_profile", "derive_behavior_values"]
