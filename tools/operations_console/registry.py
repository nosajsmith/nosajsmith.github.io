from __future__ import annotations

import asyncio
import json
import subprocess
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List

from engine.testing_api import EngineTestingAPI, TestingApiResult
from .models import ConsoleAction, ConsoleRegistryEntry, ConsoleRunContext, ConsoleSuite
from .runner_utils import make_result


DEFAULT_BRIDGE_URI = "ws://127.0.0.1:8766"
DEFAULT_CATEGORIES: tuple[str, ...] = ("ORL", "War Lab", "Utilities", "Content")


class ActionRegistry:
    def __init__(self, categories: Iterable[str] | None = None):
        self._category_order: List[str] = []
        self._entries: "OrderedDict[str, ConsoleRegistryEntry]" = OrderedDict()
        for category in categories or DEFAULT_CATEGORIES:
            self._add_category(category)

    def _add_category(self, category: str) -> None:
        text = str(category or "").strip()
        if text and text not in self._category_order:
            self._category_order.append(text)

    def register(self, entry: ConsoleRegistryEntry) -> ConsoleRegistryEntry:
        name = str(entry.name or "").strip()
        if not name:
            raise ValueError("Action name is required.")
        if name in self._entries:
            raise ValueError(f"Entry already registered: {name}")
        self._add_category(entry.category)
        self._entries[name] = entry
        return entry

    def list_entries(self) -> List[ConsoleRegistryEntry]:
        return list(self._entries.values())

    def list_actions(self) -> List[ConsoleAction]:
        return [entry for entry in self._entries.values() if isinstance(entry, ConsoleAction)]

    def list_suites(self) -> List[ConsoleSuite]:
        return [entry for entry in self._entries.values() if isinstance(entry, ConsoleSuite)]

    def categories(self) -> List[str]:
        return list(self._category_order)

    def get(self, name: str) -> ConsoleRegistryEntry | None:
        return self._entries.get(str(name or "").strip())

    def get_action(self, name: str) -> ConsoleAction | None:
        entry = self.get(name)
        return entry if isinstance(entry, ConsoleAction) else None

    def get_suite(self, name: str) -> ConsoleSuite | None:
        entry = self.get(name)
        return entry if isinstance(entry, ConsoleSuite) else None

    def actions_by_category(self) -> Dict[str, List[ConsoleAction]]:
        grouped: Dict[str, List[ConsoleAction]] = {category: [] for category in self._category_order}
        for action in self.list_actions():
            grouped.setdefault(action.category, []).append(action)
        return grouped

    def entries_by_category(self) -> Dict[str, List[ConsoleRegistryEntry]]:
        grouped: Dict[str, List[ConsoleRegistryEntry]] = {category: [] for category in self._category_order}
        for entry in self._entries.values():
            grouped.setdefault(entry.category, []).append(entry)
        return grouped


def _placeholder_runner(label: str):
    def runner(context: ConsoleRunContext):
        context.log(f"{label} is not integrated in this tranche.")
        return make_result(
            name=context.action_name,
            status="warn",
            summary=f"{label} is not wired into the console yet.",
        )

    return runner


def _console_result_from_adapter(
    context: ConsoleRunContext,
    result: TestingApiResult,
    *,
    success_summary: str,
    failure_summary: str,
) -> object:
    if result.adapter_method:
        context.log(f"using adapter: {result.adapter_method}")
    if result.executed_command:
        context.log(f"command: {' '.join(result.executed_command)}")
    for line in result.logs:
        context.log(line)

    status = "pass" if result.ok else ("fail" if result.error else "warn")
    errors = [result.error] if result.error else []
    summary = success_summary if result.ok else failure_summary
    if not result.ok and result.error:
        summary = f"{failure_summary} {result.error}"

    return make_result(
        name=context.action_name,
        status=status,
        summary=summary,
        errors=errors,
        artifact_paths=result.artifacts,
        scenario_name=context.scenario_name,
        adapter_method=result.adapter_method,
        executed_command=result.executed_command,
        return_code=result.return_code,
    )


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_ui_directory() -> Path:
    return repo_root() / "ui"


