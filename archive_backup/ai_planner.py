# -*- coding: utf-8 -*-
"""
ai_planner.py
-------------
Phase 5: Operational AI Planning module for the MacArthur War Engine (MWE).

Goals
- Generate stance-aware, weather-aware operational orders during the Orders phase.
- Support deception/maskirovka hooks (feints, staging) and multi-stage operations.
- Interface: produce a list of "AIOrders" consumable by the TurnEngine or a higher-level executor.
"""

from dataclasses import dataclass
from typing import List, Literal, Dict, Optional
import random

Stance = Literal["aggressive", "balanced", "cautious"]

@dataclass
class AIOrder:
    id: str
    unit_id: str
    order_type: Literal["attack","probe","hold","redeploy","rest","feint","engineer","resupply"]
    target_hex: Optional[tuple]  # (x,y) or None
    priority: int  # 1..5
    notes: str = ""

class AIPlanner:
    def __init__(self, rng_seed: int = 42):
        self.rand = random.Random(rng_seed)

    def plan_turn(self, stance: Stance, weather: Dict, kpis: Dict, intel: Dict, scenario: Dict) -> List[AIOrder]:
        """
        Inputs (dicts keep coupling light; replace with typed state in prod):
          - stance: 'aggressive'|'balanced'|'cautious'
          - weather: {condition, ground, wind_kph, ...}
          - kpis: {supply_pct, readiness_pct, morale_pct, ...}
          - intel: {enemy_frontline:[(x,y)], weakpoints:[(x,y)], minefields:[(x,y)], ...}
          - scenario: {units:[{id, type, strength, fatigue, pos:(x,y), hq}], hqs:[...], objectives:[(x,y)]}
        Returns: list of AIOrder
        """
        orders: List[AIOrder] = []
        supply = kpis.get("supply_pct", 60)
        readiness = kpis.get("readiness_pct", 60)
        morale = kpis.get("morale_pct", 70)
        ground = weather.get("ground","dry")
        condition = weather.get("condition","clear")

        # Determine operational tempo modifier
        tempo = 1.0
        if stance == "aggressive": tempo += 0.4
        if stance == "cautious": tempo -= 0.25
        if ground == "mud": tempo -= 0.2
        if condition in ("rain","snow"): tempo -= 0.1
        if supply < 55: tempo -= 0.2
        if readiness < 55: tempo -= 0.15
        if morale < 60: tempo -= 0.1
        tempo = max(0.4, min(1.5, tempo))

        # Helper: choose targets (weakpoints > objectives > nearest enemy line)
        weakpoints = intel.get("weakpoints", [])
        objectives = scenario.get("objectives", [])
        enemy_line = intel.get("enemy_frontline", [])
        def choose_target():
            pool = []
            pool += weakpoints*3
            pool += objectives*2
            pool += enemy_line
            return self.rand.choice(pool) if pool else None

        # Iterate units and assign orders
        for u in scenario.get("units", []):
            uid = u["id"]
            utype = u.get("type", "inf")
            strength = u.get("strength", 100)
            fatigue = u.get("fatigue", 20)
            pos = u.get("pos", (0,0))
            near_target = choose_target()

            # Baseline posture by stance
            if stance == "aggressive":
                baseline = ["attack","probe","redeploy"]
            elif stance == "cautious":
                baseline = ["hold","probe","rest"]
            else:
                baseline = ["probe","attack","hold","redeploy"]

            # Weather/ground adjustments
            if ground == "mud":
                # favor probes/engineer to clear routes
                baseline = ["probe","engineer","hold","redeploy"]
            if supply < 50 or readiness < 50 or fatigue > 60:
                baseline = ["rest","resupply","hold","probe"]

            # Unit-type preferences
            if utype in ("arm","mech") and ground != "mud":
                baseline.insert(0,"attack")
            if utype == "eng":
                baseline.insert(0,"engineer")
            if utype == "arty":
                baseline = ["hold","probe"]  # indirect support; separate fire planner later

            pick = self.rand.choice(baseline)
            prio = 3

            # Priority heuristics
            if pick == "attack" and near_target: prio = 4 if strength >= 70 else 3
            if pick in ("rest","resupply"): prio = 5 if fatigue > 65 or supply < 45 else 3
            if pick == "engineer": prio = 4

            orders.append(AIOrder(
                id=f"ai_{uid}_{self.rand.randrange(1_000_000)}",
                unit_id=uid,
                order_type=pick,
                target_hex=near_target,
                priority=prio,
                notes=f"tempo={tempo:.2f}; str={strength}; fat={fatigue}; ground={ground}; cond={condition}"
            ))

        # Deception/maskirovka: small chance to schedule feints near objectives
        if tempo >= 0.9 and objectives:
            for _ in range(max(1, len(scenario.get("units",[])) // 8)):
                tgt = self.rand.choice(objectives)
                bait = self.rand.choice(scenario.get("units",[]))["id"] if scenario.get("units") else "u0"
                orders.append(AIOrder(
                    id=f"feint_{self.rand.randrange(1_000_000)}",
                    unit_id=bait,
                    order_type="feint",
                    target_hex=tgt,
                    priority=2,
                    notes="maskirovka: demonstrate strength while main effort forms elsewhere"
                ))

        return orders
