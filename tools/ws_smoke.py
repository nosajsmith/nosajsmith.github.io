import asyncio, json
import websockets

URI = "ws://127.0.0.1:8766"
PROTO = "1.0"

async def rpc(ws, req_id, cmd, args=None):
    msg = {
        "id": req_id,
        "proto": PROTO,
        "cmd": cmd,
        "args": args or {}
    }
    await ws.send(json.dumps(msg))
    raw = await ws.recv()
    return json.loads(raw)

async def main():
    async with websockets.connect(URI) as ws:
        # ping
        r = await rpc(ws, "smoke-ping", "ping")
        print("ping:", r)
        assert r["status"] == "ok"

        # list scenarios
        r = await rpc(ws, "smoke-list", "list_scenarios")
        print("list_scenarios:", r)
        assert r["status"] == "ok"

    print("SMOKE OK")

if __name__ == "__main__":
    asyncio.run(main())
