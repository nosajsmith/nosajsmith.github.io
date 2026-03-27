from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.bai_warlab import main as bai_warlab_main


def test_bai_warlab_compare_command_smoke(tmp_path: Path):
    output_dir = tmp_path / "compare-smoke"

    exit_code = bai_warlab_main(
        [
            "--config-root",
            "configs/ai",
            "compare",
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
            "--right-doctrine",
            "korea_un_combined_arms",
            "--runs",
            "2",
            "--seed",
            "27",
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

    assert summary_payload["command"] == "compare"
    assert summary_payload["comparison"]["paired_seed_count"] == 2
    assert summary_payload["comparison"]["core_metrics"]
    assert manifest_payload["seed_policy"]["seeds"] == [27, 28]
    assert "Compare Report" in report_text
    assert "[decision]" in report_text
    assert "[key_deltas]" in report_text
    assert "[callouts]" in report_text
    assert len(csv_rows) == 4
    assert {row["variant_label"] for row in csv_rows} == {"left", "right"}

