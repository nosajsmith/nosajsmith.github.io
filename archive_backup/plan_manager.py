# plan_manager.py — persistent operational plans (arrows, phases, labels)
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Optional, Tuple, Dict, Any, List
import json, os, re, time

Coord = Tuple[int, int]

def _color_to_hex(c: str) -> str:
    c = c.strip()
    named = {
        "red": "#d33", "blue": "#1976d2", "green": "#2e7d32", "orange": "#ef6c00",
        "purple": "#7b1fa2", "teal": "#00897b", "gray": "#616161", "grey": "#616161"
    }
    if c.lower() in named: return named[c.lower()]
    if re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", c): return c
    return "#d33"

@dataclass
class Plan:
    id: str
    label: str = ""
    color: str = "#d33"
    phase: int = 1
    turn_range: Optional[Tuple[int,int]] = None
    show: bool = True
    objective_id: Optional[str] = None
    from_ep: Dict[str, Any] = field(default_factory=dict)  # {"unit_id"} or {"pos":[x,y]}
    to_ep: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["from"] = d.pop("from_ep"); d["to"] = d.pop("to_ep")
        return d

class PlanManager:
    def __init__(self, path: str = "plans.json"):
        self.path = path
        self.plans: List[Plan] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except FileNotFoundError:
            d = {"plans": []}
        self.plans = []
        for p in d.get("plans", []):
            self.plans.append(Plan(
                id=p.get("id", self._gen_id()),
                label=p.get("label",""),
                color=p.get("color","#d33"),
                phase=int(p.get("phase",1)),
                turn_range=tuple(p["turn_range"]) if p.get("turn_range") else None,
                show=bool(p.get("show", True)),
                objective_id=p.get("objective_id"),
                from_ep=p.get("from", {}),
                to_ep=p.get("to", {})
            ))

    def save(self) -> None:
        data = {"plans": [p.to_dict() for p in self.plans]}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def list(self) -> List[Plan]:
        return list(self.plans)

    def add(self, frm: Dict[str,Any], to: Dict[str,Any], label: str = "", color: str = "#d33",
            phase: int = 1, turn_range: Optional[Tuple[int,int]] = None,
            objective_id: Optional[str] = None) -> Plan:
        p = Plan(
            id=self._gen_id(), label=label or "", color=_color_to_hex(color),
            phase=int(phase), turn_range=tuple(turn_range) if turn_range else None,
            show=True, objective_id=objective_id, from_ep=frm, to_ep=to
        )
        self.plans.append(p); self.save(); return p

    def remove(self, plan_id: str) -> bool:
        n = len(self.plans)
        self.plans = [p for p in self.plans if p.id != plan_id]
        if len(self.plans) != n: self.save(); return True
        return False

    def clear_phase(self, phase: int) -> int:
        keep = [p for p in self.plans if p.phase != int(phase)]
        removed = len(self.plans) - len(keep)
        self.plans = keep
        if removed: self.save()
        return removed

    def link_objective(self, plan_id: str, objective_id: str) -> bool:
        for p in self.plans:
            if p.id == plan_id:
                p.objective_id = objective_id; self.save(); return True
        return False

    def set_color(self, plan_id: str, color: str) -> bool:
        for p in self.plans:
            if p.id == plan_id:
                p.color = _color_to_hex(color); self.save(); return True
        return False

    def set_phase(self, plan_id: str, phase: int) -> bool:
        for p in self.plans:
            if p.id == plan_id:
                p.phase = int(phase); self.save(); return True
        return False

    def set_label(self, plan_id: str, label: str) -> bool:
        for p in self.plans:
            if p.id == plan_id:
                p.label = label; self.save(); return True
        return False

    def _gen_id(self) -> str:
        t = int(time.time() * 1000) % 10_000_000
        return f"PLAN_{t}"
