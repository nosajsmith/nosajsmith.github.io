from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tools.orl import demo_readiness as demo_readiness_cli
from tools.orl.readiness import (
    check_round1_documentation_support,
    load_demo_checklist,
    load_round1_manifest,
    latest_demo_artifact_shelf,
    run_round1_scenario_matrix,
    validate_demo_artifact_shelf,
    validate_round1_scenarios,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_round1_manifest_exposes_primary_scenarios_and_variants() -> None:
    manifest = load_round1_manifest()

    assert [scenario.scenario_id for scenario in manifest.primary_scenarios] == [
        "inchon_mvp",
        "mini_gc_1942",
        "gc_1942_historical",
    ]
    assert [variant.variant_id for variant in manifest.variants] == ["base", "aggressive", "cautious"]


def test_demo_checklist_exposes_current_slice_guidance() -> None:
    checklist = load_demo_checklist()

    assert checklist.default_scenario == "inchon_mvp"
    assert [item.item_id for item in checklist.checklist] == [
        "smoke_suite",
        "ui_build_check",
        "deterministic_demo_runner",
        "artifact_output_validation",
        "report_review",
    ]
    assert checklist.inspect_artifacts
    assert "inchon_mvp" in checklist.expected_outcomes


def test_validate_round1_scenarios_passes_for_repo_primary_set() -> None:
    report = validate_round1_scenarios(repo_root_path=REPO_ROOT)

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert len(report["rows"]) == 3
    assert Path(report["artifact_path"]).exists()


def test_run_round1_scenario_matrix_produces_variant_rows() -> None:
    report = run_round1_scenario_matrix(repo_root_path=REPO_ROOT)

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert len(report["rows"]) == 6
    assert {row["variant_id"] for row in report["rows"]} == {"base", "aggressive", "cautious"}
    assert Path(report["artifact_path"]).exists()


def test_documentation_support_check_passes() -> None:
    report = check_round1_documentation_support(repo_root_path=REPO_ROOT)

    assert report["ok"] is True
    assert report["status"] == "pass"
    assert Path(report["artifact_path"]).exists()


def test_latest_demo_artifact_shelf_returns_newest_paths(tmp_path) -> None:
    operations_root = tmp_path / "artifacts" / "operations_console"
    (operations_root / "engine_adapter" / "replays").mkdir(parents=True)
    (operations_root / "engine_adapter" / "snapshots").mkdir(parents=True)
    (operations_root / "engine_adapter" / "compares").mkdir(parents=True)

    report_path = operations_root / "20260330010101-orl-demo-readiness.json"
    replay_path = operations_root / "engine_adapter" / "replays" / "20260330010101-inchon-a.json"
    snapshot_path = operations_root / "engine_adapter" / "snapshots" / "20260330010101-inchon.json"
    compare_path = operations_root / "engine_adapter" / "compares" / "20260330010101-inchon.json"
    for path in (report_path, replay_path, snapshot_path, compare_path):
        path.write_text("{}", encoding="utf-8")

    shelf = latest_demo_artifact_shelf(repo_root_path=tmp_path)

    assert shelf["demo_report"]["path"] == str(report_path)
    assert shelf["replay"]["path"] == str(replay_path)
    assert shelf["snapshot"]["path"] == str(snapshot_path)
    assert shelf["compare_output"]["path"] == str(compare_path)


def test_validate_demo_artifact_shelf_fails_when_required_slots_are_missing(tmp_path) -> None:
    report = validate_demo_artifact_shelf(repo_root_path=tmp_path)

    assert report["ok"] is False
    assert sorted(report["missing"]) == ["compare_output", "demo_report", "replay", "snapshot"]
    assert Path(report["artifact_path"]).exists()


def test_demo_readiness_cli_emits_json_payload(monkeypatch, capsys) -> None:
    class FakeAPI:
        def demo_checklist(self, scenario_name: str = ""):
            return SimpleNamespace(
                ok=True,
                adapter_method="demo_checklist",
                error="",
                artifacts=["/tmp/demo-checklist.json"],
                metrics={"checklist_count": 1},
                data={"selected_scenario": scenario_name or "inchon_mvp"},
                logs=["checklist ok"],
            )

    monkeypatch.setattr(demo_readiness_cli, "EngineTestingAPI", FakeAPI)

    exit_code = demo_readiness_cli.main(["checklist", "inchon_mvp"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"adapter_method": "demo_checklist"' in output
    assert '"selected_scenario": "inchon_mvp"' in output
