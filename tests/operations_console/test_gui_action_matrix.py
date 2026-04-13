from __future__ import annotations

import json

import pytest

from tools.operations_console.gui_action_matrix import gui_action_matrix_path, load_gui_action_matrix


def test_gui_action_matrix_file_exists_and_is_loadable() -> None:
    path = gui_action_matrix_path()

    matrix = load_gui_action_matrix(path)

    assert path.exists()
    assert matrix.version == 1
    labels = {row.label for row in matrix.entries}
    assert "Refresh Scenarios" in labels
    assert "ORL / Smoke Suite" in labels
    assert "ORL / Deterministic Demo Runner" in labels
    assert "ORL / Demo Artifact Validation" in labels
    assert "ORL / Demo Checklist" in labels
    assert "ORL / Latest Artifacts" in labels
    assert "ORL / Pitch Support Bundle" in labels
    assert "ORL / Demo Readiness" in labels
    assert "ORL / Scenario Validator" in labels
    assert "ORL / Scenario Matrix" in labels
    assert "ORL / Explainability Smoketest" in labels
    assert "ORL / Round 1 Gate" in labels
    assert "ORL / Replay Validation" in labels
    assert "ORL / Snapshot Smoke" in labels
    assert "ORL / All-Green Check" in labels
    assert "ORL / Core Validation Suite" in labels
    assert "ORL / Campaign Status" in labels
    assert "ORL / Campaign Explain" in labels
    assert "Run Bridge" in labels
    assert "Run MWE" in labels
    assert "Stop Managed Processes" in labels
    assert "Utilities / Open Repo Konsole" in labels
    assert "Utilities / Open UI Konsole" in labels
    assert "Utilities / Open Bridge Konsole" in labels
    assert "Utilities / Open Artifacts Konsole" in labels
    assert "Utilities / Tail Latest Logs in Konsole" in labels
    assert "Utilities / Run Selected Command in Konsole" in labels


def test_gui_action_matrix_seeds_current_console_rows() -> None:
    matrix = load_gui_action_matrix()

    connectivity = matrix.get_by_label("ORL / Connectivity")
    assert connectivity is not None
    assert connectivity.description
    assert connectivity.runner == "registry.run_orl_connectivity"
    assert connectivity.expected_status == "pass"
    assert "bridge_uri" in connectivity.inputs
    assert connectivity.enabled is True

    deterministic_demo = matrix.get_by_label("ORL / Deterministic Demo Runner")
    assert deterministic_demo is not None
    assert deterministic_demo.runner == "registry.run_orl_deterministic_demo_runner"
    assert "replay" in deterministic_demo.artifact_types

    run_bridge = matrix.get_by_id("run-bridge")
    assert run_bridge is not None
    assert run_bridge.label == "Run Bridge"
    assert run_bridge.category == "Process Control"
    assert run_bridge.automation_level == "semi-automated"


def test_load_gui_action_matrix_rejects_missing_required_fields(tmp_path) -> None:
    path = tmp_path / "gui_action_matrix.yaml"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "actions": [
                    {
                        "id": "broken-row",
                        "label": "Broken Row",
                        "category": "Utilities",
                        "inputs": [],
                        "preconditions": [],
                        "runner": "registry.run_broken_row",
                        "expected_status": "pass",
                        "expected_log_fragments": [],
                        "artifact_types": [],
                        "automation_level": "manual",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=r"actions\[1\]\.description is required\."):
        load_gui_action_matrix(path)


def test_load_gui_action_matrix_rejects_non_boolean_enabled(tmp_path) -> None:
    path = tmp_path / "gui_action_matrix.yaml"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "actions": [
                    {
                        "id": "broken-enabled",
                        "label": "Broken Enabled",
                        "category": "Utilities",
                        "description": "Broken enabled type.",
                        "inputs": [],
                        "preconditions": [],
                        "runner": "registry.run_broken_enabled",
                        "expected_status": "pass",
                        "expected_log_fragments": [],
                        "artifact_types": [],
                        "automation_level": "manual",
                        "enabled": "yes",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match=r"actions\[1\]\.enabled must be a boolean\."):
        load_gui_action_matrix(path)
