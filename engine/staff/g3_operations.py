from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side, Posture
from engine.staff.base_staff import StaffSection, EngineContext


@dataclass
class BattleReport:
    location_id: str
    allied_strength: int
    axis_strength: int
    winner: str
    notes: str


class G3Operations(StaffSection):
    """
    G-3 Operations

    Responsibilities (Phase 9 baseline):
    - Execute battles where opposing forces occupy the same location
    - Minimal combat resolution (strength comparison + tile defense bonus if present)
    """

    def __init__(self, ctx: EngineContext) -> None:
        super().__init__("G-3 Operations", ctx.units)
        self.ctx = ctx
        self.game_map = ctx.game_map
        self.last_battles: List[BattleReport] = []

    # ------------------------------- timing

    def on_day_start(self, t: GameTime) -> None:
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        self.last_battles.clear()
        self._check_for_battles(t)

    # ------------------------------- public API used by EngineAPI / G-6

    def issue_move_order(
        self,
        unit_id: str,
        target_location_id: str,
        posture: Posture,
        t: GameTime,
    ) -> None:
        u = self.units.get(unit_id)
        if not u:
            self._log("orders", f"Unknown unit {unit_id} for move order.")
            return

        before = u.location_id
        u.location_id = target_location_id
        u.posture = posture

        self._log(
            "orders",
            f"Move order executed: {unit_id} {before}->{target_location_id} posture={posture.name}",
        )

    # ------------------------------- internals

    def _log(self, phase: str, message: str) -> None:
        # EngineContext log sink is a list of dicts in EngineAPI
        turn = getattr(getattr(self.ctx, "time", None), "turn", 0)
        self.ctx.log_sink.append(
            {"src": "G3", "turn": turn, "phase": phase, "message": message}
        )

    def _map_get_tile(self, location_id: str):
        """
        Compatibility accessor: supports multiple GameMap implementations.
        """
        gm = self.game_map

        if gm is None:
            return None

        # Preferred: dict-like get()
        if hasattr(gm, "get") and callable(getattr(gm, "get")):
            try:
                return gm.get(location_id)
            except TypeError:
                # some get() signatures differ
                return gm.get(location_id, None)

        # Alternate: get_tile()
        if hasattr(gm, "get_tile") and callable(getattr(gm, "get_tile")):
            return gm.get_tile(location_id)

        # Common: tiles dict
        if hasattr(gm, "tiles"):
            tiles = getattr(gm, "tiles")
            if isinstance(tiles, dict):
                return tiles.get(location_id)
            if callable(tiles):
                # some implementations use tiles() -> list
                pass

        # Fallback: _tiles dict
        if hasattr(gm, "_tiles"):
            tiles = getattr(gm, "_tiles")
            if isinstance(tiles, dict):
                return tiles.get(location_id)

        return None

    def _check_for_battles(self, t: GameTime) -> None:
        """
        Find locations containing BOTH sides and resolve.
        """
        by_loc: Dict[str, Dict[Side, List[UnitState]]] = {}

        # Support both repo styles: all_units() OR list/dict internal
        if hasattr(self.units, "all_units") and callable(getattr(self.units, "all_units")):
            units_iter = self.units.all_units()
        elif hasattr(self.units, "to_list") and callable(getattr(self.units, "to_list")):
            units_iter = self.units.to_list()
        else:
            # last-resort: try internal store patterns
            units_iter = []
            if hasattr(self.units, "_units") and isinstance(getattr(self.units, "_units"), dict):
                units_iter = list(getattr(self.units, "_units").values())

        for u in units_iter:
            by_loc.setdefault(u.location_id, {}).setdefault(u.side, []).append(u)

        for loc, sides in by_loc.items():
            allies = sides.get(Side.ALLIED, [])
            axis = sides.get(Side.AXIS, [])
            if allies and axis:
                rep = self._resolve_battle(loc, allies, axis, t)
                self.last_battles.append(rep)

    def _resolve_battle(
        self, location_id: str, allies: List[UnitState], axis: List[UnitState], t: GameTime
    ) -> BattleReport:
        a_str = sum(u.strength for u in allies)
        x_str = sum(u.strength for u in axis)

        tile = self._map_get_tile(location_id)

        # If the tile supports defense_bonus, apply it to defender side (simple: axis defending if not moving)
        defense_bonus = 0
        if tile is not None and hasattr(tile, "defense_bonus"):
            try:
                defense_bonus = int(getattr(tile, "defense_bonus", 0))
            except Exception:
                defense_bonus = 0

        # Very simple: add defense bonus to the *axis* for now (bunker style)
        x_effective = x_str + defense_bonus

        if a_str >= x_effective:
            winner = "ALLIED"
            notes = f"Allies win at {location_id} ({a_str} vs {x_effective})."
            # Axis shattered: reduce strength and retreat (placeholder: keep hex but weaken)
            for u in axis:
                u.strength = max(0, u.strength - 10)
                u.morale = max(0, u.morale - 5)
                u.readiness = max(0, u.readiness - 5)
        else:
            winner = "AXIS"
            notes = f"Axis holds at {location_id} ({a_str} vs {x_effective})."
            # Allies take losses
            for u in allies:
                u.strength = max(0, u.strength - 10)
                u.morale = max(0, u.morale - 5)
                u.readiness = max(0, u.readiness - 5)

        self._log("combat", notes)

        return BattleReport(
            location_id=location_id,
            allied_strength=a_str,
            axis_strength=x_str,
            winner=winner,
            notes=notes,
        )
