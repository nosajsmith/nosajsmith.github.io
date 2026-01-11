# server/mwe_protocol.py
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

PROTO_VERSION = 1

# ----- response helpers -----

def ok(data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "status": "ok",
        "proto": PROTO_VERSION,
        **(data or {}),
    }

def err(code: str, message: str, *, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": "error",
        "proto": PROTO_VERSION,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details
    return payload

# ----- request parsing/validation -----

@dataclass(frozen=True)
class Request:
    proto: int
    cmd: str
    args: Dict[str, Any]
    raw: Dict[str, Any]

def parse_message(msg: Any) -> Tuple[Optional[Request], Optional[Dict[str, Any]]]:
    """
    Returns (Request, None) on success, or (None, error_response_dict) on failure.
    Accepts:
      - dict (already parsed)
      - str/bytes JSON (websockets typically gives str)
    """
    try:
        if isinstance(msg, (bytes, bytearray)):
            msg = msg.decode("utf-8", errors="replace")

        if isinstance(msg, str):
            obj = json.loads(msg)
        elif isinstance(msg, dict):
            obj = msg
        else:
            return None, err("bad_type", "Message must be JSON object (dict) or JSON string.", details={"type": str(type(msg))})

        if not isinstance(obj, dict):
            return None, err("bad_json", "Message JSON must be an object.", details={"type": str(type(obj))})

        # proto is optional for backward-compat; default to current.
        proto = int(obj.get("proto", PROTO_VERSION))
        if proto != PROTO_VERSION:
            return None, err("bad_proto", f"Unsupported proto version: {proto}", details={"supported": PROTO_VERSION})

        cmd = obj.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip():
            return None, err("missing_cmd", "Missing or invalid 'cmd' string.")

        args = obj.get("args", {})
        if args is None:
            args = {}
        if not isinstance(args, dict):
            return None, err("bad_args", "'args' must be an object (dict).", details={"type": str(type(args))})

        return Request(proto=proto, cmd=cmd.strip(), args=args, raw=obj), None

    except json.JSONDecodeError as e:
        return None, err("bad_json", "Invalid JSON.", details={"error": str(e)})
    except Exception as e:
        return None, err("parse_error", "Failed to parse message.", details={"error": str(e)})
