from __future__ import annotations

from dataclasses import dataclass

from engine.ai import BAIController
from engine.core.map_model import GameMap, MapTile, Terrain
from engine.core.time_system import GameTime
from engine.core.unit_model import Posture, Side, UnitRepository, UnitState, UnitType
from tools.bai_warlab.ai_report_adapter import normalize_ai_report


@dataclass
class DummyEngineState:
    time: GameTime
    game_map: GameMap
    units: UnitRepository
    meta: dict


def _build_engine_state() -> DummyEngineState:
    game_map = GameMap()
    game_map.add_tile(MapTile(tile_id="LUNGA", name="Lunga Point", terrain=Terrain.PLAINS))
    game_map.add_tile(MapTile(tile_id="TULAGI", name="Tulagi", terrain=Terrain.JUNGLE))
    game_map.add_tile(MapTile(tile_id="MANTANIKAU", name="Matanikau", terrain=Terrain.PLAINS))

    units = UnitRepository()
    units.add(
        UnitState(
            id="US-1MAR",
            name="1st Marine Division",
            side=Side.ALLIED,
            unit_type=UnitType.INFANTRY,
            strength=100,
            fatigue=10,
            morale=70,
            supply=80,
            readiness=60,
            location_id="LUNGA",
            posture=Posture.DEFEND,
        )
    )
    units.add(
        UnitState(
            id="JP-35BDE",
            name="35th Infantry Brigade",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=90,
            fatigue=5,
            morale=65,
            supply=70,
            readiness=55,
            location_id="TULAGI",
            posture=Posture.DEFEND,
        )
    )
    units.add(
        UnitState(
            id="JP-2DIV",
            name="2nd Division",
            side=Side.AXIS,
            unit_type=UnitType.INFANTRY,
            strength=80,
            fatigue=15,
            morale=60,
            supply=75,
            readiness=58,
            location_id="MANTANIKAU",
            posture=Posture.HOLD,
        )
    )

    return DummyEngineState(
        time=GameTime(day=2, phase="day"),
        game_map=game_map,
        units=units,
        meta={
            "id": "mini_gc_1942",
            "name": "Mini Guadalcanal 1942",
            "objectives": [
                {"location_id": "LUNGA", "side": "ALLIED", "value": 50},
                {"location_id": "TULAGI", "side": "ALLIED", "value": 100},
                {"location_id": "TULAGI", "side": "AXIS", "value": 50},
            ],
        },
    )


def test_bai_controller_returns_legal_orders_and_warlab_readable_report():
    controller = BAIController()
    result = controller.plan_turn(_build_engine_state(), side="AXIS", time_budget_ms=50)

    assert result.side == "AXIS"
    assert result.orders
    assert result.generated_order_count >= result.legal_order_count >= 1
    assert result.budget_exceeded is False
    assert {"campaign_stub", "strategic", "operational", "validate", "total_ms"} <= set(result.timing_breakdown)

    for order in result.orders:
        assert order["type"] == "move"
        assert order["unit_id"] in {"JP-35BDE", "JP-2DIV"}
        assert order["target"] in {"LUNGA", "TULAGI", "MANTANIKAU"}
        assert order["posture"] in {"HOLD", "MOVE", "ATTACK", "DEFEND", "REST", "REFIT"}

    normalized = normalize_ai_report(result.report)
    assert normalized["available"] is True
    assert normalized["posture"] == "CONTAIN"
    assert normalized["main_objective"] == "TULAGI"
    assert normalized["chosen_operation"] == "Hold line at TULAGI"
    assert normalized["reserve_level"] == "MEDIUM"
    assert "timing_breakdown" in normalized
    assert result.report["bai_report"]["report_version"] == "bai_report_v1"
    assert isinstance(result.report["bai_report"]["attack_reason_summaries"], list)
    assert isinstance(result.report["bai_report"]["hold_reason_summaries"], list)
    assert result.report["bai_report"]["summary_lines"][0].startswith("Posture:")
    assert result.report["bai_report"]["runtime_profile"]["thresholds"]["attack_supply_floor"] >= 20
    assert result.report["bai_report"]["runtime_profile"]["weights"]["enemy_objective"] >= 1.0
    assert result.report["bai_report"]["reserve_plan"]["target_fraction"] > 0
    assert result.report["bai_report"]["reserve_plan"]["commitment_state"] == "HOLDING_RESERVE"
    assert len(result.report["bai_report"]["reserve_plan"]["held_reserve_ids"]) == 1
    assert result.report["bai_report"]["strategic_directive"]["metadata"]["objective_explanation"]
    assert 2 <= len(result.report["bai_report"]["operations"]) <= 5
    assert result.report["bai_report"]["operations"][0]["selected"] is True
    assert len(result.report["bai_report"]["support_actions"]) <= 2
    assert result.report["bai_report"]["operations"][0]["metadata"]["evaluation"]["dominant_reason"]
    assert result.report["bai_report"]["tactical_intents"][0]["metadata"]["evaluation"]["reasons"]


