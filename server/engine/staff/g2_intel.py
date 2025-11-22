"""
G-2 Intelligence Staff Section

Maintains:
- Detection levels for enemy units (0-3)
- Last-seen day
- Simple daily recon / degradation
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
import random

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side
from engine.staff.base_staff import StaffSection


@dataclass
class DetectionStatus:
    unit_id: str
    level: int          # 0=unseen, 1=presence, 2=unit identified, 3=well-known
    last_seen_day: int


class G2Intelligence(StaffSection):
    def __init__(self, units: UnitRepository, enemy_side: Side) -> None:
        super().__init__("G-2 Intelligence", units)
        self.enemy_side = enemy_side
        self._detections: Dict[str, DetectionStatus] = {}

    def on_day_start(self, t: GameTime) -> None:
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        # Degrade old intel
        self._degrade_detections(t)
        # Apply recon efforts
        self._run_recon(t)

    # -------------------------------------------------------------------------

    def _ensure_status(self, u: UnitState, t: GameTime) -> DetectionStatus:
        status = self._detections.get(u.id)
        if status is None:
            status = DetectionStatus(unit_id=u.id, level=0, last_seen_day=t.day)
            self._detections[u.id] = status
        return status

    def _degrade_detections(self, t: GameTime) -> None:
        for u in self.units.all_units():
            if u.side != self.enemy_side:
                continue
            status = self._ensure_status(u, t)
            days_since_seen = t.day - status.last_seen_day
            if days_since_seen >= 2 and status.level > 0:
                # Lose one level every 2 days without confirmation
                status.level = max(0, status.level - 1)

    def _run_recon(self, t: GameTime) -> None:
        """
        Very abstract recon model:
        - Each enemy unit has some chance to be detected or upgraded.
        - Better supplied & ready friendly forces would increase this later.
        """
        for u in self.units.all_units():
            if u.side != self.enemy_side:
                continue

            status = self._ensure_status(u, t)

            # Base recon chance
            base_chance = 0.25

            # If enemy unit is at a port/airfield (likely), bump chance
            # (We don't yet inspect map; could hook GameMap later.)
            if u.location_id in ("LUNGA", "TULAGI"):
                base_chance += 0.10

            if random.random() < base_chance:
                new_level = min(3, status.level + 1)
                status.level = new_level
                status.last_seen_day = t.day

    # -------------------------------------------------------------------------

    def get_enemy_sitrep(self) -> List[DetectionStatus]:
        """Returns a list of intel records for enemy units."""
        out: List[DetectionStatus] = []
        for u in self.units.all_units():
            if u.side != self.enemy_side:
                continue
            status = self._detections.get(u.id)
            if status is None:
                status = DetectionStatus(unit_id=u.id, level=0, last_seen_day=0)
            out.append(status)
        return out
