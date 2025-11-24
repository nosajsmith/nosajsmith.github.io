# supply_model.py — routes with damage, interdiction & repair ticks
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import json
import math

# ---------- Data classes ----------

@dataclass
class Depot:
    id: str
    name: str
    pos: Tuple[int, int]
    side: str = "BLUE"


@dataclass
class Route:
    id: str
    name: str
    side: str                       # "BLUE" or "RED"
    capacity: float                 # nominal throughput
    path: List[Tuple[int, int]]     # list of hexes
    status: str = "active"          # "active" | "cut"
    damage: float = 0.0             # 0..100 (% damage)
    cut_turns: int = 0              # how many turns marked cut (UI badge)
    last_effective: float = 0.0     # for reporting

    # --- behavior ---
    def effective_throughput(self) -> float:
        """Capacity reduced by damage; zero if cut."""
        if self.status == "cut" or self.damage >= 100.0:
            return 0.0
        eff = max(0.0, self.capacity * (1.0 - self.damage / 100.0))
        self.last_effective = eff
        return eff

    def apply_interdiction(self, strength: float):
        """
        Increase damage by 'strength'. If >= 100, route is cut.
        Strength guidelines: 10 (light) .. 40 (heavy).
        """
        self.damage = min(100.0, self.damage + max(0.0, strength))
        if self.damage >= 100.0:
            self.status = "cut"
            self.cut_turns = max(1, self.cut_turns + 1)

    def apply_repair(self, labor: float):
        """
        Reduce damage. If damage falls <100, status may re-open.
        Labor guidelines: 10 (small team) .. 40 (large team).
        """
        self.damage = max(0.0, self.damage - max(0.0, labor))
        if self.damage < 100.0 and self.status == "cut":
            # route becomes passable again (still degraded)
            self.status = "active"

    def natural_tick(self):
        """Small automatic repair every turn; cut badge decays."""
        # natural repair: 5% per turn, lighter if heavily damaged
        delta = 5.0 if self.damage >= 40 else 3.0
        if self.status == "active":
            self.damage = max(0.0, self.damage - delta)
        else:
            # even if cut, crews find bypasses over time
            self.damage = max(0.0, self.damage - 2.0)
        if self.cut_turns > 0:
            self.cut_turns = max(0, self.cut_turns - 1)


@dataclass
class SupplyState:
    depots: List[Depot] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)


# ---------- Loader / Engine ----------

def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

class SupplyEngine:
    """
    Manages supply depots/routes with a simple damage model.
    * Interdiction increases damage; Repair reduces it.
    * Effective throughput = capacity * (1 - damage%).
    * If damage >= 100 → status 'cut' (0 throughput).
    """
    def __init__(self, path: str = "supply_routes.json"):
        self.path = path
        self.state = self._load(path)

    # ---- public API used by TurnEngine / OrderExecutor ----

    def resolve_and_apply(self, game_state) -> Dict[str, List[Dict]]:
        """
        Called each turn by TurnEngine.
        - Apply natural repair ticks.
        - Compute current effective throughput for reports/UI.
        """
        for r in self.state.routes:
            r.natural_tick()

        summary_routes = []
        for r in self.state.routes:
            eff = round(r.effective_throughput(), 2)
            summary_routes.append({
                "id": r.id,
                "name": r.name,
                "side": r.side,
                "status": r.status if r.damage < 100 else "cut",
                "capacity": r.capacity,
                "length": len(r.path),
                "effective": eff,
                "damage": round(r.damage, 1),
                "cut_turns": r.cut_turns
            })
        return {"routes": summary_routes}

    def interdict(self, route_id: str, strength: float) -> Dict[str, float]:
        """Apply interdiction damage to a route."""
        r = self._get_route(route_id)
        if not r:
            return {"ok": 0, "reason": "route_not_found"}
        r.apply_interdiction(strength)
        return {"ok": 1, "damage": r.damage, "status": r.status}

    def repair(self, route_id: str, labor: float) -> Dict[str, float]:
        """Apply repair labor to a route."""
        r = self._get_route(route_id)
        if not r:
            return {"ok": 0, "reason": "route_not_found"}
        r.apply_repair(labor)
        return {"ok": 1, "damage": r.damage, "status": r.status}

    # ---- helpers ----

    def _get_route(self, rid: str) -> Optional[Route]:
        for r in self.state.routes:
            if r.id == rid:
                return r
        return None

    def _load(self, path: str) -> SupplyState:
        data = _load_json(path)
        depots = []
        for d in data.get("depots", []):
            depots.append(Depot(
                id=d["id"], name=d.get("name", d["id"]),
                pos=tuple(d.get("pos", [0, 0])), side=d.get("side", "BLUE")
            ))
        routes = []
        for r in data.get("routes", []):
            routes.append(Route(
                id=r["id"], name=r.get("name", r["id"]),
                side=r.get("side", "BLUE"),
                capacity=float(r.get("capacity", 10.0)),
                path=[tuple(p) for p in r.get("path", [])],
                status=r.get("status", "active"),
                damage=float(r.get("damage", 0.0)),
                cut_turns=int(r.get("cut_turns", 0))
            ))
        return SupplyState(depots=depots, routes=routes)
