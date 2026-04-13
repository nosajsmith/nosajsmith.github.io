from __future__ import annotations

import json

from tools.operations_console.models import ConsoleResult, KnownIssueMatch
from tools.operations_console.report_export import export_result_json, export_result_text, report_dict


def test_report_dict_includes_subresults_and_artifacts() -> None:
    result = ConsoleResult(
        name="ORL / Scenario Integrity",
        status="warn",
        original_status="fail",
        summary="ready",
        scenario_name="inchon_mvp",
        artifact_paths=["/tmp/dist/index.html"],
        adapter_method="suite",
        executed_command=["pytest", "-q", "tests/test_inchon_scenario_stub.py"],
        return_code=0,
        details=[
            "INCIDENT ANOMALIES: ANOM-003 | Missing expected artifact",
            "INCIDENT BUNDLE: /tmp/incidents/abc",
            "INCIDENT MANIFEST: /tmp/incidents/abc/incident.json",
            "INCIDENT RUN REPORT: /tmp/incidents/abc/run_report.json",
        ],
        known_issue_matches=[
            KnownIssueMatch(
                issue_id="KI-401",
                title="Known snapshot mismatch",
                severity="high",
                category="ORL",
                status="waived",
                expected_status_override="warn",
                notes="Temporary waiver.",
            )
        ],
        subresults=[
            ConsoleResult(
                name="ORL / Smoke Suite",
                status="pass",
                summary="smoke ok",
            )
        ],
    )

    payload = report_dict(result)

    assert payload["name"] == "ORL / Scenario Integrity"
    assert payload["scenario_name"] == "inchon_mvp"
    assert payload["original_status"] == "fail"
    assert payload["artifact_paths"] == ["/tmp/dist/index.html"]
    assert payload["key_logs"] == [
        "INCIDENT ANOMALIES: ANOM-003 | Missing expected artifact",
        "INCIDENT BUNDLE: /tmp/incidents/abc",
        "INCIDENT MANIFEST: /tmp/incidents/abc/incident.json",
        "INCIDENT RUN REPORT: /tmp/incidents/abc/run_report.json",
    ]
    assert payload["adapter_method"] == "suite"
    assert payload["executed_command"] == ["pytest", "-q", "tests/test_inchon_scenario_stub.py"]
    assert payload["return_code"] == 0
    assert payload["known_issue_matches"][0]["id"] == "KI-401"
    assert payload["known_issue_matches"][0]["severity"] == "high"
    assert payload["known_issue_matches"][0]["waived"] is True
    assert payload["known_issue_matches"][0]["downgrade_applied"] is True
    assert payload["known_issue_matches"][0]["downgraded_to"] == "warn"
    assert payload["known_issue_matches"][0]["scenario_name"] == "inchon_mvp"
    assert payload["known_issue_matches"][0]["result_name"] == "ORL / Scenario Integrity"
    assert payload["incident_metadata"]["logged"] is True
    assert payload["incident_metadata"]["bundle_dir"] == "/tmp/incidents/abc"
    assert payload["incident_metadata"]["anomaly_matches"][0]["id"] == "ANOM-003"
    assert payload["gui_action_matrix"]["id"] == "orl-scenario-integrity"
    assert payload["scenario_contract_evaluation"]["matched"] is True
    assert payload["scenario_contract_evaluation"]["contract_scenario_name"] == "inchon_mvp"
    assert payload["scenario_contract_evaluation"]["status"] == "pass"
    assert payload["subresults"][0]["name"] == "ORL / Smoke Suite"


