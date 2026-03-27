from __future__ import annotations

from dataclasses import is_dataclass

from engine.ai import BAIReport, OperationCandidate, StrategicDirective, TacticalIntent, UnitOrderWrapper, attach_bai_report, build_bai_report
from tools.bai_warlab.ai_report_adapter import normalize_ai_report


def test_engine_bai_models_are_dataclasses_and_serialize_cleanly():
    directive = StrategicDirective(
        directive_id="directive_hold_seoul",
        side="ALLIED",
        posture="DEFEND",
        main_objective="SEOUL",
        supporting_objectives=["HAN_RIVER_LINE"],
        reserve_policy="preserve_one_mobile_reserve",
        desired_end_state="Hold the Seoul approaches through turn 5.",
        horizon_turns=5,
        assumptions=["Enemy main effort remains on the west axis."],
    )
    operation = OperationCandidate(
        operation_id="op_han_river_shield",
        name="Hold Han River Line",
        operation_type="defensive_shield",
        posture="DEFEND",
        target_objective="SEOUL",
        score=0.84,
        priority=1,
        reserve_level="MEDIUM",
        timing_breakdown={"planning_ms": 12, "selection_ms": 3},
        rationale=["Preserves objective control while keeping a reserve uncommitted."],
        selected=True,
    )
    intent = TacticalIntent(
        intent_id="intent_1",
        unit_id="UN-1",
        action="hold",
        posture="DEFEND",
        target_location_id="SEOUL_WEST",
        objective_id="SEOUL",
        priority=1,
        supporting_unit_ids=["UN-2"],
        rationale="Anchor the west approach and delay line collapse.",
    )
    attack_intent = TacticalIntent(
        intent_id="intent_2",
        unit_id="UN-2",
        action="attack",
        posture="ATTACK",
        target_location_id="SEOUL_BRIDGE",
        objective_id="SEOUL",
        priority=2,
        rationale="Exploit a favorable local force ratio before the enemy consolidates.",
    )
    order = UnitOrderWrapper(
        unit_id="UN-1",
        action="hold",
        posture="DEFEND",
        target_location_id="SEOUL_WEST",
        objective_id="SEOUL",
        intent_id="intent_1",
        operation_id="op_han_river_shield",
        directive_id="directive_hold_seoul",
        priority=1,
        notes="Entrench and maintain reserve link.",
    )
    attack_order = UnitOrderWrapper(
        unit_id="UN-2",
        action="attack",
        posture="ATTACK",
        target_location_id="SEOUL_BRIDGE",
        objective_id="SEOUL",
        intent_id="intent_2",
        operation_id="op_han_river_shield",
        directive_id="directive_hold_seoul",
        priority=2,
        notes="Commit only while local odds remain favorable.",
    )
    report = BAIReport(
        posture="DEFEND",
        main_objective="SEOUL",
        chosen_operation=operation,
        reserve_level="MEDIUM",
        timing_breakdown={"planning_ms": 12, "selection_ms": 3},
        strategic_directive=directive,
        tactical_intents=[intent, attack_intent],
        unit_orders=[order, attack_order],
        extra={"staff_note": "Delay, preserve reserves, and trade space carefully."},
    )

    assert is_dataclass(directive)
    assert is_dataclass(operation)
    assert is_dataclass(intent)
    assert is_dataclass(order)
    assert is_dataclass(report)

    payload = report.to_dict()
    assert payload["posture"] == "DEFEND"
    assert payload["strategic_directive"]["directive_id"] == "directive_hold_seoul"
    assert payload["chosen_operation"]["name"] == "Hold Han River Line"
    assert payload["tactical_intents"][0]["intent_id"] == "intent_1"
    assert payload["unit_orders"][0]["unit_id"] == "UN-1"
    assert payload["report_version"] == "bai_report_v1"
    assert payload["attack_reason_summaries"]
    assert payload["hold_reason_summaries"]
    assert payload["summary_lines"][0] == "Posture: DEFEND"
    assert payload["staff_note"].startswith("Delay")

    attached = attach_bai_report({}, report)
    assert attached["bai_report"]["reserve_level"] == "MEDIUM"

    built = build_bai_report(
        posture="DEFEND",
        main_objective="SEOUL",
        chosen_operation=operation,
        reserve_level="MEDIUM",
        timing_breakdown={"planning_ms": 12},
        strategic_directive=directive,
        tactical_intents=[intent, attack_intent],
        unit_orders=[order, attack_order],
    )
    normalized = normalize_ai_report(built)
    assert normalized["available"] is True
    assert normalized["posture"] == "DEFEND"
    assert normalized["main_objective"] == "SEOUL"
    assert normalized["chosen_operation"] == "Hold Han River Line"
    assert normalized["reserve_level"] == "MEDIUM"
    assert normalized["timing_breakdown"] == {"planning_ms": 12}
    assert built["bai_report"]["attack_reason_summaries"][0].startswith("UN-2 attack SEOUL_BRIDGE")
    assert built["bai_report"]["hold_reason_summaries"][0].startswith("UN-1 hold SEOUL_WEST")
