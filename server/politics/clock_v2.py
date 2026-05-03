from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from server.objectives.control_v1 import compute_objective_status
from server.politics.scoring_v1 import ScoringV1

OBJECTIVE_PRESSURE_SEMANTICS = "supply_aware_objective_pressure_v1"
OBJECTIVE_PRESSURE_RADIUS = 1
OBJECTIVE_PRESSURE_ADEQUATE_SUPPLY = 30
OBJECTIVE_PRESSURE_CRITICAL_SUPPLY = 10
OBJECTIVE_PRESSURE_LOW_SUPPLY_FACTOR = 0.5


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


def _pos(item: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    if "x" in item and "y" in item:
        return (int(item["x"]), int(item["y"]))
    pos = item.get("position")
    if not pos:
        pos = item.get("pos")
    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
        return (int(pos[0]), int(pos[1]))
    return None


def _dist(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _objective_key(side: str, location_id: str) -> str:
    return f"{side}:{location_id}"


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


def _supply_pressure_factor(supply: int) -> Tuple[float, str]:
    if supply < OBJECTIVE_PRESSURE_CRITICAL_SUPPLY:
        return 0.0, "critical"
    if supply < OBJECTIVE_PRESSURE_ADEQUATE_SUPPLY:
        return OBJECTIVE_PRESSURE_LOW_SUPPLY_FACTOR, "low"
    return 1.0, "adequate"


def compute_supply_aware_objective_pressure(
    scenario: Dict[str, Any],
    objective_status: Dict[str, Dict[str, Any]] | None = None,
    *,
    radius: int = OBJECTIVE_PRESSURE_RADIUS,
) -> Dict[str, Any]:
    objectives = scenario.get("objectives", []) if isinstance(scenario, dict) else []
    units = scenario.get("units", []) if isinstance(scenario, dict) else []
    if not isinstance(objectives, list):
        objectives = []
    if not isinstance(units, list):
        units = []

    status_by_objective = (
        objective_status
        if isinstance(objective_status, dict)
        else compute_objective_status(scenario, radius=radius)
    )

    by_objective: Dict[str, Dict[str, Any]] = {}
    objective_reasons: List[str] = []
    total_pressure_score = 0.0

    for objective in objectives:
        if not isinstance(objective, dict):
            continue
        side = str(objective.get("side", "")).upper().strip()
        location_id = str(objective.get("location_id", "")).upper().strip()
        if not side or not location_id:
            continue

        key = _objective_key(side, location_id)
        objective_pos = _pos(objective)
        status = dict(status_by_objective.get(key) or {})
        contributors: List[Dict[str, Any]] = []
        nearby_unit_count = 0
        suppressed_unit_count = 0
        low_supply_unit_count = 0
        raw_strength = 0
        pressure_score = 0.0

        for unit in units:
            if not isinstance(unit, dict):
                continue
            if _infer_side(unit) != side:
                continue
            unit_pos = _pos(unit)
            if objective_pos is None or unit_pos is None:
                continue
            if _dist(objective_pos, unit_pos) > radius:
                continue

            strength = max(0, int(unit.get("strength", 0) or 0))
            if strength <= 0:
                continue

            supply = int(unit.get("supply", 0) or 0)
            factor, supply_state = _supply_pressure_factor(supply)
            contribution = round(strength * factor, 3)

            nearby_unit_count += 1
            raw_strength += strength
            pressure_score += contribution
            if supply_state != "adequate":
                low_supply_unit_count += 1
            if contribution <= 0:
                suppressed_unit_count += 1

            contributors.append(
                {
                    "unit_id": str(unit.get("id") or unit.get("unit_id") or ""),
                    "supply": supply,
                    "strength": strength,
                    "supply_state": supply_state,
                    "contribution": contribution,
                }
            )

        if nearby_unit_count <= 0:
            pressure_state = "none"
        elif pressure_score <= 0:
            pressure_state = "suppressed"
        elif pressure_score < raw_strength:
            pressure_state = "degraded"
        else:
            pressure_state = "sustained"

        pressure_score = round(pressure_score, 3)
        total_pressure_score += pressure_score
        if pressure_state in {"suppressed", "degraded"}:
            objective_reasons.append(f"{key}:{pressure_state}_by_supply")

        by_objective[key] = {
            "side": side,
            "location_id": location_id,
            "objective_status": status.get("status", "unknown"),
            "controller_side": status.get("controller_side"),
            "objective_truth_source": "control_v1",
            "nearby_unit_count": nearby_unit_count,
            "contributing_unit_count": sum(
                1 for item in contributors if item["contribution"] > 0
            ),
            "low_supply_unit_count": low_supply_unit_count,
            "suppressed_unit_count": suppressed_unit_count,
            "raw_strength": raw_strength,
            "pressure_score": pressure_score,
            "pressure_state": pressure_state,
            "contributors": contributors,
        }

    return {
        "semantics": OBJECTIVE_PRESSURE_SEMANTICS,
        "radius": int(radius),
        "supply_thresholds": {
            "critical_below": OBJECTIVE_PRESSURE_CRITICAL_SUPPLY,
            "adequate_at_or_above": OBJECTIVE_PRESSURE_ADEQUATE_SUPPLY,
            "low_supply_factor": OBJECTIVE_PRESSURE_LOW_SUPPLY_FACTOR,
        },
        "affects_scoring": False,
        "by_objective": by_objective,
        "total_pressure_score": round(total_pressure_score, 3),
        "reasons": objective_reasons,
    }


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
        objective_pressure = compute_supply_aware_objective_pressure(scenario)
        details["objective_pressure"] = objective_pressure
        details["pressure_score"] = objective_pressure["total_pressure_score"]
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
