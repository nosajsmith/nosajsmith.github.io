# -*- coding: utf-8 -*-
"""
MWE Bridge – Phase 6+
Adds:
- /healthz HTTP endpoint (built-in http.server on health_port)
- JSONL event logging (logs/events.jsonl)
- Input validation + error codes
- ping/pong + optional auth
- Rotating file logs + console
- websockets 15.x single-argument handler

Config: ../config.yaml (see security.token, logging.events_path, server.health_port)
"""
import asyncio, json, random, heapq, logging, logging.handlers, time, threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Callable, Set
from pathlib import Path

# ---------- Paths / Config ----------
ROOT = Path(__file__).resolve().parents[1]   # .../mwe_engine
CFG_PATH = ROOT / "config.yaml"

def load_config():
    import yaml
    defaults = {
        "server": {"host": "localhost", "port": 8766, "health_port": 8770},
        "ai": {"seed": 9001, "stance": "balanced"},
        "world": {
            "red_units": [{"id":"r1","name":"NK 1st","type":"inf","strength":75,"fatigue":20,"pos":[46,30]}],
            "objectives": [[48,30],[46,28]]
        },
        "logging": {"level":"INFO", "path":"logs/bridge.log", "events_path":"logs/events.jsonl",
                    "max_bytes":1048576, "backups":5},
        "security": {"token": ""}  # empty = off
    }
    if not CFG_PATH.exists():
        import yaml
        CFG_PATH.write_text(yaml.safe_dump(defaults, sort_keys=False), encoding="utf-8")
        return defaults
    import yaml
    cfg = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8")) or {}
    # shallow merge
    for k,v in defaults.items():
        cfg.setdefault(k, v)
        if isinstance(v, dict):
            for sk,sv in v.items():
                cfg[k].setdefault(sk, sv)
    return cfg

CFG = load_config()

# ---------- Logging ----------
log_cfg = CFG["logging"]
LOG_FILE = (ROOT / log_cfg["path"]).resolve()
EVENTS_FILE = (ROOT / log_cfg["events_path"]).resolve()
LOG_FILE.parent.mkdir(parents=True, exist_ok=True); EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("mwe.bridge")
logger.propagate = False
logger.setLevel(getattr(logging, log_cfg["level"].upper(), logging.INFO))
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

print(f"[MWE] Logging to: {LOG_FILE}")
fh = logging.handlers.RotatingFileHandler(str(LOG_FILE), maxBytes=int(log_cfg["max_bytes"]),
                                          backupCount=int(log_cfg["backups"]), encoding="utf-8", delay=False)
fh.setFormatter(fmt); fh.setLevel(logger.level)
ch = logging.StreamHandler(); ch.setFormatter(fmt); ch.setLevel(logger.level)
logger.handlers.clear(); logger.addHandler(fh); logger.addHandler(ch)

