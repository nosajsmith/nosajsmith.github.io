from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

from .. import ARTIFACT_ROOT, BAI_WARLAB_VERSION
from ..regression import build_metric_snapshot, compare_against_baseline, resolve_regression_rules
from ..report_io import slugify, write_json


BASELINE_SCHEMA_VERSION = 1
BASELINE_ROOT = ARTIFACT_ROOT / "baselines"


def baseline_path(name: str, root: str | Path | None = None) -> Path:
    target_root = Path(root or BASELINE_ROOT).resolve()
    return target_root / f"{slugify(name)}.json"


def _source_record(result: Any) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "command": getattr(result, "command", ""),
        "output_dir": getattr(result, "output_dir", ""),
    }
    for field in ("scenario", "scenario_dir", "doctrine", "personality", "tuning", "suite_name"):
        value = getattr(result, field, None)
        if value not in (None, ""):
            record[field] = value
    if hasattr(result, "seed_policy"):
        seed_policy = getattr(result, "seed_policy")
        record["seed_policy"] = {
            "kind": getattr(seed_policy, "kind", ""),
            "seeds": list(getattr(seed_policy, "seeds", []) or []),
            "base_seed": getattr(seed_policy, "base_seed", None),
            "count": getattr(seed_policy, "count", None),
        }
    if getattr(result, "command", "") == "suite":
        record["jobs"] = [dict(job) for job in getattr(result, "jobs", []) or []]
    return record


def build_baseline_record(
    *,
    name: str,
    result: Any,
    metric_thresholds: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "bai_version": BAI_WARLAB_VERSION,
        "baseline_name": str(name),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": _source_record(result),
        "thresholds": resolve_regression_rules(metric_thresholds),
        "snapshot": build_metric_snapshot(result),
    }


def save_baseline(
    *,
    name: str,
    result: Any,
    root: str | Path | None = None,
    metric_thresholds: Mapping[str, Any] | None = None,
) -> Path:
    output = baseline_path(name, root)
    output.parent.mkdir(parents=True, exist_ok=True)
    record = build_baseline_record(name=name, result=result, metric_thresholds=metric_thresholds)
    write_json(output, record)
    return output


def load_baseline(name_or_path: str | Path, root: str | Path | None = None) -> Dict[str, Any]:
    candidate = Path(name_or_path)
    if candidate.suffix == ".json" or candidate.exists():
        path = candidate.resolve()
    else:
        path = baseline_path(str(name_or_path), root)
    return json.loads(path.read_text(encoding="utf-8"))


def compare_to_baseline(
    *,
    result: Any,
    baseline: str | Path | Mapping[str, Any],
    root: str | Path | None = None,
    metric_thresholds: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    baseline_record = dict(baseline) if isinstance(baseline, Mapping) else load_baseline(baseline, root)
    return compare_against_baseline(
        baseline_record=baseline_record,
        current_result=result,
        metric_thresholds=metric_thresholds,
    )


__all__ = [
    "BASELINE_ROOT",
    "BASELINE_SCHEMA_VERSION",
    "baseline_path",
    "build_baseline_record",
    "compare_to_baseline",
    "load_baseline",
    "save_baseline",
]
