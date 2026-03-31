from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Literal, TypeAlias


ConsoleStatus = Literal["idle", "running", "pass", "fail", "warn", "error"]

ALLOWED_STATUSES: tuple[ConsoleStatus, ...] = ("idle", "running", "pass", "fail", "warn", "error")


@dataclass(frozen=True)
class ConsoleRunContext:
    action_name: str
    category: str
    scenario_name: str = ""
    bridge_uri: str = ""
    command_id: str = ""
    log: Callable[[str], None] = lambda _message: None

    @property
    def scenario_input(self) -> str:
        return self.scenario_name

    @property
    def selected_command_id(self) -> str:
        return self.command_id


@dataclass(frozen=True)
class KnownIssueMatch:
    issue_id: str
    title: str
    severity: str
    category: str
    status: str
    expected_status_override: str = ""
    notes: str = ""


@dataclass(frozen=True)
class ConsoleResult:
    name: str
    status: ConsoleStatus
    summary: str
    details: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: int = 0
    started_at: str = ""
    finished_at: str = ""
    scenario_name: str = ""
    subresults: List["ConsoleResult"] = field(default_factory=list)
    artifact_paths: List[str] = field(default_factory=list)
    adapter_method: str = ""
    executed_command: List[str] = field(default_factory=list)
    return_code: int | None = None
    original_status: str = ""
    known_issue_matches: List[KnownIssueMatch] = field(default_factory=list)


@dataclass(frozen=True)
class ConsoleAction:
    name: str
    category: str
    description: str
    runner: Callable[[ConsoleRunContext], ConsoleResult]


@dataclass(frozen=True)
class ConsoleSuite:
    name: str
    category: str
    description: str
    action_names: List[str] = field(default_factory=list)

    @property
    def step_names(self) -> List[str]:
        return self.action_names


ConsoleRegistryEntry: TypeAlias = ConsoleAction | ConsoleSuite
