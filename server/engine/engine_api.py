from __future__ import annotations

from typing import Dict, Any, List, Optional

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap
from engine.core.unit_model import UnitRepository, Posture
from engine.scenario_loader import load_scenario

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
        self._logs.append({"src": src, "turn": turn, "phase": phase, "message": message})

    def _ensure_ready(self) -> None:
        if self.time is None or self.game_map is None or self.units is None or self.meta is None:
            raise RuntimeError("EngineAPI not initialized. Call load_scenario() first.")
        if self._g3 is None or self._g4 is None or self._g7 is None or self._g8 is None:
            raise RuntimeError("Staff sections not initialized. Call load_scenario() first.")

    # ------------------------------------------------------------ public API

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        self._logs.clear()
        self._orders.clear()

        start_time, game_map, units_repo, meta = load_scenario(scenario_id)

        self.time = start_time
        self.game_map = game_map
        self.units = units_repo
        self.meta = meta

        # staff setup (minimal but real)
        self._g3 = G3Operations(units=self.units, game_map=self.game_map)
        self._g4 = G4Logistics(units=self.units, supply_sources=meta.get("supply_sources", []))
        self._g7 = G7Reinforcements(units=self.units, scenario_reinforcements=meta.get("reinforcements", []))
        self._g8 = G8Objectives(units=self.units, objectives=meta.get("objectives", []))

        self._log("ENGINE", "load", f"Loaded scenario {scenario_id}")
        return meta

    def start_game(self) -> Dict[str, Any]:
        self._ensure_ready()
        self._log("ENGINE", "start", f"Game started for scenario {self.meta['id']}")
        return self.get_game_state()

    def get_game_state(self) -> Dict[str, Any]:
        self._ensure_ready()
        # VP comes from G-8
        vp = {
            "ALLIED": int(self._g8.vp.get(self._g8.vp.keys().__iter__().__next__(), 0))  # defensive
        }
        # safer explicit
        vp = {
            "ALLIED": int(self._g8.vp.get(type(list(self._g8.vp.keys())[0])( "ALLIED"), 0)) if False else int(self._g8.vp.get(self._g8.vp.keys().__iter__().__next__(), 0))
        }
        # ^ ignore the above: we’ll do the correct way below
        vp = {
            "ALLIED": int(self._g8.vp.get(next(iter(self._g8.vp.keys())), 0))  # placeholder overwritten below
        }

        # Correct VP mapping (no tricks)
        from engine.core.unit_model import Side  # local import to avoid cycles
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

        if not unit_id:
            return {"status": "error", "error": "Missing unit_id"}
        if not target:
            return {"status": "error", "error": "Missing target"}

        u = self.units.get(unit_id)
        if u is None:
            return {"status": "error", "error": f"Unknown unit {unit_id}"}

        # For Phase 8: directly set location/posture (G-3 will resolve battles later)
        u.location_id = target
        if posture_raw in {"HOLD", "ATTACK", "DEFEND", "MOVE", "REST", "REFIT"}:
            try:
                u.posture = Posture(posture_raw)
            except Exception:
                pass

        self._orders.append(dict(action))
        self._log("PLAYER", "orders", f"Order: {unit_id} -> {target}, posture={u.posture.value}")
        return {"status": "ok"}

    def process_turn(self) -> Dict[str, Any]:
        self._ensure_ready()

        # ---- DAY START staff
        self._g7.on_day_start(self.time)  # reinforcements arrive at start of day
        self._g3.on_day_start(self.time)  # operations/battles at start of day

        # ---- DAY END staff
        self._g8.on_day_end(self.time)    # objectives after operations
        self._g4.on_day_end(self.time)    # logistics at end of day

        # Advance time LAST (logs refer to the day just processed)
        processed_day = self.time.day
        self.time.advance()

        self._log("ENGINE", "turn", f"Processed Day {processed_day}; now Day {self.time.day}")
        return self.get_game_state()

    def get_logs(self) -> List[Dict[str, Any]]:
        return list(self._logs)


__all__ = ["EngineAPI"]
