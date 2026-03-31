from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from engine.testing_api import EngineTestingAPI
from tools.orl.readiness import Round1Manifest, Round1Scenario, Round1Variant


def test_list_scenarios_returns_metrics(monkeypatch) -> None:
    monkeypatch.setattr("engine.testing_api.store_list_scenarios", lambda: ["inchon_mvp.json", "mini_gc_1942.json"])

    api = EngineTestingAPI(repo_root=Path("/tmp/mwe"))
    result = api.list_scenarios()

    assert result.ok is True
    assert result.data["scenarios"] == ["inchon_mvp.json", "mini_gc_1942.json"]
    assert result.data["bridge_scenarios"] == ["inchon_mvp.json", "mini_gc_1942.json"]
    assert result.data["engine_scenarios"] == []
    assert result.metrics["scenario_count"] == 2
    assert result.adapter_method == "list_scenarios"


def test_load_scenario_reports_bridge_only_content_as_not_engine_loadable(monkeypatch) -> None:
    monkeypatch.setattr("engine.testing_api.store_list_scenarios", lambda: ["bridgehead.json"])

    api = EngineTestingAPI(repo_root=Path("/tmp/mwe"))
    result = api.load_scenario("bridgehead")

    assert result.ok is False
    assert result.adapter_method == "load_scenario"
    assert "not engine-loadable" in result.error


def test_load_scenario_can_resolve_engine_ready_server_scenario_outside_bridge_roster(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("engine.testing_api.store_list_scenarios", lambda: [])
    scenario_dir = tmp_path / "server" / "scenarios"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "gc_1942_historical.json").write_text(
        """
        {
          "id": "gc_1942_historical",
          "name": "Guadalcanal 1942 (Historical Skeleton)",
          "map": {"tiles": {"LUNGA": {"name": "Lunga", "terrain": "PLAINS"}}},
          "units": [{"id": "US-1MAR", "name": "1st Marines", "side": "ALLIED", "unit_type": "INFANTRY", "location_id": "LUNGA"}],
          "objectives": [{"location_id": "LUNGA", "side": "ALLIED", "value": 50}]
        }
        """,
        encoding="utf-8",
    )

    class FakeEngineAPI:
        def load_scenario(self, scenario_id):
            assert scenario_id == "gc_1942_historical"
            return {"id": scenario_id, "name": "Guadalcanal 1942 (Historical Skeleton)", "objectives": [{"location_id": "LUNGA"}]}

        def start_game(self):
            return {"units": [{"id": "US-1MAR"}], "game": {"scenario": "Guadalcanal 1942 (Historical Skeleton)"}}

    monkeypatch.setattr("engine.testing_api.EngineAPI", FakeEngineAPI)

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.load_scenario("gc_1942_historical")

    assert result.ok is True
    assert result.data["scenario_id"] == "gc_1942_historical"
    assert result.data["scenario_name"] == "gc_1942_historical.json"


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

    def fake_compare(path_a, path_b, output_path=None):
        calls.append(("compare", f"{path_a}|{path_b}|{output_path}"))
        from engine.testing_api import TestingApiResult

        if output_path is not None:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text("{}", encoding="utf-8")

        return TestingApiResult(
            ok=True,
            data={"compare_output_path": str(output_path or "")},
            artifacts=[str(path_a), str(path_b), str(output_path)] if output_path is not None else [str(path_a), str(path_b)],
            logs=["compare ok"],
            adapter_method="compare_replay",
        )

    monkeypatch.setattr(api, "export_replay", fake_export)
    monkeypatch.setattr(api, "compare_replay", fake_compare)

    result = api.replay_validation("inchon_mvp")

    assert result.ok is True
    assert result.adapter_method == "replay_validation"
    assert len(result.artifacts) == 3
    assert [call[0] for call in calls] == ["export", "export", "compare"]


def test_demo_checklist_uses_default_scenario_when_blank(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "engine.testing_api.load_demo_checklist",
        lambda _path: type(
            "Checklist",
            (),
            {
                "default_scenario": "inchon_mvp",
                "checklist": [type("Item", (), {"item_id": "smoke_suite", "label": "Smoke Suite", "required": True, "notes": "smoke"})()],
                "inspect_artifacts": ["artifacts/operations_console/*-orl-demo-readiness.json"],
                "bug_reports_to": "attach report",
                "expected_outcomes": {"inchon_mvp": ["demo outcome"]},
                "source_path": str(tmp_path / "tools" / "orl" / "demo_checklist.yaml"),
            },
        )(),
    )
    monkeypatch.setattr(
        "engine.testing_api.write_orl_artifact",
        lambda name, payload, repo_root_path=None: tmp_path / f"{name}.json",
    )

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.demo_checklist()

    assert result.ok is True
    assert result.adapter_method == "demo_checklist"
    assert result.data["selected_scenario"] == "inchon_mvp"
    assert result.data["checks"][0]["check_id"] == "checklist.smoke_suite"
    assert result.artifacts == [str(tmp_path / "demo-checklist.json")]


