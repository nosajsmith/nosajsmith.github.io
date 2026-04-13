from __future__ import annotations

from tools.operations_console.baselines import (
    compare_result_to_baseline,
    default_baseline_dir,
    load_baseline_for_result,
    save_baseline,
)
from tools.operations_console.report_export import export_result_text, report_dict
from tools.operations_console.runner_utils import make_result


def test_default_baseline_dir_uses_artifacts_path() -> None:
    path = default_baseline_dir()

    assert str(path).endswith("artifacts/operations_console/baselines")


def test_save_baseline_uses_default_artifacts_dir_when_repo_root_is_overridden(tmp_path) -> None:
    result = make_result(
        name="ORL / Scenario Integrity",
        status="pass",
        summary="Scenario integrity passed for inchon_mvp with 6 unit(s).",
        scenario_name="inchon_mvp",
        details=["Validated units: 6 total, 6 with basic identity/location fields"],
    )

    path = save_baseline(result, repo_root_path=tmp_path)
    record = load_baseline_for_result(result, repo_root_path=tmp_path)

    assert path == tmp_path / "artifacts" / "operations_console" / "baselines" / "orl-scenario-integrity--inchon-mvp.json"
    assert path.exists()
    assert record is not None
    assert record.source_path == str(path)


def test_save_baseline_and_load_matching_record(tmp_path) -> None:
    result = make_result(
        name="ORL / Scenario Integrity",
        status="pass",
        summary="Scenario integrity passed for inchon_mvp with 6 unit(s).",
        scenario_name="inchon_mvp",
        details=["Validated units: 6 total, 6 with basic identity/location fields"],
    )

    path = save_baseline(result, baseline_dir_path=tmp_path)
    record = load_baseline_for_result(result, baseline_dir_path=tmp_path)

    assert path.exists()
    assert record is not None
    assert record.name == "ORL / Scenario Integrity"
    assert record.metrics["status"] == "pass"
    assert record.metrics["unit_count"] == 6
    assert record.metrics["selected_fields"]["grease_board.front_status"] == "INCHON BEACHHEAD SECURE"


def test_compare_result_to_baseline_passes_for_identical_result(tmp_path) -> None:
    result = make_result(
        name="ORL / UI Build Check",
        status="pass",
        summary="UI build completed successfully.",
        artifact_paths=["/tmp/dist/index.html"],
    )
    save_baseline(result, baseline_dir_path=tmp_path)

    comparison = compare_result_to_baseline(result, baseline_dir_path=tmp_path)

    assert comparison.matched is True
    assert comparison.status == "pass"
    assert comparison.findings == []


def test_compare_result_to_baseline_warns_within_unit_tolerance(tmp_path) -> None:
    baseline = make_result(
        name="Synthetic / Scenario Check",
        status="pass",
        summary="Scenario integrity passed for demo with 10 unit(s).",
        details=["Validated units: 10 total, 10 with basic identity/location fields"],
    )
    current = make_result(
        name="Synthetic / Scenario Check",
        status="pass",
        summary="Scenario integrity passed for demo with 11 unit(s).",
        details=["Validated units: 11 total, 11 with basic identity/location fields"],
    )
    save_baseline(baseline, baseline_dir_path=tmp_path)

    comparison = compare_result_to_baseline(current, baseline_dir_path=tmp_path)

    assert comparison.matched is True
    assert comparison.status == "warn"
    assert any(item.metric == "unit_count" and item.status == "warn" for item in comparison.findings)


def test_compare_result_to_baseline_fails_on_missing_artifact(tmp_path) -> None:
    baseline = make_result(
        name="ORL / UI Build Check",
        status="pass",
        summary="UI build completed successfully.",
        artifact_paths=["/tmp/dist/index.html"],
    )
    current = make_result(
        name="ORL / UI Build Check",
        status="pass",
        summary="UI build completed successfully.",
        artifact_paths=[],
    )
    save_baseline(baseline, baseline_dir_path=tmp_path)

    comparison = compare_result_to_baseline(current, baseline_dir_path=tmp_path)

    assert comparison.matched is True
    assert comparison.status == "fail"
    assert any(item.metric.startswith("artifact_") and item.status == "fail" for item in comparison.findings)


def test_report_export_includes_baseline_drift(tmp_path) -> None:
    baseline = make_result(
        name="Synthetic / Drift Demo",
        status="pass",
        summary="Scenario integrity passed for demo with 8 unit(s).",
        details=["Validated units: 8 total, 8 with basic identity/location fields"],
    )
    current = make_result(
        name="Synthetic / Drift Demo",
        status="pass",
        summary="Scenario integrity passed for demo with 10 unit(s).",
        details=["Validated units: 10 total, 10 with basic identity/location fields"],
    )
    save_baseline(baseline, baseline_dir_path=tmp_path / "baselines")

    payload = report_dict(current, baseline_dir_path=tmp_path / "baselines")
    text_path = export_result_text(current, tmp_path / "exports", baseline_dir_path=tmp_path / "baselines")
    text = text_path.read_text(encoding="utf-8")

    assert payload["baseline_drift"]["matched"] is True
    assert payload["baseline_drift"]["status"] == "fail"
    assert payload["baseline_drift"]["baseline_path"]
    assert any(item["metric"] == "unit_count" for item in payload["baseline_drift"]["findings"])
    assert "Baseline Drift: FAIL" in text
    assert "Baseline Path:" in text
