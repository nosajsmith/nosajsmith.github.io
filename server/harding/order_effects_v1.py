from __future__ import annotations
from typing import Any, Dict


def _clamp(v: Any) -> int:
    try:
        iv = int(round(float(v)))
    except Exception:
        iv = 0
    if iv < 0:
        return 0
    if iv > 100:
        return 100
    return iv


def apply_effect_to_unit(unit: Dict[str, Any], kind: str) -> Dict[str, Any]:
    """
    Phase 9.1: deterministic, coarse wear-and-tear.
    No combat math. Just makes repeated action hurt.
    """
    dk = (kind or "").strip()
    before = {
        "fatigue": int(unit.get("fatigue", 0)),
        "readiness": int(unit.get("readiness", 50)),
        "morale": int(unit.get("morale", 50)),
        "supply": int(unit.get("supply", 50)),
        "strength": int(unit.get("strength", 100)),
    }

    # Baseline deltas (small but meaningful)
    df, dr, dm, ds, dstr = 0, 0, 0, 0, 0

    if dk.startswith("attack"):
        df, dr, dm, ds, dstr = +10, -8, -2, -4, -2
    elif dk == "rest":
        df, dr, dm, ds, dstr = -12, +8, +1, +0, +0
    elif dk in ("defend", "delay"):
        df, dr, dm, ds, dstr = +3, -2, 0, -1, 0
    elif dk == "withdraw":
        df, dr, dm, ds, dstr = +6, -3, -1, -2, -1
    elif dk == "reposition":
        df, dr, dm, ds, dstr = +4, -3, -1, -2, 0

    after = {
        "fatigue": _clamp(before["fatigue"] + df),
        "readiness": _clamp(before["readiness"] + dr),
        "morale": _clamp(before["morale"] + dm),
        "supply": _clamp(before["supply"] + ds),
        # strength is 0..100-ish in your scenario; clamp similarly
        "strength": max(0, min(100, before["strength"] + dstr)),
    }

    unit["fatigue"] = after["fatigue"]
    unit["readiness"] = after["readiness"]
    unit["morale"] = after["morale"]
    unit["supply"] = after["supply"]
    unit["strength"] = after["strength"]

    return {"before": before, "after": after, "delta": {k: after[k] - before[k] for k in after}}
