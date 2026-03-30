from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from engine.testing_api import EngineTestingAPI


def test_list_scenarios_returns_metrics(monkeypatch) -> None:
    monkeypatch.setattr("engine.testing_api.store_list_scenarios", lambda: ["inchon_mvp.json", "mini_gc_1942.json"])

    api = EngineTestingAPI(repo_root=Path("/tmp/mwe"))
    result = api.list_scenarios()

    assert result.ok is True
    assert result.data["scenarios"] == ["inchon_mvp.json", "mini_gc_1942.json"]
    assert result.metrics["scenario_count"] == 2
    assert result.adapter_method == "list_scenarios"


def test_snapshot_smoke_roundtrip_uses_save_and_load(monkeypatch, tmp_path) -> None:
    class FakeUnits:
        def __init__(self):
            self._rows = [
                SimpleNamespace(
                    id="US-1MAR",
                    location_id="INCHON_PORT",
                    strength=100,
                    fatigue=5,
                    morale=70,
                    supply=80,
                    readiness=75,
                    hq_unit_id="X-CORPS",
                ),
                SimpleNamespace(
                    id="US-7INF",
                    location_id="KIMPO",
                    strength=90,
                    fatigue=8,
                    morale=68,
                    supply=78,
                    readiness=72,
                    hq_unit_id="X-CORPS",
                ),
            ]

        def get(self, unit_id):
            for row in self._rows:
                if row.id == unit_id:
                    return row
            return None

        def all_units(self):
            return list(self._rows)

    class FakeEngineAPI:
        def __init__(self):
            self.time = SimpleNamespace(day=1, phase="DAY")
            self.units = FakeUnits()
            self.meta = {"id": "inchon_mvp", "name": "Inchon Demo Vertical Slice"}
            self.game_map = object()

        def load_scenario(self, scenario_id):
            assert scenario_id == "inchon_mvp"
            return dict(self.meta)

        def start_game(self):
            return {"game": {"scenario": "Inchon Demo Vertical Slice"}, "units": [{"id": "US-1MAR"}, {"id": "US-7INF"}]}

        def process_turn(self):
            return {"game": {"scenario": "Inchon Demo Vertical Slice"}, "units": [{"id": "US-1MAR"}, {"id": "US-7INF"}]}

        def get_logs(self):
            return [{"src": "ENGINE", "turn": 1, "phase": "load", "message": "Loaded inchon_mvp"}]

    monkeypatch.setattr("engine.testing_api.store_list_scenarios", lambda: ["inchon_mvp.json"])
    monkeypatch.setattr("engine.testing_api.read_scenario", lambda name: {"id": "inchon_mvp", "name": "Inchon Demo Vertical Slice"})
    monkeypatch.setattr("engine.testing_api.EngineAPI", FakeEngineAPI)

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.snapshot_smoke("inchon_mvp")

    assert result.ok is True
    assert result.adapter_method == "snapshot_smoke"
    assert result.metrics["unit_count"] == 2
    assert result.artifacts
    assert Path(result.artifacts[0]).exists()


def test_replay_validation_aggregates_artifacts(monkeypatch, tmp_path) -> None:
    api = EngineTestingAPI(repo_root=tmp_path)
    calls: list[tuple[str, str]] = []

    def fake_export(path, scenario_name=""):
        calls.append(("export", str(path)))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("{}", encoding="utf-8")
        from engine.testing_api import TestingApiResult

        return TestingApiResult(
            ok=True,
            artifacts=[str(path)],
            logs=[f"exported {path}"],
            adapter_method="export_replay",
        )

    def fake_compare(path_a, path_b):
        calls.append(("compare", f"{path_a}|{path_b}"))
        from engine.testing_api import TestingApiResult

        return TestingApiResult(
            ok=True,
            artifacts=[str(path_a), str(path_b)],
            logs=["compare ok"],
            adapter_method="compare_replay",
        )

    monkeypatch.setattr(api, "export_replay", fake_export)
    monkeypatch.setattr(api, "compare_replay", fake_compare)

    result = api.replay_validation("inchon_mvp")

    assert result.ok is True
    assert result.adapter_method == "replay_validation"
    assert len(result.artifacts) == 2
    assert [call[0] for call in calls] == ["export", "export", "compare"]


def test_run_all_green_captures_command_and_return_code(monkeypatch, tmp_path) -> None:
    completed = subprocess.CompletedProcess(
        args=["pytest", "-q", "tests/test_inchon_scenario_stub.py"],
        returncode=0,
        stdout="2 passed\n",
        stderr="",
    )
    monkeypatch.setattr("engine.testing_api.subprocess.run", lambda *args, **kwargs: completed)

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.run_all_green()

    assert result.ok is True
    assert result.adapter_method == "run_all_green"
    assert result.executed_command[:2] == ["pytest", "-q"]
    assert result.return_code == 0
    assert any("stdout: 2 passed" in line for line in result.logs)
