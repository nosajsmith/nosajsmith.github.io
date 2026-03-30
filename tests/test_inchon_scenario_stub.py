from __future__ import annotations

from pathlib import Path

from engine.engine_api import EngineAPI
from server.scenario_store import list_scenarios, read_scenario


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_inchon_pitch_scenario_exists_in_bridge_and_engine_roots():
    assert (REPO_ROOT / "scenarios" / "inchon_mvp.json").exists()
    assert (REPO_ROOT / "server" / "scenarios" / "inchon_mvp.json").exists()
    assert (REPO_ROOT / "server" / "rules" / "scenarios" / "inchon_mvp.json").exists()


def test_inchon_pitch_scenario_is_available_in_live_roster():
    scenarios = list_scenarios()

    assert "inchon_mvp.json" in scenarios

    scenario = read_scenario("inchon_mvp.json")

    assert scenario is not None
    assert scenario["id"] == "inchon_mvp"
    assert scenario["name"] == "Inchon Demo Vertical Slice"
    assert scenario["map_package"] == "korea_peninsula_coarse_v1"
    assert scenario["map_presentation"]["hex_scale_km"] == 5
    assert scenario["map_presentation"]["playable_scale_locked"] is True
    assert scenario["map_presentation"]["world_bounds"]["min_x"] == 14.2
    assert any(objective["name"] == "Seoul" for objective in scenario["objectives"])
    assert any(objective.get("map_label") == "SEOUL" for objective in scenario["objectives"])
    assert any(objective["name"] == "Yongdungpo Crossings" for objective in scenario["objectives"])
    assert any(port["name"] == "Inchon Harbor" for port in scenario["ports"])
    assert any(unit.get("map_label") == "1ST MAR DIV" for unit in scenario["units"])
    assert any(feature["label"] == "Seoul Axis" for feature in scenario["named_features"])
    assert any(feature.get("map_label") == "HAN ESTUARY" for feature in scenario["named_features"])
    assert any(feature["label"] == "Seoul Defensive Belt" for feature in scenario["named_features"])


def test_engine_can_load_and_process_the_inchon_pitch_scenario():
    api = EngineAPI(ai_enabled=True, ai_side="AXIS")
    meta = api.load_scenario("inchon_mvp")

    assert meta["id"] == "inchon_mvp"
    assert meta["name"] == "Inchon Demo Vertical Slice"
    assert any(objective["name"] == "Seoul" for objective in meta["objectives"])

    state = api.start_game()

    assert state["game"]["scenario"] == "Inchon Demo Vertical Slice"
    assert len(state["units"]) >= 5
    assert all("Guadalcanal" not in unit["name"] for unit in state["units"])

    next_state = api.process_turn()
    logs = api.get_logs()

    assert next_state["game"]["scenario"] == "Inchon Demo Vertical Slice"
    assert next_state["game"]["ai"]["enabled"] is True
    assert next_state["bai_report"]
    assert any("inchon_mvp" in entry["message"] for entry in logs if entry["phase"] == "load")
