from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository


@dataclass
class EngineContext:
    """
    Lightweight context object shared across staff sections.

    Kept intentionally minimal: only include fields staff sections need.
    """
    units: UnitRepository
    game_map: Any = None
    log_sink: List[Dict[str, Any]] = field(default_factory=list)
    time: Optional[Any] = None


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

