# -*- coding: utf-8 -*-
"""
command_api.py
--------------
Wire format and helpers for UI <-> Bridge <-> Engine commands & events.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import json

# Commands from UI to Engine
@dataclass
class Command:
    cmd: str
    payload: Dict[str, Any]

def encode_command(cmd: Command) -> str:
    return json.dumps(asdict(cmd))

# Events from Engine/AI to UI
@dataclass
class Event:
    type: str
    data: Dict[str, Any]

def encode_event(evt: Event) -> str:
    return json.dumps(asdict(evt))

def decode_message(s: str) -> Dict[str, Any]:
    return json.loads(s)
