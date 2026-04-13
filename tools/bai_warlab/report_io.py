from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median, pstdev
from typing import Any, Dict, Iterable, List

from . import ARTIFACT_ROOT
from .models import to_plain


RESULTS_CSV_COLUMNS = [
    "command",
    "scenario",
    "scenario_dir",
    "doctrine",
    "personality",
    "tuning",
    "seed",
    "variant_label",
    "variant_id",
    "variant_name",
    "ai_side",
    "result",
    "scenario_outcome",
    "winning_side",
    "vp_margin",
    "final_score_allied",
    "final_score_axis",
    "final_score_margin",
    "pressure_peak_score",
    "final_pressure_score",
    "objective_change_count",
    "objectives_secured",
    "allied_casualties",
    "axis_casualties",
    "casualty_ratio",
    "objective_hold_duration",
    "line_collapse_rate",
    "low_supply_turns",
    "manifest_path",
    "failure_flag",
    "failure_message",
    "ok",
    "terminal_status",
    "execution_status",
    "steps_completed",
    "hours_elapsed",
]

CORE_METRIC_COLUMNS = [
    ("vp_margin", "VP Margin"),
    ("allied_casualties", "Allied Casualties"),
    ("axis_casualties", "Axis Casualties"),
    ("casualty_ratio", "Casualty Ratio"),
    ("objective_hold_duration", "Objective Hold Duration"),
    ("line_collapse_rate", "Line Collapse Rate"),
    ("low_supply_turns", "Low Supply Turns"),
    ("hours_elapsed", "Tempo (Hours Elapsed)"),
]


def slugify(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or ""))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "default"


def stable_hash(parts: Iterable[Any]) -> str:
    joined = "|".join(str(part) for part in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:10]


def default_output_dir(command: str, label_parts: Iterable[Any], override: str | None = None) -> Path:
    if override:
        return Path(override).resolve()
    parts = [slugify(str(part)) for part in label_parts if str(part).strip()]
    return (ARTIFACT_ROOT / slugify(command)).joinpath(*parts).resolve()