def test_deterministic_demo_runner_aggregates_structured_checks(monkeypatch, tmp_path) -> None:
    checklist = type(
        "Checklist",
        (),
        {
            "default_scenario": "inchon_mvp",
            "expected_outcomes": {"inchon_mvp": ["replay remains deterministic"]},
            "bug_reports_to": "attach demo report",
        },
    )()
    monkeypatch.setattr("engine.testing_api.load_demo_checklist", lambda _path: checklist)
    monkeypatch.setattr(
        "engine.testing_api.write_orl_artifact",
        lambda name, payload, repo_root_path=None: tmp_path / f"{name}.json",
    )

    def fake_result(method: str, *, artifacts: list[str] | None = None):
        from engine.testing_api import TestingApiResult

        return TestingApiResult(
            ok=True,
            data={"scenario_name": "inchon_mvp"},
            artifacts=list(artifacts or []),
            logs=[f"{method} ok"],
            adapter_method=method,
        )

    monkeypatch.setattr(EngineTestingAPI, "campaign_status", lambda self, scenario_name="": fake_result("campaign_status"))
    monkeypatch.setattr(EngineTestingAPI, "campaign_explain", lambda self, scenario_name="": fake_result("campaign_explain"))
    monkeypatch.setattr(EngineTestingAPI, "snapshot_smoke", lambda self, scenario_name="": fake_result("snapshot_smoke", artifacts=["/tmp/snapshot.json"]))
    monkeypatch.setattr(EngineTestingAPI, "replay_validation", lambda self, scenario_name="": fake_result("replay_validation", artifacts=["/tmp/replay.json", "/tmp/compare.json"]))

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.deterministic_demo_runner()

    assert result.ok is True
    assert result.adapter_method == "deterministic_demo_runner"
    assert result.metrics["check_count"] == 4
    assert [check["check_id"] for check in result.data["checks"]] == [
        "demo.campaign_status",
        "demo.campaign_explain",
        "demo.snapshot_smoke",
        "demo.replay_compare",
    ]
    assert "/tmp/snapshot.json" in result.artifacts
    assert "/tmp/compare.json" in result.artifacts


def test_latest_artifacts_returns_warn_shape_when_shelf_is_incomplete(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "engine.testing_api.latest_demo_artifact_shelf",
        lambda repo_root_path=None: {
            "demo_report": {"label": "Latest Demo Report", "path": "", "exists": False, "modified_at": "", "size_bytes": 0},
            "replay": {"label": "Latest Replay", "path": "/tmp/replay.json", "exists": True, "modified_at": "", "size_bytes": 2},
        },
    )
    monkeypatch.setattr(
        "engine.testing_api.write_orl_artifact",
        lambda name, payload, repo_root_path=None: tmp_path / f"{name}.json",
    )

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.latest_artifacts()

    assert result.ok is False
    assert result.error == ""
    assert result.adapter_method == "latest_artifacts"
    assert result.data["checks"][0]["status"] in {"pass", "warn"}
    assert str(tmp_path / "latest-demo-artifacts.json") in result.artifacts


def test_demo_artifact_validation_surfaces_failures(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "engine.testing_api.validate_demo_artifact_shelf",
        lambda repo_root_path=None: {
            "ok": False,
            "checks": [
                {
                    "check_id": "artifact.demo_report",
                    "label": "Latest Demo Report",
                    "blocker_class": "demo.artifact_output",
                    "status": "fail",
                    "summary": "Latest Demo Report is missing.",
                    "artifacts": [],
                    "logs": ["artifact missing"],
                }
            ],
            "missing": ["demo_report"],
            "shelf": {"demo_report": {"path": "", "exists": False}},
            "logs": ["demo_report: FAIL <missing>"],
            "artifact_path": str(tmp_path / "demo-artifact-shelf.json"),
            "blocker_class": "demo.artifact_output",
        },
    )

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.demo_artifact_validation()

    assert result.ok is False
    assert result.adapter_method == "demo_artifact_validation"
    assert result.error == "Demo artifact validation failed."
    assert result.metrics["missing_count"] == 1
    assert result.data["checks"][0]["check_id"] == "artifact.demo_report"


