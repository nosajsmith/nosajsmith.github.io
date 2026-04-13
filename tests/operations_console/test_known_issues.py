from __future__ import annotations

import json

import pytest

from tools.operations_console.known_issues import apply_known_issues, load_known_issues
from tools.operations_console.runner_utils import make_result


def test_load_known_issues_reads_repo_file() -> None:
    catalog = load_known_issues()

    assert len(catalog.issues) >= 1
    assert any(issue.issue_id.startswith("KI-") for issue in catalog.issues)


def test_load_known_issues_validates_expected_status_override(tmp_path) -> None:
    path = tmp_path / "known_issues.yaml"
    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-999",
                        "title": "Bad override",
                        "severity": "high",
                        "category": "ORL",
                        "affects": ["ORL / Connectivity"],
                        "scenarios": [],
                        "status": "waived",
                        "expected_status_override": "idle",
                        "symptom_match": ["failed"],
                        "notes": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="expected_status_override"):
        load_known_issues(path)


def test_load_known_issues_validates_status_and_waiver_override_pairing(tmp_path) -> None:
    path = tmp_path / "known_issues.yaml"
    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-998",
                        "title": "Bad status",
                        "severity": "high",
                        "category": "ORL",
                        "affects": ["ORL / Connectivity"],
                        "scenarios": [],
                        "status": "tracking",
                        "expected_status_override": "",
                        "symptom_match": ["failed"],
                        "notes": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="status must be one of"):
        load_known_issues(path)

    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-997",
                        "title": "Override without waiver",
                        "severity": "high",
                        "category": "ORL",
                        "affects": ["ORL / Connectivity"],
                        "scenarios": [],
                        "status": "known",
                        "expected_status_override": "warn",
                        "symptom_match": ["failed"],
                        "notes": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="requires status waived"):
        load_known_issues(path)


def test_load_known_issues_requires_at_least_one_matcher(tmp_path) -> None:
    path = tmp_path / "known_issues.yaml"
    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-996",
                        "title": "No matcher",
                        "severity": "medium",
                        "category": "ORL",
                        "affects": [],
                        "scenarios": [],
                        "status": "known",
                        "expected_status_override": "",
                        "symptom_match": [],
                        "notes": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="must define at least one of affects, scenarios, or symptom_match"):
        load_known_issues(path)


def test_load_known_issues_rejects_non_string_optional_fields(tmp_path) -> None:
    path = tmp_path / "known_issues.yaml"
    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-995",
                        "title": "Bad notes",
                        "severity": "medium",
                        "category": "ORL",
                        "affects": ["ORL / Connectivity"],
                        "scenarios": [],
                        "status": "known",
                        "expected_status_override": "",
                        "symptom_match": ["bridge unavailable"],
                        "notes": ["not", "a", "string"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=r"known_issues\[1\]\.notes must be a string"):
        load_known_issues(path)


def test_apply_known_issues_matches_by_name_scenario_and_symptom(tmp_path) -> None:
    path = tmp_path / "known_issues.yaml"
    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-101",
                        "title": "Known connectivity fault",
                        "severity": "medium",
                        "category": "ORL",
                        "affects": ["ORL / Connectivity"],
                        "scenarios": ["inchon_mvp"],
                        "status": "known",
                        "expected_status_override": "",
                        "symptom_match": ["bridge unavailable"],
                        "notes": "Tracked while bridge supervision is stabilised.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    catalog = load_known_issues(path)
    result = make_result(
        name="ORL / Connectivity",
        status="fail",
        summary="Bridge connectivity check failed.",
        errors=["bridge unavailable: connection refused"],
        scenario_name="inchon_mvp.json",
    )

    annotated = apply_known_issues(result, catalog)

    assert annotated.status == "fail"
    assert annotated.original_status == ""
    assert [match.issue_id for match in annotated.known_issue_matches] == ["KI-101"]


def test_apply_known_issues_uses_explicit_waiver_only_when_all_matches_override(tmp_path) -> None:
    path = tmp_path / "known_issues.yaml"
    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-201",
                        "title": "Waived snapshot fault",
                        "severity": "high",
                        "category": "ORL",
                        "affects": ["ORL / Snapshot Smoke"],
                        "scenarios": ["inchon_mvp"],
                        "status": "waived",
                        "expected_status_override": "warn",
                        "symptom_match": ["snapshot mismatch"],
                        "notes": "",
                    },
                    {
                        "id": "KI-202",
                        "title": "Related known issue without waiver",
                        "severity": "medium",
                        "category": "ORL",
                        "affects": ["ORL / Snapshot Smoke"],
                        "scenarios": ["inchon_mvp"],
                        "status": "known",
                        "expected_status_override": "",
                        "symptom_match": ["snapshot mismatch"],
                        "notes": "",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    catalog = load_known_issues(path)
    result = make_result(
        name="ORL / Snapshot Smoke",
        status="fail",
        summary="Snapshot failed.",
        errors=["snapshot mismatch on load"],
        scenario_name="inchon_mvp",
    )

    annotated = apply_known_issues(result, catalog)

    assert annotated.status == "fail"
    assert annotated.original_status == ""
    assert [match.issue_id for match in annotated.known_issue_matches] == ["KI-201", "KI-202"]


def test_apply_known_issues_only_downgrades_fail_to_warn(tmp_path) -> None:
    path = tmp_path / "known_issues.yaml"
    path.write_text(
        json.dumps(
            {
                "known_issues": [
                    {
                        "id": "KI-301",
                        "title": "Waived exception",
                        "severity": "high",
                        "category": "ORL",
                        "affects": ["ORL / Snapshot Smoke"],
                        "scenarios": ["inchon_mvp"],
                        "status": "waived",
                        "expected_status_override": "warn",
                        "symptom_match": ["snapshot mismatch"],
                        "notes": "",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    catalog = load_known_issues(path)
    result = make_result(
        name="ORL / Snapshot Smoke",
        status="error",
        summary="Snapshot crashed.",
        errors=["snapshot mismatch raised an exception"],
        scenario_name="inchon_mvp",
    )

    annotated = apply_known_issues(result, catalog)

    assert annotated.status == "error"
    assert annotated.original_status == ""
    assert [match.issue_id for match in annotated.known_issue_matches] == ["KI-301"]
