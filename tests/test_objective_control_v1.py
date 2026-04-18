from __future__ import annotations

from server.objectives.control_v1 import (
    compute_objective_state,
    compute_objective_status,
)


def _scenario(*units):
    return {
        "objectives": [
            {"location_id": "SEOUL", "side": "ALLIED", "x": 10, "y": 10},
        ],
        "units": list(units),
    }


def test_objective_status_is_held_when_only_designated_side_is_in_range() -> None:
    scenario = _scenario({"id": "US-1", "side": "ALLIED", "x": 10, "y": 10})

    status = compute_objective_status(scenario)
    state = compute_objective_state(scenario)

    assert status["ALLIED:SEOUL"] == {
        "side": "ALLIED",
        "location_id": "SEOUL",
        "status": "held",
        "designated_side_in_range": True,
        "opposing_side_in_range": False,
        "controller_side": "ALLIED",
    }
    assert state["ALLIED:SEOUL"] is True


def test_objective_status_is_contested_when_both_sides_are_in_range() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "x": 10, "y": 10},
        {"id": "JP-1", "side": "AXIS", "x": 11, "y": 10},
    )

    status = compute_objective_status(scenario)
    state = compute_objective_state(scenario)

    assert status["ALLIED:SEOUL"]["status"] == "contested"
    assert status["ALLIED:SEOUL"]["designated_side_in_range"] is True
    assert status["ALLIED:SEOUL"]["opposing_side_in_range"] is True
    assert status["ALLIED:SEOUL"]["controller_side"] is None
    assert state["ALLIED:SEOUL"] is False


def test_objective_status_is_neutral_when_neither_side_is_in_range() -> None:
    scenario = _scenario(
        {"id": "US-1", "side": "ALLIED", "x": 14, "y": 14},
        {"id": "JP-1", "side": "AXIS", "x": 15, "y": 15},
    )

    status = compute_objective_status(scenario)
    state = compute_objective_state(scenario)

    assert status["ALLIED:SEOUL"]["status"] == "neutral"
    assert status["ALLIED:SEOUL"]["controller_side"] is None
    assert state["ALLIED:SEOUL"] is False


def test_objective_status_is_neutral_when_only_enemy_side_is_in_range() -> None:
    scenario = _scenario({"id": "JP-1", "side": "AXIS", "x": 10, "y": 10})

    status = compute_objective_status(scenario)
    state = compute_objective_state(scenario)

    assert status["ALLIED:SEOUL"]["status"] == "neutral"
    assert status["ALLIED:SEOUL"]["designated_side_in_range"] is False
    assert status["ALLIED:SEOUL"]["opposing_side_in_range"] is True
    assert status["ALLIED:SEOUL"]["controller_side"] is None
    assert state["ALLIED:SEOUL"] is False
