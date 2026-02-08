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

    # -----------------------------
    # Phase 8.5a: unit inspection + order effects (stub)
    # Adds ONLY: get_unit_state(), apply_order_effect()
    # -----------------------------
    def _clamp_0_100(self, v):
        try:
            iv = int(round(float(v)))
        except Exception:
            iv = 0
        if iv < 0:
            return 0
        if iv > 100:
            return 100
        return iv

    def _get_unit_obj(self, unit_id: str):
        # EngineAPI in this repo is initialized by load_scenario(); enforce that minimally.
        if unit_id is None or str(unit_id).strip() == "":
            raise ValueError("unit_id must be a non-empty string")
        uid = str(unit_id).strip()

        def match_unit(u):
            # Support both dict units and object units with either id or unit_id fields.
            if u is None:
                return False
            if isinstance(u, dict):
                return str(u.get("id", "")).strip() == uid or str(u.get("unit_id", "")).strip() == uid
            return str(getattr(u, "id", "")).strip() == uid or str(getattr(u, "unit_id", "")).strip() == uid

        def try_store(store):
            # Store may be dict-like, list-like, or have common accessors.
            if store is None:
                return None

            # Direct dict lookup
            if isinstance(store, dict):
                if uid in store:
                    return store[uid]
                # Sometimes keyed by other thing; scan values
                for v in store.values():
                    if match_unit(v):
                        return v

            # List scan
            if isinstance(store, list):
                for v in store:
                    if match_unit(v):
                        return v

            # Common accessors: get(), by_id, units, units_by_id, all()
            if hasattr(store, "get") and callable(getattr(store, "get")):
                try:
                    v = store.get(uid)
                    if v is not None:
                        return v
                except Exception:
                    pass

            for attr in ("by_id", "units_by_id", "units", "_units"):
                if hasattr(store, attr):
                    v = getattr(store, attr)
                    found = try_store(v)
                    if found is not None:
                        return found

            if hasattr(store, "all") and callable(getattr(store, "all")):
                try:
                    v = store.all()
                    found = try_store(v)
                    if found is not None:
                        return found
                except Exception:
                    pass

            return None

        # 1) Try common EngineAPI attributes and nested engine/controller holders.
        candidates = []

        # Direct common names
        for name in ("units_repo", "unit_repo", "units", "units_by_id", "gs", "game_state", "state", "engine"):
            if hasattr(self, name):
                candidates.append(getattr(self, name))

        # Also search one level deeper for engine-like objects
        for obj in list(candidates):
            for name in ("gs", "game_state", "state", "units_repo", "unit_repo", "units", "units_by_id"):
                if hasattr(obj, name):
                    candidates.append(getattr(obj, name))

        # Try each candidate store
        for c in candidates:
            found = try_store(c)
            if found is not None:
                return found

        # 2) Last resort: scan all attributes on EngineAPI (safe, bounded)
        for _, v in vars(self).items():
            found = try_store(v)
            if found is not None:
                return found

        raise KeyError(f"Unit not found: {uid}")

    def _get_stat(
self, u, key: str, default: int = 0) -> int:
        if isinstance(u, dict):
            return self._clamp_0_100(u.get(key, default))
        return self._clamp_0_100(getattr(u, key, default))

    def _set_stat(self, u, key: str, value) -> None:
        v = self._clamp_0_100(value)
        if isinstance(u, dict):
            u[key] = v
        else:
            setattr(u, key, v)

    def get_unit_state(self, unit_id: str):
        u = self._get_unit_obj(unit_id)
        return {
            "id": unit_id if not isinstance(u, dict) else u.get("id", unit_id),
            "fatigue": self._get_stat(u, "fatigue", 0),
            "readiness": self._get_stat(u, "readiness", 0),
            "morale": self._get_stat(u, "morale", 0),
            "supply": self._get_stat(u, "supply", 0),
        }

    def apply_order_effect(self, kind: str, unit_id: str, intent: str = ""):
        from engine.order_effects_stub import effect_delta, clamp_0_100

        u = self._get_unit_obj(unit_id)
        before = {
            "fatigue": self._get_stat(u, "fatigue", 0),
            "readiness": self._get_stat(u, "readiness", 0),
            "morale": self._get_stat(u, "morale", 0),
            "supply": self._get_stat(u, "supply", 0),
        }

        delta, note = effect_delta(kind)

        after = {
            "fatigue": clamp_0_100(before["fatigue"] + delta["fatigue"]),
            "readiness": clamp_0_100(before["readiness"] + delta["readiness"]),
            "morale": clamp_0_100(before["morale"] + delta["morale"]),
            "supply": clamp_0_100(before["supply"] + delta["supply"]),
        }

        self._set_stat(u, "fatigue", after["fatigue"])
        self._set_stat(u, "readiness", after["readiness"])
        self._set_stat(u, "morale", after["morale"])
        self._set_stat(u, "supply", after["supply"])

        realized = {
            "fatigue": after["fatigue"] - before["fatigue"],
            "readiness": after["readiness"] - before["readiness"],
            "morale": after["morale"] - before["morale"],
            "supply": after["supply"] - before["supply"],
        }

        return {"before": before, "after": after, "delta": realized, "note": note}
