from __future__ import annotations

from pathlib import Path

from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.models import RunRequest
from tools.bai_warlab.runners import execute_single_run


ROOT = Path(__file__).resolve().parents[1]


def test_bai_warlab_single_run_executes_headless_scenario():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_single_run(
        RunRequest(
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=7,
            max_steps=2,
        ),
        loader,
    )

    assert result.ok is True
    assert result.summary["execution_status"] == "completed"
    assert result.summary["steps_completed"] == 2
    assert result.summary["terminal_status"] == "max_steps"
    assert result.summary["scenario_name"] == "Mini Guadalcanal 1942"
    assert result.metrics["outcome"]["available"] is True
    assert result.metrics["execution"]["log_count"] > 0


def test_bai_warlab_single_run_handles_missing_scenario_gracefully():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_single_run(
        RunRequest(
            scenario="missing_scenario",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=7,
            max_steps=2,
        ),
        loader,
    )

    assert result.ok is False
    assert result.summary["terminal_status"] == "scenario_load_error"
    assert "Scenario not found" in (result.error or "")
