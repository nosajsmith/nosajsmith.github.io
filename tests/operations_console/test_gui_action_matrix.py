from __future__ import annotations

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
    assert "Run Bridge" in labels
    assert "Stop Managed Processes" in labels


def test_gui_action_matrix_seeds_current_console_rows() -> None:
    matrix = load_gui_action_matrix()

    connectivity = matrix.get_by_label("ORL / Connectivity")
    assert connectivity is not None
    assert connectivity.runner == "registry.run_orl_connectivity"
    assert connectivity.expected_status == "pass"
    assert "bridge_uri" in connectivity.inputs

    deterministic_demo = matrix.get_by_label("ORL / Deterministic Demo Runner")
    assert deterministic_demo is not None
    assert deterministic_demo.runner == "registry.run_orl_deterministic_demo_runner"
    assert "replay" in deterministic_demo.artifact_types

    run_bridge = matrix.get_by_id("run-bridge")
    assert run_bridge is not None
    assert run_bridge.label == "Run Bridge"
    assert run_bridge.category == "Process Control"
    assert run_bridge.automation_level == "semi-automated"