# ---------- Minimal Engine ----------
class TurnEngine:
    def __init__(self, days_per_turn: int = 2):
        self.state = {
            "clock": {"turn_number": 1, "days_per_turn": days_per_turn, "phase": "orders", "is_running": False},
            "kpis": {"supply_pct": 70, "readiness_pct": 65, "morale_pct": 78, "weather_impact_pct": 10},
            "weather": {"temp_c": 12, "wind_kph": 15, "precip_mm": 2, "condition": "overcast", "ground": "mud"},
        }
    def advance_one_turn(self):
        self.state["clock"]["turn_number"] += 1
        self.state["clock"]["phase"] = "orders"
        w = self.state["weather"]; k = self.state["kpis"]
        penalty = (8 if w["condition"] in ("rain","snow") else 0) + (12 if w["ground"]=="mud" else 0)
        k["weather_impact_pct"] = min(40, max(0, penalty))
        k["supply_pct"] = max(35, min(97, k["supply_pct"] - penalty//10))
        k["readiness_pct"] = max(40, min(92, k["readiness_pct"] - penalty//15))

# ---------- Scenario ----------
@dataclass
class Unit: id:str; name:str; type:str; strength:int; fatigue:int; pos:Tuple[int,int]; hq:str
@dataclass
class HQ: id:str; name:str; tier:str; stance:str
@dataclass
class Scenario: id:str; name:str; units:List[Unit]; hqs:List[HQ]; objectives:List[Tuple[int,int]]

def serialize_scenario(s: Scenario) -> str:
    return json.dumps({"id":s.id,"name":s.name,"units":[asdict(u) for u in s.units],
                       "hqs":[asdict(h) for h in s.hqs],"objectives":s.objectives})

# ---------- AI ----------
class AIPlanner:
    def __init__(self, seed: int = 9001): self.rand = random.Random(seed)
    def plan_turn(self, stance: str, weather: Dict, kpis: Dict, intel: Dict, scenario: Dict) -> List[Dict]:
        orders=[]; pool = intel.get("weakpoints", [])*3 + scenario.get("objectives", [])*2 + intel.get("enemy_frontline", [])
        for u in scenario.get("units", []):
            uid=u["id"]; utype=u.get("type","inf")
            baseline=["probe","attack","hold"]
            if stance=="cautious": baseline=["hold","probe","rest"]
            if stance=="aggressive": baseline=["attack","probe","redeploy"]
            if utype=="eng": baseline.insert(0,"engineer")
            pick=self.rand.choice(baseline); tgt=self.rand.choice(pool) if pool else None
            orders.append({"id":f"ai_{uid}_{self.rand.randrange(10**6)}","unit_id":uid,"order_type":pick,"target_hex":tgt,"priority":3})
        return orders

# ---------- Movement / Combat (simple) ----------
Coord = Tuple[int,int]
HEX_DIRS=[(1,0),(1,-1),(0,-1),(-1,0),(0,1),(-1,1)]
def neighbors(a:Coord)->List[Coord]: q,r=a; return [(q+dq,r+dr) for dq,dr in HEX_DIRS]
def heuristic(a:Coord,b:Coord)->float: dq=abs(a[0]-b[0]); dr=abs(a[1]-b[1]); ds=abs((-a[0]-a[1])-(-b[0]-b[1])); return max(dq,dr,ds)
def a_star(start:Coord,goal:Coord,cost_fn:Callable[[Coord,Coord],float]):
    frontier=[(0,start)]; came={}; g={start:0.0}
    while frontier:
        _,cur=heapq.heappop(frontier)
        if cur==goal:
            path=[cur]; 
            while cur in came: cur=came[cur]; path.append(cur)
            path.reverse(); return path
        for n in neighbors(cur):
            step=cost_fn(cur,n)
            if step>=1e9: continue
            new=g[cur]+step
            if n not in g or new<g[n]:
                g[n]=new; came[n]=cur; f=new+heuristic(n,goal); heapq.heappush(frontier,(f,n))
    return None

@dataclass
class CombatEvent:
    attacker:str; defender:str; location:Coord; odds:float; result:str; atk_losses:int; def_losses:int

def resolve_combat(attacker: Dict, defender: Dict, location: Coord)->CombatEvent:
    atk=attacker.get("strength",100); df=defender.get("strength",80)
    odds=atk/max(1,df)
    if odds>=1.5: result="attacker_win"; atk_loss=int(atk*0.05); def_loss=int(df*0.3)
    elif odds>=1.0: result="stalemate"; atk_loss=int(atk*0.12); def_loss=int(df*0.12)
    else: result="defender_hold"; atk_loss=int(atk*0.2); def_loss=int(df*0.08)
    return CombatEvent(attacker["id"], defender["id"], location, round(odds,2), result, atk_loss, def_loss)

def execute_orders(orders: List[Dict], units: List[Dict], enemies: List[Dict]) -> Dict:
    combats=[]
    for o in orders:
        if o.get("order_type") in ("attack","probe"):
            tgt = o.get("target_hex")
            if not tgt: continue
            tgt = tuple(tgt)
            for e in enemies:
                if tuple(e["pos"])==tgt:
                    combats.append(asdict(resolve_combat(o,e,e["pos"])))
    return {"movements":[], "combats":combats}

# ---------- Build world from config ----------
engine=TurnEngine()
ai=AIPlanner(seed=int(CFG["ai"]["seed"]))
blue=Scenario("blue01","Blue Force",
    [Unit("b1","1/24 Inf","inf",85,25,(40,30),"IX"),
     Unit("b2","Tank Co A","arm",70,30,(42,30),"IX"),
     Unit("b3","Eng Bn","eng",60,20,(39,29),"IX")],
    [HQ("IX","IX Corps","regular",CFG["ai"]["stance"])],
    [tuple(x) for x in CFG["world"]["objectives"]]
)
red=[{**ru, "pos": tuple(ru["pos"])} for ru in CFG["world"]["red_units"]]

# ---------- JSONL events ----------
START_TS = time.time()
def append_event(ev_type:str, data:Dict):
    rec = {"ts": time.time(), "type": ev_type, "data": data}
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

# ---------- WebSocket Bridge ----------
try:
    import websockets
except ImportError:
    raise SystemExit("Install dependencies: pip install -r ../requirements.txt")

CLIENTS:Set['websockets.WebSocketServer']=set()
AUTH_TOKEN = (CFG.get("security", {}) or {}).get("token","") or None
AUTHORIZED = set()  # track authed sockets when token is enabled

async def broadcast(t, data):
    msg=json.dumps({"type":t,"data":data})
    for c in list(CLIENTS):
        try: await c.send(msg)
        except Exception as ex:
            logger.warning("broadcast failed: %s", ex)

def error_payload(code:str, message:str, details:Dict=None):
    return {"type":"error","data":{"code":code,"message":message,"details":details or {}}}

def validate_orders(payload)->Tuple[bool,Dict]:
    if not isinstance(payload, dict): return False, {"message":"payload must be object"}
    orders = payload.get("orders")
    if not isinstance(orders, list) or not orders: return False, {"message":"orders must be non-empty list"}
    for idx, o in enumerate(orders):
        if not isinstance(o, dict): return False, {"index":idx,"message":"order must be object"}
        for key in ("unit_id","order_type"):
            if key not in o: return False, {"index":idx,"message":f"missing '{key}'"}
        if o["order_type"] not in ("attack","probe","hold","redeploy","engineer","rest"):
            return False, {"index":idx,"message":"invalid order_type"}
        if o["order_type"] in ("attack","probe","redeploy"):
            tgt = o.get("target_hex")
            if not (isinstance(tgt, (list,tuple)) and len(tgt)==2 and all(isinstance(v,int) for v in tgt)):
                return False, {"index":idx,"message":"target_hex must be [q,r] (ints)"}
    return True, {}

async def handle(ws):  # websockets 15.x
    CLIENTS.add(ws)
    logger.info("client connected")
    await ws.send(json.dumps({"type":"snapshot","data":{
        "engine":engine.state, "blue":json.loads(serialize_scenario(blue)), "red":{"units":red}
    }}))
    append_event("client_connect", {"remote":"local"})
    try:
        async for raw in ws:
            try:
                m=json.loads(raw); cmd=m.get("cmd"); payload=m.get("payload",{}) or {}
                logger.info("cmd=%s payload=%s", cmd, payload)

                # Optional auth
                if AUTH_TOKEN and ws not in AUTHORIZED and cmd not in ("auth","ping"):
                    await ws.send(json.dumps(error_payload("unauthorized","send auth first")))
                    continue
                if cmd=="auth":
                    if AUTH_TOKEN and payload.get("token")==AUTH_TOKEN:
                        AUTHORIZED.add(ws); await ws.send(json.dumps({"type":"auth_ok","data":{}}))
                    else:
                        await ws.send(json.dumps(error_payload("bad_token","invalid token")))
                    continue

                if cmd=="ping":
                    await ws.send(json.dumps({"type":"pong","data":{"ts": time.time()}}))
                    continue

                if cmd=="next_turn":
                    engine.advance_one_turn()
                    await broadcast("turn_advanced", {"turn":engine.state["clock"]["turn_number"]})
                    append_event("turn_advanced", {"turn":engine.state["clock"]["turn_number"]})

                elif cmd=="auto_execute":
                    orders=ai.plan_turn(CFG["ai"]["stance"],engine.state["weather"],engine.state["kpis"],
                                        {"enemy_frontline":[tuple(u["pos"]) for u in red],
                                         "weakpoints":[tuple(red[0]["pos"])] if red else []},
                                        {"units":[asdict(u) for u in blue.units],"objectives":blue.objectives})
                    rep=execute_orders(orders,[asdict(u) for u in blue.units],red)
                    await broadcast("movement_report", {"movements":rep["movements"]})
                    await broadcast("combat_report", {"combats":rep["combats"]})
                    append_event("auto_execute", {"orders":orders, "report":rep})

                elif cmd=="execute_orders":
                    ok, err = validate_orders(payload)
                    if not ok:
                        await ws.send(json.dumps(error_payload("bad_request","invalid orders", err)))
                        continue
                    rep=execute_orders(payload["orders"],[asdict(u) for u in blue.units],red)
                    await broadcast("movement_report", {"movements":rep["movements"]})
                    await broadcast("combat_report", {"combats":rep["combats"]})
                    append_event("execute_orders", {"orders":payload["orders"], "report":rep})

                else:
                    await ws.send(json.dumps(error_payload("unknown_cmd", f"unknown command '{cmd}'")))
            except Exception as ex:
                logger.exception("handler error")
                await ws.send(json.dumps(error_payload("internal", str(ex))))
    finally:
        CLIENTS.discard(ws); AUTHORIZED.discard(ws)
        logger.info("client disconnected")
        append_event("client_disconnect", {"remote":"local"})

# ---------- Healthz HTTP ----------
def start_health_server(host:str, port:int):
    import http.server, socketserver

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silence std logging
            logger.debug("healthz: " + fmt, *args)
        def do_GET(self):
            if self.path != "/healthz":
                self.send_response(404); self.end_headers(); return
            body = json.dumps({
                "status":"ok",
                "uptime_s": round(time.time()-START_TS,2),
                "clients": len(CLIENTS),
                "turn": engine.state["clock"]["turn_number"],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class ThreadedTCP(socketserver.ThreadingTCPServer):
        allow_reuse_address = True

    srv = ThreadedTCP((host, port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    logger.info("Healthz running on http://%s:%s/healthz", host, port)
    return srv

# ---------- Main ----------
async def main():
    try:
        import websockets
    except Exception:
        raise
    host, port = CFG["server"]["host"], int(CFG["server"]["port"])
    health_port = int(CFG["server"].get("health_port", 8770))
    # Start health server in background
    start_health_server("127.0.0.1" if host in ("localhost","127.0.0.1") else host, health_port)
    async with websockets.serve(handle, host, port):
        logger.info("Bridge P6 running on ws://%s:%s", host, port)
        await asyncio.Future()

if __name__=="__main__":
    logger.info("Bridge starting with config: host=%s port=%s", CFG["server"]["host"], CFG["server"]["port"])
    asyncio.run(main())
