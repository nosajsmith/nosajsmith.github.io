from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.bai_warlab import main as bai_warlab_main


def test_bai_warlab_suite_command_smoke(tmp_path: Path):
    output_dir = tmp_path / "suite-smoke"

    exit_code = bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "suite",
            "core_regression",
            "--runs",
            "1",
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

    assert summary_payload["command"] == "suite"
    assert summary_payload["suite_name"] == "core_regression"
    assert summary_payload["suite_summary"]["job_count"] == 4
    assert len(summary_payload["jobs"]) == 4
    assert manifest_payload["seed_policy"]["kind"] == "suite_preset"
    assert "Suite Report" in report_text
    assert "[evaluation_notes]" in report_text
    assert "[suite_jobs]" in report_text
    assert "metric_focus:" in report_text
    assert len(csv_rows) == 4

