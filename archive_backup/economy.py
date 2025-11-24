# economy.py — Convoys that replenish HQ pools; interdiction via supply routes
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import json, os, math, random

@dataclass
class ConvoySpec:
    id: str
    name: str
    route_id: str           # supply route this convoy travels on
    side: str               # "BLUE" or "RED"
    cadence: str            # "turns:0,3,6" OR "every:2" (every N turns)
    payload: Dict[str, int] # e.g., {"infantry": 10, "armor": 2, "supplies": 30}
    loss_chance_cut: float = 1.0    # if route is cut this turn
    loss_chance_degraded: float = 0.35
    loss_chance_active: float = 0.08
    throughput_scale: bool = True   # scale delivered by effective throughput ratio

class ConvoyEngine:
    """
    Reads convoys.json, decides which convoys run this turn, and credits HQ pools accordingly.
    - Delivery depends on route status:
        active    → base payload (minus random interdiction chance)
        degraded  → payload may reduce & higher loss chance
        cut       → usually lost; may deliver 0
    - If throughput_scale=True, multiply payload by (effective/capacity).
    Persists a per-turn log and returns a summary to be included in the HTML report.
    """
    def __init__(self, pool_path: str = "hq_pools.json", config_path: str = "convoys.json", log_dir: str = "."):
        self.pool_path = pool_path
        self.config_path = config_path
        self.log_dir = log_dir
        self._pools: Dict[str, Dict[str, int]] = {}     # {"BLUE": {res:qty}, "RED":{...}}
        self._convoys: List[ConvoySpec] = []
        self._load_pools()
        self._load_convoys()

    # ---------- I/O ----------
    def _load_pools(self):
        try:
            with open(self.pool_path, "r", encoding="utf-8") as f:
                self._pools = json.load(f)
        except FileNotFoundError:
            self._pools = {"BLUE": {"infantry": 0, "armor": 0, "supplies": 0},
                           "RED":  {"infantry": 0, "armor": 0, "supplies": 0}}
            self._save_pools()

    def _save_pools(self):
        with open(self.pool_path, "w", encoding="utf-8") as f:
            json.dump(self._pools, f, indent=2)

    def _load_convoys(self):
        try:
            data = json.load(open(self.config_path, "r", encoding="utf-8"))
        except FileNotFoundError:
            data = {"convoys": []}
        self._convoys = []
        for c in data.get("convoys", []):
            self._convoys.append(ConvoySpec(
                id=c["id"], name=c.get("name", c["id"]), route_id=c["route_id"], side=c.get("side","BLUE"),
                cadence=c.get("cadence","every:3"), payload=c.get("payload", {}),
                loss_chance_cut=float(c.get("loss_chance_cut", 1.0)),
                loss_chance_degraded=float(c.get("loss_chance_degraded", 0.35)),
                loss_chance_active=float(c.get("loss_chance_active", 0.08)),
                throughput_scale=bool(c.get("throughput_scale", True))
            ))

    # ---------- Helpers ----------
    def _runs_this_turn(self, cadence: str, turn: int) -> bool:
        cadence = cadence.strip()
        if cadence.startswith("every:"):
            try:
                n = int(cadence.split(":")[1])
                return (turn % n) == 0
            except:
                return False
        if cadence.startswith("turns:"):
            try:
                parts = cadence.split(":")[1]
                turns = [int(x) for x in parts.split(",") if x.strip()!=""]
                return turn in turns
            except:
                return False
        return False

    @staticmethod
    def _route_info(supply_summary: Dict[str, Any], rid: str):
        for r in supply_summary.get("routes", []):
            if r["id"] == rid:
                return r
        return None

    # ---------- Public ----------
    def resolve_for_turn(self, turn: int, supply_summary: Dict[str, Any]) -> Dict[str, Any]:
        delivered, lost, skipped = [], [], []
        for spec in self._convoys:
            if not self._runs_this_turn(spec.cadence, turn):
                continue
            r = self._route_info(supply_summary, spec.route_id)
            if not r:
                skipped.append({"id": spec.id, "name": spec.name, "reason": "route_not_found"})
                continue

            status = r["status"].split()[0]  # "active" | "degraded" | "cut"
            eff = float(r.get("effective", 0.0))
            cap = float(r.get("capacity", 1.0))
            ratio = (eff / cap) if cap > 0 else 0.0
            ratio = max(0.0, min(1.0, ratio))

            # Determine loss chance by status
            if status == "cut":
                loss_p = spec.loss_chance_cut
            elif status == "degraded":
                loss_p = spec.loss_chance_degraded
            else:
                loss_p = spec.loss_chance_active

            interdicted = (random.random() < loss_p)

            # Compute payload
            base = dict(spec.payload)
            if spec.throughput_scale:
                base = {k: int(math.floor(v * ratio)) for k, v in base.items()}

            if interdicted or status == "cut":
                # lost (either 0 delivered or explicitly logged as lost)
                lost.append({"id": spec.id, "name": spec.name, "route": spec.route_id,
                             "status": status, "loss_chance": loss_p, "would_be": base})
                continue

            if sum(base.values()) <= 0:
                skipped.append({"id": spec.id, "name": spec.name, "reason": "zero_throughput", "route": spec.route_id})
                continue

            # Credit pools
            pool = self._pools.setdefault(spec.side, {})
            for k, v in base.items():
                pool[k] = int(pool.get(k, 0)) + int(v)
            delivered.append({"id": spec.id, "name": spec.name, "route": spec.route_id,
                              "status": status, "delivered": base, "ratio": ratio})

        # persist pools and log
        self._save_pools()
        log = {"turn": turn, "delivered": delivered, "lost": lost, "skipped": skipped, "pools": self._pools}
        with open(os.path.join(self.log_dir, f"convoys_turn{turn}.json"), "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2)
        return log

    def pools(self) -> Dict[str, Dict[str,int]]:
        return self._pools.copy()
