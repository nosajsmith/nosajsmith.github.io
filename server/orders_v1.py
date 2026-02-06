from __future__ import annotations
from typing import Any, Dict


def make_order_event(
    *,
    kind: str,
    unit_id: str,
    issued_at: int,
    eta_hours: int,
    intent: str = "",
) -> Dict[str, Any]:
    """
    Phase 8 HARDING: orders are commitments -> future events.
    """
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("kind required")
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("unit_id required")
    if not isinstance(issued_at, int) or issued_at < 0:
        raise ValueError("issued_at must be int >= 0")
    if not isinstance(eta_hours, int) or eta_hours <= 0:
        raise ValueError("eta_hours must be int > 0")

    return {
        "type": "order",
        "kind": kind.strip(),
        "unit_id": unit_id.strip(),
        "issued_at": issued_at,
        "resolve_at": issued_at + eta_hours,
        "intent": intent or "",
    }
