from __future__ import annotations

from server.objectives.control_v1 import compute_objective_status
from server.politics.scoring_v1 import ScoringV1


def _scenario(*units):
    return {
        "objectives": [
            {"location_id": "INCHON", "side": "ALLIED", "value": 35, "x": 10, "y": 10},
            {"location_id": "KIMPO", "side": "ALLIED", "value": 45, "x": 20, "y": 20},
            {"location_id": "SEOUL", "side": "AXIS", "value": 60, "x": 30, "y": 30},
        ],
        "units": list(units),
    }


def test_scoring_v1_uses_scenario_objective_values() -> None:
    scoring = ScoringV1(tick_hours=6, win_score=180)
    scoring.configure_from_scenario(
        {
            "objectives": [
                {"side": "ALLIED", "location_id": "INCHON", "value": 35},
                {"side": "ALLIED", "location_id": "KIMPO", "value": 45},
                {"side": "AXIS", "location_id": "SEOUL", "value": 60},
            ]
        }
    )

    scoring.tick(
        6,
        {
            "ALLIED:INCHON": True,
            "ALLIED:KIMPO": True,
            "AXIS:SEOUL": True,
        },
    )

    snap = scoring.snapshot()
    assert snap["score_by_side"] == {"ALLIED": 80, "AXIS": 60}


def test_scoring_only_awards_held_objectives() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "x": 10, "y": 10},
        {"id": "US-2", "side": "ALLIED", "x": 20, "y": 20},
    )
    scoring = ScoringV1(tick_hours=6)
    scoring.configure_from_scenario(scenario)

    scoring.tick(6, compute_objective_status(scenario))

    assert scoring.snapshot()["score_by_side"] == {"ALLIED": 80, "AXIS": 0}


def test_scoring_does_not_award_contested_objectives() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "x": 10, "y": 10},
        {"id": "JP-1", "side": "AXIS", "x": 11, "y": 10},
    )
    scoring = ScoringV1(tick_hours=6)
    scoring.configure_from_scenario(scenario)

    scoring.tick(6, compute_objective_status(scenario))

    assert scoring.snapshot()["score_by_side"] == {"ALLIED": 0, "AXIS": 0}


def test_scoring_does_not_award_neutral_objectives() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "x": 14, "y": 14},
        {"id": "JP-1", "side": "AXIS", "x": 40, "y": 40},
    )
    scoring = ScoringV1(tick_hours=6)
    scoring.configure_from_scenario(scenario)

    scoring.tick(6, compute_objective_status(scenario))

    assert scoring.snapshot()["score_by_side"] == {"ALLIED": 0, "AXIS": 0}


def test_scoring_does_not_award_enemy_only_neutral_objective() -> None:
    scenario = _scenario({"id": "JP-1", "side": "AXIS", "x": 10, "y": 10})
    scoring = ScoringV1(tick_hours=6)
    scoring.configure_from_scenario(scenario)

    scoring.tick(6, compute_objective_status(scenario))

    assert scoring.snapshot()["score_by_side"] == {"ALLIED": 0, "AXIS": 0}
