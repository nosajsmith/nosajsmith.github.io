"""
Time system for MWE engine.

Tracks:
- day number
- phase ("day" for now)
- weather (simple placeholder)

Also defines a simple TimeListener base class used by staff sections.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GameTime:
    day: int = 1
    phase: str = "day"
    weather: str = "Clear"

    def advance(self) -> None:
        """Increment one day and roll simple placeholder weather."""
        self.day += 1

        # Simple weather cycle placeholder
        if self.day % 5 == 0:
            self.weather = "Storm"
        elif self.day % 3 == 0:
            self.weather = "Rain"
        else:
            self.weather = "Clear"


class TimeSystem:
    """
    Wrapper used by EngineAPI.
    Holds a GameTime and exposes advance().
    """

    def __init__(self, start_day: int = 1):
        self.time = GameTime(day=start_day)

    def advance(self) -> None:
        self.time.advance()

    def get(self) -> GameTime:
        return self.time


class TimeListener:
    """
    Minimal base class for anything that wants day/phase notifications.
    StaffSection subclasses inherit from this.

    Implementations can override:
      - on_day_start
      - on_day_end
      - run_daily_cycle
    """

    def on_day_start(self, t: GameTime) -> None:
        pass

    def on_day_end(self, t: GameTime) -> None:
        pass

    def run_daily_cycle(self, t: GameTime) -> None:
        pass
