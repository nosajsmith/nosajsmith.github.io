# tools/ws_smoke.py
import asyncio
import json
import sys
import websockets

URI = "ws://127.0.0.1:8766"

async def call(ws, payload):
    await ws.send(json.dumps(payload))
    resp = await ws.recv()
    try:
        return json.loads(resp)
    except Exception:
        return {"raw": resp}

async def main():
    async with websockets.connect(URI) as ws:
        # 1) Ping happy-path
        r1 = await call(ws, {"proto": 1, "cmd": "ping", "args": {}})
        print("PING:", r1)

        # 2) Bad message (missing cmd) should return structured error
        r2 = await call(ws, {"proto": 1, "args": {}})
        print("MISSING_CMD:", r2)

        # 3) Bad proto should return structured error
        r3 = await call(ws, {"proto": 999, "cmd": "ping", "args": {}})
        print("BAD_PROTO:", r3)

        # 4) Optional: engine_status (we’ll add this in Phase 6)
        r4 = await call(ws, {"proto": 1, "cmd": "engine_status", "args": {}})
        print("ENGINE_STATUS:", r4)

    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(130)
