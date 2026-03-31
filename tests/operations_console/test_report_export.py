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
    assert payload["key_logs"] == []
    assert payload["adapter_method"] == "suite"
    assert payload["executed_command"] == ["pytest", "-q", "tests/test_inchon_scenario_stub.py"]
    assert payload["return_code"] == 0
    assert payload["known_issue_matches"][0]["id"] == "KI-401"
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
        details=["line 1", "line 2"],
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
    assert payload["scenario_contract_evaluation"]["matched"] is True
    assert payload["scenario_contract_evaluation"]["contract_scenario_name"] == "inchon_mvp"
    assert payload["key_logs"] == ["warn detail", "line 1", "line 2"]
    assert "Status: WARN" in text
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
    assert "Key Logs:" in text
    assert "KI-402: Waived replay regression [waived] -> WARN" in text
