# -*- coding: utf-8 -*-
"""
MacArthur / MWE - Turn Engine (Phase 4)
---------------------------------------
Operational turn loop with variable turn durations (1/2/3 days),
phase progression (orders -> execution -> review), weather & ground effects,
staff capacity system, and KPI drift. Deterministic RNG for repeatable sims.
"""

import math, random
from typing import Callable, Dict, List, Literal, TypedDict

TurnLength = Literal[1, 2, 3]
Phase = Literal["orders", "execution", "review"]

class TurnClock(TypedDict):
    turn_number: int
    days_per_turn: TurnLength
    phase: Phase
    is_running: bool

class StaffCapacityState(TypedDict):
    tier: str
    actions_available: int

class WeatherState(TypedDict):
    temp_c: float
    wind_kph: float
    precip_mm: float
    condition: str
    ground: str
    forecast_confidence: float

class KPIs(TypedDict):
    supply_pct: int
    readiness_pct: int
    morale_pct: int
    weather_impact_pct: int

class EngineState(TypedDict):
    clock: TurnClock
    staff: StaffCapacityState
    kpis: KPIs
    weather: WeatherState
    alerts: List[Dict]
    history: Dict[str, List[Dict[str, int]]]

class TurnEngine:
    def __init__(self, days_per_turn: TurnLength = 2, staff_tier: str = "regular", rng_seed: int = 1337):
        self.listeners: List[Callable[[Dict], None]] = []
        random.seed(rng_seed)
        caps = {"green": 2, "regular": 3, "veteran": 4, "elite": 5}
        self.staff_caps = caps
        self.state: EngineState = {
            "clock": {"turn_number": 1, "days_per_turn": days_per_turn, "phase": "orders", "is_running": False},
            "staff": {"tier": staff_tier, "actions_available": caps[staff_tier]},
            "kpis": {"supply_pct": 70, "readiness_pct": 65, "morale_pct": 78, "weather_impact_pct": 10},
            "weather": {"temp_c": 12, "wind_kph": 15, "precip_mm": 2, "condition": "overcast", "ground": "mud", "forecast_confidence": 72},
            "alerts": [],
            "history": {"supply": [], "readiness": []},
        }

    def _emit(self, event: Dict): [fn(event) for fn in self.listeners]
    def on(self, fn: Callable[[Dict], None]): self.listeners.append(fn)

    def next_phase(self):
        order = ["orders", "execution", "review"]
        idx = order.index(self.state["clock"]["phase"])
        next_phase = order[(idx + 1) % 3]
        self.state["clock"]["phase"] = next_phase
        if next_phase == "orders": self.reset_staff_capacity()
        elif next_phase == "execution": self.resolve_execution()
        elif next_phase == "review": self.summarize_turn()
        self._emit({"type": "phase_changed", "phase": next_phase, "turn": self.state["clock"]["turn_number"]})

    def advance_one_turn(self):
        for _ in range(3): self.next_phase()
        self.state["clock"]["turn_number"] += 1
        self.state["clock"]["phase"] = "orders"
        self.reset_staff_capacity()
        self._emit({"type": "turn_advanced", "turn": self.state["clock"]["turn_number"]})

    def reset_staff_capacity(self):
        tier = self.state["staff"]["tier"]
        cap = self.staff_caps[tier]
        self.state["staff"]["actions_available"] = cap
        self._emit({"type": "staff_reset", "actions": cap})

    def consume_staff_action(self, n=1):
        if self.state["staff"]["actions_available"] < n: return False
        self.state["staff"]["actions_available"] -= n
        return True

    def resolve_execution(self):
        env_penalty = self.environment_penalty()
        d_supply = random.randint(-2, 3) - int(env_penalty / 10)
        d_readiness = random.randint(-1, 2) - int(env_penalty / 15)
        d_morale = random.randint(-1, 1)
        days = self.state["clock"]["days_per_turn"]

        def adj(v, d, lo, hi): return max(lo, min(hi, v + d * days))
        k = self.state["kpis"]
        k["supply_pct"] = adj(k["supply_pct"], d_supply, 35, 97)
        k["readiness_pct"] = adj(k["readiness_pct"], d_readiness, 40, 92)
        k["morale_pct"] = adj(k["morale_pct"], d_morale, 50, 95)
        k["weather_impact_pct"] = min(40, max(0, env_penalty))
        self.advance_weather()
        if k["supply_pct"] <= 50: self.push_alert("Theater supply throughput falling below 50%.", "warn")
        if self.state["weather"]["ground"] == "mud" and k["weather_impact_pct"] >= 20: self.push_alert("Ground state mud causing major movement penalties.", "crit")
        self.state["history"]["supply"].append({"turn": self.state["clock"]["turn_number"], "pct": k["supply_pct"]})
        self.state["history"]["readiness"].append({"turn": self.state["clock"]["turn_number"], "pct": k["readiness_pct"]})
        self._emit({"type": "kpi_updated", "kpis": k})

    def summarize_turn(self):
        dev = self.forecast_deviation()
        if dev > 15: self.push_alert(f"Forecast deviation {dev}% impacted operations.", "info")

    def environment_penalty(self) -> int:
        w = self.state["weather"]
        p = 0
        if w["condition"] in ("rain", "snow"): p += 8
        if w["wind_kph"] >= 25: p += 4
        if w["ground"] == "mud": p += 12
        if w["ground"] == "frozen": p += 5
        return min(40, max(0, p))

    def advance_weather(self):
        w = self.state["weather"]
        c = w["forecast_confidence"]
        jitter = (1 - c / 100.0) * 0.6
        w["temp_c"] += (random.random() - 0.5) * 6 * jitter
        w["wind_kph"] = max(0, min(60, w["wind_kph"] + (random.random() - 0.5) * 10 * jitter))
        w["precip_mm"] = max(0, min(20, w["precip_mm"] + (random.random() - 0.5) * 4 * jitter))
        if w["precip_mm"] >= 6: w["condition"] = "rain"
        elif w["precip_mm"] <= 1 and w["wind_kph"] < 20: w["condition"] = "clear"
        else: w["condition"] = "overcast"
        if w["condition"] == "rain" and w["precip_mm"] >= 8: w["ground"] = "mud"
        if w["temp_c"] <= -2: w["ground"] = "frozen"
        if w["condition"] == "clear" and w["precip_mm"] == 0 and w["temp_c"] >= 5 and w["ground"] == "mud":
            w["ground"] = "dry" if random.random() > 0.5 else "mud"
        w["forecast_confidence"] = max(40, min(90, w["forecast_confidence"] + (1 if random.random() > 0.5 else -1)))

    def forecast_deviation(self) -> int:
        conf = self.state["weather"]["forecast_confidence"]
        base = 100 - conf
        dev = int(base * (0.6 + random.random() * 0.8))
        return max(0, min(40, dev))

    def push_alert(self, text: str, severity: str = "info"):
        alert = {"id": f"alert_{random.randint(1000,9999)}", "text": text, "severity": severity}
        self.state["alerts"].append(alert)
        self._emit({"type": "alert_pushed", "alert": alert})

if __name__ == "__main__":
    e = TurnEngine(days_per_turn=2)
    e.on(lambda ev: print("EVENT:", ev))
    e.advance_one_turn()
