from __future__ import annotations

import asyncio

from server import mwe_bridge_p8_ws15 as bridge
from server.view_snapshot import build_view_snapshot


def test_view_snapshot_contract_unifies_operation_truth_pressure_score_ai_and_reports() -> None:
    authored = {
        "id": "contract_demo",
        "name": "Contract Demo",
        "theater_id": "demo_theater",
        "map_package": "demo_map",
        "weather": "Clear",
        "objectives": [
            {
                "id": "obj_hill",
                "location_id": "HILL",
                "name": "Hill 101",
                "side": "ALLIED",
                "value": 80,
                "state": "unheld",
                "x": 10,
                "y": 10,
            }
        ],
        "units": [
            {
                "id": "US-1",
                "side": "ALLIED",
                "strength": 100,
                "supply": 20,
                "readiness": 70,
                "location_id": "HILL",
                "x": 10,
                "y": 10,
            }
        ],
    }
    engine_state = {
        "game": {
            "scenario": "Contract Demo",
            "time": {"day": 2, "phase": "day", "weather": "Rain"},
            "vp": {"ALLIED": 80, "AXIS": 0},
            "ai": {"enabled": True, "side": "AXIS", "last_orders": 1},
        },
        "units": [
            {
                "id": "US-1",
                "side": "ALLIED",
                "strength": 100,
                "supply": 20,
                "readiness": 70,
                "location_id": "HILL",
            }
        ],
        "bai_report": {"chosen_operation": {"name": "Hold Hill 101"}},
    }
    logs = [{"src": "G8", "turn": 2, "phase": "objectives", "message": "Hill 101 remains held."}]

    snapshot = build_view_snapshot(
        scenario_id="contract_demo",
        scenario_name="Contract Demo",
        authored_scenario=authored,
        engine_state=engine_state,
        engine_logs=logs,
    )

    assert snapshot["contract"] == {
        "id": "view.snapshot",
        "version": 1,
        "source": "backend_read_model",
    }
    assert snapshot["operation"]["id"] == "contract_demo"
    assert snapshot["scenario"]["name"] == "Contract Demo"
    assert snapshot["time"]["day"] == 2
    assert snapshot["time"]["turn"] == 2
    assert snapshot["time"]["current_hours"] == 24
    assert snapshot["weather"] == {"condition": "Rain"}
    assert snapshot["campaign"]["status"] == "active"
    assert snapshot["campaign"]["score_by_side"] == {"ALLIED": 80, "AXIS": 0}
    assert snapshot["score"]["score_by_side"] == {"ALLIED": 80, "AXIS": 0}
    assert snapshot["objective_truth"]["ALLIED:HILL"]["status"] == "held"
    assert snapshot["objective_state"] == {"ALLIED:HILL": True}
    assert snapshot["objectives"][0]["state"] == "held_allied"
    assert snapshot["objectives"][0]["truth_state"] == "held"
    assert snapshot["objectives"][0]["pressure_state"] == "degraded"
    assert snapshot["pressure"]["semantics"] == "supply_aware_objective_pressure_v1"
    assert snapshot["pressure"]["objective_pressure"]["affects_scoring"] is False
    assert snapshot["pressure"]["by_objective"]["ALLIED:HILL"]["pressure_score"] == 50.0
    assert snapshot["ai"]["enabled"] is True
    assert snapshot["ai"]["last_intent"] == "Hold Hill 101"
    assert snapshot["reports"]["pending_count"] is None
    assert snapshot["reports"]["recent"][0]["title"] == "G8 objectives"
    assert snapshot["read_first"]["scenario"] == "Contract Demo"
    assert snapshot["read_first"]["key_objective"] == "Hill 101"


def test_bridge_view_snapshot_exposes_authoritative_contract_in_current_envelope() -> None:
    bridge.reset_runtime()

    async def run(packet):
        return await bridge.dispatch_request(packet)

    asyncio.run(
        run({"id": "req-load", "proto": "1.0", "cmd": "load_scenario", "args": {"name": "inchon_mvp.json"}})
    )
    asyncio.run(run({"id": "req-start", "proto": "1.0", "cmd": "start_game", "args": {}}))
    response = asyncio.run(run({"id": "req-snapshot", "proto": "1.0", "cmd": "view.snapshot", "args": {}}))

    assert response["status"] == "ok"
    snapshot = response["data"]
    assert snapshot["contract"]["id"] == "view.snapshot"
    assert snapshot["contract"]["version"] == 1
    assert snapshot["objective_truth"]
    assert snapshot["objective_state"]
    assert snapshot["pressure"]["objective_pressure"]["semantics"] == "supply_aware_objective_pressure_v1"
    assert snapshot["campaign"]["score_by_side"] == {"ALLIED": 0, "AXIS": 0}
    assert "recent" in snapshot["reports"]
    assert snapshot["read_first"]["scenario"] == "Inchon Demo Vertical Slice"
