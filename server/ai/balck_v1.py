from __future__ import annotations
from typing import Any, Dict, List


class BalckAIV1:
    """
    Phase 8.6–9.4: Balck AI v1 (Maneuver Kernel) for harness/kernel.
    Deterministic. No randomness.
    Uses scenario file ids for mini_gc_1942 and objective/score awareness (9.4).
    """

    def __init__(self, side: str = "AXIS"):
        self.side = side

    def decide_orders(self, shell: Any, now_hours: int) -> List[Dict[str, Any]]:
        axis_unit_id = "JP-35BDE"
        target_unit_id = "US-1MAR"

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

        # 1) Always recover if in bad condition
        if fatigue >= 70 or readiness <= 40 or supply <= 40:
            return [{
                "kind": "rest",
                "unit_id": axis_unit_id,
                "eta_hours": 6,
                "intent": "recover",
            }]

        # 2) Objective/score awareness (Phase 9.4)
        obj = getattr(shell, "objective_state", {}) if hasattr(shell, "objective_state") else {}
        tulagi = bool(obj.get("AXIS:TULAGI", False))

        # Score comparison if available
        axis_score = 0
        allied_score = 0
        try:
            scoring = getattr(getattr(shell, "politics", None), "scoring", None)
            if scoring is not None and hasattr(scoring, "score_by_side"):
                sb = scoring.score_by_side
                axis_score = int(sb.get("AXIS", 0))
                allied_score = int(sb.get("ALLIED", 0))
        except Exception:
            pass

        # If we don't hold our objective, we must attack to flip it
        if not tulagi:
            return [{
                "kind": "attack",
                "unit_id": axis_unit_id,
                "eta_hours": 6,
                "intent": f"retake TULAGI; probe {target_unit_id}",
            }]

        # If behind on score, attack; otherwise stall
        if axis_score < allied_score:
            return [{
                "kind": "attack",
                "unit_id": axis_unit_id,
                "eta_hours": 6,
                "intent": f"contest score; probe {target_unit_id}",
            }]

        return [{
            "kind": "delay",
            "unit_id": axis_unit_id,
            "eta_hours": 6,
            "intent": "stall and preserve lead",
        }]
