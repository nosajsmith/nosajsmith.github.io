"""
Core time system for MWE.

- Tracks current day and phase
- Notifies registered subsystems (staff sections, UI, etc.)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Dict


@dataclass
class GameTime:
    day: int = 1       # Day number in campaign (D+1, D+2, ...)
    phase: str = "day" # e.g. "day", "night", "logistics"

    def advance_day(self) -> None:
        self.day += 1
        self.phase = "day"


class TimeListener(Protocol):
    """
    Anything that wants to react to time advancing implements this.
    """

    def on_day_start(self, t: GameTime) -> None:
        ...

    def on_day_end(self, t: GameTime) -> None:
        ...


class TimeSystem:
    """
    Central time engine.

    Usage:
        ts = TimeSystem()
        ts.register_listener("g4", g4_object)
        ts.advance_one_day()
    """

    def __init__(self) -> None:
        self.time = GameTime()
        self._listeners: Dict[str, TimeListener] = {}

    # --- Listener management -------------------------------------------------

    def register_listener(self, name: str, listener: TimeListener) -> None:
        """Register a subsystem by name (e.g. 'g4_logistics')."""
        self._listeners[name] = listener

    def unregister_listener(self, name: str) -> None:
        self._listeners.pop(name, None)

    # --- Time progression ----------------------------------------------------

    def advance_one_day(self) -> None:
        """Run one full daily cycle."""
        # Start of day
        for listener in self._listeners.values():
            listener.on_day_start(self.time)

        # (Later: phases like movement/combat/logistics can go here)

        # End of day
        for listener in self._listeners.values():
            listener.on_day_end(self.time)

        # Move to next day
        self.time.advance_day()
