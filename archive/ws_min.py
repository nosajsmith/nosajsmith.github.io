import asyncio, json
try:
    import websockets
except ImportError:
    raise SystemExit("Install websockets:  pip install websockets")

async def handle(ws, path):
    await ws.send(json.dumps({"type":"hello","data":"server alive"}))
    await ws.wait_closed()

async def main():
    async with websockets.serve(handle, "localhost", 8767):
        print("WS MIN running on ws://localhost:8767")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
