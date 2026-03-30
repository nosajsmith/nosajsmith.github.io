from __future__ import annotations

from tools.operations_console.process_control import gui_action_matrix_path, load_gui_action_matrix


def test_gui_action_matrix_file_exists_and_is_loadable() -> None:
    path = gui_action_matrix_path()

    payload = load_gui_action_matrix(path)

    assert path.exists()
    assert payload["version"] == 1
    labels = {row["label"] for row in payload["actions"]}
    assert "Refresh Scenarios" in labels
    assert "ORL / Smoke Suite" in labels
    assert "Run Bridge" in labels
    assert "Stop Managed Processes" in labels