def resolve_target_scenario(scenarios: Iterable[object], requested: str = "") -> str | None:
    available = [str(value or "").strip() for value in scenarios if str(value or "").strip()]
    if not available:
        return None

    requested_text = str(requested or "").strip()
    if not requested_text:
        return available[0]

    requested_lower = requested_text.lower()
    requested_json = requested_lower if requested_lower.endswith(".json") else f"{requested_lower}.json"
    for candidate in available:
        candidate_lower = candidate.lower()
        candidate_stem = candidate_lower[:-5] if candidate_lower.endswith(".json") else candidate_lower
        if candidate_lower in {requested_lower, requested_json}:
            return candidate
        if candidate_stem == requested_lower:
            return candidate
    return None


def _unit_has_basic_fields(unit: object) -> bool:
    if not isinstance(unit, dict):
        return False
    has_identity = any(str(unit.get(key) or "").strip() for key in ("id", "unit_id", "name"))
    position = unit.get("position")
    has_position = isinstance(position, (list, tuple)) and len(position) >= 2
    has_xy = isinstance(unit.get("x"), (int, float)) and isinstance(unit.get("y"), (int, float))
    has_location = any(str(unit.get(key) or "").strip() for key in ("location_id", "hex_id", "area_id"))
    return has_identity and (has_position or has_xy or has_location)


def validate_loaded_scenario_payload(load_data: dict) -> dict:
    if not isinstance(load_data, dict):
        raise RuntimeError("load_scenario returned malformed data.")

    scenario = load_data.get("scenario")
    if not isinstance(scenario, dict):
        raise RuntimeError("Loaded scenario payload is missing a scenario object.")

    scenario_id = str(scenario.get("id") or load_data.get("id") or "").strip()
    scenario_name = str(scenario.get("name") or load_data.get("name") or scenario_id).strip()
    if not scenario_id and not scenario_name:
        raise RuntimeError("Loaded scenario is missing a readable identifier.")

    units = scenario.get("units")
    if not isinstance(units, list):
        raise RuntimeError("Loaded scenario is missing a units collection.")
    unit_count = len(units)
    if unit_count <= 0:
        raise RuntimeError("Loaded scenario contains zero units.")

    valid_unit_count = sum(1 for unit in units if _unit_has_basic_fields(unit))
    if valid_unit_count <= 0:
        raise RuntimeError("Loaded scenario does not expose any unit with identity and position/location fields.")

    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario_name or scenario_id,
        "unit_count": unit_count,
        "valid_unit_count": valid_unit_count,
    }


async def _send_rpc(ws, cmd: str, args: dict | None = None) -> dict:
    payload = {
        "id": f"operations-console-{uuid.uuid4()}",
        "proto": "1.0",
        "cmd": cmd,
        "args": args or {},
    }
    await ws.send(json.dumps(payload))
    raw = await ws.recv()
    response = json.loads(raw)
    if not isinstance(response, dict):
        raise RuntimeError(f"Bridge returned a non-object response for {cmd}.")
    return response


async def _run_connectivity_check(uri: str) -> list:
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python package 'websockets' is required for ORL connectivity checks.") from exc

    async with websockets.connect(uri) as ws:
        ping_data = _ok_data(await _send_rpc(ws, "ping"), "ping")
        scenarios_data = _ok_data(await _send_rpc(ws, "list_scenarios"), "list_scenarios")
    if not bool(ping_data.get("pong")):
        raise RuntimeError("ping returned ok status without pong=true.")
    scenarios = scenarios_data.get("scenarios") if isinstance(scenarios_data.get("scenarios"), list) else []
    return scenarios


