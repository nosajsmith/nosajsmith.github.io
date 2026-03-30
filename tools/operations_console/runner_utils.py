from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
from time import perf_counter
from typing import Callable, Iterable, List

from .models import ALLOWED_STATUSES, ConsoleAction, ConsoleRegistryEntry, ConsoleResult, ConsoleRunContext, ConsoleStatus, ConsoleSuite


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_status(value: object, default: ConsoleStatus = "error") -> ConsoleStatus:
    text = str(value or "").strip().lower()
    if text in ALLOWED_STATUSES:
        return text  # type: ignore[return-value]
    return default


def normalize_lines(values: Iterable[object] | None) -> List[str]:
    lines: List[str] = []
    for value in list(values or []):
        text = str(value).rstrip()
        if text:
            lines.append(text)
    return lines


def make_result(
    *,
    name: str,
    status: object,
    summary: object,
    details: Iterable[object] | None = None,
    errors: Iterable[object] | None = None,
    duration_ms: int = 0,
    started_at: str = "",
    finished_at: str = "",
    scenario_name: str = "",
    subresults: Iterable[ConsoleResult] | None = None,
    artifact_paths: Iterable[object] | None = None,
    adapter_method: str = "",
    executed_command: Iterable[object] | None = None,
    return_code: int | None = None,
) -> ConsoleResult:
    return ConsoleResult(
        name=str(name).strip() or "Unnamed Action",
        status=normalize_status(status),
        summary=str(summary).strip() or "No summary provided.",
        details=normalize_lines(details),
        errors=normalize_lines(errors),
        duration_ms=max(0, int(duration_ms or 0)),
        started_at=str(started_at or "").strip(),
        finished_at=str(finished_at or "").strip(),
        scenario_name=str(scenario_name or "").strip(),
        subresults=list(subresults or []),
        artifact_paths=normalize_lines(artifact_paths),
        adapter_method=str(adapter_method or "").strip(),
        executed_command=normalize_lines(executed_command),
        return_code=int(return_code) if return_code is not None else None,
    )


def finalize_result(
    result: ConsoleResult,
    *,
    duration_ms: int,
    fallback_name: str,
    default_status: ConsoleStatus = "pass",
    default_summary: str = "Completed.",
) -> ConsoleResult:
    name_text = str(result.name).strip()
    summary_text = str(result.summary).strip()
    name = name_text if name_text and name_text != "Unnamed Action" else fallback_name
    summary = summary_text if summary_text and summary_text != "No summary provided." else default_summary
    status = result.status if result.status in ALLOWED_STATUSES else default_status
    return replace(
        result,
        name=name,
        status=normalize_status(status, default_status),
        summary=summary,
        duration_ms=max(0, int(duration_ms or 0)),
    )


def run_action(
    action: ConsoleAction,
    *,
    scenario_input: str = "",
    bridge_uri: str = "",
    log_sink: Callable[[str], None] | None = None,
) -> ConsoleResult:
    start = perf_counter()
    started_at = utc_timestamp()
    log_lines: List[str] = []

    def emit(message: object) -> None:
        text = str(message).rstrip()
        if not text:
            return
        log_lines.append(text)
        if log_sink is not None:
            log_sink(text)

    context = ConsoleRunContext(
        action_name=action.name,
        category=action.category,
        scenario_name=str(scenario_input or "").strip(),
        bridge_uri=str(bridge_uri or "").strip(),
        log=emit,
    )
    emit(f"[{action.category}] {action.name}")

    try:
        result = action.runner(context)
        duration_ms = int((perf_counter() - start) * 1000)
        finalized = finalize_result(
            result,
            duration_ms=duration_ms,
            fallback_name=action.name,
        )
        if not finalized.details:
            finalized = replace(finalized, details=log_lines.copy())
        return replace(
            finalized,
            started_at=finalized.started_at or started_at,
            finished_at=finalized.finished_at or utc_timestamp(),
            scenario_name=finalized.scenario_name or context.scenario_name,
        )
    except Exception as exc:  # pragma: no cover - exercised in tests via wrapper result
        duration_ms = int((perf_counter() - start) * 1000)
        emit(f"Unhandled error: {exc}")
        return make_result(
            name=action.name,
            status="error",
            summary="Action raised an unhandled exception.",
            details=log_lines,
            errors=[str(exc)],
            duration_ms=duration_ms,
            started_at=started_at,
            finished_at=utc_timestamp(),
            scenario_name=context.scenario_name,
        )