def test_bai_controller_uses_budget_fallback_and_still_returns_legal_orders():
    controller = BAIController()
    controller._elapsed_ms = lambda started_ns: 1  # force budget exhaustion path

    result = controller.plan_turn(_build_engine_state(), side="AXIS", time_budget_ms=0)

    assert result.orders
    assert result.budget_exceeded is True
    assert any(item["code"] == "controller.tactical_budget_fallback" for item in result.diagnostics)
    assert all(order["type"] == "move" for order in result.orders)

    normalized = normalize_ai_report(result.report)
    assert normalized["available"] is True
    assert normalized["posture"] in {"OFFENSIVE", "DEFENSIVE", "CONTAIN"}
    assert normalized["chosen_operation"] is not None


def test_bai_controller_runtime_profile_overrides_change_behavior():
    controller = BAIController()
    aggressive = controller.plan_turn(
        _build_engine_state(),
        side="AXIS",
        engine_config={
            "axis": {
                "aggression": 0.9,
                "caution_bias": 0.15,
                "risk_tolerance": 0.9,
                "reserve_preservation_bias": 0.2,
                "reserve_commitment": 0.8,
                "breakthrough_focus": 0.9,
            }
        },
    )
    cautious = controller.plan_turn(
        _build_engine_state(),
        side="AXIS",
        engine_config={
            "axis": {
                "aggression": 0.2,
                "caution_bias": 0.9,
                "risk_tolerance": 0.2,
                "reserve_preservation_bias": 0.9,
                "reserve_commitment": 0.2,
                "logistics_emphasis": 0.8,
            }
        },
    )

    aggressive_report = aggressive.report["bai_report"]["runtime_profile"]
    cautious_report = cautious.report["bai_report"]["runtime_profile"]

    assert normalize_ai_report(aggressive.report)["posture"] == "OFFENSIVE"
    assert normalize_ai_report(cautious.report)["posture"] == "DEFENSIVE"
    assert aggressive_report["thresholds"]["attack_supply_floor"] < cautious_report["thresholds"]["attack_supply_floor"]
    assert aggressive_report["thresholds"]["reserve_target_fraction"] < cautious_report["thresholds"]["reserve_target_fraction"]


def test_bai_controller_keeps_strategic_direction_sticky_between_turns():
    controller = BAIController()
    state = _build_engine_state()

    first = controller.plan_turn(state, side="AXIS", time_budget_ms=50)
    state.time.day = 3
    second = controller.plan_turn(state, side="AXIS", time_budget_ms=50)

    first_report = first.report["bai_report"]["strategic_directive"]
    second_report = second.report["bai_report"]["strategic_directive"]

    assert first_report["posture"] == second_report["posture"]
    assert first_report["main_objective"] == second_report["main_objective"]
    assert "avoid posture whiplash" in " ".join(second_report["notes"]).lower()


def test_bai_controller_validation_layer_filters_conflicts_and_returns_stable_output():
    controller = BAIController()
    controller._run_tactical_layer = lambda snapshot, directive, operation, reserve_plan, runtime_profile: {
        "orders": [
            {},
            {"type": "move", "unit_id": "JP-35BDE", "target": "NOPE", "posture": "ATTACK"},
            {"type": "move", "unit_id": "JP-35BDE", "target": "TULAGI", "posture": "BROKEN"},
            {"type": "move", "unit_id": "JP-35BDE", "target": "MANTANIKAU", "posture": "MOVE"},
            {"type": "move", "unit_id": "US-1MAR", "target": "LUNGA", "posture": "ATTACK"},
        ],
        "intents": [],
        "wrapped_orders": [],
        "diagnostics": [],
        "metadata": {},
    }

    result = controller.plan_turn(_build_engine_state(), side="AXIS", time_budget_ms=50)

    assert result.orders == [{"type": "move", "unit_id": "JP-35BDE", "target": "TULAGI", "posture": "HOLD"}]
    codes = {item["code"] for item in result.diagnostics}
    assert {"order.empty_action", "order.unknown_target", "order.invalid_posture", "order.conflicting_duplicate", "order.unknown_or_wrong_side_unit"} <= codes
