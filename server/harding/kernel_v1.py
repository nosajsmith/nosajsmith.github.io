from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from server.objectives.control_v1 import (
    compute_objective_state,
    compute_objective_status,
)
from server.politics.clock_v2 import PoliticalClockV2


SUPPORTED_AI_KINDS = {"attack", "support", "withdraw"}


class SimTime:
    def __init__(self) -> None:
        self._now = 0

    def now(self) -> int:
        return self._now

    def advance(self, dt_hours: int) -> int:
        self._now += int(dt_hours)
        return self._now

    def set(self, value: int) -> None:
        self._now = int(value)


class EventQueue:
    def __init__(self) -> None:
        self._pending: List[Dict[str, Any]] = []

    def push(self, event: Dict[str, Any]) -> None:
        if isinstance(event, dict):
            self._pending.append(dict(event))

    def pending(self) -> List[Dict[str, Any]]:
        return list(self._pending)

    def advance_to(self, now: int) -> List[Dict[str, Any]]:
        ready: List[Dict[str, Any]] = []
        remaining: List[Dict[str, Any]] = []
        for event in self._pending:
            available_at = int(event.get("available_at", now) or now)
            if available_at <= now:
                ready.append(event)
            else:
                remaining.append(event)
        self._pending = remaining
        return ready


class StaffModelV1:
    def __init__(self) -> None:
        self.load = 0
        self.staff_capacity = 4

    def reset(self) -> None:
        self.load = 0


class BalckAIV1:
    def __init__(self, side: str = "AXIS") -> None:
        self.side = side

    def decide_orders(self, state: Dict[str, Any], now: int) -> List[Dict[str, Any]]:
        return []


class ReplayV1:
    def __init__(self, name: str = "kma_mhk") -> None:
        self.name = name
        self.recording = False
        self.events: List[Dict[str, Any]] = []

    def start(self) -> None:
        self.recording = True

    def stop(self) -> None:
        self.recording = False

    def record(self, t: int, cmd: str, args: Dict[str, Any], result: Dict[str, Any]) -> None:
        if not self.recording:
            return
        self.events.append(
            {
                "t": int(t),
                "cmd": cmd,
                "args": dict(args or {}),
                "result": dict(result or {}),
            }
        )

    def export(self, path: str) -> str:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"events": self.events}, indent=2) + "\n", encoding="utf-8")
        return str(target)