async def _run_scenario_integrity_check(uri: str, requested_scenario: str = "") -> dict:
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python package 'websockets' is required for ORL scenario integrity checks.") from exc

    async with websockets.connect(uri) as ws:
        ping_data = _ok_data(await _send_rpc(ws, "ping"), "ping")
        if not bool(ping_data.get("pong")):
            raise RuntimeError("ping returned ok status without pong=true.")

        list_data = _ok_data(await _send_rpc(ws, "list_scenarios"), "list_scenarios")
        scenarios = list_data.get("scenarios") if isinstance(list_data.get("scenarios"), list) else []
        selected_scenario = resolve_target_scenario(scenarios, requested_scenario)
        if selected_scenario is None:
            if scenarios:
                raise RuntimeError(f"Scenario not found in live roster: {requested_scenario}")
            raise RuntimeError("Bridge reachable, but scenario roster is empty.")

        load_data = _ok_data(await _send_rpc(ws, "load_scenario", {"name": selected_scenario}), "load_scenario")
        validated = validate_loaded_scenario_payload(load_data)

    return {
        "scenario_count": len(scenarios),
        "selected_scenario": selected_scenario,
        "requested_scenario": str(requested_scenario or "").strip(),
        **validated,
    }


def _ok_data(response: dict, cmd: str) -> dict:
    status = str(response.get("status") or "").strip().lower()
    if status != "ok":
        code = str(response.get("code") or "bridge_error").strip()
        message = str(response.get("msg") or f"{cmd} failed.").strip()
        raise RuntimeError(f"{cmd} failed [{code}]: {message}")
    data = response.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"{cmd} returned malformed data.")
    return data


def run_orl_connectivity(context: ConsoleRunContext):
    uri = context.bridge_uri or DEFAULT_BRIDGE_URI

    context.log(f"Connecting to bridge at {uri}")
    try:
        scenarios = asyncio.run(_run_connectivity_check(uri))
        context.log("Ping OK: pong=True")
        context.log(f"Scenario roster received: {len(scenarios)} item(s)")
        for index, value in enumerate(scenarios[:10], start=1):
            context.log(f"  {index}. {value}")
        if len(scenarios) > 10:
            context.log(f"  ... and {len(scenarios) - 10} more")
    except RuntimeError as exc:
        context.log(str(exc))
        return make_result(
            name=context.action_name,
            status="fail",
            summary="Bridge connectivity check failed.",
            errors=[str(exc)],
        )
    except (OSError, asyncio.TimeoutError) as exc:
        context.log(f"Bridge unavailable: {exc}")
        return make_result(
            name=context.action_name,
            status="fail",
            summary="Bridge connectivity check failed.",
            errors=[str(exc)],
        )
    except Exception as exc:  # pragma: no cover - environment/socket failures are non-deterministic
        context.log(f"Bridge connection error: {exc}")
        return make_result(
            name=context.action_name,
            status="error",
            summary="Bridge connectivity check hit an unexpected error.",
            errors=[str(exc)],
        )

    if not scenarios:
        return make_result(
            name=context.action_name,
            status="warn",
            summary="Bridge reachable, but scenario roster is empty.",
        )
    return make_result(
        name=context.action_name,
        status="pass",
        summary=f"Bridge reachable. {len(scenarios)} scenario(s) available.",
    )


def run_orl_scenario_integrity(context: ConsoleRunContext):
    uri = context.bridge_uri or DEFAULT_BRIDGE_URI
    requested_scenario = context.scenario_name

    context.log(f"Connecting to bridge at {uri}")
    if requested_scenario:
        context.log(f"Requested scenario: {requested_scenario}")
    else:
        context.log("No scenario specified; defaulting to the first live roster entry.")

    try:
        result = asyncio.run(_run_scenario_integrity_check(uri, requested_scenario))
        context.log("Connected to bridge and received pong.")
        context.log(f"Listed {result['scenario_count']} scenario(s)")
        context.log(f"Selected scenario: {result['selected_scenario']}")
        context.log(
            f"Loaded scenario successfully: {result['scenario_name']} "
            f"({result['scenario_id'] or result['selected_scenario']})"
        )
        context.log(
            f"Validated units: {result['unit_count']} total, "
            f"{result['valid_unit_count']} with basic identity/location fields"
        )
    except RuntimeError as exc:
        context.log(str(exc))
        return make_result(
            name=context.action_name,
            status="fail",
            summary="Scenario integrity check failed.",
            errors=[str(exc)],
        )
    except (OSError, asyncio.TimeoutError) as exc:
        context.log(f"Bridge unavailable: {exc}")
        return make_result(
            name=context.action_name,
            status="fail",
            summary="Scenario integrity check failed.",
            errors=[str(exc)],
        )
    except Exception as exc:  # pragma: no cover - environment/socket failures are non-deterministic
        context.log(f"Bridge connection error: {exc}")
        return make_result(
            name=context.action_name,
            status="error",
            summary="Scenario integrity check hit an unexpected error.",
            errors=[str(exc)],
        )

    return make_result(
        name=context.action_name,
        status="pass",
        summary=(
            f"Scenario integrity passed for {result['scenario_name']} "
            f"with {result['unit_count']} unit(s)."
        ),
    )


