"""
Time system for MWE.

- GameTime: lightweight record of the current time slice
- TimeSystem: helper to advance time and expose it to the engine/UI
- TimeListener: small base class that staff sections inherit from
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class GameTime:
    """
    Core game time state.

    `turn` is a simple counter of how many turns have elapsed since the
    scenario started. Day and phase are what the UI mostly cares about.
    """
    day: int = 1
    phase: str = "day"
    weather: str = "Clear"
    turn: int = 1

    def to_dict(self) -> Dict[str, object]:
        return {
            "day": self.day,
            "phase": self.phase,
            "weather": self.weather,
        }


class TimeListener:
    """
    Base class for anything that wants time callbacks.

    Staff sections (G-3, G-4, G-5, etc.) subclass this via StaffSection.
    Methods are no-ops by default; sections override what they need.
    """

    def on_day_start(self, t: GameTime) -> None:  # pragma: no cover - default no-op
        pass

    def on_day_end(self, t: GameTime) -> None:  # pragma: no cover - default no-op
        pass

    def run_daily_cycle(self, t: GameTime) -> None:  # pragma: no cover - default no-op
        pass


class TimeSystem:
    """
    Minimal time controller used by EngineAPI.

    EngineAPI uses it roughly as:
      - self.ts = TimeSystem(start_time)
      - self.ts.advance_one_day() each processed turn
      - self.ts.get_time().to_dict() when building game state
    """

    def __init__(self, start: GameTime | None = None) -> None:
        self.current: GameTime = start or GameTime()

    def set_time(self, t: GameTime) -> None:
        """Replace current time with a new GameTime (used on scenario load)."""
        self.current = t

    def advance_one_day(self) -> None:
        """
        Advance time by one day / one turn.
        You can make this more sophisticated later (phases, weather rolls, etc.).
        """
        self.current.day += 1
        self.current.turn += 1

    def get_time(self) -> GameTime:
        return self.current
