import asyncio
import json
import websockets

URI = "ws://127.0.0.1:8766"

async def rpc(ws, cmd, args=None):
    payload = {"cmd": cmd}
    if args is not None:
        payload["args"] = args
    await ws.send(json.dumps(payload))
    raw = await ws.recv()
    try:
        return json.loads(raw)
    except Exception:
        return {"status": "error", "raw": raw}

async def main():
    async with websockets.connect(URI) as ws:
        print(f"Connected: {URI}")
        for cmd, args in [
            ("ping", None),
            ("help", None),
            ("list_scenarios", None),
        ]:
            resp = await rpc(ws, cmd, args)
            print(f"{cmd} -> {resp}")

if __name__ == "__main__":
    asyncio.run(main())
