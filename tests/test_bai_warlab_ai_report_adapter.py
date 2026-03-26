from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.bai_warlab.ai_report_adapter import empty_ai_report, normalize_ai_report
from tools.bai_warlab.config_loader import ConfigLoader
from tools.bai_warlab.models import RunRequest
from tools.bai_warlab.report_io import run_result_to_row, write_json, write_results_csv
from tools.bai_warlab.runners import execute_single_run


def test_ai_report_adapter_normalizes_nested_payload():
    payload = {
        "reasoning": {
            "posture": "ATTACK",
            "objective_candidates": [
                {"id": "LUNGA", "selected": False},
                {"id": "TULAGI", "selected": True},
            ],
            "operations": [
                {"name": "probe", "selected": False},
                {"name": "encirclement", "selected": True},
            ],
            "reserve": {"level": "medium"},
            "timing": {"sense_ms": 5, "plan_ms": 11},
        }
    }

    report = normalize_ai_report(payload)

    assert report["available"] is True
    assert report["posture"] == "ATTACK"
    assert report["main_objective"] == "TULAGI"
    assert report["chosen_operation"] == "encirclement"
    assert report["reserve_level"] == "medium"
    assert report["timing_breakdown"] == {"sense_ms": 5, "plan_ms": 11}
    assert report["missing_fields"] == []


def test_ai_report_adapter_sparse_payload_does_not_break():
    report = normalize_ai_report({"ai_report": {"posture": "DEFEND"}})

    assert report["available"] is True
    assert report["posture"] == "DEFEND"
    assert report["main_objective"] is None
    assert "main_objective" in report["missing_fields"]
    assert "timing_breakdown" in report["missing_fields"]
    assert empty_ai_report()["available"] is False


def test_bai_warlab_single_run_captures_and_writes_ai_report(tmp_path: Path):
    config_root = tmp_path / "configs"
    (config_root / "doctrines").mkdir(parents=True)
    (config_root / "personalities").mkdir(parents=True)
    (config_root / "tuning").mkdir(parents=True)

    (config_root / "doctrines" / "demo.yaml").write_text(
        "\n".join(
            [
                "name: demo",
                "axis:",
                "  aggression: 0.8",
                "run:",
                "  max_steps: 4",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (config_root / "personalities" / "demo.yaml").write_text(
        "\n".join(
            [
                "name: demo",
                "axis:",
                "  aggression: 0.7",
                "run: {}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (config_root / "tuning" / "demo.yaml").write_text(
        "\n".join(
            [
                "name: demo",
                "run:",
                "  ai_report:",
                "    posture: ATTACK",
                "    main_objective: TULAGI",
                "    chosen_operation: encirclement",
                "    reserve_level: low",
                "    timing_breakdown:",
                "      plan_ms: 12",
                "      issue_ms: 3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = execute_single_run(
        RunRequest(
            scenario="mini_gc_1942",
            scenario_dir="scenarios",
            doctrine="demo",
            personality="demo",
            tuning="demo",
            seed=9,
        ),
        ConfigLoader(config_root),
    )

    assert result.ok is True
    assert result.ai_report["available"] is True
    assert result.ai_report["posture"] == "ATTACK"
    assert result.ai_report["chosen_operation"] == "encirclement"

    summary_path = write_json(tmp_path / "summary.json", result)
    csv_path = write_results_csv(tmp_path / "results.csv", [run_result_to_row(result)])

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    csv_rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

    assert summary_payload["ai_report"]["main_objective"] == "TULAGI"
    assert csv_rows[0]["ai_report_available"] == "True"
    assert csv_rows[0]["ai_report_chosen_operation"] == "encirclement"
