from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class GameTime:
    day: int = 1
    phase: str = "day"      # "day" / "night" later if you want
    weather: str = "Clear"  # keep simple for now
    turn: int = 1

    def advance(self) -> None:
        """Advance the game by one day/turn (v0 skeleton)."""
        self.day += 1
        self.turn += 1
        self.phase = "day"  # keep deterministic for v0

    def to_dict(self) -> Dict[str, Any]:
        return {"day": self.day, "phase": self.phase, "weather": self.weather}
