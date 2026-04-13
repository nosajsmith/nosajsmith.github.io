from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

from .baselines import BaselineRecord, capture_result_metrics, load_baseline_for_result
from .models import ConsoleResult


REPORT_IGNORED_FIELDS = {"started_at", "finished_at", "duration_ms", "first_divergence"}


@dataclass(frozen=True)
class FirstDivergence:
    comparable: bool
    identical: bool
    comparison_kind: str
    scenario_name: str = ""
    field_path: str = ""
    step: str = ""
    phase: str = ""
    tick: int | None = None
    artifact_paths: List[str] = field(default_factory=list)
    left_value: object = None
    right_value: object = None
    message: str = ""

    def to_report_dict(self) -> Dict[str, object]:
        return {
            "comparable": self.comparable,
            "identical": self.identical,
            "comparison_kind": self.comparison_kind,
            "scenario_name": self.scenario_name,
            "field_path": self.field_path,
            "step": self.step,
            "phase": self.phase,
            "tick": self.tick,
            "artifact_paths": list(self.artifact_paths),
            "left_value": self.left_value,
            "right_value": self.right_value,
            "message": self.message,
        }


@dataclass(frozen=True)
class ComparableSource:
    kind: str
    payload: object
    scenario_name: str = ""
    artifact_paths: List[str] = field(default_factory=list)
    label: str = ""
    result: ConsoleResult | None = None


@dataclass(frozen=True)
class RawDifference:
    field_path: str
    left_value: object
    right_value: object


def find_first_divergence(left: object, right: object) -> FirstDivergence:
    left_source = _normalize_source(left)
    right_source = _normalize_source(right)
    comparison_kind = _resolve_comparison_kind(left_source, right_source)
    artifact_paths = list(dict.fromkeys(left_source.artifact_paths + right_source.artifact_paths))
    scenario_name = left_source.scenario_name or right_source.scenario_name

    if comparison_kind == "":
        return FirstDivergence(
            comparable=False,
            identical=False,
            comparison_kind=f"{left_source.kind}:{right_source.kind}",
            scenario_name=scenario_name,
            artifact_paths=artifact_paths,
            message=f"Sources are not comparable: {left_source.kind} vs {right_source.kind}.",
        )

    if comparison_kind == "baseline_metrics":
        left_metrics = _metrics_payload(left_source)
        right_metrics = _metrics_payload(right_source)
        if left_metrics is None or right_metrics is None:
            return FirstDivergence(
                comparable=False,
                identical=False,
                comparison_kind="baseline_metrics",
                scenario_name=scenario_name,
                artifact_paths=artifact_paths,
                message="Unable to extract comparable baseline metrics.",
            )
        return _compare_metric_payloads(
            left_metrics,
            right_metrics,
            scenario_name=scenario_name,
            artifact_paths=artifact_paths,
        )

    if comparison_kind == "replay":
        return _compare_replay_payloads(
            _mapping(left_source.payload),
            _mapping(right_source.payload),
            scenario_name=scenario_name or _scenario_from_replay(_mapping(left_source.payload), _mapping(right_source.payload)),
            artifact_paths=artifact_paths,
        )

    if comparison_kind == "snapshot":
        return _compare_snapshot_payloads(
            _mapping(left_source.payload),
            _mapping(right_source.payload),
            scenario_name=scenario_name or _scenario_from_snapshot(_mapping(left_source.payload), _mapping(right_source.payload)),
            artifact_paths=artifact_paths,
        )

    return _compare_report_payloads(
        _mapping(left_source.payload),
        _mapping(right_source.payload),
        scenario_name=scenario_name or _scenario_from_report(_mapping(left_source.payload), _mapping(right_source.payload)),
        artifact_paths=artifact_paths,
    )