def list_live_scenarios(uri: str = DEFAULT_BRIDGE_URI) -> List[str]:
    return asyncio.run(_run_connectivity_check(uri or DEFAULT_BRIDGE_URI))


def build_default_registry() -> ActionRegistry:
    registry = ActionRegistry()
    registry.register(
        ConsoleAction(
            name="ORL / Connectivity",
            category="ORL",
            description="Ping the bridge and fetch the live scenario roster from ws://127.0.0.1:8766.",
            runner=run_orl_connectivity,
        )
    )
    registry.register(
        ConsoleAction(
            name="ORL / Scenario Integrity",
            category="ORL",
            description="Resolve a scenario from the live bridge, load it, and validate the minimum authored structure.",
            runner=run_orl_scenario_integrity,
        )
    )
    registry.register(
        ConsoleSuite(
            name="ORL / Smoke Suite",
            category="ORL",
            description="Run the ORL connectivity and scenario-integrity checks in sequence for a quick readiness answer.",
            action_names=[
                "ORL / Connectivity",
                "ORL / Scenario Integrity",
            ],
        )
    )
    registry.register(
        ConsoleAction(
            name="ORL / UI Build Check",
            category="ORL",
            description="Validate the UI build command and confirm the expected build artifact is produced.",
            runner=run_orl_ui_build_check,
        )
    )
    registry.register(
        ConsoleSuite(
            name="ORL / Demo Readiness",
            category="ORL",
            description="Run the smoke suite and UI build check to produce a simple demo-readiness answer.",
            action_names=[
                "ORL / Smoke Suite",
                "ORL / UI Build Check",
            ],
        )
    )
    registry.register(
        ConsoleAction(
            name="ORL / Replay Validation",
            category="ORL",
            description="Run deterministic replay export/compare validation through the internal engine testing adapter.",
            runner=run_orl_replay_validation,
        )
    )
    registry.register(
        ConsoleAction(
            name="ORL / Snapshot Smoke",
            category="ORL",
            description="Run save/load snapshot smoke validation through the internal engine testing adapter.",
            runner=run_orl_snapshot_smoke,
        )
    )
    registry.register(
        ConsoleAction(
            name="ORL / All-Green Check",
            category="ORL",
            description="Run the repo all-green validation hook through the internal engine testing adapter.",
            runner=run_orl_all_green_check,
        )
    )
    registry.register(
        ConsoleSuite(
            name="ORL / Core Validation Suite",
            category="ORL",
            description="Run smoke, replay, snapshot, and all-green validation in one ordered internal QA bundle.",
            action_names=[
                "ORL / Smoke Suite",
                "ORL / Replay Validation",
                "ORL / Snapshot Smoke",
                "ORL / All-Green Check",
            ],
        )
    )
    registry.register(
        ConsoleAction(
            name="War Lab / Coming Soon",
            category="War Lab",
            description="Reserved slot for future War Lab hooks.",
            runner=_placeholder_runner("War Lab"),
        )
    )
    registry.register(
        ConsoleAction(
            name="Utilities / Coming Soon",
            category="Utilities",
            description="Reserved slot for future utility actions.",
            runner=_placeholder_runner("Utilities"),
        )
    )
    registry.register(
        ConsoleAction(
            name="Content / Coming Soon",
            category="Content",
            description="Reserved slot for future content validation actions.",
            runner=_placeholder_runner("Content"),
        )
    )
    return registry


