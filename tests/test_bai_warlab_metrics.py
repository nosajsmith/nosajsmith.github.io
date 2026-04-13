from __future__ import annotations

from pathlib import Path

from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.metrics import (
    compute_behavior_metrics,
    compute_logistics_metrics,
    compute_objective_visibility,
    compute_outcome_metrics,
    compute_pressure_visibility,
    compute_score_visibility,
    compute_visibility_metrics,
)
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
    score_visibility = compute_score_visibility({})
    pressure_visibility = compute_pressure_visibility({})
    objective_visibility = compute_objective_visibility({})
    visibility = compute_visibility_metrics({})

    assert outcome["scenario_outcome"] == "unknown"
    assert outcome["vp_margin_allied"] == 0
    assert behavior["failed_attack_count"] == 0
    assert behavior["reserve_preservation_available"] is False
    assert behavior["objective_hold_turns_allied"] == 0
    assert behavior["line_collapse_rate_allied"] == 0.0
    assert logistics["available"] is False
    assert logistics["low_supply_turns_allied"] == 0
    assert score_visibility["available"] is False
    assert pressure_visibility["available"] is False
    assert objective_visibility["available"] is False
    assert "pressure_visibility" in visibility


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
    assert "line_collapse_rate_allied" in result.metrics["behavior"]
    assert "low_supply_turns_allied" in result.metrics["logistics"]
    assert _scalar_metric_count(
        {
            "outcome": result.metrics["outcome"],
            "behavior": result.metrics["behavior"],
            "logistics": result.metrics["logistics"],
        }
    ) >= 5


def test_bai_warlab_single_run_emits_visibility_timelines():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_single_run(
        RunRequest(
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=19,
            max_steps=2,
        ),
        loader,
    )

    score_visibility = result.metrics["score_visibility"]
    pressure_visibility = result.metrics["pressure_visibility"]
    objective_visibility = result.metrics["objective_visibility"]

    assert result.ok is True
    assert score_visibility["available"] is True
    assert len(score_visibility["timeline"]) == 2
    assert "score_margin_allied" in score_visibility["final"]
    assert pressure_visibility["available"] is True
    assert pressure_visibility["peak"]["pressure_score"] >= 0.0
    assert pressure_visibility["summary_lines"]
    assert objective_visibility["available"] is True
    assert len(objective_visibility["timeline"]) == 2
    assert "controls" in objective_visibility["final"]
