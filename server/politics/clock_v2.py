from __future__ import annotations

from typing import Any, Dict, List, Tuple

from server.politics.scoring_v1 import ScoringV1


def _infer_side(unit: Dict[str, Any]) -> str:
    side = str(unit.get("side", "")).strip().upper()
    if side:
        return side
    uid = str(unit.get("id") or unit.get("unit_id") or "").strip().upper()
    if uid.startswith("US-") or uid.startswith("ALL-"):
        return "ALLIED"
    if uid.startswith("JP-") or uid.startswith("AX-"):
        return "AXIS"
    return "UNKNOWN"


def _units_for_side(scenario: Dict[str, Any], side: str) -> List[Dict[str, Any]]:
    units = scenario.get("units", []) if isinstance(scenario, dict) else []
    out: List[Dict[str, Any]] = []
    if not isinstance(units, list):
        return out
    for unit in units:
        if not isinstance(unit, dict):
            continue
        if _infer_side(unit) == side:
            out.append(unit)
    return out


def snapshot_side_metrics(scenario: Dict[str, Any], side: str) -> Dict[str, Any]:
    units = _units_for_side(scenario, side)
    if not units:
        return {
            "side": side,
            "count": 0,
            "strength": 0,
            "avg_supply": 0,
            "avg_readiness": 0,
        }

    strength = sum(int(unit.get("strength", 0)) for unit in units)
    avg_supply = sum(int(unit.get("supply", 0)) for unit in units) / len(units)
    avg_readiness = sum(int(unit.get("readiness", 0)) for unit in units) / len(units)
    return {
        "side": side,
        "count": len(units),
        "strength": int(strength),
        "avg_supply": float(avg_supply),
        "avg_readiness": float(avg_readiness),
    }


def evaluate_collapse(
    scenario: Dict[str, Any],
    side: str,
    baseline_strength: int,
    thresholds: Dict[str, float] | None = None,
) -> Tuple[bool, Dict[str, Any]]:
    th = thresholds or {
        "min_strength_ratio": 0.7,
        "min_avg_supply": 30.0,
        "min_avg_readiness": 35.0,
    }
    metrics = snapshot_side_metrics(scenario, side)
    strength_now = int(metrics["strength"])
    strength_ratio = strength_now / baseline_strength if baseline_strength > 0 else 1.0
    avg_supply = float(metrics["avg_supply"])
    avg_readiness = float(metrics["avg_readiness"])

    reasons: List[str] = []
    if strength_ratio <= float(th["min_strength_ratio"]):
        reasons.append(
            f"force_integrity {strength_ratio:.2f} <= {float(th['min_strength_ratio']):.2f}"
        )
    if avg_supply <= float(th["min_avg_supply"]):
        reasons.append(
            f"supply_collapse {avg_supply:.1f} <= {float(th['min_avg_supply']):.1f}"
        )
    if avg_readiness <= float(th["min_avg_readiness"]):
        reasons.append(
            f"cohesion_collapse {avg_readiness:.1f} <= {float(th['min_avg_readiness']):.1f}"
        )

    details = {
        "metrics": metrics,
        "baseline_strength": int(baseline_strength),
        "strength_ratio": float(strength_ratio),
        "thresholds": th,
        "reasons": reasons,
    }
    return (len(reasons) > 0, details)


class PoliticalClockV2:
    """
    Phase 9.1 + 9.2:
    - Early-loss pressure
    - Objective-based scoring
    - Deadline
    """

    __static_attributes__ = (
        "baseline_strength",
        "deadline_hours",
        "last_pressure",
        "player_side",
        "scoring",
        "status",
    )

    def __init__(self, deadline_hours: int = 72, player_side: str = "ALLIED"):
        self.deadline_hours = int(deadline_hours)
        self.player_side = player_side
        self.status = "ongoing"
        self.baseline_strength = 0
        self.last_pressure: Dict[str, Any] = {}
        self.scoring = ScoringV1()

    def set_baseline(self, scenario: Dict[str, Any]) -> None:
        units = scenario.get("units", []) if isinstance(scenario, dict) else []
        total = 0
        for unit in units:
            if not isinstance(unit, dict):
                continue
            uid = str(unit.get("id") or unit.get("unit_id") or "").upper()
            side = str(unit.get("side", "")).upper()
            if side != self.player_side:
                if self.player_side != "ALLIED" or not uid.startswith("US-"):
                    continue
            total += int(unit.get("strength", 0) or 0)

        self.baseline_strength = total if total > 0 else 1
        self.scoring.reset()
        self.scoring.configure_from_scenario(scenario)

    def snapshot(self, now: int, objective_state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": self.status,
            "deadline_hours": self.deadline_hours,
            "time_now": now,
            "time_remaining": max(0, self.deadline_hours - now),
            "pressure": self.last_pressure,
            "scoring": self.scoring.snapshot(),
            "objective_state": dict(objective_state),
        }

    def on_time_advance(
        self,
        dt_hours: int,
        now: int,
        scenario: Dict[str, Any],
        objective_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.baseline_strength <= 0:
            self.set_baseline(scenario)

        if self.status != "ongoing":
            return self.snapshot(now, objective_state)

        self.scoring.tick(dt_hours, objective_state)
        is_loss, details = evaluate_collapse(
            scenario=scenario,
            side=self.player_side,
            baseline_strength=self.baseline_strength,
        )
        self.last_pressure = details
        if is_loss:
            self.status = "loss"
            return self.snapshot(now, objective_state)

        winner = self.scoring.has_winner()
        if winner == self.player_side:
            self.status = "win"
            return self.snapshot(now, objective_state)

        if now >= self.deadline_hours:
            self.status = "loss"

        return self.snapshot(now, objective_state)
