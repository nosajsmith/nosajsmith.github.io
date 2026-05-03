from __future__ import annotations

from server.objectives.control_v1 import compute_objective_status
from server.politics.clock_v2 import (
    PoliticalClockV2,
    compute_supply_aware_objective_pressure,
)
from server.politics.scoring_v1 import ScoringV1


def _scenario(*units):
    return {
        "objectives": [
            {
                "location_id": "SEOUL",
                "side": "ALLIED",
                "value": 80,
                "x": 10,
                "y": 10,
            }
        ],
        "units": list(units),
    }


def test_adequate_supply_force_near_objective_contributes_full_pressure() -> None:
    scenario = _scenario(
        {
            "id": "US-1",
            "side": "ALLIED",
            "strength": 100,
            "supply": 80,
            "readiness": 70,
            "x": 10,
            "y": 10,
        }
    )

    pressure = compute_supply_aware_objective_pressure(scenario)
    seoul = pressure["by_objective"]["ALLIED:SEOUL"]

    assert pressure["semantics"] == "supply_aware_objective_pressure_v1"
    assert pressure["affects_scoring"] is False
    assert seoul["objective_status"] == "held"
    assert seoul["pressure_state"] == "sustained"
    assert seoul["nearby_unit_count"] == 1
    assert seoul["contributing_unit_count"] == 1
    assert seoul["pressure_score"] == 100.0
    assert seoul["contributors"][0]["supply_state"] == "adequate"


def test_critically_low_supply_force_near_objective_is_suppressed_not_rewritten() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "strength": 100, "supply": 5, "x": 10, "y": 10}
    )

    status = compute_objective_status(scenario)
    pressure = compute_supply_aware_objective_pressure(scenario, status)
    scoring = ScoringV1(tick_hours=6)
    scoring.configure_from_scenario(scenario)
    scoring.tick(6, status)
    seoul = pressure["by_objective"]["ALLIED:SEOUL"]

    assert pressure["affects_scoring"] is False
    assert status["ALLIED:SEOUL"]["status"] == "held"
    assert status["ALLIED:SEOUL"]["controller_side"] == "ALLIED"
    assert seoul["objective_status"] == "held"
    assert seoul["pressure_state"] == "suppressed"
    assert seoul["nearby_unit_count"] == 1
    assert seoul["contributing_unit_count"] == 0
    assert seoul["suppressed_unit_count"] == 1
    assert seoul["pressure_score"] == 0.0
    assert seoul["contributors"][0]["supply_state"] == "critical"
    assert scoring.snapshot()["score_by_side"] == {"ALLIED": 80, "AXIS": 0}


def test_low_supply_force_contributes_degraded_pressure() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "strength": 100, "supply": 20, "x": 10, "y": 10}
    )

    pressure = compute_supply_aware_objective_pressure(scenario)
    seoul = pressure["by_objective"]["ALLIED:SEOUL"]

    assert seoul["pressure_state"] == "degraded"
    assert seoul["low_supply_unit_count"] == 1
    assert seoul["contributing_unit_count"] == 1
    assert seoul["pressure_score"] == 50.0
    assert seoul["contributors"][0]["supply_state"] == "low"


def test_pressure_does_not_replace_contested_truth_or_scoring() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "strength": 100, "supply": 80, "x": 10, "y": 10},
        {"id": "JP-1", "side": "AXIS", "strength": 90, "supply": 80, "x": 11, "y": 10},
    )
    status = compute_objective_status(scenario)
    pressure = compute_supply_aware_objective_pressure(scenario, status)
    scoring = ScoringV1(tick_hours=6)
    scoring.configure_from_scenario(scenario)

    scoring.tick(6, status)

    seoul = pressure["by_objective"]["ALLIED:SEOUL"]
    assert status["ALLIED:SEOUL"]["status"] == "contested"
    assert status["ALLIED:SEOUL"]["controller_side"] is None
    assert seoul["objective_status"] == "contested"
    assert seoul["pressure_state"] == "sustained"
    assert scoring.snapshot()["score_by_side"] == {"ALLIED": 0, "AXIS": 0}


def test_political_clock_carries_supply_aware_pressure_as_distinct_campaign_signal() -> None:
    scenario = _scenario(
        {
            "id": "US-1",
            "side": "ALLIED",
            "strength": 100,
            "supply": 80,
            "readiness": 70,
            "x": 10,
            "y": 10,
        }
    )
    status = compute_objective_status(scenario)
    clock = PoliticalClockV2(deadline_hours=72, player_side="ALLIED")
    clock.set_baseline(scenario)

    campaign = clock.on_time_advance(6, 6, scenario, status)

    objective_pressure = campaign["pressure"]["objective_pressure"]
    assert campaign["status"] == "ongoing"
    assert campaign["scoring"]["score_by_side"] == {"ALLIED": 80, "AXIS": 0}
    assert campaign["pressure"]["pressure_score"] == 100.0
    assert objective_pressure["affects_scoring"] is False
    assert objective_pressure["by_objective"]["ALLIED:SEOUL"]["pressure_state"] == "sustained"
