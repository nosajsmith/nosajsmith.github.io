from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.bai_warlab.bai_warlab import build_parser, main as bai_warlab_main


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "bai_warlab" / "bai_warlab.py"


def test_bai_warlab_help_works():
    result = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "run" in result.stdout
    assert "batch" in result.stdout
    assert "compare" in result.stdout
    assert "suite" in result.stdout


def test_bai_warlab_subcommands_parse_correctly():
    parser = build_parser()
    assert parser.parse_args(
        [
            "run",
            "--scenario",
            "foundation_smoke.json",
            "--doctrine",
            "korea_nkpa_shock",
            "--personality",
            "aggressive",
            "--tuning",
            "default",
        ]
    ).command == "run"
    assert parser.parse_args(
        [
            "batch",
            "--scenario",
            "foundation_smoke.json",
            "--doctrine",
            "korea_nkpa_shock",
            "--personality",
            "aggressive",
            "--tuning",
            "default",
        ]
    ).command == "batch"
    assert parser.parse_args(
        [
            "compare",
            "--scenario",
            "foundation_smoke.json",
            "--left-doctrine",
            "korea_un_combined_arms",
            "--left-personality",
            "historical",
            "--left-tuning",
            "default",
            "--right-doctrine",
            "korea_nkpa_shock",
            "--right-personality",
            "aggressive",
            "--right-tuning",
            "offense_focus",
        ]
    ).command == "compare"
    assert parser.parse_args(["suite", "korea_core_v1"]).command == "suite"


def test_bai_warlab_cli_smoke_outputs(tmp_path: Path):
    run_dir = tmp_path / "run"
    batch_dir = tmp_path / "batch"
    compare_dir = tmp_path / "compare"
    suite_dir = tmp_path / "suite"

    assert bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "run",
            "--scenario",
            "foundation_smoke.json",
            "--scenario-dir",
            "synthetic_scenarios",
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
            str(run_dir),
        ]
    ) == 0
    run_summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert run_summary["summary"]["execution_status"] == "not_executed"
    assert (run_dir / "results.csv").exists()
    assert (run_dir / "report.txt").exists()
    assert (run_dir / "manifest.json").exists()

    assert bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "batch",
            "--scenario",
            "foundation_smoke.json",
            "--scenario-dir",
            "synthetic_scenarios",
            "--doctrine",
            "korea_nkpa_shock",
            "--personality",
            "adaptive",
            "--tuning",
            "offense_focus",
            "--count",
            "2",
            "--seed-start",
            "11",
            "--output-dir",
            str(batch_dir),
        ]
    ) == 0
    batch_summary = json.loads((batch_dir / "summary.json").read_text(encoding="utf-8"))
    assert batch_summary["aggregate"]["total_runs"] == 2
    assert (batch_dir / "results.csv").exists()

    assert bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "compare",
            "--scenario",
            "foundation_smoke.json",
            "--scenario-dir",
            "synthetic_scenarios",
            "--left-doctrine",
            "korea_un_combined_arms",
            "--left-personality",
            "historical",
            "--left-tuning",
            "default",
            "--right-doctrine",
            "korea_nkpa_shock",
            "--right-personality",
            "aggressive",
            "--right-tuning",
            "offense_focus",
            "--count",
            "2",
            "--seed-start",
            "21",
            "--output-dir",
            str(compare_dir),
        ]
    ) == 0
    compare_summary = json.loads((compare_dir / "summary.json").read_text(encoding="utf-8"))
    assert compare_summary["comparison"]["paired_seed_count"] == 2
    assert (compare_dir / "results.csv").exists()

    assert bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "suite",
            "korea_core_v1",
            "--output-dir",
            str(suite_dir),
        ]
    ) == 0
    suite_summary = json.loads((suite_dir / "summary.json").read_text(encoding="utf-8"))
    assert suite_summary["suite_name"] == "korea_core_v1"
    assert len(suite_summary["runs"]) == 3
    assert (suite_dir / "results.csv").exists()

