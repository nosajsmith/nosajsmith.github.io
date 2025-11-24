# order_persistence.py — save/load of orders with robust fallback
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Any, Dict

class OrderStorage:
    def __init__(self, path: str):
        self.path = Path(path)

    def save(self, order_list: List[Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: List[Dict] = []
        for o in order_list:
            if hasattr(o, "to_dict"):
                payload.append(o.to_dict())
            else:
                # best-effort fallback
                payload.append({
                    "unit_id": getattr(o, "unit_id", "?"),
                    "action": getattr(o, "action", "?"),
                    "priority": getattr(o, "priority", "normal"),
                    "status": getattr(o, "status", "pending"),
                    "text": getattr(o, "text", ""),
                    "target_id": getattr(o, "target_id", None),
                    "data": getattr(o, "data", {}),
                })
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load(self) -> List[Dict]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)
