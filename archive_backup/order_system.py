# order_system.py — order objects + dispatcher (supports interdict/repair, now with to_dict)
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

VALID_ACTIONS = {
    "attack", "move_to", "dig_in", "hold", "rest",
    "fallback", "fallback_to", "refit",
    # supply actions
    "interdict_route", "repair_route",
}

@dataclass
class Order:
    unit_id: str
    action: str
    priority: str = "normal"
    status: str = "pending"           # pending | executed | rejected
    text: str = ""
    target_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Stable serialization used by order_persistence."""
        # asdict handles nested dataclasses; safe for our simple types too
        d = asdict(self)
        # Ensure tuples are JSON-safe
        if "data" in d and isinstance(d["data"], dict):
            d["data"] = _jsonify(d["data"])
        return d


def _jsonify(obj: Any) -> Any:
    """Convert tuples->lists recursively to keep JSON happy."""
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, list):
        return [_jsonify(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    return obj


class OrderDispatcher:
    def __init__(self):
        self.active_orders: List[Order] = []

    def clear(self):
        self.active_orders.clear()

    def dispatch_from_recommendations(self, unit_id: str, recs: List[Dict[str, Any]], turn: int):
        """Accept lightweight dicts and turn them into validated Orders."""
        for r in recs:
            action = r.get("action")
            if action not in VALID_ACTIONS:
                print(f"[OrderDispatcher] REJECTED {unit_id}->{action} (prio={r.get('priority','-')}): "
                      f"Unknown action '{action}'. Valid: {sorted(VALID_ACTIONS)}")
                continue

            order = Order(
                unit_id=unit_id,
                action=action,
                priority=r.get("priority", "normal"),
                text=r.get("text", action),
            )

            # normalize
            if action == "attack":
                order.target_id = r.get("target_id")
                if not order.target_id:
                    print(f"[OrderDispatcher] REJECTED {unit_id}->attack: missing target_id")
                    continue

            elif action == "move_to":
                txy = r.get("target_xy") or r.get("target") or r.get("to")
                if not txy or len(txy) != 2:
                    print(f"[OrderDispatcher] REJECTED {unit_id}->move_to: missing target_xy [x,y]")
                    continue
                order.data["target_xy"] = tuple(txy)

            elif action == "fallback_to":
                txy = r.get("target_xy") or r.get("to")
                if not txy or len(txy) != 2:
                    print(f"[OrderDispatcher] REJECTED {unit_id}->fallback_to: missing target_xy [x,y]")
                    continue
                order.data["target_xy"] = tuple(txy)

            elif action == "interdict_route":
                rid = r.get("route_id")
                strength = float(r.get("strength", 25))
                if not rid:
                    print(f"[OrderDispatcher] REJECTED {unit_id}->interdict_route: missing route_id")
                    continue
                order.data.update({"route_id": rid, "strength": strength})

            elif action == "repair_route":
                rid = r.get("route_id")
                labor = float(r.get("labor", 25))
                if not rid:
                    print(f"[OrderDispatcher] REJECTED {unit_id}->repair_route: missing route_id")
                    continue
                order.data.update({"route_id": rid, "labor": labor})

            # simple actions (dig_in/hold/rest/fallback/refit) need nothing extra

            self.active_orders.append(order)
            print(f"[OK] queued")
