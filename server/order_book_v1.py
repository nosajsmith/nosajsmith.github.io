from __future__ import annotations
from typing import Dict, Any, List


class OrderBookV1:
    """
    Phase 8 HARDING
    Stores issued orders before/after scheduling.
    """

    def __init__(self) -> None:
        self._orders: List[Dict[str, Any]] = []
        self._next_id: int = 1

    def add(self, order: Dict[str, Any]) -> Dict[str, Any]:
        order = dict(order)
        order["order_id"] = self._next_id
        self._next_id += 1
        self._orders.append(order)
        return order

    def all(self) -> List[Dict[str, Any]]:
        return list(self._orders)

    def clear(self) -> None:
        self._orders.clear()
        self._next_id = 1
