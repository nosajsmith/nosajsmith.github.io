from __future__ import annotations
from typing import Any, Dict

from politics.pressure_v1 import snapshot_side_metrics


class ScoringV1:
    """
    Phase 9.2: dynamic objective scoring (stubbed hold logic).
    Deterministic. Uses supply/readiness proxies until map control exists.
    """

    def __init__(self, tick_hours: int = 6, win_score: int = 200, player_side: str = "ALLIED"):
        self.tick_hours = int(tick_hours)
        self.win_score = int(win_score)
        self.player_side = player_side
        self.score_by_side: Dict[str, int] = {"ALLIED": 0, "AXIS": 0}
        self._accum_hours = 0

    def reset(self) -> None:
        self.score_by_side = {"ALLIED": 0, "AXIS": 0}
        self._accum_hours = 0

    def _held_objectives_stub(self, scenario: Dict[str, Any]) -> Dict[str, bool]:
        """
        Stub control:
          - ALLIED holds LUNGA if avg_supply >= 50
          - AXIS holds TULAGI if avg_supply >= 50
        """
        a = snapshot_side_metrics(scenario, "ALLIED")
        x = snapshot_side_metrics(scenario, "AXIS")
        return {
            "ALLIED:LUNGA": float(a.get("avg_supply", 0)) >= 50.0,
            "AXIS:TULAGI": float(x.get("avg_supply", 0)) >= 50.0,
        }

    def tick(self, dt_hours: int, scenario: Dict[str, Any]) -> Dict[str, Any]:
        self._accum_hours += int(dt_hours)
        ticks = self._accum_hours // self.tick_hours
        self._accum_hours = self._accum_hours % self.tick_hours

        if ticks <= 0:
            return self.snapshot()

        held = self._held_objectives_stub(scenario)

        # Award per-tick points using scenario meta objectives list if present,
        # else fallback to fixed values.
        objectives = scenario.get("objectives", []) if isinstance(scenario, dict) else []
        if not isinstance(objectives, list):
            objectives = []

        # Default values if objectives missing
        default_values = {
            "ALLIED:LUNGA": 50,
            "AXIS:TULAGI": 50,
        }

        for _ in range(ticks):
            # Use scenario objectives when available
            if objectives:
                for obj in objectives:
                    if not isinstance(obj, dict):
                        continue
                    side = str(obj.get("side", "")).upper()
                    loc = str(obj.get("location_id", "")).upper()
                    key = f"{side}:{loc}"
                    val = int(obj.get("value", 0))
                    if held.get(key, False) and side in self.score_by_side:
                        self.score_by_side[side] += val
            else:
                for key, ok in held.items():
                    if ok:
                        side = key.split(":", 1)[0]
                        self.score_by_side[side] += int(default_values.get(key, 0))

        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tick_hours": self.tick_hours,
            "win_score": self.win_score,
            "score_by_side": dict(self.score_by_side),
        }

    def player_score(self) -> int:
        return int(self.score_by_side.get(self.player_side, 0))

    def has_player_won(self) -> bool:
        return self.player_score() >= self.win_score