def compare_result_to_baseline_divergence(
    result: ConsoleResult,
    *,
    baseline_dir_path: Path | None = None,
    repo_root_path: Path | None = None,
) -> FirstDivergence:
    record = load_baseline_for_result(
        result,
        baseline_dir_path=baseline_dir_path,
        repo_root_path=repo_root_path,
    )
    artifact_paths = ([record.source_path] if record is not None and record.source_path else []) + list(result.artifact_paths)
    scenario_name = str(result.scenario_name or (record.scenario_name if record is not None else "") or "").strip()
    if record is None:
        return FirstDivergence(
            comparable=False,
            identical=False,
            comparison_kind="baseline_metrics",
            scenario_name=scenario_name,
            artifact_paths=artifact_paths,
            message="No saved baseline available for divergence compare.",
        )

    current_metrics = capture_result_metrics(
        result,
        repo_root_path=repo_root_path,
    )
    return _compare_metric_payloads(
        record.metrics,
        current_metrics,
        scenario_name=scenario_name or record.scenario_name,
        artifact_paths=artifact_paths,
    )


def find_first_divergence_in_artifact_paths(
    artifact_paths: Sequence[str | Path],
) -> FirstDivergence | None:
    candidates = [
        str(path or "").strip()
        for path in list(artifact_paths or [])
        if str(path or "").strip()
    ]
    if len(candidates) < 2:
        return None

    first_identical: FirstDivergence | None = None
    for left_index in range(len(candidates)):
        for right_index in range(left_index + 1, len(candidates)):
            try:
                divergence = find_first_divergence(candidates[left_index], candidates[right_index])
            except Exception:
                continue
            if not divergence.comparable:
                continue
            if divergence.identical:
                if first_identical is None:
                    first_identical = divergence
                continue
            return divergence
    return first_identical


def _normalize_source(source: object) -> ComparableSource:
    if isinstance(source, ComparableSource):
        return source
    if isinstance(source, ConsoleResult):
        return ComparableSource(
            kind="report",
            payload=_result_payload(source),
            scenario_name=str(source.scenario_name or "").strip(),
            artifact_paths=list(source.artifact_paths),
            label=source.name,
            result=source,
        )
    if isinstance(source, BaselineRecord):
        return ComparableSource(
            kind="baseline_metrics",
            payload=dict(source.metrics),
            scenario_name=str(source.scenario_name or "").strip(),
            artifact_paths=[source.source_path] if source.source_path else [],
            label=source.baseline_key or source.name,
        )
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.exists() and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            kind = _detect_kind(payload)
            return ComparableSource(
                kind=kind,
                payload=payload,
                scenario_name=_detect_scenario_name(kind, payload),
                artifact_paths=[str(path)],
                label=str(path),
            )
    if isinstance(source, Mapping):
        kind = _detect_kind(source)
        return ComparableSource(
            kind=kind,
            payload=dict(source),
            scenario_name=_detect_scenario_name(kind, source),
            artifact_paths=[],
            label=kind,
        )
    raise RuntimeError(f"Unsupported divergence source: {type(source).__name__}")


def _detect_kind(payload: object) -> str:
    mapping = payload if isinstance(payload, Mapping) else {}
    if not isinstance(mapping, Mapping):
        return "unknown"
    if "initial_game" in mapping and "final_units" in mapping:
        return "replay"
    if "scenario_id" in mapping and "time" in mapping and "units" in mapping and "meta" in mapping:
        return "snapshot"
    if "baseline_key" in mapping and isinstance(mapping.get("metrics"), Mapping):
        return "baseline_file"
    if "name" in mapping and "status" in mapping and "summary" in mapping:
        return "report"
    if "status" in mapping and any(key in mapping for key in ("unit_count", "artifact_presence", "selected_fields")):
        return "baseline_metrics"
    return "unknown"


def _detect_scenario_name(kind: str, payload: Mapping[str, object]) -> str:
    if kind in {"report", "baseline_file"}:
        return str(payload.get("scenario_name") or "").strip()
    if kind == "snapshot":
        return str(payload.get("scenario_id") or "").strip()
    if kind == "replay":
        return _scenario_from_replay(payload, payload)
    if kind == "baseline_metrics":
        return str(payload.get("scenario_name") or "").strip()
    return ""


def _resolve_comparison_kind(left: ComparableSource, right: ComparableSource) -> str:
    left_kind = "baseline_metrics" if left.kind == "baseline_file" else left.kind
    right_kind = "baseline_metrics" if right.kind == "baseline_file" else right.kind
    if left_kind == right_kind and left_kind in {"replay", "report", "snapshot", "baseline_metrics"}:
        return left_kind
    if {left_kind, right_kind} == {"report", "baseline_metrics"}:
        return "baseline_metrics"
    return ""


