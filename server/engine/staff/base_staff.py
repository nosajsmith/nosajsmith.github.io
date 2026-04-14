from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List
from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository


@dataclass
class EngineContext:
    """
    Legacy compatibility shim for older staff modules that still import
    EngineContext from base_staff. Newer code can continue passing richer
    objects as long as they expose the same attributes.
    """

    units: UnitRepository
    game_map: Any = None
    time: Any = None
    log_sink: list[dict[str, Any]] = field(default_factory=list)


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
