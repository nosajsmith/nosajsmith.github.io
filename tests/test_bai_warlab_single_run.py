from __future__ import annotations

import json
from pathlib import Path

from tools.bai_warlab.bai_warlab import main as bai_warlab_main
from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.models import RunRequest
from tools.bai_warlab.reports.first_divergence import find_first_divergence
from tools.bai_warlab.reports.summary_report import render_report
from tools.bai_warlab.runners import execute_single_run, execute_variant_compare


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


def test_bai_warlab_single_run_records_variant_metadata_and_visibility_report():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_single_run(
        RunRequest(
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="korea_nkpa_shock",
            personality="aggressive",
            tuning="default",
            seed=11,
            max_steps=2,
            variant_id="aggressive_nkpa",
            variant_name="Aggressive NKPA",
            run_overrides={"attack_supply_floor": 60},
        ),
        loader,
    )

    report_text = render_report(result)

    assert result.ok is True
    assert result.variant_id == "aggressive_nkpa"
    assert result.variant_name == "Aggressive NKPA"
    assert result.resolved_profile["config_provenance"]["run_overrides"]["attack_supply_floor"] == 60
    assert result.summary["variant_id"] == "aggressive_nkpa"
    assert "[score_visibility]" in report_text
    assert "[pressure_visibility]" in report_text
    assert "[objective_visibility]" in report_text


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


def test_bai_warlab_single_run_smoke_writes_expected_output_files(tmp_path: Path):
    output_dir = tmp_path / "single-run-smoke"

    exit_code = bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "run",
            "--scenario",
            "mini_gc_1942",
            "--scenario-dir",
            "scenarios",
            "--doctrine",
            "korea_nkpa_shock",
            "--personality",
            "aggressive",
            "--tuning",
            "default",
            "--seed",
            "7",
            "--max-steps",
            "2",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "summary.json").exists()
    assert (output_dir / "report.txt").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "results.csv").exists()

    summary_payload = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    report_text = (output_dir / "report.txt").read_text(encoding="utf-8")
    manifest_payload = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

    assert summary_payload["ok"] is True
    assert summary_payload["summary"]["execution_status"] == "completed"
    assert summary_payload["summary"]["scenario_name"] == "Mini Guadalcanal 1942"
    assert "BAI War Lab" in report_text
    assert "Scenario: mini_gc_1942" in report_text
    assert "Execution Status: completed" in report_text
    assert manifest_payload["command"] == "run"
    assert manifest_payload["output_dir"] == str(output_dir.resolve())


def test_bai_warlab_variant_compare_emits_structured_summary_and_divergence():
    loader = ConfigLoader(ROOT / "configs" / "ai")
    result = execute_variant_compare(
        scenario="mini_gc_1942",
        scenario_dir="scenarios",
        variants=[
            {
                "variant_id": "shock_aggressive",
                "label": "Shock Aggressive",
                "doctrine": "korea_nkpa_shock",
                "personality": "aggressive",
                "tuning": "default",
            },
            {
                "variant_id": "un_historical",
                "label": "UN Historical",
                "doctrine": "korea_un_combined_arms",
                "personality": "historical",
                "tuning": "default",
            },
        ],
        loader=loader,
        seed=5,
        max_steps=2,
    )

    divergence = find_first_divergence(result.runs[0], result.runs[1])
    report_text = render_report(result)

    assert result.ok is True
    assert result.comparison["variant_count"] == 2
    assert len(result.comparison["variants"]) == 2
    assert result.comparison["best_score"] is not None
    assert result.comparison["largest_pressure_delta"] is not None
    assert divergence["comparable"] is True
    assert "Variant Comparison Report" in report_text
    assert "best score:" in report_text