def _metrics_payload(source: ComparableSource) -> Dict[str, object] | None:
    if source.kind == "baseline_file":
        metrics = _mapping(source.payload).get("metrics")
        return dict(metrics) if isinstance(metrics, Mapping) else None
    if source.kind == "baseline_metrics":
        return dict(_mapping(source.payload))
    if source.kind == "report" and source.result is not None:
        return capture_result_metrics(source.result)
    return None


def _compare_replay_payloads(
    left: Mapping[str, object],
    right: Mapping[str, object],
    *,
    scenario_name: str,
    artifact_paths: List[str],
) -> FirstDivergence:
    left_logs = _list(left.get("logs"))
    right_logs = _list(right.get("logs"))
    for index in range(max(len(left_logs), len(right_logs))):
        if index >= len(left_logs) or index >= len(right_logs):
            left_value = left_logs[index] if index < len(left_logs) else None
            right_value = right_logs[index] if index < len(right_logs) else None
            entry = left_value if isinstance(left_value, Mapping) else right_value if isinstance(right_value, Mapping) else {}
            phase = str(entry.get("phase") or "").strip() if isinstance(entry, Mapping) else ""
            tick = _int_or_none(entry.get("turn")) if isinstance(entry, Mapping) else None
            return _difference_result(
                comparison_kind="replay",
                scenario_name=scenario_name,
                artifact_paths=artifact_paths,
                field_path=f"logs[{index}]",
                left_value=left_value,
                right_value=right_value,
                step=f"log {index + 1}",
                phase=phase,
                tick=tick,
            )
        diff = _first_difference(
            left_logs[index],
            right_logs[index],
            path=f"logs[{index}]",
            preferred_keys=("turn", "phase", "src", "message"),
        )
        if diff is not None:
            entry = left_logs[index] if isinstance(left_logs[index], Mapping) else right_logs[index]
            phase = str(entry.get("phase") or "").strip() if isinstance(entry, Mapping) else ""
            tick = _int_or_none(entry.get("turn")) if isinstance(entry, Mapping) else None
            return _difference_result(
                comparison_kind="replay",
                scenario_name=scenario_name,
                artifact_paths=artifact_paths,
                field_path=diff.field_path,
                left_value=diff.left_value,
                right_value=diff.right_value,
                step=f"log {index + 1}",
                phase=phase,
                tick=tick,
            )

    for field_name in ("initial_game", "final_game", "initial_units", "final_units"):
        diff = _first_difference(left.get(field_name), right.get(field_name), path=field_name)
        if diff is not None:
            final_game = left.get("final_game") if isinstance(left.get("final_game"), Mapping) else right.get("final_game")
            time_data = dict(final_game.get("time") or {}) if isinstance(final_game, Mapping) else {}
            return _difference_result(
                comparison_kind="replay",
                scenario_name=scenario_name,
                artifact_paths=artifact_paths,
                field_path=diff.field_path,
                left_value=diff.left_value,
                right_value=diff.right_value,
                phase=str(time_data.get("phase") or "").strip(),
                tick=_int_or_none(time_data.get("day")),
            )

    return _identical_result("replay", scenario_name, artifact_paths)


def _compare_snapshot_payloads(
    left: Mapping[str, object],
    right: Mapping[str, object],
    *,
    scenario_name: str,
    artifact_paths: List[str],
) -> FirstDivergence:
    for field_name in ("scenario_id", "time", "meta", "units"):
        diff = _first_difference(left.get(field_name), right.get(field_name), path=field_name)
        if diff is not None:
            time_data = left.get("time") if isinstance(left.get("time"), Mapping) else right.get("time")
            return _difference_result(
                comparison_kind="snapshot",
                scenario_name=scenario_name,
                artifact_paths=artifact_paths,
                field_path=diff.field_path,
                left_value=diff.left_value,
                right_value=diff.right_value,
                phase=str(time_data.get("phase") or "").strip() if isinstance(time_data, Mapping) else "",
                tick=_int_or_none(time_data.get("day")) if isinstance(time_data, Mapping) else None,
            )
    return _identical_result("snapshot", scenario_name, artifact_paths)


