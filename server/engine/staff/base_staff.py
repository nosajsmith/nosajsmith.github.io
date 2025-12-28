from __future__ import annotations

from typing import List
from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository


class StaffSection:
    def __init__(self, name: str, units: UnitRepository) -> None:
        self.name = name
        self.units = units

    # Optional hooks
    def on_day_start(self, t: GameTime) -> None:
        return

    def on_day_end(self, t: GameTime) -> None:
        return

    def run_daily_cycle(self, t: GameTime) -> None:
        return