def test_export_result_json_and_text_create_files(tmp_path) -> None:
    result = ConsoleResult(
        name="ORL / Demo Readiness",
        status="warn",
        original_status="fail",
        summary="one step warned",
        started_at="2026-03-30T10:00:00+00:00",
        finished_at="2026-03-30T10:00:05+00:00",
        scenario_name="inchon_mvp",
        details=[
            "line 1",
            "line 2",
            "INCIDENT ANOMALIES: ANOM-003 | Missing expected artifact",
            "INCIDENT BUNDLE: /tmp/incidents/demo",
            "INCIDENT MANIFEST: /tmp/incidents/demo/incident.json",
            "INCIDENT RUN REPORT: /tmp/incidents/demo/run_report.json",
        ],
        errors=["warn detail"],
        artifact_paths=["/tmp/dist/index.html"],
        adapter_method="run_all_green",
        executed_command=["pytest", "-q", "tests/test_inchon_scenario_stub.py"],
        return_code=1,
        known_issue_matches=[
            KnownIssueMatch(
                issue_id="KI-402",
                title="Waived replay regression",
                severity="medium",
                category="ORL",
                status="waived",
                expected_status_override="warn",
                notes="Pending deterministic fixture refresh.",
            )
        ],
        subresults=[
            ConsoleResult(
                name="ORL / Smoke Suite",
                status="pass",
                summary="smoke ok",
            )
        ],
    )

    json_path = export_result_json(result, tmp_path)
    text_path = export_result_text(result, tmp_path)

    assert json_path.exists()
    assert text_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    text = text_path.read_text(encoding="utf-8")

    assert payload["status"] == "warn"
    assert payload["original_status"] == "fail"
    assert payload["subresults"][0]["name"] == "ORL / Smoke Suite"
    assert payload["known_issue_matches"][0]["id"] == "KI-402"
    assert payload["incident_metadata"]["logged"] is True
    assert payload["incident_metadata"]["run_report_json_path"] == "/tmp/incidents/demo/run_report.json"
    assert payload["scenario_contract_evaluation"]["matched"] is True
    assert payload["scenario_contract_evaluation"]["contract_scenario_name"] == "inchon_mvp"
    assert payload["key_logs"] == [
        "warn detail",
        "line 1",
        "line 2",
        "INCIDENT ANOMALIES: ANOM-003 | Missing expected artifact",
        "INCIDENT BUNDLE: /tmp/incidents/demo",
        "INCIDENT MANIFEST: /tmp/incidents/demo/incident.json",
        "INCIDENT RUN REPORT: /tmp/incidents/demo/run_report.json",
    ]
    assert "Status: WARN" in text
    assert "Incident Logged: YES" in text
    assert "Incident Bundle: /tmp/incidents/demo" in text
    assert "Original Status: FAIL" in text
    assert "Scenario: inchon_mvp" in text
    assert "Scenario Contract: inchon_mvp" in text
    assert "Artifacts:" in text
    assert payload["adapter_method"] == "run_all_green"
    assert payload["executed_command"] == ["pytest", "-q", "tests/test_inchon_scenario_stub.py"]
    assert payload["return_code"] == 1
    assert "Adapter Method: run_all_green" in text
    assert "Executed Command: pytest -q tests/test_inchon_scenario_stub.py" in text
    assert "Return Code: 1" in text
    assert "Known Issues:" in text
    assert "Known Issue Scenario: inchon_mvp" in text
    assert "Incident Anomalies:" in text
    assert "Key Logs:" in text
    assert payload["known_issue_matches"][0]["waived"] is True
    assert payload["known_issue_matches"][0]["downgrade_applied"] is True
    assert payload["known_issue_matches"][0]["scenario_name"] == "inchon_mvp"
    assert "KI-402: Waived replay regression [severity=medium, status=waived] -> WARN (downgrade applied)" in text


def test_report_dict_promotes_nested_errors_into_key_logs() -> None:
    result = ConsoleResult(
        name="ORL / Demo Readiness",
        status="fail",
        summary="demo failed",
        details=["suite started"],
        subresults=[
            ConsoleResult(
                name="ORL / Demo Artifact Validation",
                status="fail",
                summary="artifact missing",
                errors=["missing expected screenshot"],
                details=["validation step failed"],
            )
        ],
    )

    payload = report_dict(result)

    assert payload["key_logs"] == [
        "suite started",
        "missing expected screenshot",
        "validation step failed",
    ]