def _compare_report_payloads(
    left: Mapping[str, object],
    right: Mapping[str, object],
    *,
    scenario_name: str,
    artifact_paths: List[str],
) -> FirstDivergence:
    left_subresults = _list(left.get("subresults"))
    right_subresults = _list(right.get("subresults"))
    for index in range(max(len(left_subresults), len(right_subresults))):
        if index >= len(left_subresults) or index >= len(right_subresults):
            left_item = left_subresults[index] if index < len(left_subresults) else {}
            right_item = right_subresults[index] if index < len(right_subresults) else {}
            step = _subresult_name(left_item) or _subresult_name(right_item)
            return _difference_result(
                comparison_kind="report",
                scenario_name=scenario_name,
                artifact_paths=artifact_paths,
                field_path=f"subresults[{index}]",
                left_value=left_item if left_item else None,
                right_value=right_item if right_item else None,
                step=step,
            )
        diff = _compare_report_payloads(
            _mapping(left_subresults[index]),
            _mapping(right_subresults[index]),
            scenario_name=scenario_name,
            artifact_paths=artifact_paths,
        )
        if diff.comparable and not diff.identical:
            step = _subresult_name(left_subresults[index]) or _subresult_name(right_subresults[index]) or diff.step
            return FirstDivergence(
                comparable=True,
                identical=False,
                comparison_kind="report",
                scenario_name=scenario_name,
                field_path=diff.field_path,
                step=step,
                phase=diff.phase,
                tick=diff.tick,
                artifact_paths=artifact_paths,
                left_value=diff.left_value,
                right_value=diff.right_value,
                message=diff.message,
            )

    ordered_fields = (
        "scenario_name",
        "status",
        "original_status",
        "errors",
        "artifact_paths",
        "scenario_contract_evaluation",
        "baseline_drift",
        "explainability_summary",
        "details",
        "summary",
        "name",
        "adapter_method",
        "executed_command",
        "return_code",
    )
    for field_name in ordered_fields:
        diff = _first_difference(left.get(field_name), right.get(field_name), path=field_name)
        if diff is not None:
            return _difference_result(
                comparison_kind="report",
                scenario_name=scenario_name,
                artifact_paths=artifact_paths,
                field_path=diff.field_path,
                left_value=diff.left_value,
                right_value=diff.right_value,
            )

    return _identical_result("report", scenario_name, artifact_paths)


def _compare_metric_payloads(
    left: Mapping[str, object],
    right: Mapping[str, object],
    *,
    scenario_name: str,
    artifact_paths: List[str],
) -> FirstDivergence:
    ordered_fields = (
        "status",
        "scenario_name",
        "unit_count",
        "artifact_count",
        "artifact_presence",
        "selected_fields",
        "observed_fields",
        "subresult_statuses",
    )
    for field_name in ordered_fields:
        diff = _first_difference(left.get(field_name), right.get(field_name), path=field_name)
        if diff is None:
            continue
        step = ""
        if diff.field_path.startswith("subresult_statuses."):
            step = diff.field_path.partition(".")[2]
        return _difference_result(
            comparison_kind="baseline_metrics",
            scenario_name=scenario_name or str(left.get("scenario_name") or right.get("scenario_name") or "").strip(),
            artifact_paths=artifact_paths,
            field_path=diff.field_path,
            left_value=diff.left_value,
            right_value=diff.right_value,
            step=step,
        )
    return _identical_result("baseline_metrics", scenario_name, artifact_paths)


def _difference_result(
    *,
    comparison_kind: str,
    scenario_name: str,
    artifact_paths: List[str],
    field_path: str,
    left_value: object,
    right_value: object,
    step: str = "",
    phase: str = "",
    tick: int | None = None,
) -> FirstDivergence:
    location_bits: List[str] = []
    if step:
        location_bits.append(f"step={step}")
    if tick is not None:
        location_bits.append(f"tick={tick}")
    if phase:
        location_bits.append(f"phase={phase}")
    if scenario_name:
        location_bits.append(f"scenario={scenario_name}")
    location = f" ({', '.join(location_bits)})" if location_bits else ""
    return FirstDivergence(
        comparable=True,
        identical=False,
        comparison_kind=comparison_kind,
        scenario_name=scenario_name,
        field_path=field_path,
        step=step,
        phase=phase,
        tick=tick,
        artifact_paths=artifact_paths,
        left_value=left_value,
        right_value=right_value,
        message=(
            f"{field_path} diverged{location}: "
            f"{_value_preview(left_value)} -> {_value_preview(right_value)}"
        ),
    )


