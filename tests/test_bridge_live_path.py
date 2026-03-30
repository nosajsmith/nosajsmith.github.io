from __future__ import annotations

import asyncio

from server import mwe_bridge_p8_ws15 as bridge


def run(packet):
    return asyncio.run(bridge.dispatch_request(packet))


def test_bridge_roster_launch_and_snapshot_flow_for_inchon():
    bridge.reset_runtime()

    roster = run({"id": "req-roster", "proto": "1.0", "cmd": "list_scenarios", "args": {}})
    assert roster["status"] == "ok"
    assert "inchon_mvp.json" in roster["data"]["scenarios"]

    not_ready = run({"id": "req-snapshot-before", "proto": "1.0", "cmd": "view.snapshot", "args": {}})
    assert not_ready["status"] == "error"
    assert not_ready["error"]["code"] == "not_ready"

    loaded = run({"id": "req-load", "proto": "1.0", "cmd": "load_scenario", "args": {"name": "inchon_mvp.json"}})
    assert loaded["status"] == "ok"
    assert loaded["data"]["id"] == "inchon_mvp"

    started = run({"id": "req-start", "proto": "1.0", "cmd": "start_game", "args": {}})
    assert started["status"] == "ok"
    assert started["data"]["game"]["scenario"] == "Inchon Demo Vertical Slice"

    snapshot = run({"id": "req-snapshot-after", "proto": "1.0", "cmd": "view.snapshot", "args": {}})
    assert snapshot["status"] == "ok"
    data = snapshot["data"]

    assert data["scenario"]["id"] == "inchon_mvp"
    assert data["scenario"]["name"] == "Inchon Demo Vertical Slice"
    assert data["map_presentation"]["hex_scale_km"] == 5
    assert data["map_presentation"]["playable_scale_locked"] is True
    assert data["map_presentation"]["world_bounds"]["max_x"] == 51.2
    assert data["pressure"]["active"] is True
    assert data["pressure"]["summary"]
    assert "amphibious_landing" in data["pressure"]["reasons"]
    assert data["reports"]["pending_count"] is None
    assert any(point["label"] == "Yongdungpo Crossings" for point in data["map_presentation"]["focus_points"])
    assert any(objective["name"] == "Seoul" for objective in data["objectives"])
    assert any(objective["name"] == "Yongdungpo Crossings" for objective in data["objectives"])
    assert any(port["name"] == "Inchon Harbor" for port in data["ports"])
    assert any(feature["label"] == "Seoul Axis" for feature in data["named_features"])
    assert any(feature["label"] == "Seoul Defensive Belt" for feature in data["named_features"])
    assert any(unit["id"] == "US-1MAR" for unit in data["units"])
