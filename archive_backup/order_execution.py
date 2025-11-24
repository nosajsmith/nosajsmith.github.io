# order_execution.py — executes orders (movement, combat timeline, interdiction/repair)
from __future__ import annotations
from typing import List, Dict, Any

class OrderExecutor:
    """
    Interprets and executes pending orders into a simple WEGO timeline.
    Also handles special non-movement actions like interdict/repair routes.
    """
    def __init__(self, game_state, config=None):
        self.gs = game_state
        self.config = config or {"resolution_mode": "WEGO", "slices_per_turn": 3, "enable_op_fire": True}

    def execute_orders(self, dispatcher, config=None) -> List[str]:
        cfg = config or self.config
        timeline: List[str] = []
        wego_slices = max(1, int(cfg.get("slices_per_turn", 3)))

        # First: handle route actions immediately so supply reflects next turn
        for o in list(dispatcher.active_orders):
            if getattr(o, "status", "pending") != "pending":
                continue
            if o.action == "interdict_route":
                rid = o.data.get("route_id")
                strength = float(o.data.get("strength", 20))
                res = self.gs.supply_engine.interdict(rid, strength) if hasattr(self.gs, "supply_engine") else {"ok": 0}
                o.status = "executed" if res.get("ok") else "rejected"
                timeline.append(f"[INTERDICT] {o.unit_id} → route {rid} +{strength} damage (status={res.get('status','?')}, dmg={res.get('damage','?')})")
            elif o.action == "repair_route":
                rid = o.data.get("route_id")
                labor = float(o.data.get("labor", 25))
                res = self.gs.supply_engine.repair(rid, labor) if hasattr(self.gs, "supply_engine") else {"ok": 0}
                o.status = "executed" if res.get("ok") else "rejected"
                timeline.append(f"[REPAIR] {o.unit_id} → route {rid} -{labor} damage (status={res.get('status','?')}, dmg={res.get('damage','?')})")

        # Then: movement / op-fire sketch
        pending_moves = [o for o in dispatcher.active_orders if o.action == "move_to" and o.status == "pending"]
        for step in range(wego_slices):
            for o in pending_moves:
                u = self.gs.get_unit(o.unit_id)
                if not u:
                    o.status = "rejected"; continue
                dest = tuple(o.data.get("target_xy", u.position))
                # simple one-hex step towards destination
                nx, ny = self._step_towards(u.position, dest)
                if (nx, ny) != tuple(u.position):
                    timeline.append(f"[MOVE] {u.unit_id} → {nx},{ny}")
                    u.position = (nx, ny)
                if (nx, ny) == dest:
                    o.status = "executed"
        return timeline

    # --- utils ---
    @staticmethod
    def _step_towards(src, dst):
        sx, sy = src; tx, ty = dst
        dx = 0 if sx == tx else (1 if tx > sx else -1)
        dy = 0 if sy == ty else (1 if ty > sy else -1)
        return (sx + dx, sy) if abs(tx - sx) >= abs(ty - sy) else (sx, sy + dy)
