from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, List, Tuple

from .models import ResolvedProfiles


DEFAULT_AXIS_CONFIG: Dict[str, Any] = {
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

DEFAULT_RUN_CONFIG: Dict[str, Any] = {
    "ai_side": None,
    "attack_supply_floor": 45,
    "attack_readiness_floor": 45,
    "rest_supply_floor": 25,
    "rest_fatigue_floor": 65,
    "fallback_posture": "HOLD",
}

SIDE_BY_FORCE = {
    "un": "ALLIED",
    "allied": "ALLIED",
    "us": "ALLIED",
    "south_korea": "ALLIED",
    "rok": "ALLIED",
    "nkpa": "AXIS",
    "north_korea": "AXIS",
    "kpa": "AXIS",
    "chinese": "AXIS",
    "prc": "AXIS",
    "axis": "AXIS",
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def apply_profile_overrides(
    resolved: ResolvedProfiles,
    *,
    axis_overrides: Dict[str, Any] | None = None,
    run_overrides: Dict[str, Any] | None = None,
) -> ResolvedProfiles:
    # Merge precedence is explicit and stable: doctrine -> personality -> tuning -> runtime overrides.
    axis_patch = dict(axis_overrides or {})
    run_patch = dict(run_overrides or {})
    if not axis_patch and not run_patch:
        return resolved

    warnings = list(getattr(resolved, "warnings", []) or [])
    if axis_patch:
        warnings.append("Applied runtime axis overrides.")
    if run_patch:
        warnings.append("Applied runtime run overrides.")

    return replace(
        resolved,
        merged_axis=_deep_merge(dict(resolved.merged_axis or {}), axis_patch),
        merged_run=_deep_merge(dict(resolved.merged_run or {}), run_patch),
        warnings=warnings,
    )


def _normalize_side(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"ALLIED", "AXIS"}:
        return raw
    raise ValueError(f"Unsupported AI side: {value!r}")


def _merged_metadata(resolved: ResolvedProfiles) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    metadata = _deep_merge(metadata, resolved.doctrine.metadata)
    metadata = _deep_merge(metadata, resolved.personality.metadata)
    metadata = _deep_merge(metadata, resolved.tuning.metadata)
    metadata.setdefault("doctrine_id", resolved.doctrine.name)
    metadata.setdefault("personality_id", resolved.personality.name)
    metadata.setdefault("tuning_id", resolved.tuning.name)
    return metadata


def _defaults_applied(defaults: Dict[str, Any], supplied: Dict[str, Any]) -> List[str]:
    return [key for key in defaults if key not in supplied]


def infer_ai_side(resolved: ResolvedProfiles, merged_run: Dict[str, Any], explicit_side: str | None = None) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    if explicit_side is not None:
        return _normalize_side(explicit_side), warnings

    raw_side = merged_run.get("ai_side")
    if raw_side not in (None, ""):
        try:
            return _normalize_side(raw_side), warnings
        except ValueError:
            warnings.append(f"Unsupported ai_side {raw_side!r}; falling back to inferred/default side.")

    historical_force = str(resolved.doctrine.metadata.get("historical_force", "")).strip().lower()
    if historical_force in SIDE_BY_FORCE:
        return SIDE_BY_FORCE[historical_force], warnings

    warnings.append("No explicit AI side configured; defaulting to ALLIED.")
    return "ALLIED", warnings


def merge_ai_config(resolved: ResolvedProfiles, *, side: str | None = None) -> Dict[str, Any]:
    axis = _deep_merge(DEFAULT_AXIS_CONFIG, resolved.merged_axis)
    run = _deep_merge(DEFAULT_RUN_CONFIG, resolved.merged_run)
    metadata = _merged_metadata(resolved)
    ai_side, side_warnings = infer_ai_side(resolved, run, explicit_side=side)
    run["ai_side"] = ai_side

    return {
        "profile_selection": {
            "doctrine": resolved.doctrine.name,
            "personality": resolved.personality.name,
            "tuning": resolved.tuning.name,
        },
        "ai_side": ai_side,
        "axis": axis,
        "run": run,
        "metadata": metadata,
        "defaults_applied": {
            "axis": _defaults_applied(DEFAULT_AXIS_CONFIG, resolved.merged_axis),
            "run": _defaults_applied(DEFAULT_RUN_CONFIG, resolved.merged_run),
        },
        "warnings": side_warnings,
    }


__all__ = ["DEFAULT_AXIS_CONFIG", "DEFAULT_RUN_CONFIG", "apply_profile_overrides", "infer_ai_side", "merge_ai_config"]
