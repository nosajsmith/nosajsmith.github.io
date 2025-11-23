"""
Time system for MWE.

- Tracks day / phase
- Notifies registered listeners at day start, daily cycle, and day end
- Integrates with WeatherEngine to set daily weather
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Protocol

from engine.core.weather_engine import WeatherEngine


@dataclass
class GameTime:
    day: int = 1
    phase: str = "day"
    weather: str = "Clear"


class TimeListener(Protocol):
    def on_day_start(self, t: GameTime) -> None: ...
    def run_daily_cycle(self, t: GameTime) -> None: ...
    def on_day_end(self, t: GameTime) -> None: ...


class TimeSystem:
    def __init__(self) -> None:
        self.time = GameTime()
        self._listeners: Dict[str, TimeListener] = {}
        self._weather_engine = WeatherEngine(self.time.weather)

    # ------------------------------------------------------------------ weather

    def set_initial_weather(self, weather: str) -> None:
        """
        Set initial weather (e.g. from scenario metadata) before running days.
        """
        self.time.weather = weather
        self._weather_engine.current_weather = weather

    # ------------------------------------------------------------------ listeners

    def register_listener(self, name: str, listener: TimeListener) -> None:
        self._listeners[name] = listener

    # ------------------------------------------------------------------ advance

    def advance_one_day(self) -> None:
        """
        Advance one full day:
        - Increment day
        - Determine weather
        - Call on_day_start, run_daily_cycle, on_day_end on all listeners
        """
        # Advance day count
        self.time.day += 1

        # Determine and set weather for this new day
        self.time.weather = self._weather_engine.advance_day(self.time.day)

        # Notify listeners
        for listener in self._listeners.values():
            listener.on_day_start(self.time)

        for listener in self._listeners.values():
            listener.run_daily_cycle(self.time)

        for listener in self._listeners.values():
            listener.on_day_end(self.time)
