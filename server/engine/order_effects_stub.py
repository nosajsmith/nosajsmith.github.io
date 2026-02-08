from __future__ import annotations
from typing import Any, Dict, Tuple


def clamp_0_100(v: Any) -> int:
    try:
        iv = int(round(float(v)))
    except Exception:
        iv = 0
    if iv < 0:
        return 0
    if iv > 100:
        return 100
    return iv


def effect_delta(kind: str) -> Tuple[Dict[str, int], str]:
    """
    Phase 8.5 stub deltas.
    Returns (delta_dict, note).
    """
    dk = (kind or "").strip()

    if dk.startswith("attack"):
        return ({"fatigue": 10, "readiness": -6, "morale": -2, "supply": -4}, "attack_stub")
    if dk == "rest":
        return ({"fatigue": -15, "readiness": 10, "morale": 2, "supply": 0}, "rest_stub")
    if dk == "withdraw":
        return ({"fatigue": 6, "readiness": -3, "morale": -1, "supply": -2}, "withdraw_stub")
    if dk == "delay":
        return ({"fatigue": 3, "readiness": -1, "morale": 0, "supply": -1}, "delay_stub")
    if dk == "defend":
        return ({"fatigue": 2, "readiness": -1, "morale": 0, "supply": -1}, "defend_stub")
    if dk == "reposition":
        return ({"fatigue": 4, "readiness": -3, "morale": -1, "supply": -2}, "reposition_stub")

    return ({"fatigue": 0, "readiness": 0, "morale": 0, "supply": 0}, "no_effect_stub")
