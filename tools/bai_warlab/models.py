from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List


def to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    return value


@dataclass
class ProfileDocument:
    kind: str
    name: str
    description: str = ""
    axis: Dict[str, Any] = field(default_factory=dict)
    run: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_path: str = ""


@dataclass
class ResolvedProfiles:
    doctrine: ProfileDocument
    personality: ProfileDocument
    tuning: ProfileDocument
    merged_axis: Dict[str, Any] = field(default_factory=dict)
    merged_run: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SeedPolicy:
    kind: str
    seeds: List[int] = field(default_factory=list)
    base_seed: int | None = None
    count: int | None = None


@dataclass
class RunRequest:
    scenario: str
    scenario_dir: str
    doctrine: str
    personality: str
    tuning: str
    seed: int
    max_steps: int | None = None
    dt_hours: int | None = None
    stop_on_terminal: bool = True
    variant_label: str = ""


@dataclass
class RunResult:
    ok: bool
    command: str
    scenario: str
    scenario_dir: str
    doctrine: str
    personality: str
    tuning: str
    seed: int
    max_steps: int
    dt_hours: int
    variant_label: str = ""
    error: str | None = None
    warnings: List[str] = field(default_factory=list)
    applied_axis: Dict[str, Any] = field(default_factory=dict)
    run_options: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    ai_report: Dict[str, Any] = field(default_factory=dict)
    output_dir: str = ""


@dataclass
class AggregateSummary:
    total_runs: int
    ok_runs: int
    failed_runs: int
    failure_count: int = 0
    partial_failures: bool = False
    status_counts: Dict[str, int] = field(default_factory=dict)
    mean_summary: Dict[str, Any] = field(default_factory=dict)
    min_summary: Dict[str, Any] = field(default_factory=dict)
    max_summary: Dict[str, Any] = field(default_factory=dict)
    mean_metrics: Dict[str, Any] = field(default_factory=dict)
    min_metrics: Dict[str, Any] = field(default_factory=dict)
    max_metrics: Dict[str, Any] = field(default_factory=dict)
    averages: Dict[str, Any] = field(default_factory=dict)
    mins: Dict[str, Any] = field(default_factory=dict)
    maxes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    ok: bool
    command: str
    scenario: str
    scenario_dir: str
    doctrine: str
    personality: str
    tuning: str
    seed_policy: SeedPolicy
    runs: List[RunResult] = field(default_factory=list)
    aggregate: AggregateSummary | None = None
    warnings: List[str] = field(default_factory=list)
    output_dir: str = ""


@dataclass
class CompareResult:
    ok: bool
    command: str
    scenario: str
    scenario_dir: str
    seed_policy: SeedPolicy
    left_label: str
    right_label: str
    left_runs: List[RunResult] = field(default_factory=list)
    right_runs: List[RunResult] = field(default_factory=list)
    comparison: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    output_dir: str = ""


@dataclass
class SuiteCase:
    id: str
    scenario: str
    scenario_dir: str
    doctrine: str
    personality: str
    tuning: str
    seed: int
    runs: int = 1
    max_steps: int = 0
    dt_hours: int = 0
    evaluation_goal: str = ""
    notes: str = ""
    metric_focus: List[str] = field(default_factory=list)
    metric_thresholds: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuiteResult:
    ok: bool
    command: str
    suite_name: str
    runs: List[RunResult] = field(default_factory=list)
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    aggregate: AggregateSummary | None = None
    suite_summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    output_dir: str = ""


@dataclass
class ManifestRecord:
    bai_version: str
    command: str
    generated_at: str
    scenario: Any
    doctrine: Any
    personality: Any
    tuning: Any
    seed_policy: Dict[str, Any]
    command_line: str
    output_dir: str
    extra: Dict[str, Any] = field(default_factory=dict)
