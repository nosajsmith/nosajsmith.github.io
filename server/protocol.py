from __future__ import annotations

from typing import Any, Dict, Optional
import uuid

PROTOCOL_VERSION = "1.0"


def _req_id() -> str:
    return uuid.uuid4().hex


def mk_ok(req_id: Optional[str], payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": True,
        "req_id": (req_id or _req_id()),
        "payload": (payload or {}),
        "v": PROTOCOL_VERSION,
    }


def mk_err(req_id: Optional[str], code: str, message: str, details: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details

    return {
        "ok": False,
        "req_id": (req_id or _req_id()),
        "error": err,
        "v": PROTOCOL_VERSION,
    }


def normalize_request(msg: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(msg, dict):
        raise ValueError("message must be a dict")

    cmd = msg.get("cmd")
    if not isinstance(cmd, str) or not cmd.strip():
        raise ValueError("cmd must be a non-empty string")
    cmd = cmd.strip()

    req_id = msg.get("req_id")
    if not isinstance(req_id, str) or not req_id.strip():
        req_id = _req_id()
    else:
        req_id = req_id.strip()

    payload = msg.get("payload", {})
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    v = msg.get("v", PROTOCOL_VERSION)
    if not isinstance(v, str) or not v.strip():
        v = PROTOCOL_VERSION

    return {"cmd": cmd, "req_id": req_id, "payload": payload, "v": v}
