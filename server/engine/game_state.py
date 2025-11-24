# game_state.py — sides (BLUE/RED), movement helpers, enemy-only ZOC utilities

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

class Unit:
    def __init__(self, unit_id, name, position, side="BLUE"):
        self.unit_id = unit_id
        self.name = name
        self.position = tuple(position)  # (x, y)
        self.side = (side or "BLUE").upper()  # "BLUE" | "RED"

        # Core stats
        self.fatigue = 0          # 0..100 (higher = worse)
        self.supply = 100         # 0..100
        self.entrenchment = 0     # 0..5
        self.exposure = 0         # 0..100
        self.combat_ready = True
        self.stance = "normal"    # "normal" | "defend" | "retreat" | "hold"

        # Combat v2: suppression (auto-clears each turn)
        self.suppressed_turns = 0
        self.suppression_penalty = 0.15

        # Movement flag for overlay
        self._moved_this_turn = False

    # Movement hooks used by orders / engine
    def move(self, dx):
        x, y = self.position
        self.position = (x + dx, y)
        self.fatigue = _clamp(self.fatigue + 5, 0, 100)
        self.exposure = _clamp(self.exposure - 10, 0, 100)
        self.stance = "retreat"
        self._moved_this_turn = True
        print(f"{self.name} moved to {self.position}")

    def move_to_exact(self, pos):
        self.position = tuple(pos)
        self.fatigue = _clamp(self.fatigue + 5, 0, 100)
        self.entrenchment = _clamp(self.entrenchment - 0.5, 0, 5)
        self._moved_this_turn = True

    def rest(self):
        self.combat_ready = False
        print(f"{self.name} is resting (recovery next turn).")

    def dig_in(self):
        self.entrenchment = _clamp(self.entrenchment + 1, 0, 5)
        self.stance = "defend"
        print(f"{self.name} digs in. Entrenchment: {self.entrenchment}")

    def hold(self):
        self.stance = "hold"
        print(f"{self.name} holds position.")

class GameState:
    def __init__(self, grid_w=20, grid_h=20):
        self.units = {}  # unit_id -> Unit
        self.grid_w = grid_w
        self.grid_h = grid_h

    # ---- unit management
    def add_unit(self, unit):
        self.units[unit.unit_id] = unit

    def get_unit(self, unit_id):
        return self.units.get(unit_id)

    def all_units(self):
        return list(self.units.values())

    # ---- geometry helpers
    def clamp_pos(self, pos):
        x, y = int(pos[0]), int(pos[1])
        x = max(0, min(self.grid_w - 1, x))
        y = max(0, min(self.grid_h - 1, y))
        return (x, y)

    def neighbors4(self, pos):
        x, y = pos
        cand = [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]
        return [self.clamp_pos(p) for p in cand]

    def is_adjacent(self, a, b) -> bool:
        ax, ay = a
        bx, by = b
        return abs(ax - bx) + abs(ay - by) == 1

    def occupied_positions(self, exclude_unit_id=None):
        occ = set()
        for u in self.units.values():
            if exclude_unit_id and u.unit_id == exclude_unit_id:
                continue
            occ.add(tuple(u.position))
        return occ

    def zoc_tiles(self, for_side: str, exclude_unit_id=None):
        """
        Enemy-only ZOC tiles from the perspective of 'for_side'.
        A tile is in ZOC if it is adjacent to at least one ENEMY unit.
        """
        for_side = (for_side or "BLUE").upper()
        z = set()
        for u in self.units.values():
            if exclude_unit_id and u.unit_id == exclude_unit_id:
                continue
            if u.side == for_side:
                continue  # friendly units do NOT project ZOC
            for n in self.neighbors4(tuple(u.position)):
                z.add(n)
        return z

    def next_step_towards(self, start, goal):
        """One-step Manhattan greedy path (v1)."""
        sx, sy = start
        gx, gy = goal
        if start == goal:
            return start
        # prefer x step, then y
        if sx < gx:
            cand = (sx + 1, sy)
        elif sx > gx:
            cand = (sx - 1, sy)
        elif sy < gy:
            cand = (sx, sy + 1)
        else:
            cand = (sx, sy - 1)
        return self.clamp_pos(cand)

    def advance_turn(self):
        """
        Per-turn world tick:
        - Supply drift, fatigue recovery/increase, entrenchment, exposure easing
        - Suppression decrement, stance reset unless 'hold'
        - Clear per-turn move flags
        """
        for u in self.units.values():
            # Supply drift
            if u.supply > 50:
                u.supply = _clamp(u.supply - 2, 0, 100)
            else:
                u.supply = _clamp(u.supply - 5, 0, 100)

            # Fatigue dynamics
            if u.combat_ready is False:
                u.fatigue = _clamp(u.fatigue - 25, 0, 100)
                u.combat_ready = True
            else:
                if u.supply >= 40:
                    u.fatigue = _clamp(u.fatigue - 5, 0, 100)
                else:
                    u.fatigue = _clamp(u.fatigue + 3, 0, 100)

            # Entrenchment drift
            if u.stance in ("defend", "hold"):
                u.entrenchment = _clamp(u.entrenchment + 0.5, 0, 5)
            elif u.stance == "retreat":
                u.entrenchment = _clamp(u.entrenchment - 1.0, 0, 5)
            else:
                u.entrenchment = _clamp(u.entrenchment - 0.25, 0, 5)

            # Exposure easing
            u.exposure = _clamp(u.exposure - 5, 0, 100)

            # Suppression tick
            if getattr(u, "suppressed_turns", 0) > 0:
                u.suppressed_turns -= 1
                if u.suppressed_turns <= 0:
                    u.suppressed_turns = 0
                    u.suppression_penalty = 0.15  # reset default

            # Stance reset unless hold
            if u.stance != "hold":
                u.stance = "normal"

            # reset per-turn flags
            u._moved_this_turn = False

        print("Advancing to next turn...")
