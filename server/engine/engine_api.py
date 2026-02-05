from __future__ import annotations

from typing import Dict, Any, List, Optional

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap
from engine.core.unit_model import UnitRepository, Posture, Side
from engine.scenario_loader import load_scenario

from engine.staff.base_staff import EngineContext
from engine.staff.g3_operations import G3Operations
from engine.staff.g4_logistics import G4Logistics
from engine.staff.g7_reinforcements import G7Reinforcements
from engine.staff.g8_objectives import G8Objectives


class EngineAPI:
    """
    Phase 8/9: Simple, stable API surface for UI/bridge.

    Important: This module MUST export EngineAPI so tools can:
        from engine.engine_api import EngineAPI
    """

    def __init__(self) -> None:
        self.time: Optional[GameTime] = None
        self.game_map: Optional[GameMap] = None
        self.units: Optional[UnitRepository] = None
        self.meta: Optional[Dict[str, Any]] = None

        self._logs: List[Dict[str, Any]] = []

        # Staff sections
        self._g3: Optional[G3Operations] = None
        self._g4: Optional[G4Logistics] = None
        self._g7: Optional[G7Reinforcements] = None
        self._g8: Optional[G8Objectives] = None

        # bookkeeping
        self._orders: List[Dict[str, Any]] = []

    # ------------------------------------------------------------ internal

    def _log(self, src: str, phase: str, message: str) -> None:
        turn = self.time.turn if self.time else 0
        self._logs.append(
            {"src": src, "turn": turn, "phase": phase, "message": message}
        )

    def _ensure_ready(self) -> None:
        if (
            self.time is None
            or self.game_map is None
            or self.units is None
            or self.meta is None
        ):
            raise RuntimeError(
                "EngineAPI not initialized. Call load_scenario() first."
            )
        if (
            self._g3 is None
            or self._g4 is None
            or self._g7 is None
            or self._g8 is None
        ):
            raise RuntimeError(
                "Staff sections not initialized. Call load_scenario() first."
            )

    # ------------------------------------------------------------ public API

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        self._logs.clear()
        self._orders.clear()

        start_time, game_map, units_repo, meta = load_scenario(scenario_id)

        self.time = start_time
        self.game_map = game_map
        self.units = units_repo
        self.meta = meta

        # Shared context for staff
        ctx = EngineContext(
            units=self.units,
            game_map=self.game_map,
            log_sink=self._logs,
            time=self.time,
        )

        # staff setup (minimal but real)
        self._g3 = G3Operations(ctx)
        self._g4 = G4Logistics(
            units=self.units,
            supply_sources=meta.get("supply_sources", []),
        )
        self._g7 = G7Reinforcements(
            units=self.units,
            scenario_reinforcements=meta.get("reinforcements", []),
        )
        self._g8 = G8Objectives(
            units=self.units,
            objectives=meta.get("objectives", []),
        )

        self._log("ENGINE", "load", f"Loaded scenario {scenario_id}")
        return meta

    def start_game(self) -> Dict[str, Any]:
        self._ensure_ready()
        self._log(
            "ENGINE",
            "start",
            f"Game started for scenario {self.meta['id']}",
        )
        return self.get_game_state()

    def get_game_state(self) -> Dict[str, Any]:
        self._ensure_ready()

        vp = {
            "ALLIED": int(self._g8.vp.get(Side.ALLIED, 0)),
            "AXIS": int(self._g8.vp.get(Side.AXIS, 0)),
        }

        return {
            "game": {
                "time": self.time.to_dict(),
                "scenario": self.meta["name"],
                "vp": vp,
            },
            "units": self.units.to_list(),
        }

    def apply_player_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_ready()

        if action.get("type") != "move":
            return {"status": "error", "error": "Unsupported action type"}

        unit_id = str(action.get("unit_id", "")).strip()
        target = str(action.get("target", "")).strip()
        posture_raw = str(action.get("posture", "HOLD")).upper().strip()

        try:
            posture = Posture[posture_raw]
        except KeyError:
            return {
                "status": "error",
                "error": f"Invalid posture {posture_raw}",
            }

        self._g3.issue_move_order(
            unit_id=unit_id,
            target_location_id=target,
            posture=posture,
            t=self.time,
        )

        self._orders.append(action)
        return {"status": "ok"}

    def process_turn(self) -> Dict[str, Any]:
        """
        Compatibility: advance the simulation by one day/turn and return state.

        This is a minimal Phase 8/9 driver used by smoke tests and early UI.
        """
        self._ensure_ready()

        t = self.time

        # Day start hooks
        for sec in (self._g3, self._g4, self._g7, self._g8):
            if sec and hasattr(sec, "on_day_start"):
                sec.on_day_start(t)

        # Daily cycle hooks (some sections may implement run_daily_cycle)
        for sec in (self._g3, self._g4, self._g7, self._g8):
            if sec and hasattr(sec, "run_daily_cycle"):
                sec.run_daily_cycle(t)

        # Day end hooks
        for sec in (self._g3, self._g4, self._g7, self._g8):
            if sec and hasattr(sec, "on_day_end"):
                sec.on_day_end(t)

        # Advance time by 1 day using whatever GameTime supports
        if hasattr(self.time, "advance_day") and callable(getattr(self.time, "advance_day")):
            self.time.advance_day(1)
        elif hasattr(self.time, "next_day") and callable(getattr(self.time, "next_day")):
            self.time.next_day()
        elif hasattr(self.time, "day"):
            # last-resort: bump day counter
            self.time.day = int(getattr(self.time, "day", 0)) + 1

        self._log("ENGINE", "turn", "Processed turn")
        return self.get_game_state()

    def get_logs(self) -> List[Dict[str, Any]]:
        """
        Compatibility: return engine/staff log events accumulated during play.
        """
        return list(self._logs)

    def clear_logs(self) -> None:
        self._logs.clear()
