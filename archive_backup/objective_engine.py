# objective_engine.py — dynamic objectives with map pins & scoring
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any
import json, os

Coord = Tuple[int, int]

@dataclass
class Objective:
    id: str
    title: str
    desc: str
    type: str                           # hold_hex | occupy_by | unit_supply_ge | route_state | cut_route_consecutive
    params: Dict[str, Any]
    points: int = 10
    status: str = "pending"             # pending | secured | failed
    created_turn: int = 0
    awarded_turn: Optional[int] = None
    failed_turn: Optional[int] = None
    progress: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self): return asdict(self)

class ObjectiveEngine:
    """
    Loads objectives.json and evaluates each turn.
    Provides: score, list of objective dicts, and an overlay list for map pins.
    """
    def __init__(self, game_state, path="objectives.json", state_path="objectives_state.json"):
        self.gs = game_state
        self.path = path
        self.state_path = state_path
        self.turn = 0
        self.objs: List[Objective] = []
        self.score = 0
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                spec = json.load(f)
        except FileNotFoundError:
            spec = {"objectives": []}
        self.objs = []
        for o in spec.get("objectives", []):
            self.objs.append(Objective(
                id=o["id"], title=o.get("title", o["id"]), desc=o.get("desc",""),
                type=o["type"], params=o.get("params", {}), points=int(o.get("points",10))
            ))
        # restore state if present
        try:
            with open(self.state_path,"r",encoding="utf-8") as f:
                st = json.load(f)
            self.score = int(st.get("score",0))
            saved = {o["id"]: o for o in st.get("objectives", [])}
            for ob in self.objs:
                if ob.id in saved:
                    s = saved[ob.id]
                    ob.status = s.get("status","pending")
                    ob.created_turn = s.get("created_turn",0)
                    ob.awarded_turn = s.get("awarded_turn")
                    ob.failed_turn = s.get("failed_turn")
                    ob.progress = s.get("progress",{})
        except FileNotFoundError:
            pass

    def _save(self):
        data = {
            "turn": self.turn,
            "score": self.score,
            "objectives": [o.to_dict() for o in self.objs]
        }
        with open(self.state_path,"w",encoding="utf-8") as f: json.dump(data,f,indent=2)

    # ---- evaluation ----
    def evaluate(self, turn: int, supply_state=None) -> Dict[str, Any]:
        self.turn = turn
        for o in self.objs:
            if o.status in ("secured","failed"): continue
            t = o.type
            p = o.params
            if t == "hold_hex":
                self._eval_hold_hex(o, turn)
            elif t == "occupy_by":
                self._eval_occupy_by(o, turn)
            elif t == "unit_supply_ge":
                self._eval_unit_supply_ge(o, turn)
            elif t == "route_state":
                self._eval_route_state(o, supply_state)
            elif t == "cut_route_consecutive":
                self._eval_cut_route_consecutive(o, supply_state)
        self._save()
        return {"score": self.score, "all": [o.to_dict() for o in self.objs], "path": self.state_path}

    # ---- individual checkers ----
    def _friendly_at(self, pos: Coord, side="BLUE") -> bool:
        for u in self.gs.all_units():
            if u.side == side and tuple(u.position) == tuple(pos):
                return True
        return False

    def _eval_hold_hex(self, obj: Objective, turn: int):
        """ Keep any friendly unit within radius of pos until turn<=limit """
        pos = tuple(obj.params["pos"])
        side = obj.params.get("side","BLUE")
        limit = int(obj.params.get("through_turn", turn))
        radius = int(obj.params.get("radius", 0))
        ok = False
        for u in self.gs.all_units():
            if u.side != side: continue
            x,y = u.position
            if abs(x-pos[0]) + abs(y-pos[1]) <= radius:
                ok = True; break
        if ok and turn <= limit:
            # still holding
            if turn == limit:
                obj.status = "secured"; obj.awarded_turn = turn; self.score += obj.points
        else:
            if turn <= limit:
                # early failure if unit not near
                pass
            else:
                # limit passed without holding
                if obj.status != "secured":
                    obj.status = "failed"; obj.failed_turn = turn

    def _eval_occupy_by(self, obj: Objective, turn: int):
        pos = tuple(obj.params["pos"])
        side = obj.params.get("side","BLUE")
        by_turn = int(obj.params.get("by_turn", turn))
        if self._friendly_at(pos, side):
            obj.status = "secured"; obj.awarded_turn = turn; self.score += obj.points
        elif turn > by_turn and obj.status != "secured":
            obj.status = "failed"; obj.failed_turn = turn

    def _eval_unit_supply_ge(self, obj: Objective, turn: int):
        unit_id = obj.params["unit_id"]; threshold = float(obj.params.get("supply", 90))
        u = self.gs.get_unit(unit_id)
        if not u: return
        if float(u.supply) >= threshold:
            obj.status = "secured"; obj.awarded_turn = turn; self.score += obj.points

    def _eval_route_state(self, obj: Objective, supply_state):
        """ route has desired state for this turn """
        rid = obj.params["route_id"]; desired = obj.params.get("state","active")
        if not supply_state: return
        for r in supply_state["routes"]:
            if r["id"] == rid:
                st = str(r["status"]).split()[0]
                if st == desired:
                    obj.status = "secured"; obj.awarded_turn = self.turn; self.score += obj.points
                return

    def _eval_cut_route_consecutive(self, obj: Objective, supply_state):
        """ route must be cut for N consecutive turns """
        rid = obj.params["route_id"]; need = int(obj.params.get("turns", 2))
        pr = obj.progress.get("cut_streak", 0)
        now_cut = False
        if supply_state:
            for r in supply_state["routes"]:
                if r["id"] == rid:
                    now_cut = str(r["status"]).startswith("cut")
                    break
        pr = pr + 1 if now_cut else 0
        obj.progress["cut_streak"] = pr
        if pr >= need:
            obj.status = "secured"; obj.awarded_turn = self.turn; self.score += obj.points
