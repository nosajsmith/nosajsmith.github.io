from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional


@dataclass
class LogEntry:
    turn: int
    phase: str
    src: str
    message: str
    level: str = "info"
    tag: Optional[str] = None

    def to_packet(self) -> Dict:
        d = asdict(self)
        if d["tag"] is None:
            d["tag"] = ""
        return d


class LogBuffer:
    def __init__(self) -> None:
        self._entries: List[LogEntry] = []

    def add(self, turn: int, phase: str, src: str, message: str,
            level: str = "info", tag: Optional[str] = None) -> None:
        self._entries.append(
            LogEntry(turn=turn, phase=phase, src=src,
                     message=message, level=level, tag=tag)
        )

    def extend(self, entries: List[LogEntry]) -> None:
        self._entries.extend(entries)

    def clear(self) -> None:
        self._entries.clear()

    def to_packets_and_clear(self) -> List[Dict]:
        packets = [e.to_packet() for e in self._entries]
        self._entries.clear()
        return packets