def test_pitch_support_bundle_wraps_export_report(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "tools.orl.pitch_support.export_pitch_support_bundle",
        lambda scenario_name="", repo_root_path=None: {
            "ok": True,
            "checks": [
                {
                    "check_id": "latest-orl-demo-readiness-report",
                    "label": "Latest ORL Demo Readiness Report",
                    "blocker_class": "support.pitch_support_bundle",
                    "status": "pass",
                    "summary": "Latest ORL Demo Readiness Report copied into the bundle.",
                    "artifacts": ["/tmp/pitch-support/reports/demo.json"],
                    "logs": ["report copied"],
                }
            ],
            "artifact_paths": ["/tmp/pitch-support/bundle_manifest.json"],
            "bundle_dir": "/tmp/pitch-support",
            "selected_scenario": scenario_name or "inchon_mvp",
            "logs": ["bundle_dir: /tmp/pitch-support"],
        },
    )

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.pitch_support_bundle("inchon_mvp")

    assert result.ok is True
    assert result.adapter_method == "pitch_support_bundle"
    assert result.data["bundle_dir"] == "/tmp/pitch-support"
    assert result.data["checks"][0]["check_id"] == "latest-orl-demo-readiness-report"
    assert result.artifacts == ["/tmp/pitch-support/bundle_manifest.json"]


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


def test_round1_gate_aggregates_structured_checks(monkeypatch, tmp_path) -> None:
    manifest = Round1Manifest(
        primary_scenarios=[Round1Scenario(scenario_id="inchon_mvp", label="Inchon")],
        variants=[
            Round1Variant(variant_id="base", label="Base"),
            Round1Variant(variant_id="aggressive", label="Aggressive"),
            Round1Variant(variant_id="cautious", label="Cautious"),
        ],
        run_tests=["pytest -q tests/engine/test_round1_support.py"],
        inspect_artifacts=["artifacts/orl/*"],
        bug_reports_to="attach artifacts/orl/*.json",
        source_path=str(tmp_path / "tools" / "orl" / "round1_manifest.yaml"),
    )
    monkeypatch.setattr("engine.testing_api.load_round1_manifest", lambda _path: manifest)
    monkeypatch.setattr(
        "engine.testing_api.write_orl_artifact",
        lambda name, payload, repo_root_path=None: tmp_path / f"{name}.json",
    )
    monkeypatch.setattr(
        EngineTestingAPI,
        "_run_pytest_check",
        lambda self, **kwargs: {
            "check_id": kwargs["check_id"],
            "label": kwargs["label"],
            "blocker_class": kwargs["blocker_class"],
            "status": "pass",
            "summary": f"{kwargs['label']} passed.",
            "artifacts": [],
            "logs": [],
            "executed_command": ["pytest", "-q"],
        },
    )
    pass_result = lambda method: type("Result", (), {
        "ok": True,
        "data": {},
        "error": "",
        "artifacts": [],
        "metrics": {},
        "logs": [f"{method} passed"],
        "adapter_method": method,
        "executed_command": [],
        "return_code": 0,
    })()
    monkeypatch.setattr(EngineTestingAPI, "snapshot_smoke", lambda self, scenario_name="": pass_result("snapshot_smoke"))
    monkeypatch.setattr(EngineTestingAPI, "replay_validation", lambda self, scenario_name="": pass_result("replay_validation"))
    monkeypatch.setattr(EngineTestingAPI, "scenario_validator", lambda self: pass_result("scenario_validator"))
    monkeypatch.setattr(EngineTestingAPI, "scenario_matrix", lambda self: pass_result("scenario_matrix"))
    monkeypatch.setattr(EngineTestingAPI, "explainability_smoke", lambda self: pass_result("explainability_smoke"))
    monkeypatch.setattr(EngineTestingAPI, "run_all_green", lambda self: pass_result("run_all_green"))
    monkeypatch.setattr(
        "engine.testing_api.check_round1_documentation_support",
        lambda repo_root_path=None, manifest=None: {
            "ok": True,
            "status": "pass",
            "summary": "docs ok",
            "artifact_path": str(tmp_path / "docs.json"),
            "logs": ["docs ok"],
            "blocker_class": "support.documentation",
        },
    )

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.round1_gate()

    assert result.ok is True
    assert result.adapter_method == "round1_gate"
    assert result.metrics["check_count"] >= 5
    assert "tooling.all_green" in result.data["blocker_classes"]
    assert result.data["bug_reports_to"] == "attach artifacts/orl/*.json"


