from __future__ import annotations
from typing import Any, Dict, List, Tuple


def _infer_side(u: Dict[str, Any]) -> str:
    # Prefer explicit side field if present
    side = u.get("side")
    if isinstance(side, str) and side.strip():
        return side.strip().upper()

    uid = str(u.get("id", "")).upper()
    if uid.startswith("US-") or uid.startswith("ALL-"):
        return "ALLIED"
    if uid.startswith("JP-") or uid.startswith("AX-"):
        return "AXIS"
    return "UNKNOWN"


def _units_for_side(scenario: Dict[str, Any], side: str) -> List[Dict[str, Any]]:
    units = scenario.get("units", [])
    if not isinstance(units, list):
        return []
    out: List[Dict[str, Any]] = []
    for u in units:
        if isinstance(u, dict) and _infer_side(u) == side:
            out.append(u)
    return out


def snapshot_side_metrics(scenario: Dict[str, Any], side: str) -> Dict[str, Any]:
    us = _units_for_side(scenario, side)
    if not us:
        return {"side": side, "count": 0, "strength": 0, "avg_supply": 0, "avg_readiness": 0}

    strength = sum(int(u.get("strength", 0)) for u in us)
    avg_supply = sum(int(u.get("supply", 0)) for u in us) / len(us)
    avg_readiness = sum(int(u.get("readiness", 0)) for u in us) / len(us)

    return {
        "side": side,
        "count": len(us),
        "strength": int(strength),
        "avg_supply": float(avg_supply),
        "avg_readiness": float(avg_readiness),
    }


def evaluate_collapse(
    scenario: Dict[str, Any],
    side: str,
    baseline_strength: int,
    thresholds: Dict[str, Any] | None = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Returns (is_loss, details)
    """
    th = thresholds or {
        "min_strength_ratio": 0.70,
        "min_avg_supply": 30.0,
        "min_avg_readiness": 25.0,
    }

    m = snapshot_side_metrics(scenario, side)

    strength_now = int(m["strength"])
    strength_ratio = (strength_now / baseline_strength) if baseline_strength > 0 else 1.0

    avg_supply = float(m["avg_supply"])
    avg_read = float(m["avg_readiness"])

    reasons = []
    if strength_ratio <= float(th["min_strength_ratio"]):
        reasons.append(f"force_integrity {strength_ratio:.2f} <= {float(th['min_strength_ratio']):.2f}")
    if avg_supply <= float(th["min_avg_supply"]):
        reasons.append(f"supply_collapse {avg_supply:.1f} <= {float(th['min_avg_supply']):.1f}")
    if avg_read <= float(th["min_avg_readiness"]):
        reasons.append(f"cohesion_collapse {avg_read:.1f} <= {float(th['min_avg_readiness']):.1f}")

    is_loss = len(reasons) > 0
    details = {
        "metrics": m,
        "baseline_strength": int(baseline_strength),
        "strength_ratio": float(strength_ratio),
        "thresholds": th,
        "reasons": reasons,
    }
    return is_loss, details
