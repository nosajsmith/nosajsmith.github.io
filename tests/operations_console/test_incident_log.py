from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.operations_console.incident_log import detect_anomalies, load_anomaly_rules, log_incident_bundle
from tools.operations_console.runner_utils import make_result


def test_load_anomaly_rules_reads_repo_file() -> None:
    catalog = load_anomaly_rules()

    assert len(catalog.rules) >= 1
    assert any(rule.rule_id == "ANOM-001" for rule in catalog.rules)


def test_detect_anomalies_flags_empty_scenario_roster_warn() -> None:
    result = make_result(
        name="Refresh Scenarios",
        status="warn",
        summary="Scenario refresh completed, but the live roster is empty.",
        details=["refreshed 0 scenarios"],
    )

    matches = detect_anomalies(result)

    assert [match.rule_id for match in matches] == ["ANOM-001"]


def test_detect_anomalies_flags_missing_expected_artifact() -> None:
    result = make_result(
        name="ORL / UI Build Check",
        status="fail",
        summary="UI build check failed.",
        errors=["Build command exited with code 2."],
        artifact_paths=[],
    )

    matches = detect_anomalies(result)

    assert [match.rule_id for match in matches] == ["ANOM-003"]


def test_detect_anomalies_flags_empty_campaign_explain_output() -> None:
    result = make_result(
        name="ORL / Campaign Explain",
        status="fail",
        summary="Campaign explain failed.",
        errors=["Scenario payload missing for campaign explain."],
        details=["CAMPAIGN EXPLAIN ERROR: Scenario payload missing for campaign explain."],
    )

    matches = detect_anomalies(result)

    assert [match.rule_id for match in matches] == ["ANOM-004"]


def test_log_incident_bundle_writes_manifest_and_run_report(tmp_path, monkeypatch) -> None:
    def fake_run(args, cwd=None, capture_output=None, text=None, check=None):
        if args[1:] == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="main\n", stderr="")
        if args[1:] == ["rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="abc123\n", stderr="")
        if args[1:] == ["status", "--porcelain"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=" M tools/operations_console/app.py\n", stderr="")
        raise AssertionError(f"Unexpected git command: {args}")

    monkeypatch.setattr("tools.operations_console.incident_log.subprocess.run", fake_run)

    result = make_result(
        name="ORL / UI Build Check",
        status="fail",
        summary="UI build check failed.",
        scenario_name="inchon_mvp",
        errors=["Build command exited with code 2."],
        details=["package.json found", "build failed"],
    )

    incident = log_incident_bundle(result, incidents_dir=tmp_path)

    assert incident.logged is True
    assert incident.bundle_dir
    assert incident.incident_json_path
    assert incident.run_report_json_path

    manifest = json.loads(Path(incident.incident_json_path).read_text(encoding="utf-8"))
    report = json.loads(Path(incident.run_report_json_path).read_text(encoding="utf-8"))

    assert manifest["action_name"] == "ORL / UI Build Check"
    assert manifest["scenario_name"] == "inchon_mvp"
    assert manifest["git"]["branch"] == "main"
    assert manifest["git"]["commit"] == "abc123"
    assert manifest["git"]["worktree_status"] == "dirty"
    assert manifest["anomaly_matches"][0]["id"] == "ANOM-003"
    assert report["name"] == "ORL / UI Build Check"


def test_log_incident_bundle_copies_existing_artifacts_into_bundle(tmp_path, monkeypatch) -> None:
    def fake_run(args, cwd=None, capture_output=None, text=None, check=None):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("tools.operations_console.incident_log.subprocess.run", fake_run)
    artifact_path = tmp_path / "dist" / "index.html"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("<html></html>\n", encoding="utf-8")

    result = make_result(
        name="ORL / UI Build Check",
        status="fail",
        summary="UI build check failed.",
        artifact_paths=[str(artifact_path)],
        errors=["Build command exited with code 2."],
    )

    incident = log_incident_bundle(result, incidents_dir=tmp_path / "incidents")

    assert incident.logged is True
    assert len(incident.copied_artifact_paths) == 1
    copied_path = Path(incident.copied_artifact_paths[0])
    assert copied_path.exists()
    assert copied_path.read_text(encoding="utf-8") == "<html></html>\n"

    manifest = json.loads(Path(incident.incident_json_path).read_text(encoding="utf-8"))
    assert manifest["copied_artifact_paths"] == incident.copied_artifact_paths


def test_warn_without_anomaly_does_not_log_incident(tmp_path) -> None:
    result = make_result(
        name="Utilities / Coming Soon",
        status="warn",
        summary="Utilities is not wired into the console yet.",
    )

    incident = log_incident_bundle(result, incidents_dir=tmp_path)

    assert incident.logged is False
    assert incident.anomaly_matches == []
    assert list(tmp_path.iterdir()) == []
