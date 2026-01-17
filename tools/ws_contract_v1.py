import asyncio, json
import websockets

URI = "ws://127.0.0.1:8766"
PROTO = "1.0"

def must(cond, msg):
    if not cond:
        raise AssertionError(msg)

async def rpc(ws, req_id, cmd, args=None):
    msg = {"id": req_id, "proto": PROTO, "cmd": cmd, "args": args or {}}
    await ws.send(json.dumps(msg))
    raw = await ws.recv()
    return json.loads(raw)

def check_envelope(r, req_id, cmd):
    must(isinstance(r, dict), "response must be object")
    must(r.get("id") == req_id, "id mismatch")
    must(r.get("proto") == PROTO, "proto mismatch")
    must(r.get("cmd") == cmd, "cmd mismatch")
    must(r.get("status") in ("ok","error"), "status must be ok|error")

def check_ok(r):
    must(r["status"] == "ok", f"expected ok got {r}")
    must("data" in r and isinstance(r["data"], dict), "ok must include data object")

def check_err(r):
    must(r["status"] == "error", f"expected error got {r}")
    must("error" in r and isinstance(r["error"], dict), "error must include error object")
    must(isinstance(r["error"].get("code"), str) and r["error"]["code"], "error.code required")
    must(isinstance(r["error"].get("message"), str) and r["error"]["message"], "error.message required")
    must(isinstance(r["error"].get("details", {}), dict), "error.details must be object")

async def main():
    async with websockets.connect(URI) as ws:
        # ping
        r = await rpc(ws, "ct-ping", "ping")
        check_envelope(r, "ct-ping", "ping")
        check_ok(r)
        must(r["data"].get("pong") is True, "ping must return pong true")

        # get_state
        r = await rpc(ws, "ct-state", "get_state")
        check_envelope(r, "ct-state", "get_state")
        check_ok(r)
        must("clock" in r["data"] and isinstance(r["data"]["clock"], dict), "get_state.clock must be object")
        must("kpis" in r["data"] and isinstance(r["data"]["kpis"], dict), "get_state.kpis must be object")

        # list_scenarios
        r = await rpc(ws, "ct-list", "list_scenarios")
        check_envelope(r, "ct-list", "list_scenarios")
        check_ok(r)
        must(isinstance(r["data"].get("scenarios"), list), "list_scenarios.scenarios must be list")

        # load_scenario negative (must error cleanly)
        r = await rpc(ws, "ct-load-missing", "load_scenario", {"name": "does_not_exist.json"})
        check_envelope(r, "ct-load-missing", "load_scenario")
        check_err(r)
        must(r["error"]["code"] in ("not_found","internal","bad_request"), "load_scenario missing should error with known code")

    print("CONTRACT V1 OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
