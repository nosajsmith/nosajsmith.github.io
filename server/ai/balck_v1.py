from __future__ import annotations
from typing import Any, Dict, List


class BalckAIV1:
    """
    Phase 8.6: Balck AI v1 (Maneuver Kernel) for harness.
    Deterministic. No randomness.
    Uses scenario file ids for mini_gc_1942.
    """

    def __init__(self, side: str = "AXIS"):
        self.side = side

    def decide_orders(self, shell: Any, now_hours: int) -> List[Dict[str, Any]]:
        # mini_gc_1942 hardcoded ids
        axis_unit_id = "JP-35BDE"
        target_unit_id = "US-1MAR"

        # Shell currently does not expose EngineAPI; use scenario state for minimal v1.
        # If scenario doesn't contain units, return [].
        sc = getattr(shell, "scenario", None)
        if not isinstance(sc, dict):
            return []

        units = sc.get("units", [])
        if not isinstance(units, list):
            return []

        axis = None
        for u in units:
            if isinstance(u, dict) and str(u.get("id", "")).strip() == axis_unit_id:
                axis = u
                break

        if axis is None:
            return []

        fatigue = int(axis.get("fatigue", 0))
        readiness = int(axis.get("readiness", 0))
        supply = int(axis.get("supply", 0))

        if fatigue >= 70 or readiness <= 40 or supply <= 40:
            return [{
                "kind": "rest",
                "unit_id": axis_unit_id,
                "eta_hours": 6,
                "intent": "recover",
            }]

        return [{
            "kind": "attack",
            "unit_id": axis_unit_id,
            "eta_hours": 6,
            "intent": f"probe {target_unit_id}",
        }]
