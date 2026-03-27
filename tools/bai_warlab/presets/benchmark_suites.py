from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .. import CONFIG_ROOT
from ..models import SuiteCase


SUITE_CONFIG_ROOT = CONFIG_ROOT / "suites"


def _suite_path(name_or_path: str) -> Path:
    candidate = Path(name_or_path)
    if candidate.suffix in {".yaml", ".yml"} and candidate.exists():
        return candidate.resolve()

    for suffix in (".yaml", ".yml"):
        resolved = (SUITE_CONFIG_ROOT / f"{name_or_path}{suffix}").resolve()
        if resolved.exists():
            return resolved
    raise KeyError(f"Unknown War Lab suite: {name_or_path}")


def _suite_case(payload: Dict[str, Any], defaults: Dict[str, Any]) -> SuiteCase:
    merged = dict(defaults)
    merged.update(dict(payload))
    required = ["id", "scenario", "doctrine", "personality", "tuning", "seed"]
    missing = [field for field in required if merged.get(field) in (None, "")]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Suite job is missing required fields: {missing_text}")
    return SuiteCase(
        id=str(merged["id"]),
        scenario=str(merged["scenario"]),
        scenario_dir=str(merged.get("scenario_dir") or "scenarios"),
        doctrine=str(merged["doctrine"]),
        personality=str(merged["personality"]),
        tuning=str(merged["tuning"]),
        seed=int(merged["seed"]),
        runs=int(merged.get("runs") or 1),
        max_steps=int(merged.get("max_steps") or 0),
        dt_hours=int(merged.get("dt_hours") or 0),
        evaluation_goal=str(merged.get("evaluation_goal") or ""),
        notes=str(merged.get("notes") or ""),
        metric_focus=[str(item) for item in list(merged.get("metric_focus") or [])],
        metric_thresholds={str(key): value for key, value in dict(merged.get("metric_thresholds") or merged.get("thresholds") or {}).items()},
    )


def load_benchmark_suite_definition(name: str) -> Dict[str, Any]:
    path = _suite_path(name)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Suite config at {path} must load as a mapping")

    defaults = dict(payload.get("defaults") or {})
    jobs_payload = list(payload.get("jobs") or [])
    if not jobs_payload:
        raise ValueError(f"Suite config at {path} must define at least one job")

    cases = [_suite_case(dict(job), defaults) for job in jobs_payload]
    return {
        "name": str(payload.get("name") or path.stem),
        "description": str(payload.get("description") or ""),
        "evaluation_notes": [str(note) for note in list(payload.get("evaluation_notes") or [])],
        "source_path": str(path),
        "cases": cases,
    }


def list_suite_names() -> List[str]:
    names = {
        path.stem
        for path in SUITE_CONFIG_ROOT.glob("*.y*ml")
        if path.is_file()
    }
    return sorted(names)


def load_benchmark_suite(name: str) -> List[SuiteCase]:
    return deepcopy(load_benchmark_suite_definition(name)["cases"])


BENCHMARK_SUITES: Dict[str, List[SuiteCase]] = {
    name: load_benchmark_suite(name)
    for name in list_suite_names()
}


__all__ = [
    "BENCHMARK_SUITES",
    "SUITE_CONFIG_ROOT",
    "list_suite_names",
    "load_benchmark_suite",
    "load_benchmark_suite_definition",
]
