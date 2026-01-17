import asyncio, json
import websockets

URI = "ws://127.0.0.1:8766"
PROTO = "1.0"

async def rpc(ws, req_id, cmd, args=None):
    msg = {"id": req_id, "proto": PROTO, "cmd": cmd, "args": args or {}}
    await ws.send(json.dumps(msg))
    raw = await ws.recv()
    return json.loads(raw)

async def main():
    async with websockets.connect(URI) as ws:
        r = await rpc(ws, "eng-ping", "ping")
        assert r["status"] == "ok"
        print("ping:", r)

        r = await rpc(ws, "eng-state", "get_state")
        assert r["status"] == "ok"
        print("get_state:", r)

        r = await rpc(ws, "eng-list", "list_scenarios")
        assert r["status"] == "ok"
        print("list_scenarios:", r)

    print("ENGINE SMOKE OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
