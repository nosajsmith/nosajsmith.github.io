import asyncio, json, sys
import websockets

URI = "ws://127.0.0.1:8766"
PROTO = "1.0"

async def rpc(ws, req_id, cmd, args=None):
    msg = {"id": req_id, "proto": PROTO, "cmd": cmd, "args": args or {}}
    await ws.send(json.dumps(msg))
    raw = await ws.recv()
    return json.loads(raw)

def fail(msg, resp=None):
    print(f"SMOKE ROUNDTRIP FAIL: {msg}")
    if resp is not None:
        print(f"resp={resp}")
    return 2

async def main():
    async with websockets.connect(URI) as ws:
        # ping
        r = await rpc(ws, "rt-ping", "ping")
        print("ping:", r)
        if r.get("status") != "ok":
            return fail("ping returned non-ok", r)

        # list_scenarios
        r = await rpc(ws, "rt-list", "list_scenarios")
        print("list_scenarios:", r)
        if r.get("status") != "ok":
            return fail("list_scenarios returned non-ok", r)

        scenarios = r.get("data", {}).get("scenarios", [])
        if not scenarios:
            return fail("no scenarios found in scenarios directory", r)

        base = scenarios[0]
        print("using scenario:", base)

        # load
        r = await rpc(ws, "rt-load-1", "load_scenario", {"name": base})
        if r.get("status") != "ok":
            return fail("load_scenario returned non-ok", r)
        scenario = r.get("data", {}).get("scenario")
        if not isinstance(scenario, dict):
            return fail("load_scenario returned non-dict scenario", r)

        # save under new name
        if base.endswith(".json"):
            out_name = base[:-5] + "_roundtrip.json"
        else:
            out_name = base + "_roundtrip.json"

        scenario2 = dict(scenario)
        scenario2.setdefault("meta", {})
        scenario2["meta"]["_roundtrip"] = True

        r = await rpc(ws, "rt-save-1", "save_scenario", {"name": out_name, "scenario": scenario2})
        if r.get("status") != "ok":
            return fail("save_scenario returned non-ok", r)

        # load saved
        r = await rpc(ws, "rt-load-2", "load_scenario", {"name": out_name})
        if r.get("status") != "ok":
            return fail("load saved scenario returned non-ok", r)

        print("SMOKE ROUNDTRIP OK")
        return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
