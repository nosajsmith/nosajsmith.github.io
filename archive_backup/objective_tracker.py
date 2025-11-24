# objective_tracker.py
# Lightweight objective system with per-turn evaluation and a running score.

import json
import os
from typing import List, Dict, Any, Optional, Tuple

class ObjectiveTracker:
    """
    Objectives file schema (objectives.json):
    {
      "objectives": [
        {
          "id": "HOLD_RIDGE",
          "type": "hold",                 // keep a specific unit near (x,y) until deadline
          "unit_id": "2DIV",
          "pos": [10,5],
          "radius": 1,
          "deadline": 3,                  // last required turn inclusive
          "points": 25,
          "title": "Hold the Ridge",
          "desc": "Keep 2DIV near (10,5) until end of turn 3."
        },
        {
          "id": "OCCUPY_BRIDGE",
          "type": "occupy",               // any friendly unit occupies (x,y) by deadline
          "pos": [7,4],
          "radius": 0,
          "deadline": 2,
          "points": 20,
          "title": "Secure the Bridge",
          "desc": "Occupy the bridge hex by turn 2."
        }
      ]
    }
    """

    def __init__(self, game_state, path="objectives.json", score_path="score.json"):
        self.gs = game_state
        self.path = path
        self.score_path = score_path
        self.objectives: List[Dict[str, Any]] = []
        self.score = 0
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.objectives = data.get("objectives", [])
        except FileNotFoundError:
            self.objectives = []
        # Init score file if absent
        if os.path.exists(self.score_path):
            try:
                self.score = json.load(open(self.score_path, "r", encoding="utf-8")).get("score", 0)
            except Exception:
                self.score = 0
        else:
            self._save_score()

    def _save_score(self):
        with open(self.score_path, "w", encoding="utf-8") as f:
            json.dump({"score": self.score}, f, indent=2)

    def evaluate_for_turn(self, turn: int) -> Dict[str, Any]:
        """
        Evaluate objectives for the current turn.
        For 'hold': award points if unit is within radius on/after its deadline turn (once).
        For 'occupy': award points once when any friendly unit is within radius by the deadline.
        We mark awarded objectives with 'awarded': true and persist in objectives_status_turnN.json
        """
        awarded_this_turn = []
        status_out = []

        for obj in self.objectives:
            obj = dict(obj)  # shallow copy
            obj.setdefault("awarded", False)
            typ = obj.get("type")
            deadline = int(obj.get("deadline", 0))
            points = int(obj.get("points", 0))
            radius = int(obj.get("radius", 0))
            pos = tuple(obj.get("pos", (0, 0)))

            if obj["awarded"]:
                status_out.append(obj)
                continue

            if typ == "hold":
                uid = obj.get("unit_id")
                u = self.gs.get_unit(uid)
                if u and turn >= deadline and self._in_radius(u.position, pos, radius):
                    self.score += points
                    obj["awarded"] = True
                    obj["awarded_turn"] = turn
                    awarded_this_turn.append({"id": obj["id"], "points": points})
            elif typ == "occupy":
                if turn <= deadline:
                    if any(self._in_radius(x.position, pos, radius) for x in self.gs.all_units()):
                        self.score += points
                        obj["awarded"] = True
                        obj["awarded_turn"] = turn
                        awarded_this_turn.append({"id": obj["id"], "points": points})

            status_out.append(obj)

        # persist updated objective state for next call
        self.objectives = status_out
        self._save_score()

        # write per-turn status
        out_path = f"objectives_turn{turn}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({"turn": turn, "score": self.score, "objectives": status_out, "awarded": awarded_this_turn}, f, indent=2)

        return {"score": self.score, "awarded": awarded_this_turn, "all": status_out, "path": out_path}

    @staticmethod
    def _in_radius(a: Tuple[int, int], b: Tuple[int, int], r: int) -> bool:
        return abs(a[0] - b[0]) <= r and abs(a[1] - b[1]) <= r
