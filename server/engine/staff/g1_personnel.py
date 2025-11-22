"""
G-1 Personnel Staff Section

Handles:
- Fatigue recovery / accumulation
- Morale drift
- Readiness changes
- Light non-combat attrition
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import random

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Posture
from engine.staff.base_staff import StaffSection


@dataclass
class PersonnelStatus:
    unit_id: str
    fatigue_delta: int
    morale_delta: int
    readiness_delta: int
    strength_delta: int
    notes: str = ""


def _clamp(value: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, value))


class G1Personnel(StaffSection):
    def __init__(self, units: UnitRepository) -> None:
        super().__init__("G-1 Personnel", units)
        self.last_report: Dict[str, PersonnelStatus] = {}

    def on_day_start(self, t: GameTime) -> None:
        # Run the personnel cycle at the start of each day
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        for u in self.units.all_units():
            self._update_unit(u, t)

    # -------------------------------------------------------------------------

    def _update_unit(self, u: UnitState, t: GameTime) -> None:
        fatigue_before = u.fatigue
        morale_before = u.morale
        readiness_before = u.readiness
        strength_before = u.strength

        # --- Fatigue ---------------------------------------------------------
        fatigue_delta = 0
        if u.posture == Posture.REST:
            fatigue_delta -= 8
        elif u.posture in (Posture.DEFEND, Posture.REFIT):
            fatigue_delta -= 3
        elif u.posture in (Posture.MOVE, Posture.ATTACK):
            fatigue_delta += 10

        if u.supply < 50:
            fatigue_delta += 3
        if u.supply < 25:
            fatigue_delta += 3

        u.fatigue = _clamp(u.fatigue + fatigue_delta)

        # --- Morale ----------------------------------------------------------
        morale_delta = 0

        # Drift toward 50 baseline
        if u.morale > 50:
            morale_delta -= 1
        elif u.morale < 50:
            morale_delta += 1

        # Supply effects
        if u.supply > 80:
            morale_delta += 2
        elif u.supply < 40:
            morale_delta -= 3

        # Exhaustion impact
        if u.fatigue > 70:
            morale_delta -= 2
        if u.fatigue > 90:
            morale_delta -= 3

        u.morale = _clamp(u.morale + morale_delta)

        # --- Readiness -------------------------------------------------------
        readiness_delta = 0

        if u.posture == Posture.REST and u.supply >= 60 and u.fatigue < 50:
            readiness_delta += 6
        elif u.posture in (Posture.DEFEND, Posture.REFIT):
            readiness_delta += 2
        elif u.posture in (Posture.MOVE, Posture.ATTACK):
            readiness_delta -= 8

        if u.fatigue > 70:
            readiness_delta -= 4
        if u.supply < 50:
            readiness_delta -= 3
        if u.supply < 30:
            readiness_delta -= 5

        u.readiness = _clamp(u.readiness + readiness_delta)

        # --- Light non-combat attrition -------------------------------------
        strength_delta = 0
        # Very small chance of attrition if fatigued & undersupplied
        if u.fatigue > 80 and u.supply < 40:
            if random.random() < 0.10:  # 10% daily chance in harsh conditions
                loss = random.randint(1, 3)
                strength_delta -= loss
                u.strength = max(1, u.strength - loss)

        notes = []
        if fatigue_delta != 0:
            notes.append(f"Fatigue {fatigue_before}->{u.fatigue}")
        if morale_delta != 0:
            notes.append(f"Morale {morale_before}->{u.morale}")
        if readiness_delta != 0:
            notes.append(f"Readiness {readiness_before}->{u.readiness}")
        if strength_delta != 0:
            notes.append(f"Strength {strength_before}->{u.strength}")

        self.last_report[u.id] = PersonnelStatus(
            unit_id=u.id,
            fatigue_delta=fatigue_delta,
            morale_delta=morale_delta,
            readiness_delta=readiness_delta,
            strength_delta=strength_delta,
            notes="; ".join(notes),
        )
