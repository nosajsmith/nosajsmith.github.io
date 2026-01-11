import asyncio, json, websockets

URI = "ws://127.0.0.1:8766"

async def main():
    async with websockets.connect(URI) as ws:
        msg = {"cmd": "ping", "args": {}}
        await ws.send(json.dumps(msg))
        resp = await ws.recv()
        print("RECV:", resp)

asyncio.run(main())
