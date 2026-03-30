from __future__ import annotations

import json

from tools.operations_console.models import ConsoleResult
from tools.operations_console.report_export import export_result_json, export_result_text, report_dict


def test_report_dict_includes_subresults_and_artifacts() -> None:
    result = ConsoleResult(
        name="ORL / Demo Readiness",
        status="pass",
        summary="ready",
        scenario_name="inchon_mvp",
        artifact_paths=["/tmp/dist/index.html"],
        adapter_method="suite",
        executed_command=["pytest", "-q", "tests/test_inchon_scenario_stub.py"],
        return_code=0,
        subresults=[
            ConsoleResult(
                name="ORL / Smoke Suite",
                status="pass",
                summary="smoke ok",
            )
        ],
    )

    payload = report_dict(result)

    assert payload["name"] == "ORL / Demo Readiness"
    assert payload["scenario_name"] == "inchon_mvp"
    assert payload["artifact_paths"] == ["/tmp/dist/index.html"]
    assert payload["adapter_method"] == "suite"
    assert payload["executed_command"] == ["pytest", "-q", "tests/test_inchon_scenario_stub.py"]
    assert payload["return_code"] == 0
    assert payload["subresults"][0]["name"] == "ORL / Smoke Suite"


def test_export_result_json_and_text_create_files(tmp_path) -> None:
    result = ConsoleResult(
        name="ORL / Demo Readiness",
        status="warn",
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
    assert payload["subresults"][0]["name"] == "ORL / Smoke Suite"
    assert "Status: WARN" in text
    assert "Scenario: inchon_mvp" in text
    assert "Artifacts:" in text
    assert payload["adapter_method"] == "run_all_green"
    assert payload["executed_command"] == ["pytest", "-q", "tests/test_inchon_scenario_stub.py"]
    assert payload["return_code"] == 1
    assert "Adapter Method: run_all_green" in text
    assert "Executed Command: pytest -q tests/test_inchon_scenario_stub.py" in text
    assert "Return Code: 1" in text