def _identical_result(comparison_kind: str, scenario_name: str, artifact_paths: List[str]) -> FirstDivergence:
    return FirstDivergence(
        comparable=True,
        identical=True,
        comparison_kind=comparison_kind,
        scenario_name=scenario_name,
        artifact_paths=artifact_paths,
        message="No divergence found.",
    )


def _result_payload(result: ConsoleResult) -> Dict[str, object]:
    return {
        "name": result.name,
        "status": result.status,
        "original_status": result.original_status,
        "summary": result.summary,
        "scenario_name": result.scenario_name,
        "details": list(result.details),
        "errors": list(result.errors),
        "artifact_paths": list(result.artifact_paths),
        "adapter_method": result.adapter_method,
        "executed_command": list(result.executed_command),
        "return_code": result.return_code,
        "subresults": [_result_payload(item) for item in result.subresults],
    }


def _first_difference(
    left: object,
    right: object,
    *,
    path: str,
    preferred_keys: Sequence[str] = (),
) -> RawDifference | None:
    if left == right:
        return None
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        keys = _ordered_keys(set(left) | set(right), preferred=preferred_keys)
        for key in keys:
            if path == "" and str(key) in REPORT_IGNORED_FIELDS:
                continue
            if key not in left or key not in right:
                return RawDifference(
                    field_path=_join_path(path, str(key)),
                    left_value=left.get(key),
                    right_value=right.get(key),
                )
            diff = _first_difference(left.get(key), right.get(key), path=_join_path(path, str(key)))
            if diff is not None:
                return diff
        return None
    if isinstance(left, list) and isinstance(right, list):
        for index in range(max(len(left), len(right))):
            item_path = f"{path}[{index}]"
            if index >= len(left) or index >= len(right):
                return RawDifference(
                    field_path=item_path,
                    left_value=left[index] if index < len(left) else None,
                    right_value=right[index] if index < len(right) else None,
                )
            diff = _first_difference(left[index], right[index], path=item_path)
            if diff is not None:
                return diff
        return None
    return RawDifference(field_path=path, left_value=left, right_value=right)


def _ordered_keys(keys: Sequence[object] | set[object], *, preferred: Sequence[str] = ()) -> List[str]:
    values = [str(key) for key in keys]
    prioritized = [key for key in preferred if key in values]
    remainder = sorted(key for key in values if key not in prioritized)
    return prioritized + remainder


def _join_path(path: str, key: str) -> str:
    if not path:
        return key
    if key.startswith("["):
        return f"{path}{key}"
    return f"{path}.{key}"


def _mapping(value: object) -> Dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: object) -> List[object]:
    return list(value) if isinstance(value, list) else []


def _scenario_from_replay(left: Mapping[str, object], right: Mapping[str, object]) -> str:
    for payload in (left, right):
        for key in ("initial_game", "final_game"):
            game = payload.get(key)
            if isinstance(game, Mapping):
                scenario = str(game.get("scenario") or "").strip()
                if scenario:
                    return scenario
    return ""


def _scenario_from_snapshot(left: Mapping[str, object], right: Mapping[str, object]) -> str:
    return str(left.get("scenario_id") or right.get("scenario_id") or "").strip()


def _scenario_from_report(left: Mapping[str, object], right: Mapping[str, object]) -> str:
    return str(left.get("scenario_name") or right.get("scenario_name") or "").strip()


def _subresult_name(value: object) -> str:
    if not isinstance(value, Mapping):
        return ""
    return str(value.get("name") or "").strip()


def _int_or_none(value: object) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _value_preview(value: object) -> str:
    if isinstance(value, str):
        return repr(value if len(value) <= 80 else value[:77] + "...")
    if isinstance(value, (int, float, bool)) or value is None:
        return repr(value)
    if isinstance(value, Mapping):
        return "{...}"
    if isinstance(value, list):
        return "[...]"
    return repr(value)
