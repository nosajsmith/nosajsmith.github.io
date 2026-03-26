from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.bai_warlab import BAI_WARLAB_VERSION
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
    assert "batch" not in result.stdout
    assert "compare" not in result.stdout
    assert "suite" not in result.stdout


def test_bai_warlab_subcommands_parse_correctly():
    parser = build_parser()
    assert parser.parse_args(
        [
            "run",
            "--scenario",
            "mini_gc_1942",
            "--doctrine",
            "korea_nkpa_shock",
            "--personality",
            "aggressive",
            "--tuning",
            "default",
        ]
    ).command == "run"


def test_bai_warlab_cli_smoke_outputs(tmp_path: Path):
    run_dir = tmp_path / "run"

    assert bai_warlab_main(
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
            str(run_dir),
        ]
    ) == 0
    run_summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert run_summary["summary"]["execution_status"] == "completed"
    assert run_summary["summary"]["scenario_outcome"] in {"allied_victory", "axis_victory", "draw"}
    assert run_manifest["bai_version"] == BAI_WARLAB_VERSION
    assert "run --scenario mini_gc_1942" in run_manifest["command_line"]
    assert run_manifest["extra"]["rerun"]["argv"][:3] == ["--config-root", "configs/ai", "run"]
    assert run_manifest["extra"]["scenario_records"][0]["source_path"].endswith("mini_gc_1942.json")
    assert len(run_manifest["extra"]["scenario_records"][0]["sha256"]) == 64
    assert run_manifest["extra"]["profile_records"]["doctrine"]["source_path"].endswith("korea_nkpa_shock.yaml")
    assert len(run_manifest["extra"]["profile_records"]["doctrine"]["sha256"]) == 64
    assert (run_dir / "results.csv").exists()
    assert (run_dir / "report.txt").exists()
    assert (run_dir / "manifest.json").exists()
