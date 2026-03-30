from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.bai_warlab import main as bai_warlab_main


def test_bai_warlab_batch_command_smoke(tmp_path: Path, capsys):
    output_dir = tmp_path / "batch-smoke"

    exit_code = bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "batch",
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
            "--runs",
            "2",
            "--seed",
            "17",
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
    manifest_payload = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    report_text = (output_dir / "report.txt").read_text(encoding="utf-8")
    csv_rows = list(csv.DictReader((output_dir / "results.csv").open(encoding="utf-8")))
    stdout = capsys.readouterr().out

    assert summary_payload["command"] == "batch"
    assert summary_payload["aggregate"]["total_runs"] == 2
    assert summary_payload["aggregate"]["ok_runs"] >= 1
    assert manifest_payload["seed_policy"]["seeds"] == [17, 18]
    assert "Batch Report" in report_text
    assert "[aggregate_summary]" in report_text
    assert "[core_metrics]" in report_text
    assert len(csv_rows) == 2
    assert "BAI War Lab — Batch Summary" in stdout
    assert "Scenario: mini_gc_1942" in stdout
    assert f"Artifacts: {output_dir}" in stdout