def ensure_output_dir(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def write_json(path: str | Path, payload: Any) -> Path:
    output = Path(path)
    output.write_text(json.dumps(to_plain(payload), indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return output


def _scalar_csv_value(value: Any) -> str | int | float | bool:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return json.dumps(to_plain(value), sort_keys=True)


def flatten_mapping(mapping: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for key, value in mapping.items():
        field = f"{prefix}_{key}" if prefix else str(key)
        if isinstance(value, dict):
            row.update(flatten_mapping(value, field))
        else:
            row[field] = _scalar_csv_value(value)
    return row


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except Exception:
        return None


def _round_metric(value: float) -> float:
    return round(float(value), 3)


def _result_score(value: Any) -> float | None:
    normalized = str(value or "").strip().lower()
    if normalized == "win":
        return 1.0
    if normalized == "draw":
        return 0.5
    if normalized == "loss":
        return 0.0
    return None


def _normalized_token(value: Any, *, default: str = "unknown", uppercase: bool = False) -> str:
    token = str(value or "").strip()
    if not token:
        token = default
    return token.upper() if uppercase else token.lower()


def _winning_side_token(row: Dict[str, Any]) -> str:
    raw = str(row.get("winning_side") or "").strip().upper()
    if raw:
        return raw
    if _normalized_token(row.get("result")) == "draw" or _normalized_token(row.get("scenario_outcome")) == "draw":
        return "DRAW"
    return "UNKNOWN"


def summarize_core_metric_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    summary: Dict[str, Dict[str, Any]] = {}
    row_list = list(rows)
    for key, label in CORE_METRIC_COLUMNS:
        values = [_coerce_float(row.get(key)) for row in row_list]
        numeric = [value for value in values if value is not None]
        if not numeric:
            continue
        summary[key] = {
            "label": label,
            "count": len(numeric),
            "mean": _round_metric(sum(numeric) / len(numeric)),
            "median": _round_metric(median(numeric)),
            "min": _round_metric(min(numeric)),
            "max": _round_metric(max(numeric)),
            "spread": _round_metric(max(numeric) - min(numeric)),
            "stddev": _round_metric(pstdev(numeric)) if len(numeric) > 1 else 0.0,
        }
    return summary


def summarize_outcome_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    row_list = list(rows)
    if not row_list:
        return {
            "available": False,
            "sample_count": 0,
            "ai_side_counts": {},
            "result_counts": {},
            "scenario_outcome_counts": {},
            "winning_side_counts": {},
            "win_rate": 0.0,
            "loss_rate": 0.0,
            "draw_rate": 0.0,
            "non_loss_rate": 0.0,
            "mean_result_score": None,
        }

    ai_side_counts = Counter(_normalized_token(row.get("ai_side"), default="unknown", uppercase=True) for row in row_list)
    result_counts = Counter(_normalized_token(row.get("result")) for row in row_list)
    scenario_outcome_counts = Counter(_normalized_token(row.get("scenario_outcome")) for row in row_list)
    winning_side_counts = Counter(_winning_side_token(row) for row in row_list)
    result_scores = [_result_score(row.get("result")) for row in row_list]
    numeric_result_scores = [value for value in result_scores if value is not None]
    sample_count = len(row_list)

    return {
        "available": True,
        "sample_count": sample_count,
        "ai_side_counts": dict(sorted(ai_side_counts.items())),
        "result_counts": dict(sorted(result_counts.items())),
        "scenario_outcome_counts": dict(sorted(scenario_outcome_counts.items())),
        "winning_side_counts": dict(sorted(winning_side_counts.items())),
        "win_rate": _round_metric(result_counts.get("win", 0) / sample_count),
        "loss_rate": _round_metric(result_counts.get("loss", 0) / sample_count),
        "draw_rate": _round_metric(result_counts.get("draw", 0) / sample_count),
        "non_loss_rate": _round_metric((result_counts.get("win", 0) + result_counts.get("draw", 0)) / sample_count),
        "mean_result_score": _round_metric(sum(numeric_result_scores) / len(numeric_result_scores))
        if numeric_result_scores
        else None,
    }


def _metric_block(run_result: Any, name: str) -> Dict[str, Any]:
    return dict((getattr(run_result, "metrics", {}) or {}).get(name, {}) or {})


def _summary_block(run_result: Any) -> Dict[str, Any]:
    return dict(getattr(run_result, "summary", {}) or {})


def _perspective_side(run_result: Any) -> str:
    summary = _summary_block(run_result)
    raw = str(summary.get("ai_side") or "").strip().upper()
    return raw if raw in {"ALLIED", "AXIS"} else "ALLIED"


def _perspective_metric(block: Dict[str, Any], prefix: str, side: str) -> Any:
    key = f"{prefix}_{side.lower()}"
    return block.get(key)


def _result_value(run_result: Any, side: str) -> Any:
    summary = _summary_block(run_result)
    outcome = _metric_block(run_result, "outcome")
    return (
        outcome.get(f"win_loss_draw_{side.lower()}")
        or summary.get("result")
        or outcome.get("scenario_outcome")
        or summary.get("scenario_outcome")
        or ""
    )


def _failure_message(run_result: Any) -> str:
    if getattr(run_result, "ok", False):
        return ""
    summary = _summary_block(run_result)
    return str(getattr(run_result, "error", "") or summary.get("terminal_status") or "run_failed")


def run_result_to_row(run_result: Any) -> Dict[str, Any]:
    side = _perspective_side(run_result)
    summary = _summary_block(run_result)
    outcome = _metric_block(run_result, "outcome")
    behavior = _metric_block(run_result, "behavior")
    logistics = _metric_block(run_result, "logistics")
    score_visibility = _metric_block(run_result, "score_visibility")
    pressure_visibility = _metric_block(run_result, "pressure_visibility")
    objective_visibility = _metric_block(run_result, "objective_visibility")
    score_final = dict(score_visibility.get("final") or {})
    pressure_peak = dict(pressure_visibility.get("peak") or {})
    pressure_final = dict(pressure_visibility.get("final") or {})
    objective_final = dict(objective_visibility.get("final") or {})
    row = {
        "command": getattr(run_result, "command", "run"),
        "scenario": getattr(run_result, "scenario", ""),
        "scenario_dir": getattr(run_result, "scenario_dir", ""),
        "doctrine": getattr(run_result, "doctrine", ""),
        "personality": getattr(run_result, "personality", ""),
        "tuning": getattr(run_result, "tuning", ""),
        "seed": getattr(run_result, "seed", ""),
        "variant_label": getattr(run_result, "variant_label", ""),
        "variant_id": getattr(run_result, "variant_id", "") or dict(getattr(run_result, "resolved_profile", {}) or {}).get("variant_id", ""),
        "variant_name": getattr(run_result, "variant_name", "") or dict(getattr(run_result, "resolved_profile", {}) or {}).get("variant_name", ""),
        "ai_side": side,
        "result": _result_value(run_result, side),
        "scenario_outcome": summary.get("scenario_outcome") or outcome.get("scenario_outcome") or "",
        "winning_side": summary.get("winning_side") or outcome.get("winning_side") or "",
        "vp_margin": _perspective_metric(outcome, "vp_margin", side),
        "final_score_allied": score_final.get("score_allied"),
        "final_score_axis": score_final.get("score_axis"),
        "final_score_margin": score_final.get("score_margin_allied"),
        "pressure_peak_score": pressure_peak.get("pressure_score"),
        "final_pressure_score": pressure_final.get("pressure_score"),
        "objective_change_count": len(list(objective_visibility.get("changes") or [])),
        "objectives_secured": objective_final.get("allied_controlled") if side == "ALLIED" else objective_final.get("axis_controlled"),
        "allied_casualties": behavior.get("allied_casualties"),
        "axis_casualties": behavior.get("axis_casualties"),
        "casualty_ratio": _perspective_metric(behavior, "casualty_ratio", side),
        "objective_hold_duration": _perspective_metric(behavior, "objective_hold_turns", side),
        "line_collapse_rate": _perspective_metric(behavior, "line_collapse_rate", side),
        "low_supply_turns": _perspective_metric(logistics, "low_supply_turns", side),
        "manifest_path": getattr(run_result, "manifest_path", ""),
        "failure_flag": not bool(getattr(run_result, "ok", False)),
        "failure_message": _failure_message(run_result),
        "ok": bool(getattr(run_result, "ok", False)),
        "terminal_status": summary.get("terminal_status", ""),
        "execution_status": summary.get("execution_status", ""),
        "steps_completed": summary.get("steps_completed"),
        "hours_elapsed": summary.get("hours_elapsed"),
    }
    row.update(flatten_mapping(summary, "summary"))
    row.update(flatten_mapping(dict(getattr(run_result, "metrics", {}) or {}), "metrics"))
    row.update(flatten_mapping(dict(getattr(run_result, "ai_report", {}) or {}), "ai_report"))
    row.update(flatten_mapping(dict(getattr(run_result, "resolved_profile", {}) or {}), "resolved_profile"))
    return row


def write_results_csv(path: str | Path, rows: List[Dict[str, Any]]) -> Path:
    output = Path(path)
    fieldnames: List[str] = list(RESULTS_CSV_COLUMNS)
    for row in rows:
        for key in row.keys():
            if key not in fieldnames:
                fieldnames.append(key)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _scalar_csv_value(row.get(key)) for key in fieldnames})
    return output


__all__ = [
    "CORE_METRIC_COLUMNS",
    "RESULTS_CSV_COLUMNS",
    "default_output_dir",
    "ensure_output_dir",
    "flatten_mapping",
    "run_result_to_row",
    "slugify",
    "stable_hash",
    "summarize_core_metric_rows",
    "summarize_outcome_rows",
    "write_json",
    "write_report_txt",
    "write_results_csv",
]


def write_report_txt(path: str | Path, content: str) -> Path:
    output = Path(path)
    output.write_text(content.rstrip() + "\n", encoding="utf-8")
    return output
