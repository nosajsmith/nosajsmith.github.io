from __future__ import annotations

from pathlib import Path

from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.metrics import compute_behavior_metrics, compute_logistics_metrics, compute_outcome_metrics
from tools.bai_warlab.models import RunRequest
from tools.bai_warlab.runners import execute_single_run


ROOT = Path(__file__).resolve().parents[1]


def _scalar_metric_count(metrics: dict) -> int:
    count = 0
    for payload in metrics.values():
        if not isinstance(payload, dict):
            continue
        for value in payload.values():
            if isinstance(value, (str, int, float, bool)) or value is None:
                count += 1
    return count


def test_bai_warlab_metrics_modules_handle_sparse_context():
    outcome = compute_outcome_metrics({})
    behavior = compute_behavior_metrics({})
    logistics = compute_logistics_metrics({})

    assert outcome["scenario_outcome"] == "unknown"
    assert outcome["vp_margin_allied"] == 0
    assert behavior["failed_attack_count"] == 0
    assert behavior["reserve_preservation_available"] is False
    assert behavior["objective_hold_turns_allied"] == 0
    assert logistics["available"] is False
    assert logistics["low_supply_turns_allied"] == 0


def test_bai_warlab_single_run_emits_v1_metrics():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_single_run(
        RunRequest(
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=17,
            max_steps=2,
        ),
        loader,
    )

    assert result.ok is True
    assert "outcome" in result.metrics
    assert "behavior" in result.metrics
    assert "logistics" in result.metrics
    assert result.metrics["outcome"]["win_loss_draw_allied"] in {"win", "loss", "draw"}
    assert "vp_margin_allied" in result.metrics["outcome"]
    assert "casualty_ratio_allied" in result.metrics["behavior"]
    assert "objective_hold_turns_allied" in result.metrics["behavior"]
    assert "low_supply_turns_allied" in result.metrics["logistics"]
    assert _scalar_metric_count(
        {
            "outcome": result.metrics["outcome"],
            "behavior": result.metrics["behavior"],
            "logistics": result.metrics["logistics"],
        }
    ) >= 5
