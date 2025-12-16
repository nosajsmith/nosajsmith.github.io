from __future__ import annotations

from typing import Dict, Any, List, Protocol

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap
from engine.core.unit_model import UnitRepository


class StaffSection(Protocol):
    def on_day_start(self, t: GameTime) -> None: ...
    def get_logs(self) -> List[Dict[str, Any]]: ...


class EngineContext:
    """
    Shared context handed to staff sections.
    """
    def __init__(self, game_map: GameMap, units: UnitRepository, log_sink: List[Dict[str, Any]]) -> None:
        self.game_map = game_map
        self.units = units
        self.log_sink = log_sink