def roll_up_statuses(statuses: Iterable[object]) -> ConsoleStatus:
    normalized = [normalize_status(status, "pass") for status in statuses]
    if any(status == "error" for status in normalized):
        return "error"
    if any(status == "fail" for status in normalized):
        return "fail"
    if any(status == "warn" for status in normalized):
        return "warn"
    return "pass"


def run_suite(
    suite: ConsoleSuite,
    *,
    entry_lookup: Callable[[str], ConsoleRegistryEntry | None],
    scenario_input: str = "",
    bridge_uri: str = "",
    log_sink: Callable[[str], None] | None = None,
) -> ConsoleResult:
    start = perf_counter()
    started_at = utc_timestamp()
    log_lines: List[str] = []
    step_results: List[ConsoleResult] = []

    def emit(message: object) -> None:
        text = str(message).rstrip()
        if not text:
            return
        log_lines.append(text)
        if log_sink is not None:
            log_sink(text)

    emit(f"## {suite.name}")
    total = len(suite.step_names)
    for index, step_name in enumerate(suite.step_names, start=1):
        emit(f"[{index}/{total}] {step_name}")
        entry = entry_lookup(step_name)
        if entry is None:
            result = make_result(
                name=step_name,
                status="error",
                summary="Suite step is not registered in the console.",
                errors=[f"Unknown entry: {step_name}"],
                started_at=utc_timestamp(),
                finished_at=utc_timestamp(),
                scenario_name=scenario_input,
            )
            emit(f"ERROR: {result.summary}")
        else:
            result = run_registry_entry(
                entry,
                entry_lookup=entry_lookup,
                scenario_input=scenario_input,
                bridge_uri=bridge_uri,
                log_sink=emit,
            )
            emit(f"{result.status.upper()}: {result.summary}")
        step_results.append(result)

    overall_status = roll_up_statuses(result.status for result in step_results)
    duration_ms = int((perf_counter() - start) * 1000)
    step_summary = ", ".join(f"{result.name}={result.status.upper()}" for result in step_results)
    summary = f"Suite completed with status {overall_status.upper()}."
    if step_summary:
        summary = f"{summary} {step_summary}"
    artifact_paths = [
        path
        for result in step_results
        for path in result.artifact_paths
    ]
    adapter_methods = [
        result.adapter_method
        for result in step_results
        if result.adapter_method
    ]
    return make_result(
        name=suite.name,
        status=overall_status,
        summary=summary,
        details=log_lines,
        duration_ms=duration_ms,
        started_at=started_at,
        finished_at=utc_timestamp(),
        scenario_name=scenario_input,
        subresults=step_results,
        artifact_paths=artifact_paths,
        adapter_method="suite",
        executed_command=adapter_methods,
    )


def run_registry_entry(
    entry: ConsoleRegistryEntry,
    *,
    entry_lookup: Callable[[str], ConsoleRegistryEntry | None],
    scenario_input: str = "",
    bridge_uri: str = "",
    log_sink: Callable[[str], None] | None = None,
) -> ConsoleResult:
    if isinstance(entry, ConsoleSuite):
        return run_suite(
            entry,
            entry_lookup=entry_lookup,
            scenario_input=scenario_input,
            bridge_uri=bridge_uri,
            log_sink=log_sink,
        )
    return run_action(
        entry,
        scenario_input=scenario_input,
        bridge_uri=bridge_uri,
        log_sink=log_sink,
    )
