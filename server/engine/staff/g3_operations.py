# engine/staff/g3_operations.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from engine.staff.base_staff import StaffSection
from engine.core.unit_model import UnitState, UnitRepository, Side, UnitType, Posture


class G3Operations(StaffSection):
    """
    G3 (Operations): detects battles, resolves simple combat, and logs outcomes.

    This version is deliberately defensive:
    - Never references UnitType.ARMORED (canonical is UnitType.ARMOR)
    - Works even if some units don't have optional fields
    """

    def __init__(self, engine: Any) -> None:
        super().__init__(engine)
        self.src = "G3"

    # ------------------------------------------------------------
    # Hooks called by EngineAPI / engine loop
    # ------------------------------------------------------------
    def on_day_start(self) -> None:
        # Daily operational checks (battles, posture-driven moves, etc.)
        self.run_daily_cycle()

    def run_daily_cycle(self) -> None:
        self._check_for_battles()

    # ------------------------------------------------------------
    # Battle detection / resolution
    # ------------------------------------------------------------
    def _check_for_battles(self) -> None:
        """
        A "battle" occurs when opposing sides are in the same location.
        """
        repo: UnitRepository = self.engine.units
        all_units = self._all_units(repo)

        # group by location
        by_loc: Dict[str, List[UnitState]] = {}
        for u in all_units:
            loc = getattr(u, "location_id", None) or ""
            by_loc.setdefault(loc, []).append(u)

        for loc, units in by_loc.items():
            if not loc:
                continue
            allied = [u for u in units if getattr(u, "side", None) == Side.ALLIED]
            axis = [u for u in units if getattr(u, "side", None) == Side.AXIS]

            if allied and axis:
                report = self._resolve_battle(loc, allied, axis)
                self.engine.logs.append(
                    {
                        "src": self.src,
                        "turn": self.engine.turn,
                        "phase": "battle",
                        "message": report,
                    }
                )

    def _resolve_battle(self, location_id: str, allied: List[UnitState], axis: List[UnitState]) -> str:
        """
        Simple deterministic-ish resolver:
        - chooses frontline (up to N "frontage" units)
        - computes attack vs defense
        - reduces strength on loser
        """
        atk_side = Side.ALLIED
        def_side = Side.AXIS

        atk_units = allied
        def_units = axis

        atk_front, atk_res = self._pick_frontline(atk_units)
        def_front, def_res = self._pick_frontline(def_units)

        atk_power = self._combat_power(atk_front, posture_hint=Posture.ATTACK)
        def_power = self._combat_power(def_front, posture_hint=Posture.DEFEND)

        # crude but stable casualty model
        # winner inflicts more
        if atk_power >= def_power:
            self._apply_losses(def_front, loss=10)
            outcome = f"Allied attack at {location_id}: defender repulsed (def -10 str on frontline)."
        else:
            self._apply_losses(atk_front, loss=8)
            outcome = f"Allied attack at {location_id}: attack stalled (atk -8 str on frontline)."

        return outcome

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _all_units(self, repo: UnitRepository) -> List[UnitState]:
        # Support multiple repository shapes
        if hasattr(repo, "all_units"):
            return list(repo.all_units())
        if hasattr(repo, "units") and isinstance(getattr(repo, "units"), dict):
            return list(repo.units.values())
        if hasattr(repo, "_units") and isinstance(getattr(repo, "_units"), dict):
            return list(repo._units.values())
        # last resort: iterate attribute
        try:
            return list(repo)  # type: ignore
        except Exception:
            return []

    def _unit_frontage_cost(self, u: UnitState) -> int:
        ut = getattr(u, "unit_type", None)
        # canonical: UnitType.ARMOR (not ARMORED)
        if ut == getattr(UnitType, "ARMOR", None):
            return 2
        # artillery / heavy units could be 2 later; for now keep simple
        return 1

    def _pick_frontline(self, units: List[UnitState], max_frontage: int = 3) -> Tuple[List[UnitState], List[UnitState]]:
        """
        Picks up to max_frontage "cost" worth of units as frontline.
        """
        front: List[UnitState] = []
        reserve: List[UnitState] = []

        cost = 0
        for u in units:
            c = self._unit_frontage_cost(u)
            if cost + c <= max_frontage:
                front.append(u)
                cost += c
            else:
                reserve.append(u)

        return front, reserve

    def _combat_power(self, units: List[UnitState], posture_hint: Posture) -> int:
        total = 0
        for u in units:
            strength = int(getattr(u, "strength", 0))
            morale = int(getattr(u, "morale", 50))
            readiness = int(getattr(u, "readiness", 50))
            fatigue = int(getattr(u, "fatigue", 0))

            # posture influence (fallback if unit lacks posture)
            posture = getattr(u, "posture", posture_hint)
            mult = 1.0
            if posture == Posture.ATTACK:
                mult = 1.10
            elif posture == Posture.DEFEND:
                mult = 1.05

            # cheap “quality” scaler
            quality = (0.5 * morale + 0.5 * readiness) / 100.0
            fatigue_penalty = max(0.5, 1.0 - (fatigue / 200.0))

            total += int(strength * mult * quality * fatigue_penalty)

        return total

    def _apply_losses(self, units: List[UnitState], loss: int) -> None:
        for u in units:
            u.strength = max(0, int(getattr(u, "strength", 0)) - loss)
