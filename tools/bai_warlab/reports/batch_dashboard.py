from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List

from ..report_io import run_result_to_row


def dashboard_row_for_run(run: Any) -> Dict[str, Any]:
    row = run_result_to_row(run)
    return {
        "scenario": row.get("scenario"),
        "variant_id": row.get("variant_id") or row.get("variant_label"),
        "variant_name": row.get("variant_name") or row.get("variant_label"),
        "result": row.get("result"),
        "score_margin_allied": row.get("final_score_margin"),
        "pressure_peak_score": row.get("pressure_peak_score"),
        "final_pressure_score": row.get("final_pressure_score"),
        "objectives_secured": row.get("objectives_secured"),
        "objective_change_count": row.get("objective_change_count"),
        "manifest_path": row.get("manifest_path"),
        "ok": row.get("ok"),
    }


def build_batch_dashboard_payload(runs: Iterable[Any]) -> Dict[str, Any]:
    rows = [dashboard_row_for_run(run) for run in runs]
    status_counts = Counter("pass" if row.get("ok") else "fail" for row in rows)
    scenario_counts = Counter(str(row.get("scenario") or "") for row in rows if str(row.get("scenario") or "").strip())
    variant_counts = Counter(str(row.get("variant_id") or "") for row in rows if str(row.get("variant_id") or "").strip())

    score_rows = [row for row in rows if row.get("score_margin_allied") not in (None, "")]
    pressure_rows = [row for row in rows if row.get("pressure_peak_score") not in (None, "")]
    objective_rows = [row for row in rows if row.get("objective_change_count") not in (None, "")]

    notable = {
        "best_score": None,
        "highest_pressure": None,
        "most_objective_changes": None,
    }
    if score_rows:
        winner = max(score_rows, key=lambda row: float(row["score_margin_allied"]))
        notable["best_score"] = {
            "scenario": winner["scenario"],
            "variant_id": winner["variant_id"],
            "score_margin_allied": winner["score_margin_allied"],
        }
    if pressure_rows:
        peak = max(pressure_rows, key=lambda row: float(row["pressure_peak_score"]))
        notable["highest_pressure"] = {
            "scenario": peak["scenario"],
            "variant_id": peak["variant_id"],
            "pressure_peak_score": peak["pressure_peak_score"],
        }
    if objective_rows:
        changes = max(objective_rows, key=lambda row: int(row["objective_change_count"]))
        notable["most_objective_changes"] = {
            "scenario": changes["scenario"],
            "variant_id": changes["variant_id"],
            "objective_change_count": changes["objective_change_count"],
        }

    return {
        "rows": rows,
        "status_counts": dict(sorted(status_counts.items())),
        "scenario_counts": dict(sorted(scenario_counts.items())),
        "variant_counts": dict(sorted(variant_counts.items())),
        "notable": notable,
    }


def render_batch_dashboard_markdown(payload: Dict[str, Any]) -> str:
    data = dict(payload or {})
    rows = list(data.get("rows") or [])
    lines = [
        "# BAI War Lab Batch Dashboard",
        "",
        f"Rows: {len(rows)}",
        f"Statuses: {data.get('status_counts') or {}}",
        "",
        "| Scenario | Variant | Result | Score | Pressure Peak | Objectives Secured | Objective Changes |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row.get('scenario') or '-'} | "
            f"{row.get('variant_name') or row.get('variant_id') or '-'} | "
            f"{row.get('result') or '-'} | "
            f"{row.get('score_margin_allied') if row.get('score_margin_allied') is not None else '-'} | "
            f"{row.get('pressure_peak_score') if row.get('pressure_peak_score') is not None else '-'} | "
            f"{row.get('objectives_secured') if row.get('objectives_secured') is not None else '-'} | "
            f"{row.get('objective_change_count') if row.get('objective_change_count') is not None else '-'} |"
        )

    notable = dict(data.get("notable") or {})
    if notable:
        lines.extend(["", "## Notable"])
        if notable.get("best_score"):
            lines.append(f"- best score: {notable['best_score']}")
        if notable.get("highest_pressure"):
            lines.append(f"- highest pressure: {notable['highest_pressure']}")
        if notable.get("most_objective_changes"):
            lines.append(f"- most objective changes: {notable['most_objective_changes']}")
    return "\n".join(lines)


__all__ = ["build_batch_dashboard_payload", "dashboard_row_for_run", "render_batch_dashboard_markdown"]
