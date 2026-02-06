from __future__ import annotations
from typing import Any, Dict, List


class EventQueue:
    """
    Phase 8 HARDING: minimal future-event scheduler.
    Events must include: {"resolve_at": int, ...}
    """
    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []
        self._next_id: int = 1

    def schedule(self, event: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(event, dict):
            raise ValueError("event must be a dict")
        if "resolve_at" not in event:
            raise ValueError("event missing resolve_at")
        if not isinstance(event["resolve_at"], int):
            raise ValueError("resolve_at must be int")

        ev = dict(event)
        ev["id"] = self._next_id
        self._next_id += 1
        self._events.append(ev)
        return ev

    def resolve_up_to(self, t: int) -> List[Dict[str, Any]]:
        ready: List[Dict[str, Any]] = []
        remaining: List[Dict[str, Any]] = []

        for ev in self._events:
            if ev["resolve_at"] <= t:
                ready.append(ev)
            else:
                remaining.append(ev)

        self._events = remaining
        return ready

    def pending(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()
        self._next_id = 1
