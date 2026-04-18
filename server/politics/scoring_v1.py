from __future__ import annotations

from typing import Any, Dict


def _is_held_state(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        if value.get("status") == "held":
            return True
        held = value.get("held")
        if isinstance(held, bool):
            return held
        controller_side = value.get("controller_side")
        designated_side = value.get("side") or value.get("designated_side")
        return bool(controller_side) and controller_side == designated_side
    return False


class ScoringV1:
    def __init__(self, tick_hours: int = 6, win_score: int = 200):
        self.tick_hours = int(tick_hours)
        self.win_score = int(win_score)
        self.score_by_side = {"ALLIED": 0, "AXIS": 0}
        self._accum_hours = 0
        self.objective_values: Dict[str, Dict[str, Any]] = {}

    def reset(self) -> None:
        self.score_by_side = {"ALLIED": 0, "AXIS": 0}
        self._accum_hours = 0

    def configure_from_scenario(self, scenario: Dict[str, Any]) -> None:
        self.objective_values = {}
        objectives = scenario.get("objectives", []) if isinstance(scenario, dict) else []
        if not isinstance(objectives, list):
            return
        for objective in objectives:
            if not isinstance(objective, dict):
                continue
            side = str(objective.get("side", "")).upper().strip()
            location_id = str(objective.get("location_id", "")).upper().strip()
            if not side or not location_id:
                continue
            key = f"{side}:{location_id}"
            self.objective_values[key] = {
                "side": side,
                "value": int(objective.get("value", 50) or 50),
            }

    def tick(self, dt_hours: int, objective_state: Dict[str, Any]) -> None:
        self._accum_hours += int(dt_hours)
        state = objective_state if isinstance(objective_state, dict) else {}

        while self._accum_hours >= self.tick_hours:
            self._accum_hours -= self.tick_hours

            if self.objective_values:
                for key, spec in self.objective_values.items():
                    if not _is_held_state(state.get(key)):
                        continue
                    side = str(spec.get("side", "")).upper()
                    if side not in self.score_by_side:
                        continue
                    self.score_by_side[side] += int(spec.get("value", 50) or 50)
                continue

            if _is_held_state(state.get("ALLIED:LUNGA")):
                self.score_by_side["ALLIED"] += 50
            if _is_held_state(state.get("AXIS:TULAGI")):
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
