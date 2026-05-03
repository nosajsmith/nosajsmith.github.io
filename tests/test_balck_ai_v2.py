from __future__ import annotations

from server.ai.balck_v1 import SUPPORTED_BALCK_KINDS, BalckAIV2
from server.harding.kernel_v1 import HardingKernelV1
from server.objectives.control_v1 import compute_objective_state, compute_objective_status
from server.politics.clock_v2 import compute_supply_aware_objective_pressure


def _objective(location_id: str, *, value: int = 100, tier: int = 5) -> dict:
    return {
        "id": f"obj_{location_id.lower()}",
        "location_id": location_id,
        "side": "AXIS",
        "value": value,
        "importance_tier": tier,
        "x": 10,
        "y": 10,
    }


def _axis_unit(
    unit_id: str = "JP-1",
    *,
    supply: int = 80,
    readiness: int = 70,
    x: int = 10,
    y: int = 10,
) -> dict:
    return {
        "id": unit_id,
        "side": "AXIS",
        "strength": 100,
        "supply": supply,
        "readiness": readiness,
        "x": x,
        "y": y,
    }


def _allied_unit(unit_id: str = "US-1", *, x: int = 11, y: int = 10) -> dict:
    return {
        "id": unit_id,
        "side": "ALLIED",
        "strength": 90,
        "supply": 80,
        "readiness": 70,
        "x": x,
        "y": y,
    }


def _scenario(*units: dict, objectives: list[dict] | None = None) -> dict:
    return {
        "objectives": objectives if objectives is not None else [_objective("SEOUL")],
        "units": list(units),
    }


def _state(scenario: dict) -> dict:
    objective_status = compute_objective_status(scenario)
    return {
        "scenario": scenario,
        "objective_state": compute_objective_state(scenario),
        "objective_status": objective_status,
        "objective_pressure": compute_supply_aware_objective_pressure(
            scenario,
            objective_status,
        ),
        "score_by_side": {"ALLIED": 0, "AXIS": 0},
    }


def test_contested_priority_objective_changes_balck_behavior_from_hold_to_attack() -> None:
    ai = BalckAIV2(side="AXIS")
    held_state = _state(_scenario(_axis_unit()))
    contested_state = _state(_scenario(_axis_unit(), _allied_unit()))

    held_order = ai.decide_orders(held_state, now=6)
    contested_order = ai.decide_orders(contested_state, now=6)

    assert len(held_order) == 1
    assert len(contested_order) == 1
    assert held_order[0]["kind"] == "support"
    assert held_order[0]["intent"] == "hold_objective"
    assert contested_order[0]["kind"] == "attack"
    assert contested_order[0]["intent"] == "press_objective"
    assert contested_order[0]["metadata"]["objective_status"] == "contested"
    assert contested_order[0]["metadata"]["pressure_state"] == "sustained"


def test_suppressed_pressure_or_poor_supply_causes_conservative_balck_behavior() -> None:
    ai = BalckAIV2(side="AXIS")
    scenario = _scenario(_axis_unit(supply=5), _allied_unit())

    orders = ai.decide_orders(_state(scenario), now=6)

    assert len(orders) == 1
    assert orders[0]["kind"] == "withdraw"
    assert orders[0]["intent"] == "recover_supply_before_pressure"
    assert orders[0]["metadata"]["objective_status"] == "contested"
    assert orders[0]["metadata"]["pressure_state"] == "suppressed"


def test_neutral_objective_without_pressure_uses_probe_support_not_attack() -> None:
    ai = BalckAIV2(side="AXIS")
    scenario = _scenario(_axis_unit(x=20, y=20))

    orders = ai.decide_orders(_state(scenario), now=6)

    assert len(orders) == 1
    assert orders[0]["kind"] == "support"
    assert orders[0]["intent"] == "probe_without_overcommitment"
    assert orders[0]["metadata"]["objective_status"] == "neutral"
    assert orders[0]["metadata"]["pressure_state"] == "none"


def test_adequate_supply_and_sustained_pressure_allow_balck_to_press() -> None:
    ai = BalckAIV2(side="AXIS")
    scenario = _scenario(_axis_unit(supply=80, readiness=75), _allied_unit())

    orders = ai.decide_orders(_state(scenario), now=6)

    assert len(orders) == 1
    assert orders[0]["kind"] == "attack"
    assert orders[0]["unit_id"] == "JP-1"
    assert orders[0]["target_location_id"] == "SEOUL"
    assert orders[0]["metadata"]["semantics"] == "balck_ai_v2"


def test_balck_v2_preserves_one_intent_for_multiple_candidate_objectives() -> None:
    ai = BalckAIV2(side="AXIS")
    objectives = [
        _objective("SEOUL", value=120, tier=5),
        {**_objective("KIMPO", value=60, tier=3), "x": 20, "y": 20},
    ]
    scenario = _scenario(
        _axis_unit("JP-SEOUL", x=10, y=10),
        _allied_unit("US-SEOUL", x=11, y=10),
        _axis_unit("JP-KIMPO", x=20, y=20),
        _allied_unit("US-KIMPO", x=21, y=20),
        objectives=objectives,
    )

    orders = ai.decide_orders(_state(scenario), now=6)

    assert len(orders) == 1
    assert orders[0]["kind"] in SUPPORTED_BALCK_KINDS
    assert orders[0]["target_location_id"] == "SEOUL"


def test_harding_kernel_default_balck_v2_submits_one_supported_kind() -> None:
    kernel = HardingKernelV1("scenarios")
    kernel.scenario = _scenario(_axis_unit(), _allied_unit())
    kernel.ai_enabled = True

    result = kernel.handle("clock.step", {"dt_hours": 6})
    pending = kernel.event_queue.pending()

    assert result["ok"] is True
    assert result["ai_submitted"] == ["attack"]
    assert len(pending) == 1
    assert pending[0]["kind"] in SUPPORTED_BALCK_KINDS
    assert pending[0]["event"]["metadata"]["semantics"] == "balck_ai_v2"