def run_orl_ui_build_check(context: ConsoleRunContext):
    ui_dir = resolve_ui_directory()
    package_json_path = ui_dir / "package.json"
    build_artifact_path = ui_dir / "dist" / "index.html"
    command = ["npm", "run", "build"]

    context.log(f"Inspecting UI directory: {ui_dir}")
    if not ui_dir.exists() or not ui_dir.is_dir():
        return make_result(
            name=context.action_name,
            status="fail",
            summary="UI build check failed.",
            errors=[f"UI directory not found: {ui_dir}"],
        )

    if not package_json_path.exists() or not package_json_path.is_file():
        return make_result(
            name=context.action_name,
            status="fail",
            summary="UI build check failed.",
            errors=[f"package.json not found: {package_json_path}"],
        )

    context.log("package.json found")
    try:
        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        context.log(f"Unable to read package.json: {exc}")
        return make_result(
            name=context.action_name,
            status="error",
            summary="UI build check hit an unexpected error.",
            errors=[str(exc)],
            scenario_name=context.scenario_name,
            executed_command=command,
        )

    scripts = package_json.get("scripts")
    if not isinstance(scripts, dict) or not str(scripts.get("build") or "").strip():
        return make_result(
            name=context.action_name,
            status="fail",
            summary="UI build check failed.",
            errors=["package.json does not expose a build script."],
        )

    context.log("build script found")
    context.log(f"Running build command: {' '.join(command)}")
    try:
        completed = subprocess.run(
            command,
            cwd=ui_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        context.log(f"Build command failed to start: {exc}")
        return make_result(
            name=context.action_name,
            status="error",
            summary="UI build check hit an unexpected error.",
            errors=[str(exc)],
        )

    for stream_name, payload in (("stdout", completed.stdout), ("stderr", completed.stderr)):
        for line in str(payload or "").splitlines():
            text = line.rstrip()
            if text:
                context.log(f"{stream_name}: {text}")

    if completed.returncode != 0:
        return make_result(
            name=context.action_name,
            status="fail",
            summary="UI build check failed.",
            errors=[f"Build command exited with code {completed.returncode}."],
            scenario_name=context.scenario_name,
            executed_command=command,
            return_code=completed.returncode,
        )

    context.log("UI build completed")
    if not build_artifact_path.exists() or not build_artifact_path.is_file():
        return make_result(
            name=context.action_name,
            status="fail",
            summary="UI build check failed.",
            errors=[f"Expected build artifact missing: {build_artifact_path}"],
        )

    context.log(f"Build artifact found: {build_artifact_path}")
    return make_result(
        name=context.action_name,
        status="pass",
        summary="UI build completed successfully.",
        artifact_paths=[str(build_artifact_path)],
        scenario_name=context.scenario_name,
        executed_command=command,
        return_code=completed.returncode,
    )


def run_orl_replay_validation(context: ConsoleRunContext):
    adapter = EngineTestingAPI(repo_root=repo_root())
    result = adapter.replay_validation(scenario_name=context.scenario_name)
    return _console_result_from_adapter(
        context,
        result,
        success_summary="Replay validation passed.",
        failure_summary="Replay validation failed.",
    )


def run_orl_snapshot_smoke(context: ConsoleRunContext):
    adapter = EngineTestingAPI(repo_root=repo_root())
    result = adapter.snapshot_smoke(scenario_name=context.scenario_name)
    return _console_result_from_adapter(
        context,
        result,
        success_summary="Snapshot smoke passed.",
        failure_summary="Snapshot smoke failed.",
    )


def run_orl_all_green_check(context: ConsoleRunContext):
    adapter = EngineTestingAPI(repo_root=repo_root())
    result = adapter.run_all_green()
    return _console_result_from_adapter(
        context,
        result,
        success_summary="All-green check passed.",
        failure_summary="All-green check failed.",
    )
