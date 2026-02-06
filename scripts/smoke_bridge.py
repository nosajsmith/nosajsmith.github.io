from __future__ import annotations

import asyncio
import json
import os
import uuid

import websockets  # type: ignore

BRIDGE_URL = os.environ.get("MWE_BRIDGE_URL", "ws://127.0.0.1:8766")
V = "1.0"


def req(cmd: str, payload: dict | None = None) -> dict:
    return {"cmd": cmd, "req_id": str(uuid.uuid4()), "payload": payload or {}, "v": V}


async def send(ws, message: dict) -> dict:
    await ws.send(json.dumps(message))
    raw = await ws.recv()
    return json.loads(raw)


async def main() -> int:
    scenario_name = os.environ.get("MWE_SMOKE_SCENARIO", "default")

    try:
        async with websockets.connect(BRIDGE_URL) as ws:
            r1 = await send(ws, req("ping"))
            print("PING:", r1)
            if not r1.get("ok"):
                return 2

            r2 = await send(ws, req("list_scenarios"))
            print("LIST:", r2)
            if not r2.get("ok"):
                return 2

            r3 = await send(ws, req("load_scenario", {"name": scenario_name}))
            print("LOAD:", r3)
            if not r3.get("ok"):
                print("Tip: set MWE_SMOKE_SCENARIO to a real scenario name from list_scenarios.")
                return 2

        return 0

    except Exception as e:
        print("Smoke test failed:", repr(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
