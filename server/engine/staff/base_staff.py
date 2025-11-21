"""
Base class for all staff sections.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from engine.core.time_system import TimeListener, GameTime
from engine.core.unit_model import UnitRepository


class StaffSection(TimeListener, ABC):
    def __init__(self, name: str, units: UnitRepository) -> None:
        self.name = name
        self.units = units

    def on_day_start(self, t: GameTime) -> None:
        pass

    def on_day_end(self, t: GameTime) -> None:
        pass

    @abstractmethod
    def run_daily_cycle(self, t: GameTime) -> None:
        pass
