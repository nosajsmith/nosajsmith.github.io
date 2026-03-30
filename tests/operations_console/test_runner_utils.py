from __future__ import annotations

from tools.operations_console.models import ConsoleAction, ConsoleSuite
from tools.operations_console.runner_utils import (
    finalize_result,
    make_result,
    normalize_status,
    roll_up_statuses,
    run_action,
    run_registry_entry,
    run_suite,
)


def test_normalize_status_accepts_known_values_and_defaults_unknown() -> None:
    assert normalize_status("PASS") == "pass"
    assert normalize_status(" warn ") == "warn"
    assert normalize_status("not-a-status") == "error"
    assert normalize_status(None, default="idle") == "idle"


def test_make_result_normalizes_text_lists() -> None:
    result = make_result(
        name=" Demo ",
        status="PASS",
        summary=" Ready ",
        details=["line 1", "", " line 2  "],
        errors=["", "boom"],
        duration_ms=-15,
    )

    assert result.name == "Demo"
    assert result.status == "pass"
    assert result.summary == "Ready"
    assert result.details == ["line 1", " line 2"]
    assert result.errors == ["boom"]
    assert result.duration_ms == 0


def test_finalize_result_backfills_name_summary_and_duration() -> None:
    result = finalize_result(
        make_result(name="", status="PASS", summary="", duration_ms=0),
        duration_ms=37,
        fallback_name="Fallback Action",
    )

    assert result.name == "Fallback Action"
    assert result.summary == "Completed."
    assert result.status == "pass"
    assert result.duration_ms == 37


def test_run_action_captures_logs_and_normalizes_output() -> None:
    emitted: list[str] = []
    seen = {}

    def runner(context):
        seen["scenario_name"] = context.scenario_name
        seen["scenario_input"] = context.scenario_input
        seen["bridge_uri"] = context.bridge_uri
        context.log("Checking subsystem")
        return make_result(name="", status="PASS", summary="", details=[])

    action = ConsoleAction(
        name="Utilities / Sample",
        category="Utilities",
        description="Sample action",
        runner=runner,
    )

    result = run_action(
        action,
        scenario_input="mini_gc_1942",
        bridge_uri="ws://127.0.0.1:8766",
        log_sink=emitted.append,
    )

    assert result.status == "pass"
    assert result.name == "Utilities / Sample"
    assert result.summary == "Completed."
    assert result.duration_ms >= 0
    assert result.details == emitted
    assert emitted[0] == "[Utilities] Utilities / Sample"
    assert emitted[1] == "Checking subsystem"
    assert seen == {
        "scenario_name": "mini_gc_1942",
        "scenario_input": "mini_gc_1942",
        "bridge_uri": "ws://127.0.0.1:8766",
    }


def test_run_action_wraps_unhandled_exceptions() -> None:
    def runner(context):
        context.log("Starting")
        raise RuntimeError("boom")

    action = ConsoleAction(
        name="Utilities / Crash",
        category="Utilities",
        description="Crashing action",
        runner=runner,
    )

    result = run_action(action)

    assert result.status == "error"
    assert result.summary == "Action raised an unhandled exception."
    assert result.errors == ["boom"]
    assert "Starting" in result.details
    assert "Unhandled error: boom" in result.details


def test_roll_up_statuses_obeys_error_fail_warn_precedence() -> None:
    assert roll_up_statuses(["pass", "pass"]) == "pass"
    assert roll_up_statuses(["pass", "warn"]) == "warn"
    assert roll_up_statuses(["warn", "fail"]) == "fail"
    assert roll_up_statuses(["pass", "error", "fail"]) == "error"


