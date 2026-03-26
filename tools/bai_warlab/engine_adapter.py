from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .config_merge import merge_ai_config
from .models import ResolvedProfiles


def inject_engine_config(
    *,
    state: Dict[str, Any],
    resolved: ResolvedProfiles,
    logs: List[Dict[str, Any]],
    side: str | None = None,
) -> Dict[str, Any]:
    engine_config = merge_ai_config(resolved, side=side)
    state["engine_config"] = engine_config
    state["ai_side"] = engine_config["ai_side"]
    state["profile_selection"] = dict(engine_config["profile_selection"])
    logs.append(
        {
            "src": "ENGINE_ADAPTER",
            "turn": 0,
            "phase": "config",
            "message": (
                f"Injected AI config for side={engine_config['ai_side']} "
                f"doctrine={resolved.doctrine.name} personality={resolved.personality.name} tuning={resolved.tuning.name}"
            ),
        }
    )
    return engine_config


def _choose_posture(unit: Dict[str, Any], engine_config: Dict[str, Any], day: int) -> str:
    axis = dict(engine_config.get("axis") or {})
    run = dict(engine_config.get("run") or {})
    supply = int(unit.get("supply", 0))
    readiness = int(unit.get("readiness", 0))
    fatigue = int(unit.get("fatigue", 0))

    if supply < int(run.get("rest_supply_floor", 25)) or fatigue > int(run.get("rest_fatigue_floor", 65)):
        return "REST" if float(axis.get("reserve_preservation_bias", 0.5)) >= 0.55 else "DEFEND"

    if float(axis.get("aggression", 0.5)) >= 0.72 and supply >= int(run.get("attack_supply_floor", 45)) and readiness >= int(run.get("attack_readiness_floor", 45)):
        return "ATTACK"

    if float(axis.get("infiltration_bias", 0.5)) >= 0.75 and day % 2 == 1:
        return "MOVE"

    if float(axis.get("caution_bias", 0.5)) >= 0.68:
        return "DEFEND"

    if float(axis.get("breakthrough_focus", 0.5)) >= 0.7:
        return "ATTACK"

    if float(axis.get("adaptation_rate", 0.5)) >= 0.8:
        return "MOVE" if day % 2 == 0 else "DEFEND"

    fallback = str(run.get("fallback_posture", "HOLD")).strip().upper()
    return fallback if fallback in {"HOLD", "MOVE", "ATTACK", "DEFEND", "REST", "REFIT"} else "HOLD"


def apply_ai_config_policy(state: Dict[str, Any], day: int, logs: List[Dict[str, Any]]) -> None:
    engine_config = dict(state.get("engine_config") or {})
    ai_side = str(engine_config.get("ai_side") or "").strip().upper()
    if ai_side not in {"ALLIED", "AXIS"}:
        return

    changed = 0
    posture_counts: Counter[str] = Counter()
    for unit in state.get("units", []):
        if unit.get("side") != ai_side:
            continue
        posture = _choose_posture(unit, engine_config, day)
        posture_counts[posture] += 1
        if unit.get("posture") != posture:
            unit["posture"] = posture
            changed += 1

    logs.append(
        {
            "src": "ENGINE_ADAPTER",
            "turn": day,
            "phase": "policy",
            "message": f"Applied AI posture policy to side={ai_side}; changed={changed}; postures={dict(posture_counts)}",
        }
    )


__all__ = ["apply_ai_config_policy", "inject_engine_config"]