def test_campaign_status_returns_concise_structured_truth(monkeypatch, tmp_path) -> None:
    class FakeEngineAPI:
        def load_scenario(self, scenario_id):
            assert scenario_id == "inchon_mvp"
            return {"id": "inchon_mvp", "name": "Inchon Demo Vertical Slice"}

        def start_game(self):
            return {
                "game": {
                    "scenario": "Inchon Demo Vertical Slice",
                    "vp": {"ALLIED": 10, "AXIS": 3},
                    "ai": {"enabled": False},
                },
                "units": [{"id": "US-1MAR"}, {"id": "US-7INF"}],
            }

    monkeypatch.setattr("engine.testing_api.store_list_scenarios", lambda: ["inchon_mvp.json"])
    monkeypatch.setattr(
        "engine.testing_api.read_scenario",
        lambda _name: {
            "id": "inchon_mvp",
            "name": "Inchon Demo Vertical Slice",
            "description": "Curated Inchon demo.",
            "grease_board": {
                "turn": "TURN 1",
                "objective": "SEOUL",
                "front_status": "INCHON BEACHHEAD SECURE",
                "supply_status": "PORT OPEN / AXIS ADVANCE",
                "main_effort": "INCHON / SEOUL AXIS",
                "alerts": ["Kimpo corridor remains contested."],
            },
            "objectives": [{"name": "Seoul"}, {"name": "Kimpo Airfield"}],
        },
    )
    monkeypatch.setattr("engine.testing_api.EngineAPI", FakeEngineAPI)

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.campaign_status("inchon_mvp")

    assert result.ok is True
    assert result.adapter_method == "campaign_status"
    assert result.data["objective"] == "SEOUL"
    assert result.data["front_status"] == "INCHON BEACHHEAD SECURE"
    assert result.metrics["unit_count"] == 2
    assert any("CAMPAIGN STATUS:" in line for line in result.logs)
    assert any("CAMPAIGN STATUS DETAIL:" in line for line in result.logs)


def test_campaign_explain_returns_staff_notes_orders_and_alerts(monkeypatch, tmp_path) -> None:
    class FakeEngineAPI:
        def load_scenario(self, scenario_id):
            assert scenario_id == "inchon_mvp"
            return {"id": "inchon_mvp", "name": "Inchon Demo Vertical Slice"}

        def start_game(self):
            return {
                "game": {
                    "scenario": "Inchon Demo Vertical Slice",
                    "vp": {"ALLIED": 10, "AXIS": 3},
                    "ai": {"enabled": False},
                },
                "units": [{"id": "US-1MAR"}, {"id": "US-7INF"}],
            }

    monkeypatch.setattr("engine.testing_api.store_list_scenarios", lambda: ["inchon_mvp.json"])
    monkeypatch.setattr(
        "engine.testing_api.read_scenario",
        lambda _name: {
            "id": "inchon_mvp",
            "name": "Inchon Demo Vertical Slice",
            "description": "Curated Inchon demo.",
            "grease_board": {
                "staff_notes": "Exploit the landing before the ring stabilizes.",
                "orders": [
                    "1st Marines push east from Inchon toward Kimpo.",
                    "7th Infantry secures the beachhead.",
                    "Reserve follows.",
                ],
                "alerts": [
                    "Kimpo corridor remains contested.",
                    "NKPA reserves are forming south of Seoul.",
                ],
            },
            "objectives": [{"name": "Seoul"}, {"name": "Kimpo Airfield"}],
        },
    )
    monkeypatch.setattr("engine.testing_api.EngineAPI", FakeEngineAPI)

    api = EngineTestingAPI(repo_root=tmp_path)
    result = api.campaign_explain("inchon_mvp")

    assert result.ok is True
    assert result.adapter_method == "campaign_explain"
    assert result.data["staff_notes"] == "Exploit the landing before the ring stabilizes."
    assert result.metrics["order_count"] == 3
    assert any("CAMPAIGN EXPLAIN:" in line for line in result.logs)
    assert any("CAMPAIGN NOTES:" in line for line in result.logs)
    assert any("CAMPAIGN ORDERS:" in line for line in result.logs)
