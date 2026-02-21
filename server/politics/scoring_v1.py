from __future__ import annotations
from typing import Dict, Any


class ScoringV1:
    """
    Phase 9.2 (clean rebuild):
    Deterministic objective-based scoring.
    """

    def __init__(self, tick_hours: int = 6, win_score: int = 200):
        self.tick_hours = int(tick_hours)
        self.win_score = int(win_score)
        self.score_by_side: Dict[str, int] = {"ALLIED": 0, "AXIS": 0}
        self._accum_hours = 0

    def reset(self) -> None:
        self.score_by_side = {"ALLIED": 0, "AXIS": 0}
        self._accum_hours = 0

    def tick(self, dt_hours: int, objective_state: Dict[str, bool]) -> None:
        self._accum_hours += int(dt_hours)

        while self._accum_hours >= self.tick_hours:
            self._accum_hours -= self.tick_hours

            if objective_state.get("ALLIED:LUNGA"):
                self.score_by_side["ALLIED"] += 50

            if objective_state.get("AXIS:TULAGI"):
                self.score_by_side["AXIS"] += 50

    def has_winner(self) -> str | None:
        for side, score in self.score_by_side.items():
            if score >= self.win_score:
                return side
        return None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "score_by_side": dict(self.score_by_side),
            "win_score": self.win_score,
            "tick_hours": self.tick_hours,
        }
