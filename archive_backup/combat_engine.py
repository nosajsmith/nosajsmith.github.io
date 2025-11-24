# combat_engine.py — grouped battles with frontage & support, metrics logging
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
import random
from battle_metrics import METRICS

@dataclass
class CombatResult:
    attackers: List[str]
    defender_id: str
    outcome: str            # "attacker_win" | "defender_hold" | "repulsed"
    atk_strength: float
    def_strength: float
    atk_losses: int
    def_losses: int
    notes: str

class CombatEngine:
    def __init__(self, game_state, terrain=None, frontage_slots:int=2, support_slots:int=1):
        self.gs = game_state
        self.terrain = terrain
        self.frontage_slots = max(1, int(frontage_slots))
        self.support_slots = max(0, int(support_slots))
        random.seed()

    def set_terrain(self, terrain):
        self.terrain = terrain

    # ---- core entry point (keeps existing TurnEngine call signature) ----
    def resolve_attacks_from_orders(self, orders) -> List[CombatResult]:
        # group all pending "attack" orders by defender
        groups: Dict[str, List[Any]] = {}
        for o in list(orders):
            if getattr(o, "status", "pending") != "pending":
                continue
            if o.action != "attack":
                continue
            tgt = getattr(o, "target_id", None)
            if not tgt:
                continue
            groups.setdefault(tgt, []).append(o)

        results: List[CombatResult] = []
        if not groups:
            METRICS.reset()  # no combats this turn; keep metrics sane
            return results

        METRICS.reset()
        for defender_id, atk_orders in groups.items():
            defender = self.gs.get_unit(defender_id)
            if not defender:
                # mark these bogus orders as rejected
                for o in atk_orders:
                    o.status = "rejected"
                continue

            # collect available attackers (alive, not routed)
            attackers = []
            for o in atk_orders:
                u = self.gs.get_unit(o.unit_id)
                if not u or getattr(u, "routed", False):
                    o.status = "rejected"
                    continue
                attackers.append(u)

            if not attackers:
                continue

            # pick frontline & supports by simple quality score (cohesion + morale - fatigue)
            scored = []
            for u in attackers:
                qual = (getattr(u, "cohesion", 70) + getattr(u, "morale", 70)) - 0.5 * getattr(u, "fatigue", 0)
                scored.append((qual, u))
            scored.sort(key=lambda t: t[0], reverse=True)

            engaged = [u for _, u in scored[: self.frontage_slots]]
            supports = [u for _, u in scored[self.frontage_slots : self.frontage_slots + self.support_slots]]

            # compute strengths / odds
            atk_fp = self._attack_fp(engaged, supports)
            def_fp = self._defense_fp(defender)
            odds = max(0.1, atk_fp / max(0.1, def_fp))

            # stochastic resolution with gentle noise
            roll = random.uniform(0.85, 1.15)
            eff = odds * roll

            # outcomes & losses (transparent, tweakable)
            if eff >= 1.25:
                outcome = "attacker_win"
                atk_losses = self._losses(engaged, base=2, scale=1/eff)
                def_losses = self._losses([defender], base=4, scale=eff)
                self._apply_losses(engaged, atk_losses)
                self._apply_losses([defender], def_losses)
                self._shock_effect(defender, shock=10)
                # optional: push defender back 1 hex if path clear
                self._attempt_retreat(defender, engaged[0].position)
            elif eff >= 0.9:
                outcome = "defender_hold"
                atk_losses = self._losses(engaged, base=3, scale=1.0)
                def_losses = self._losses([defender], base=2, scale=1.0)
                self._apply_losses(engaged, atk_losses)
                self._apply_losses([defender], def_losses)
            else:
                outcome = "repulsed"
                atk_losses = self._losses(engaged, base=4, scale=1.2)
                def_losses = self._losses([defender], base=1, scale=0.7)
                self._apply_losses(engaged, atk_losses)
                self._apply_losses([defender], def_losses)
                self._shock_effect(engaged[0], shock=8)

            # finish: mark orders executed, log metrics, collect result
            for o in atk_orders:
                o.status = "executed"

            METRICS.log(engaged_attackers=len(engaged), odds=odds, atk_losses=atk_losses, def_losses=def_losses)
            notes = f"frontage={len(engaged)} support={len(supports)} odds={round(odds,2)} roll={round(roll,2)} eff={round(eff,2)}"
            results.append(CombatResult(
                attackers=[u.unit_id for u in engaged],
                defender_id=defender.unit_id,
                outcome=outcome,
                atk_strength=round(atk_fp, 2),
                def_strength=round(def_fp, 2),
                atk_losses=int(atk_losses),
                def_losses=int(def_losses),
                notes=notes
            ))

        return results

    # ---- internals -------------------------------------------------------

    def _attack_fp(self, engaged: List[Any], supports: List[Any]) -> float:
        fp = 0.0
        for u in engaged:
            base = 1.0
            base += max(0, (getattr(u, "cohesion", 70) - 50) / 50.0) * 0.6
            base += max(0, (getattr(u, "morale", 70) - 50) / 50.0) * 0.4
            if getattr(u, "fatigue", 0) > 70: base -= 0.3
            if getattr(u, "supply", 50) < 30: base -= 0.3
            fp += max(0.2, base)
        # supports add smaller bonus
        for u in supports:
            fp += 0.35 + max(0, (getattr(u, "cohesion", 70) - 50) / 50.0) * 0.2
        return max(0.2, fp)

    def _defense_fp(self, defender: Any) -> float:
        base = 1.0
        base += getattr(defender, "entrenchment", 0) / 100.0 * 0.8
        base += max(0, (getattr(defender, "cohesion", 70) - 50) / 50.0) * 0.4
        base += max(0, (getattr(defender, "morale", 70) - 50) / 50.0) * 0.3
        if getattr(defender, "fatigue", 0) > 70: base -= 0.2
        if getattr(defender, "supply", 50) < 30: base -= 0.2
        return max(0.2, base)

    def _losses(self, units: List[Any], base: float, scale: float) -> int:
        # small, readable casualty model
        total = 0.0
        for u in units:
            qual = (getattr(u, "cohesion", 70) + getattr(u, "morale", 70)) / 140.0
            damp = 1.0 - 0.25 * qual
            total += base * scale * damp
        # clamp & discretize
        return max(0, int(round(total)))

    def _apply_losses(self, units: List[Any], losses: int):
        # distribute evenly for now
        n = max(1, len(units))
        per = int(losses / n) if losses >= n else (1 if losses > 0 else 0)
        spent = 0
        for i, u in enumerate(units):
            take = per
            if i == n - 1:
                take = max(0, losses - spent)
            u.fatigue = min(100, getattr(u, "fatigue", 0) + 5 + take)
            u.cohesion = max(0, getattr(u, "cohesion", 70) - (5 + take))
            u.morale = max(0, getattr(u, "morale", 70) - (3 + take//2))
            spent += take

    def _shock_effect(self, unit: Any, shock: int = 8):
        unit.shaken = True
        unit.cohesion = max(0, getattr(unit, "cohesion", 70) - shock)

    def _attempt_retreat(self, defender: Any, from_pos: Tuple[int,int]):
        # naive 1-hex step away from attacker if open
        dx = defender.position[0] - from_pos[0]
        dy = defender.position[1] - from_pos[1]
        step = (defender.position[0] + (1 if dx >= 0 else -1),
                defender.position[1] + (1 if dy >= 0 else -1))
        # only move if nobody occupies step
        try:
            if hasattr(self.gs, "get_unit_at"):
                occ = self.gs.get_unit_at(step)
            else:
                occ = next((u for u in self.gs.all_units() if tuple(u.position) == tuple(step)), None)
            if occ is None and min(step) >= 0:
                defender.position = step
        except Exception:
            pass
