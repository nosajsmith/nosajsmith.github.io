# plan_validator.py — stronger validation for plans.json
from __future__ import annotations
from typing import Dict, List, Tuple, Any, Optional

Coord = Tuple[int, int]

def _dist(a: Coord, b: Coord) -> int:
    ax, ay = a; bx, by = b
    return abs(ax - bx) + abs(ay - by)

def _unit_pos(game_state, unit_id: str) -> Optional[Coord]:
    u = game_state.get_unit(unit_id)
    return tuple(u.position) if u else None

def _eta_turns(path: List[Coord], hexes_per_turn: float) -> float:
    if not path or len(path) < 2: return 0.0
    d = 0
    for i in range(1, len(path)):
        d += _dist(path[i-1], path[i])
    return d / max(0.01, hexes_per_turn)

def _objective_ids(obj_state: Dict[str, Any]) -> set:
    return {o["id"] for o in obj_state.get("all", [])}

def _objective_deadlines(objectives_state: Dict[str, Any]) -> Dict[str, int]:
    out = {}
    for o in objectives_state.get("all", []):
        params = o.get("params", {})
        if "by_turn" in params:
            out[o["id"]] = int(params["by_turn"])
    return out

def _cut_route_hexes(supply_summary: Optional[Dict[str, Any]]) -> set:
    bad = set()
    if not supply_summary: 
        return bad
    for r in supply_summary.get("routes", []):
        # consider "cut" or damage >= 80% as dangerous
        status = str(r.get("status","active")).lower()
        dmg = float(r.get("damage", 0))
        if status == "cut" or dmg >= 80.0:
            for p in r.get("path", []):
                bad.add(tuple(p))
    return bad

def validate_plans(
    plans: Dict[str, Any],
    game_state,
    objectives_state: Optional[Dict[str, Any]] = None,
    hexes_per_turn: float = 1.0,
    supply_summary: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Returns list of diagnostics:
      {level: 'warn'|'error', code: str, unit: str|None, msg: str}
    """
    warn: List[Dict[str, Any]] = []
    if not plans or "plans" not in plans:
        return warn

    obj_ids = _objective_ids(objectives_state or {"all":[]})
    deadlines = _objective_deadlines(objectives_state or {"all":[]})
    cut_hexes = _cut_route_hexes(supply_summary)

    # group plans per unit
    per_unit: Dict[str, List[Dict[str, Any]]] = {}
    for p in plans.get("plans", []):
        per_unit.setdefault(p.get("unit_id","?"), []).append(p)

    for uid, plist in per_unit.items():
        upos = _unit_pos(game_state, uid)
        if upos is None:
            warn.append({"level":"error","code":"unit.missing","unit":uid,"msg":f"{uid}: unit not found in game_state"})
            # still continue to surface other schema issues

        # phases
        phases = [int(p.get("phase",0)) for p in plist]
        if len(set(phases)) != len(phases):
            warn.append({"level":"warn","code":"phase.duplicate","unit":uid,"msg":f"{uid}: duplicate phase numbers {phases}"})
        if any(ph > 1 for ph in phases) and 1 not in phases:
            warn.append({"level":"warn","code":"phase.missing1","unit":uid,"msg":f"{uid}: has later phase(s) but no phase 1"})

        # per-plan checks
        for p in plist:
            ph = int(p.get("phase", 0))
            path = [tuple(t) for t in p.get("path", [])]
            if not path:
                warn.append({"level":"warn","code":"path.empty","unit":uid,"msg":f"{uid} phase {ph}: empty path"})
                continue

            # start gap vs current pos
            if upos is not None:
                gap = _dist(upos, path[0])
                if gap > 2:
                    warn.append({"level":"warn","code":"path.start_gap","unit":uid,
                                 "msg":f"{uid} phase {ph}: path starts {gap} hexes away from current pos {upos} → {path[0]}"})

            # large jumps inside path (likely missing steps)
            for i in range(1, len(path)):
                step_d = _dist(path[i-1], path[i])
                if step_d > 3:
                    warn.append({"level":"warn","code":"path.gap","unit":uid,
                                 "msg":f"{uid} phase {ph}: large jump {path[i-1]}→{path[i]} (d={step_d})"})

            # objective linkage exists
            link = p.get("link_objective")
            if link and link not in obj_ids:
                warn.append({"level":"warn","code":"objective.missing","unit":uid,
                             "msg":f"{uid} phase {ph}: linked objective '{link}' does not exist"})

            # ETA vs deadline
            eta = _eta_turns(path, hexes_per_turn)
            if link and link in deadlines:
                by = deadlines[link]
                if eta > (by - game_state.turn):
                    warn.append({"level":"warn","code":"eta.slip","unit":uid,
                                 "msg":f"{uid} phase {ph} to '{link}' ETA≈{eta:.1f}T exceeds deadline T{by}"})

            # path crosses cut / badly damaged routes
            if cut_hexes:
                hits = [h for h in path if h in cut_hexes]
                if hits:
                    warn.append({"level":"warn","code":"path.cut_route","unit":uid,
                                 "msg":f"{uid} phase {ph}: path crosses interdicted/cut route at {sorted(set(hits))[:3]}{'…' if len(hits)>3 else ''}"})

    return warn