class HardingKernelV1:
    """
    Phase 8 HARDING kernel, reusable by harness + production bridge adapters.
    Keeps the Phase 8 command surface stable.
    Envelope: {"ok": bool, ...}
    """

    __static_attributes__ = (
        "scenario_dir",
        "sim_time",
        "event_queue",
        "staff",
        "scenario",
        "ai_enabled",
        "ai",
        "ai_last_submit_hour",
        "ai_min_interval_hours",
        "politics",
        "report_delay_hours",
        "_pending_reports",
        "objective_state",
        "objective_status",
        "_tick_ledger",
        "_tick_ledger_max",
        "_last_ai_intent",
        "replay",
    )

    def __init__(self, scenario_dir: str):
        self.scenario_dir = scenario_dir
        self.sim_time = SimTime()
        self.event_queue = EventQueue()
        self.staff = StaffModelV1()
        self.scenario: Optional[Dict[str, Any]] = None

        self.ai_enabled = False
        self.ai = BalckAIV1(side="AXIS")
        self.ai_last_submit_hour = -999
        self.ai_min_interval_hours = 6
        self.politics = PoliticalClockV2(deadline_hours=72, player_side="ALLIED")

        self.report_delay_hours = 6
        self._pending_reports: List[Dict[str, Any]] = []

        self.objective_state: Dict[str, bool] = {}
        self.objective_status: Dict[str, Dict[str, Any]] = {}
        self.objective_truth: Dict[str, Dict[str, Any]] = self.objective_status

        self._tick_ledger: List[Dict[str, Any]] = []
        self._tick_ledger_max = 20
        self._last_ai_intent: Optional[str] = None
        self.replay = ReplayV1(name="kma_mhk")

    def _staff_reset(self) -> None:
        if hasattr(self.staff, "reset"):
            self.staff.reset()
        else:
            self.staff.load = 0

    def _build_ai_decision_state(self) -> Dict[str, Any]:
        score_by_side: Dict[str, Any] = {}
        try:
            scoring = getattr(getattr(self, "politics", None), "scoring", None)
            if scoring is not None and hasattr(scoring, "score_by_side"):
                raw = getattr(scoring, "score_by_side", {})
                if isinstance(raw, dict):
                    score_by_side = dict(raw)
        except Exception:
            score_by_side = {}

        return {
            "scenario": self.scenario if isinstance(self.scenario, dict) else {},
            "objective_state": dict(getattr(self, "objective_state", {}) or {}),
            "score_by_side": score_by_side,
        }

    def _has_pending_ai_event(self) -> bool:
        try:
            pending = self.event_queue.pending()
            if isinstance(pending, list):
                return any(
                    isinstance(event, dict) and event.get("issuer") == "ai"
                    for event in pending
                )
            return False
        except Exception:
            return False

    def _ai_gate_state(self, now: int) -> Dict[str, Any]:
        staff_load = int(getattr(self.staff, "load", 0))
        staff_capacity = int(getattr(self.staff, "staff_capacity", 4))
        cadence_ok = now - int(getattr(self, "ai_last_submit_hour", -999)) >= int(
            getattr(self, "ai_min_interval_hours", 6)
        )
        pending_ok = not self._has_pending_ai_event()
        staff_overloaded = staff_load > staff_capacity + 1
        enabled = bool(self.ai_enabled)
        should_act = enabled and cadence_ok and pending_ok and not staff_overloaded
        return {
            "enabled": enabled,
            "cadence_ok": cadence_ok,
            "pending_ok": pending_ok,
            "staff_overloaded": staff_overloaded,
            "staff_load": staff_load,
            "staff_capacity": staff_capacity,
            "should_act": should_act,
        }

    def _is_supported_ai_kind(self, kind: str) -> bool:
        return str(kind or "") in SUPPORTED_AI_KINDS

    def _active_support_effects(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for event in self.event_queue.pending():
            if isinstance(event, dict) and event.get("kind") == "support":
                out.append(dict(event))
        return out

    def _list_scenarios(self) -> List[str]:
        root = Path(self.scenario_dir)
        if not root.exists():
            return []
        return sorted(path.name for path in root.glob("*.json") if path.is_file())

    def _read_scenario(self, scenario_name: str) -> Optional[Dict[str, Any]]:
        if not scenario_name or "/" in scenario_name or "\\" in scenario_name:
            return None
        if not scenario_name.endswith(".json"):
            return None
        path = Path(self.scenario_dir) / scenario_name
        if not path.exists() or not path.is_file():
            return None
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            return None
        if not isinstance(loaded.get("units"), list):
            loaded["units"] = []
        if not isinstance(loaded.get("objectives"), list):
            loaded["objectives"] = []
        return loaded

    def _campaign_snapshot(self, now: int) -> Dict[str, Any]:
        try:
            return self.politics.snapshot(now, self.objective_state)
        except Exception:
            return {}

    def handle(self, cmd: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = args or {}
        try:
            t = int(self.sim_time.now())
        except Exception:
            t = 0

        result = self._handle_impl(cmd, args)

        try:
            self.replay.record(t, cmd, args or {}, result)
        except Exception:
            pass

        return result

    def _handle_impl(self, cmd: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if cmd == "ping":
            return {"ok": True, "version": 1}

        if cmd == "list_scenarios":
            return {"ok": True, "scenarios": self._list_scenarios()}

        if cmd == "load_scenario":
            scenario_name = str(args.get("scenario_name") or "")
            scenario = self._read_scenario(scenario_name)
            if scenario is None:
                return {"ok": False, "error": f"unknown scenario: {scenario_name}"}

            self.scenario = scenario
            self.objective_status = compute_objective_status(self.scenario)
            self.objective_truth = self.objective_status
            self.objective_state = compute_objective_state(self.scenario)
            self.scenario["objective_status"] = self.objective_status
            self.scenario["objective_state"] = self.objective_state

            self.sim_time.set(0)
            self._staff_reset()
            self._pending_reports = []
            self.event_queue = EventQueue()
            self.politics = PoliticalClockV2(
                deadline_hours=int(args.get("deadline_hours", 72) or 72),
                player_side=str(args.get("side") or "ALLIED"),
            )
            self.politics.set_baseline(self.scenario)

            return {
                "ok": True,
                "loaded": scenario_name,
                "scenario": self.scenario,
                "objective_state": self.objective_state,
                "campaign": self._campaign_snapshot(now=int(self.sim_time.now())),
            }

        if cmd == "campaign.status":
            now = int(self.sim_time.now())
            return {"ok": True, "campaign": self._campaign_snapshot(now)}

        if cmd == "campaign.explain":
            now = int(self.sim_time.now())
            campaign = self._campaign_snapshot(now)
            pressure = campaign.get("pressure", {}) if isinstance(campaign, dict) else {}
            scoring = campaign.get("scoring", {}) if isinstance(campaign, dict) else {}
            return {
                "ok": True,
                "campaign_status": campaign.get("status", "unknown"),
                "time_now": campaign.get("time_now", now),
                "time_remaining": campaign.get("time_remaining", 0),
                "score_by_side": scoring.get("score_by_side", {}),
                "pressure_reasons": pressure.get("reasons", []),
                "objective_state": dict(self.objective_state),
            }

        if cmd == "ai.enable":
            self.ai_enabled = bool(args.get("enabled", True))
            return {"ok": True, "enabled": self.ai_enabled}

        if cmd == "ai.status":
            return {"ok": True, **self._ai_gate_state(now=int(self.sim_time.now()))}

        if cmd == "replay.start":
            self.replay.start()
            return {"ok": True, "recording": self.replay.recording}

        if cmd == "replay.stop":
            self.replay.stop()
            return {"ok": True, "recording": self.replay.recording}

        if cmd == "replay.export":
            path = str(args.get("path") or "artifacts/replays/kma_mhk_replay.json")
            return {"ok": True, "path": self.replay.export(path)}

        if cmd == "save.snapshot":
            path = Path(str(args.get("path") or "artifacts/snapshots/kma_mhk_snapshot.json"))
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "sim_time": int(self.sim_time.now()),
                "scenario": self.scenario if isinstance(self.scenario, dict) else {},
                "objective_state": dict(self.objective_state),
                "objective_status": dict(self.objective_status),
                "campaign": self._campaign_snapshot(int(self.sim_time.now())),
                "tick_ledger": list(self._tick_ledger),
            }
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return {"ok": True, "path": str(path)}

        if cmd == "load.snapshot":
            path = Path(str(args.get("path") or "artifacts/snapshots/kma_mhk_snapshot.json"))
            if not path.exists() or not path.is_file():
                return {"ok": False, "error": f"missing snapshot: {path}"}
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.scenario = payload.get("scenario") if isinstance(payload, dict) else {}
            if not isinstance(self.scenario, dict):
                self.scenario = {}
            self.objective_state = dict(payload.get("objective_state") or {})
            self.objective_status = dict(payload.get("objective_status") or {})
            self.objective_truth = self.objective_status
            self.scenario["objective_state"] = self.objective_state
            self.scenario["objective_status"] = self.objective_status
            self.sim_time.set(int(payload.get("sim_time", 0) or 0))
            self.politics = PoliticalClockV2()
            self.politics.set_baseline(self.scenario)
            return {"ok": True, "loaded": str(path)}

        if cmd == "clock.step":
            try:
                dt_hours = int(args.get("dt_hours", 0))
            except Exception:
                dt_hours = 0
            if dt_hours <= 0:
                return {"ok": False, "error": "dt_hours must be int > 0"}

            now = int(self.sim_time.advance(dt_hours))
            resolved_events = self.event_queue.advance_to(now)

            reports: List[Dict[str, Any]] = []
            remaining_reports: List[Dict[str, Any]] = []
            for report in self._pending_reports:
                available_at = int(report.get("available_at", now) or now)
                if available_at <= now:
                    reports.append(dict(report))
                else:
                    remaining_reports.append(report)
            self._pending_reports = remaining_reports

            self._staff_reset()
            if not isinstance(self.scenario, dict):
                self.scenario = {"units": [], "objectives": []}

            self.objective_status = compute_objective_status(self.scenario)
            self.objective_truth = self.objective_status
            self.objective_state = compute_objective_state(self.scenario)
            self.scenario["objective_status"] = self.objective_status
            self.scenario["objective_state"] = self.objective_state

            ai_submitted: List[str] = []
            gate = self._ai_gate_state(now=now)
            if gate["should_act"] and hasattr(self.ai, "decide_orders"):
                decision_state = self._build_ai_decision_state()
                try:
                    raw_orders = self.ai.decide_orders(decision_state, now)
                except TypeError:
                    raw_orders = self.ai.decide_orders(decision_state)
                except Exception:
                    raw_orders = []
                for item in raw_orders or []:
                    if not isinstance(item, dict):
                        continue
                    kind = str(item.get("kind") or "")
                    if not self._is_supported_ai_kind(kind):
                        continue
                    eta_hours = int(item.get("eta_hours", dt_hours) or dt_hours)
                    self.event_queue.push(
                        {
                            "issuer": "ai",
                            "kind": kind,
                            "intent": item.get("intent"),
                            "unit_id": item.get("unit_id"),
                            "available_at": now + eta_hours,
                            "eta_hours": eta_hours,
                            "event": dict(item),
                        }
                    )
                    ai_submitted.append(kind)
                    self.ai_last_submit_hour = now
                    self._last_ai_intent = str(item.get("intent") or "")

            campaign = self.politics.on_time_advance(
                dt_hours,
                now,
                self.scenario,
                self.objective_state,
            )
            scoring = campaign.get("scoring", {}) if isinstance(campaign, dict) else {}
            score_by_side = (
                dict(scoring.get("score_by_side", {}))
                if isinstance(scoring, dict)
                else {}
            )
            pressure = campaign.get("pressure", {}) if isinstance(campaign, dict) else {}
            reasons = pressure.get("reasons", []) if isinstance(pressure, dict) else []

            ledger_item = {
                "t": now,
                "status": campaign.get("status", "unknown"),
                "score_by_side": score_by_side,
                "objective_state": dict(self.objective_state),
                "pressure_reasons": list(reasons) if isinstance(reasons, list) else [],
                "reports_delivered": len(reports),
                "ai_submitted": list(ai_submitted),
                "last_ai_intent": self._last_ai_intent,
            }
            self._tick_ledger.append(ledger_item)
            if len(self._tick_ledger) > self._tick_ledger_max:
                self._tick_ledger = self._tick_ledger[-self._tick_ledger_max :]

            return {
                "ok": True,
                "time": now,
                "reports": reports,
                "resolved_events": resolved_events,
                "staff_load": int(getattr(self.staff, "load", 0)),
                "ai_submitted": ai_submitted,
                "objective_state": self.objective_state,
                "campaign": campaign,
                "pending_reports": len(self._pending_reports),
            }

        return {"ok": False, "error": f"unknown cmd: {cmd}"}
