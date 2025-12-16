from __future__ import annotations

from typing import Dict, Any, List, Optional

from engine.core.time_system import GameTime
from engine.core.map_model import GameMap
from engine.core.unit_model import UnitRepository, Posture
from engine.scenario_loader import load_scenario
from engine.staff.base_staff import EngineContext
from engine.staff.g3_operations import G3Operations


class EngineAPI:
    def __init__(self) -> None:
        self.time: Optional[GameTime] = None
        self.game_map: Optional[GameMap] = None
        self.units: Optional[UnitRepository] = None
        self.meta: Optional[Dict[str, Any]] = None

        self._logs: List[Dict[str, Any]] = []
        self._g3: Optional[G3Operations] = None

        # orders store (v0)
        self._orders: List[Dict[str, Any]] = []

    def _log(self, src: str, phase: str, message: str) -> None:
        t = self.time.turn if self.time else 0
        self._logs.append({"src": src, "turn": t, "phase": phase, "message": message})

    def _ensure_ready(self) -> None:
        if not (self.time and self.game_map and self.units and self.meta and self._g3):
            raise RuntimeError("EngineAPI is not initialized. Call load_scenario() first.")

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        self._logs.clear()
        self._orders.clear()

        start_time, game_map, units_repo, meta = load_scenario(scenario_id)

        self.time = start_time
        self.game_map = game_map
        self.units = units_repo
        self.meta = meta

        ctx = EngineContext(game_map=self.game_map, units=self.units, log_sink=self._logs)
        self._g3 = G3Operations(ctx)

        self._log("ENGINE", "load", f"Loaded scenario {scenario_id}")
        return meta

    def start_game(self) -> Dict[str, Any]:
        self._ensure_ready()
        self._log("ENGINE", "start", f"Game started for scenario {self.meta['id']}")
        return self.get_game_state()

    def get_game_state(self) -> Dict[str, Any]:
        self._ensure_ready()
        return {
            "game": {
                "time": self.time.to_dict(),
                "scenario": self.meta["name"],
                "vp": {"ALLIED": 0, "AXIS": 0},  # placeholder for Phase 9
            },
            "units": self.units.to_list(),
        }

    def apply_player_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_ready()

        # v0: only supports "move" order -> sets location + posture
        if action.get("type") != "move":
            return {"status": "error", "error": "Unsupported action type"}

        unit_id = str(action.get("unit_id", ""))
        target = str(action.get("target", ""))
        posture = str(action.get("posture", "HOLD")).upper().strip()

        u = self.units.get(unit_id)
        if not u:
            return {"status": "error", "error": f"Unknown unit {unit_id}"}

        if not target:
            return {"status": "error", "error": "Missing target"}

        # Update unit state
        u.location_id = target
        if posture in {"HOLD", "ATTACK", "DEFEND", "MOVE"}:
            u.posture = Posture(posture)

        self._orders.append(action)
        self._log("PLAYER", "orders", f"Order: {unit_id} -> {target}, posture={u.posture.value}")
        return {"status": "ok"}

    def process_turn(self) -> Dict[str, Any]:
        self._ensure_ready()

        # Advance time FIRST (so logs reflect the new turn/day)
        self.time.advance()

        # G3 daily cycle
        self._g3.on_day_start(self.time)

        self._log("ENGINE", "end", f"Turn processed (day={self.time.day})")
        return self.get_game_state()

    def get_logs(self) -> List[Dict[str, Any]]:
        return list(self._logs)
