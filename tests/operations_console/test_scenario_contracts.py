from __future__ import annotations

import json

import pytest

from tools.operations_console.gui_action_matrix import load_gui_action_matrix
from tools.operations_console.runner_utils import make_result
from tools.operations_console.scenario_contracts import (
    ScenarioContract,
    ScenarioContractCatalog,
    apply_scenario_contracts,
    evaluate_result_contract,
    evaluate_scenario_contract,
    load_scenario_contracts,
)


def test_load_scenario_contracts_reads_repo_file() -> None:
    catalog = load_scenario_contracts()

    assert catalog.version == 1
    assert len(catalog.contracts) >= 2
    assert any(contract.scenario_name == "inchon_mvp" for contract in catalog.contracts)
    assert any(contract.scenario_name == "breakthrough" for contract in catalog.contracts)


def test_scenario_contract_catalog_lookup_normalizes_json_suffix() -> None:
    catalog = load_scenario_contracts()

    contract = catalog.get("inchon_mvp.json")

    assert contract is not None
    assert contract.scenario_name == "inchon_mvp"


def test_evaluate_scenario_contract_passes_for_seeded_inchon_contract() -> None:
    evaluation = evaluate_scenario_contract("inchon_mvp")

    assert evaluation.matched is True
    assert evaluation.contract_scenario_name == "inchon_mvp"
    assert evaluation.status == "pass"
    assert evaluation.issues == []


def test_evaluate_scenario_contract_reports_missing_objectives_and_fields(tmp_path) -> None:
    contracts_path = tmp_path / "scenario_contracts.yaml"
    contracts_path.write_text(
        json.dumps(
            {
                "version": 1,
                "contracts": [
                    {
                        "scenario_name": "demo_case",
                        "expected_unit_count_range": [2, 4],
                        "expected_objectives": ["Seoul"],
                        "expected_status_fields": ["grease_board.front_status"],
                        "expected_explain_fields": ["grease_board.staff_notes"],
                        "known_issues": [],
                        "mismatch_status": "warn",
                        "notes": "Synthetic test contract.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    payload = {
        "id": "demo_case",
        "name": "Demo Case",
        "units": [{"id": "u1"}],
        "objectives": [{"name": "Inchon Harbor"}],
    }
    catalog = load_scenario_contracts(contracts_path)

    evaluation = evaluate_scenario_contract(
        "demo_case",
        contract_catalog=catalog,
        scenario_payload=payload,
    )

    assert evaluation.matched is True
    assert evaluation.status == "warn"
    assert any("Unit count 1 fell outside expected range [2, 4]." == issue for issue in evaluation.issues)
    assert any("Expected objective missing: Seoul." == issue for issue in evaluation.issues)
    assert any("Expected status field missing: grease_board.front_status." == issue for issue in evaluation.issues)
    assert any("Expected explain field missing: grease_board.staff_notes." == issue for issue in evaluation.issues)


def test_apply_scenario_contracts_upgrades_result_status_on_mismatch(tmp_path) -> None:
    contracts_path = tmp_path / "scenario_contracts.yaml"
    contracts_path.write_text(
        json.dumps(
            {
                "version": 1,
                "contracts": [
                    {
                        "scenario_name": "demo_case",
                        "expected_unit_count_range": [3, 3],
                        "expected_objectives": [],
                        "expected_status_fields": [],
                        "expected_explain_fields": [],
                        "known_issues": ["KI-002"],
                        "mismatch_status": "warn",
                        "notes": "Synthetic warning contract.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    catalog = load_scenario_contracts(contracts_path)
    result = make_result(
        name="ORL / Scenario Integrity",
        status="pass",
        summary="Scenario integrity passed.",
        scenario_name="demo_case",
    )

    updated, evaluation = apply_scenario_contracts(
        result,
        contract_catalog=catalog,
        scenario_name="demo_case",
        action_matrix=None,
        repo_root_path=tmp_path,
    )

    assert evaluation is not None
    assert evaluation.status == "warn"
    assert updated.status == "warn"
    assert "Scenario contract mismatch" in updated.summary
    assert any("CONTRACT MISMATCH:" in line for line in updated.details)


def test_evaluate_result_contract_skips_non_scenario_result() -> None:
    result = make_result(
        name="ORL / UI Build Check",
        status="pass",
        summary="UI build passed.",
    )

    evaluation = evaluate_result_contract(result)

    assert evaluation is None


def test_load_scenario_contracts_rejects_missing_version(tmp_path) -> None:
    contracts_path = tmp_path / "scenario_contracts.yaml"
    contracts_path.write_text(
        json.dumps(
            {
                "contracts": [
                    {
                        "scenario_name": "demo_case",
                        "notes": "missing version should fail",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="integer version"):
        load_scenario_contracts(contracts_path)


def test_load_scenario_contracts_rejects_non_boolean_enabled(tmp_path) -> None:
    contracts_path = tmp_path / "scenario_contracts.yaml"
    contracts_path.write_text(
        json.dumps(
            {
                "version": 1,
                "contracts": [
                    {
                        "scenario_name": "demo_case",
                        "enabled": "yes",
                        "notes": "bad enabled value",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="enabled must be a boolean"):
        load_scenario_contracts(contracts_path)


def test_disabled_contracts_are_not_matched() -> None:
    catalog = ScenarioContractCatalog(
        contracts=[
            ScenarioContract(
                scenario_name="demo_case",
                enabled=False,
                notes="disabled contract",
            )
        ]
    )

    evaluation = evaluate_scenario_contract("demo_case", contract_catalog=catalog)

    assert evaluation.matched is False


def test_evaluate_result_contract_uses_selected_scenario_and_unit_logs() -> None:
    result = make_result(
        name="ORL / Smoke Suite",
        status="pass",
        summary="Suite completed with status PASS.",
        details=[
            "Selected scenario: inchon_mvp.json",
            "Validated units: 6 total, 6 with basic identity/location fields",
        ],
    )

    evaluation = evaluate_result_contract(
        result,
        action_matrix=load_gui_action_matrix(),
    )

    assert evaluation is not None
    assert evaluation.matched is True
    assert evaluation.scenario_name == "inchon_mvp"
    assert evaluation.status == "pass"
    assert "unit count in range [5, 8] (observed 6)" in evaluation.passed_checks


def test_evaluate_scenario_contract_checks_expected_artifacts() -> None:
    catalog = ScenarioContractCatalog(
        contracts=[
            ScenarioContract(
                scenario_name="demo_case",
                expected_artifacts=["replay.json", "snapshot.png"],
                notes="artifact expectations",
            )
        ]
    )

    evaluation = evaluate_scenario_contract(
        "demo_case",
        contract_catalog=catalog,
        scenario_payload={"units": []},
        artifact_paths=["/tmp/replay.json"],
    )

    assert evaluation.matched is True
    assert evaluation.status == "fail"
    assert evaluation.expected_artifacts == ["replay.json", "snapshot.png"]
    assert evaluation.issues == ["Expected artifact missing: snapshot.png."]
