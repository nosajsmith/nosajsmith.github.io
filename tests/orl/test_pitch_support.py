from __future__ import annotations

import json
from types import SimpleNamespace

from tools.orl import pitch_support


def test_export_pitch_support_bundle_copies_reports_and_generates_summaries(tmp_path, monkeypatch) -> None:
    operations_root = tmp_path / "artifacts" / "operations_console"
    operations_root.mkdir(parents=True)
    (operations_root / "20260330010101-orl-demo-readiness.json").write_text("{}", encoding="utf-8")
    (operations_root / "20260330010101-orl-demo-readiness.txt").write_text("demo", encoding="utf-8")
    (operations_root / "20260330010202-orl-core-validation-suite.json").write_text("{}", encoding="utf-8")
    (operations_root / "20260330010202-orl-core-validation-suite.txt").write_text("core", encoding="utf-8")
    for rel_path in (
        "artifacts/operations_console/engine_adapter/replays/demo.json",
        "artifacts/operations_console/engine_adapter/snapshots/demo.json",
        "artifacts/operations_console/engine_adapter/compares/demo.json",
    ):
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    docs_root = tmp_path / "docs" / "pitch_support"
    docs_root.mkdir(parents=True)
    (docs_root / "README.md").write_text("# Pitch Support Runbook\n", encoding="utf-8")
    (docs_root / "architecture_support_note.md").write_text("# Architecture\n", encoding="utf-8")

    known_issues_path = tmp_path / "tools" / "operations_console" / "known_issues.yaml"
    known_issues_path.parent.mkdir(parents=True, exist_ok=True)
    known_issues_path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-001",
                        "title": "Example",
                        "severity": "medium",
                        "category": "ORL",
                        "affects": ["ORL / UI Build Check"],
                        "scenarios": [],
                        "status": "known",
                        "expected_status_override": "",
                        "symptom_match": ["build failed"],
                        "notes": "example note",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        pitch_support,
        "load_demo_checklist",
        lambda _path: SimpleNamespace(
            default_scenario="inchon_mvp",
            expected_outcomes={"inchon_mvp": ["demo outcome"]},
        ),
    )
    monkeypatch.setattr(
        pitch_support,
        "load_round1_manifest",
        lambda _path: SimpleNamespace(
            primary_scenarios=[SimpleNamespace(scenario_id="inchon_mvp", label="Inchon", notes="demo", expected_outcomes=["manifest outcome"])],
            expected_outcomes={"inchon_mvp": ["round1 outcome"]},
        ),
    )

    class FakeAPI:
        def __init__(self, repo_root=None):
            self.repo_root = repo_root

        def _resolve_scenario_entry(self, scenario_name):
            return {"scenario_id": scenario_name, "bridge_listed": True, "engine_loadable": True, "payload_paths": ["/tmp/scenario.json"]}

        def _read_scenario_payload(self, entry):
            return {
                "id": "inchon_mvp",
                "name": "Inchon Demo Vertical Slice",
                "description": "demo description",
                "units": [{"id": "u1"}],
                "objectives": [{"name": "Seoul"}],
                "grease_board": {
                    "turn": "TURN 1",
                    "objective": "SEOUL",
                    "front_status": "SECURE",
                    "supply_status": "OPEN",
                    "main_effort": "AXIS",
                    "staff_notes": "notes",
                    "alerts": ["alert"],
                    "orders": ["order"],
                },
            }

        def campaign_status(self, scenario_name):
            return SimpleNamespace(
                data={
                    "scenario_id": "inchon_mvp",
                    "display_name": "Inchon Demo Vertical Slice",
                    "unit_count": 6,
                    "objective_count": 5,
                    "turn": "TURN 1",
                    "objective": "SEOUL",
                    "front_status": "SECURE",
                    "supply_status": "OPEN",
                    "main_effort": "AXIS",
                }
            )

        def campaign_explain(self, scenario_name):
            return SimpleNamespace(
                data={
                    "description": "demo description",
                    "staff_notes": "notes",
                    "objectives": ["Seoul"],
                    "alerts": ["alert"],
                    "orders": ["order"],
                }
            )

    monkeypatch.setattr(pitch_support, "EngineTestingAPI", FakeAPI)

    report = pitch_support.export_pitch_support_bundle(repo_root_path=tmp_path)

    assert report["ok"] is True
    assert (tmp_path / "artifacts" / "pitch_support" / "latest.json").exists()
    bundle_dir = tmp_path / "artifacts" / "pitch_support"
    bundle_dirs = [path for path in bundle_dir.iterdir() if path.is_dir()]
    assert bundle_dirs
    exported = bundle_dirs[0]
    assert (exported / "reports" / "20260330010101-orl-demo-readiness.json").exists()
    assert (exported / "reports" / "20260330010202-orl-core-validation-suite.json").exists()
    assert (exported / "known_issues_summary.md").exists()
    assert (exported / "scenario_fact_sheet.md").exists()
    assert (exported / "expected_outcomes_summary.md").exists()
    assert (exported / "artifact_directory_summary.md").exists()
    assert (exported / "docs" / "README.md").exists()
    assert (exported / "docs" / "architecture_support_note.md").exists()


def test_pitch_support_cli_returns_error_for_unsupported_command(capsys) -> None:
    exit_code = pitch_support.main(["unknown"])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert '"supported": [' in output


def test_latest_console_report_keeps_json_and_text_on_same_stem(tmp_path) -> None:
    operations_root = tmp_path / "artifacts" / "operations_console"
    operations_root.mkdir(parents=True)
    (operations_root / "20260330010101-orl-core-validation-suite.json").write_text("{}", encoding="utf-8")
    (operations_root / "20260330010101-orl-core-validation-suite.txt").write_text("old", encoding="utf-8")
    (operations_root / "20260330020202-orl-core-validation-suite.json").write_text("{}", encoding="utf-8")

    report = pitch_support._latest_console_report(tmp_path, "orl-core-validation-suite")

    assert report["json_path"].endswith("20260330020202-orl-core-validation-suite.json")
    assert report["text_path"] == ""
