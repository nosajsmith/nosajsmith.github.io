from __future__ import annotations
from typing import List, Dict, Any


class LogBookV1:
    """
    Phase 8 HARDING
    Forward-only operational log.
    """

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []

    def record(self, *, t: int, msg: str, data: Dict[str, Any] | None = None) -> None:
        entry = {
            "t": t,
            "msg": msg,
        }
        if data:
            entry["data"] = dict(data)
        self._entries.append(entry)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def clear(self) -> None:
        self._entries.clear()
