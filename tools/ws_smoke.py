import asyncio, json, websockets

URI = "ws://127.0.0.1:8766"

async def send(cmd, args=None):
    payload = {"cmd": cmd}
    if args:
        payload["args"] = args

    async with websockets.connect(URI) as ws:
        await ws.send(json.dumps(payload))
        print(f">>> {payload}")
        resp = await ws.recv()
        print(f"<<< {resp}\n")

async def main():
    await send("ping")
    await send("list_scenarios")
    # replace with a real scenario id from list_scenarios
    # await send("load_scenario", {"scenario_id": "INCHON_1950"})
    await send("next_turn")

asyncio.run(main())
