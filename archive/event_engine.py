import json

class EventEngine:
    def __init__(self, game_state, path="events.json"):
        self.game_state = game_state
        self.path = path
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.events = json.load(f).get("events", [])
        except FileNotFoundError:
            self.events = []

    def run_for_turn(self, turn_number):
        """Evaluate AND apply events for the current turn."""
        fired = []
        for ev in self.events:
            if self._matches(ev, turn_number):
                self._apply(ev)
                fired.append(ev.get("name", "unnamed"))
        if fired:
            print(f"[EVENTS] Fired this turn: {', '.join(fired)}")

    def _matches(self, ev, turn):
        # Conditions supported: turn == N, turn >= N, unit_exists, unit_attr thresholds
        cond = ev.get("when", {})
        if "turn" in cond:
            if isinstance(cond["turn"], int) and cond["turn"] != turn:
                return False
            if isinstance(cond["turn"], dict):
                ge = cond["turn"].get(">=")
                le = cond["turn"].get("<=")
                if ge is not None and not (turn >= ge): return False
                if le is not None and not (turn <= le): return False

        unit_id = cond.get("unit_id")
        if unit_id:
            u = self.game_state.get_unit(unit_id)
            if not u:
                return False
            # optional unit attribute checks
            ua = cond.get("unit_attr", {})
            for k, rule in ua.items():
                val = getattr(u, k, None)
                if val is None:
                    return False
                if isinstance(rule, dict):
                    if ">=" in rule and not (val >= rule[">="]): return False
                    if "<=" in rule and not (val <= rule["<="]): return False
                    if ">"  in rule and not (val >  rule[">"]):  return False
                    if "<"  in rule and not (val <  rule["<"]):  return False
                else:
                    if val != rule: return False

        return True

    def _apply(self, ev):
        # Supported actions: spawn_unit, modify_unit, message
        action = ev.get("action")
        if action == "spawn_unit":
            u = ev.get("unit", {})
            from game_state import Unit
            unit = Unit(u["unit_id"], u["name"], tuple(u.get("position", (0,0))))
            unit.fatigue = u.get("fatigue", 0)
            unit.supply = u.get("supply", 100)
            unit.entrenchment = u.get("entrenchment", 0)
            unit.exposure = u.get("exposure", 0)
            self.game_state.add_unit(unit)
            print(f"[EVENT] Spawned unit {unit.unit_id} at {unit.position}")

        elif action == "modify_unit":
            unit_id = ev.get("unit_id")
            u = self.game_state.get_unit(unit_id)
            if u:
                changes = ev.get("changes", {})
                for k, v in changes.items():
                    if hasattr(u, k):
                        setattr(u, k, v)
                print(f"[EVENT] Modified unit {unit_id}: {changes}")
            else:
                print(f"[EVENT] modify_unit failed: {unit_id} not found")

        elif action == "message":
            print(f"[EVENT] {ev.get('text', '')}")
