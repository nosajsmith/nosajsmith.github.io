import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional

import websockets


class BridgeClient:
    def __init__(self, uri: str = "ws://127.0.0.1:8766", timeout_s: float = 5.0):
        self.uri = uri
        self.timeout_s = timeout_s

    async def request(self, cmd: str, args: Optional[Dict[str, Any]] = None, msg_id: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "id": msg_id or str(uuid.uuid4()),
            "cmd": cmd,
            "args": args or {},
        }
        async with websockets.connect(self.uri) as ws:
            await ws.send(json.dumps(payload))
            raw = await asyncio.wait_for(ws.recv(), timeout=self.timeout_s)
            return json.loads(raw)


async def _demo():
    c = BridgeClient()
    r1 = await c.request("ping")
    r2 = await c.request("list_scenarios")
    print("ping:", r1)
    print("list_scenarios:", r2)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_demo()))
