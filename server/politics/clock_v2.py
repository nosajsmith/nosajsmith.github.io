from __future__ import annotations
from typing import Dict, Any

from politics.pressure_v1 import evaluate_collapse
from politics.scoring_v1 import ScoringV1


class PoliticalClockV2:
    """
    Phase 9.1 + 9.2 (clean):
    - Early-loss pressure
    - Objective-based scoring
    - Deadline
    """

    def __init__(self, deadline_hours: int = 72, player_side: str = "ALLIED"):
        self.deadline_hours = int(deadline_hours)
        self.player_side = player_side
        self.status = "ongoing"
        self.baseline_strength = 0
        self.last_pressure: Dict[str, Any] = {}
        self.scoring = ScoringV1()

    def set_baseline(self, scenario: Dict[str, Any]) -> None:
        units = scenario.get("units", []) if isinstance(scenario, dict) else []
        total = 0
        for u in units:
            if not isinstance(u, dict):
                continue
            uid = str(u.get("id", "")).upper()
            side = str(u.get("side", "")).upper()
            if side == self.player_side or (
                self.player_side == "ALLIED" and uid.startswith("US-")
            ):
                total += int(u.get("strength", 0))
        self.baseline_strength = total if total > 0 else 1
        self.scoring.reset()

    def snapshot(self, now: int, objective_state: Dict[str, bool]) -> Dict[str, Any]:
        return {
            "status": self.status,
            "deadline_hours": self.deadline_hours,
            "time_now": now,
            "time_remaining": max(0, self.deadline_hours - now),
            "pressure": self.last_pressure,
            "scoring": self.scoring.snapshot(),
            "objective_state": dict(objective_state),
        }

    def on_time_advance(
        self,
        dt_hours: int,
        now: int,
        scenario: Dict[str, Any],
        objective_state: Dict[str, bool],
    ) -> Dict[str, Any]:

        if self.baseline_strength <= 0:
            self.set_baseline(scenario)

        if self.status != "ongoing":
            return self.snapshot(now, objective_state)

        # 1) Score tick
        self.scoring.tick(dt_hours, objective_state)

        # 2) Collapse check (overrides win)
        is_loss, details = evaluate_collapse(
            scenario=scenario,
            side=self.player_side,
            baseline_strength=self.baseline_strength,
        )
        self.last_pressure = details
        if is_loss:
            self.status = "loss"
            return self.snapshot(now, objective_state)

        # 3) Early win via score
        winner = self.scoring.has_winner()
        if winner == self.player_side:
            self.status = "win"
            return self.snapshot(now, objective_state)

        # 4) Deadline fallback
        if now >= self.deadline_hours:
            self.status = "loss"

        return self.snapshot(now, objective_state)
