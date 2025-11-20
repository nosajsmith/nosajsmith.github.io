# hq_hierarchy.py — simple command network + initiative-based order delays
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import json, os

@dataclass
class HQNode:
    id: str
    side: str
    initiative: int = 70     # 0..100
    staff_capacity: int = 6  # number of new orders released per turn
    pos: Tuple[int,int] = (0,0)

class CommandNetwork:
    """
    Loads a basic HQ graph from hq_network.json (optional), otherwise builds defaults.
    Provides delay calculation and batching per turn.
    """
    def __init__(self, path: str = "hq_network.json"):
        self.path = path
        self.hqs: Dict[str, HQNode] = {}
        self.unit_to_hq: Dict[str, str] = {}
        self._load_or_default()

        # track how many orders released this turn per HQ
        self._released_this_turn: Dict[str, int] = {}

    def _load_or_default(self):
        if not os.path.exists(self.path):
            # Defaults: 2 HQs, simple mapping by side prefix
            self.hqs = {
                "BLUE_HQ": HQNode("BLUE_HQ", "BLUE", initiative=75, staff_capacity=6, pos=(3,3)),
                "RED_HQ":  HQNode("RED_HQ",  "RED",  initiative=65, staff_capacity=5, pos=(16,16)),
            }
            self.unit_to_hq = {}  # infer by side at runtime
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.hqs = {}
            for h in data.get("hqs", []):
                self.hqs[h["id"]] = HQNode(
                    id=h["id"], side=h.get("side","BLUE"),
                    initiative=int(h.get("initiative",70)),
                    staff_capacity=int(h.get("staff_capacity",6)),
                    pos=tuple(h.get("pos",[0,0])),
                )
            self.unit_to_hq = data.get("unit_to_hq", {})
        except Exception:
            # fallback defaults
            self.hqs = {
                "BLUE_HQ": HQNode("BLUE_HQ", "BLUE", initiative=75, staff_capacity=6, pos=(3,3)),
                "RED_HQ":  HQNode("RED_HQ",  "RED",  initiative=65, staff_capacity=5, pos=(16,16)),
            }
            self.unit_to_hq = {}

    def _hq_for_unit(self, unit) -> HQNode:
        # explicit mapping first
        hid = self.unit_to_hq.get(getattr(unit, "unit_id", ""), None)
        if hid and hid in self.hqs:
            return self.hqs[hid]
        # heuristic by side
        side = getattr(unit, "side", "BLUE").upper()
        for h in self.hqs.values():
            if h.side.upper() == side:
                return h
        # fallback arbitrary
        return list(self.hqs.values())[0]

    def reset_turn(self):
        self._released_this_turn = {}

    def apply_delays(self, orders: List[Any], game_state, current_turn: int) -> Tuple[List[Any], List[Any], List[str]]:
        """
        For a list of Order objects, compute/reuse 'release_turn' in o.data.
        Returns (ready, held, timeline_lines)
        """
        ready, held = [], []
        timeline: List[str] = []
        self.reset_turn()

        for o in orders:
            # Skip if already executed/rejected
            if getattr(o, "status", "pending") != "pending":
                continue

            u = game_state.get_unit(o.unit_id)
            if not u:
                ready.append(o)
                continue

            hq = self._hq_for_unit(u)

            # existing release?
            rt = o.data.get("release_turn", None)
            if rt is None:
                # compute base delay from initiative (better initiative → lower delay)
                # initiative 90+ → 0, 70 → 1, 50 → 2, else 3
                ini = max(0, min(100, int(hq.initiative)))
                if   ini >= 90: base = 0
                elif ini >= 70: base = 1
                elif ini >= 50: base = 2
                else:           base = 3

                # distance penalty (simple manhattan to HQ)
                dx = abs(u.position[0] - hq.pos[0])
                dy = abs(u.position[1] - hq.pos[1])
                dist_pen = 1 if (dx + dy) > 8 else 0

                # staff throttling
                already = self._released_this_turn.get(hq.id, 0)
                if already >= hq.staff_capacity:
                    # push to next turn window
                    base += 1

                rt = current_turn + base + dist_pen
                o.data["release_turn"] = rt

            # now decide if ready or held
            if rt <= current_turn:
                # respect staff gate per this exact turn as well
                cnt = self._released_this_turn.get(hq.id, 0)
                if cnt >= hq.staff_capacity:
                    # even if technically ripe, capacity is full → slip one more turn
                    o.data["release_turn"] = current_turn + 1
                    held.append(o)
                    timeline.append(f"[HQ] {hq.id}: capacity full; delaying {o.unit_id} → {o.action} to T{current_turn+1}")
                else:
                    self._released_this_turn[hq.id] = cnt + 1
                    ready.append(o)
                    timeline.append(f"[HQ] {hq.id}: released {o.unit_id} → {o.action} (rt=T{current_turn})")
            else:
                held.append(o)
                timeline.append(f"[HQ] {hq.id}: holding {o.unit_id} → {o.action} until T{rt}")

        return ready, held, timeline