def test_run_suite_executes_in_order_and_passes_shared_context() -> None:
    seen: list[tuple[str, str, str]] = []

    def make_runner(label: str):
        def runner(context):
            seen.append((label, context.scenario_name, context.bridge_uri))
            context.log(f"{label} ran")
            return make_result(name=label, status="pass", summary=f"{label} ok")

        return runner

    actions = {
        "ORL / Connectivity": ConsoleAction(
            name="ORL / Connectivity",
            category="ORL",
            description="Connectivity",
            runner=make_runner("ORL / Connectivity"),
        ),
        "ORL / Scenario Integrity": ConsoleAction(
            name="ORL / Scenario Integrity",
            category="ORL",
            description="Integrity",
            runner=make_runner("ORL / Scenario Integrity"),
        ),
    }
    suite = ConsoleSuite(
        name="ORL / Smoke Suite",
        category="ORL",
        description="Smoke suite",
        action_names=["ORL / Connectivity", "ORL / Scenario Integrity"],
    )

    result = run_suite(
        suite,
        entry_lookup=actions.get,
        scenario_input="inchon_mvp",
        bridge_uri="ws://127.0.0.1:8766",
    )

    assert result.status == "pass"
    assert seen == [
        ("ORL / Connectivity", "inchon_mvp", "ws://127.0.0.1:8766"),
        ("ORL / Scenario Integrity", "inchon_mvp", "ws://127.0.0.1:8766"),
    ]
    assert "[1/2] ORL / Connectivity" in result.details
    assert "[2/2] ORL / Scenario Integrity" in result.details


def test_run_suite_rolls_up_warn_fail_and_error() -> None:
    statuses = {
        "warn-step": "warn",
        "fail-step": "fail",
        "error-step": "error",
    }

    def lookup(name: str):
        status = statuses.get(name)
        if status is None:
            return None
        return ConsoleAction(
            name=name,
            category="ORL",
            description=name,
            runner=lambda _context, status=status, name=name: make_result(name=name, status=status, summary=status),
        )

    warn_suite = ConsoleSuite(name="Warn Suite", category="ORL", description="", action_names=["warn-step"])
    fail_suite = ConsoleSuite(name="Fail Suite", category="ORL", description="", action_names=["warn-step", "fail-step"])
    error_suite = ConsoleSuite(name="Error Suite", category="ORL", description="", action_names=["fail-step", "error-step"])

    assert run_suite(warn_suite, entry_lookup=lookup).status == "warn"
    assert run_suite(fail_suite, entry_lookup=lookup).status == "fail"
    assert run_suite(error_suite, entry_lookup=lookup).status == "error"


def test_run_registry_entry_dispatches_suites() -> None:
    action = ConsoleAction(
        name="ORL / Connectivity",
        category="ORL",
        description="Connectivity",
        runner=lambda _context: make_result(name="ORL / Connectivity", status="pass", summary="ok"),
    )
    suite = ConsoleSuite(
        name="ORL / Smoke Suite",
        category="ORL",
        description="Smoke",
        action_names=["ORL / Connectivity"],
    )

    result = run_registry_entry(suite, entry_lookup=lambda name: action if name == action.name else None)

    assert result.status == "pass"
    assert result.name == "ORL / Smoke Suite"
    assert "ORL / Connectivity=PASS" in result.summary


def test_run_registry_entry_handles_nested_suites_in_order() -> None:
    seen: list[str] = []

    def make_action(name: str) -> ConsoleAction:
        return ConsoleAction(
            name=name,
            category="ORL",
            description=name,
            runner=lambda _context, name=name: seen.append(name) or make_result(name=name, status="pass", summary="ok"),
        )

    entries = {
        "ORL / Connectivity": make_action("ORL / Connectivity"),
        "ORL / Scenario Integrity": make_action("ORL / Scenario Integrity"),
        "ORL / Smoke Suite": ConsoleSuite(
            name="ORL / Smoke Suite",
            category="ORL",
            description="Smoke",
            action_names=["ORL / Connectivity", "ORL / Scenario Integrity"],
        ),
        "ORL / UI Build Check": make_action("ORL / UI Build Check"),
        "ORL / Demo Readiness": ConsoleSuite(
            name="ORL / Demo Readiness",
            category="ORL",
            description="Demo",
            action_names=["ORL / Smoke Suite", "ORL / UI Build Check"],
        ),
    }

    result = run_registry_entry(
        entries["ORL / Demo Readiness"],
        entry_lookup=entries.get,
        scenario_input="inchon_mvp",
    )

    assert result.status == "pass"
    assert seen == ["ORL / Connectivity", "ORL / Scenario Integrity", "ORL / UI Build Check"]
    assert [item.name for item in result.subresults] == ["ORL / Smoke Suite", "ORL / UI Build Check"]
