from __future__ import annotations
from typing import Any, Dict

from politics.pressure_v1 import evaluate_collapse


class PoliticalClockV2:
    """
    Phase 9.1: Political clock + early-loss pressure.
    """

    def __init__(self, deadline_hours: int = 72, player_side: str = "ALLIED"):
        self.deadline_hours = int(deadline_hours)
        self.player_side = player_side
        self.status = "ongoing"  # ongoing | win | loss
        self.baseline_strength = 0
        self.last_pressure = {}

    def set_baseline(self, scenario: Dict[str, Any]) -> None:
        # baseline strength for player side
        units = scenario.get("units", []) if isinstance(scenario, dict) else []
        total = 0
        for u in units:
            if isinstance(u, dict):
                uid = str(u.get("id", "")).upper()
                side = str(u.get("side", "")).upper()
                if side == self.player_side or (self.player_side == "ALLIED" and uid.startswith("US-")):
                    total += int(u.get("strength", 0))
        self.baseline_strength = int(total) if total > 0 else 1

    def snapshot(self, now_hours: int) -> Dict[str, Any]:
        return {
            "status": self.status,
            "deadline_hours": self.deadline_hours,
            "time_now": int(now_hours),
            "time_remaining": max(0, self.deadline_hours - int(now_hours)),
            "pressure": self.last_pressure,
        }

    def evaluate(self, now_hours: int, scenario: Dict[str, Any]) -> Dict[str, Any]:
        if self.baseline_strength <= 0:
            self.set_baseline(scenario)

        if self.status != "ongoing":
            return self.snapshot(now_hours)

        # Early-loss pressure
        is_loss, details = evaluate_collapse(
            scenario=scenario,
            side=self.player_side,
            baseline_strength=self.baseline_strength,
        )
        self.last_pressure = details
        if is_loss:
            self.status = "loss"
            return self.snapshot(now_hours)

        # Deadline win/loss (carry over 9.0 rule)
        if int(now_hours) >= self.deadline_hours:
            objectives = scenario.get("objectives", []) if isinstance(scenario, dict) else []
            total_value = 0
            for obj in objectives:
                if isinstance(obj, dict):
                    total_value += int(obj.get("value", 0))
            self.status = "win" if total_value >= 100 else "loss"

        return self.snapshot(now_hours)
