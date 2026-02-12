from __future__ import annotations
from typing import Any, Dict

from sim_time import SimTime
from event_queue import EventQueue
from orders_v1 import make_order_event
from scenario_store import list_scenarios, read_scenario
from staff_model_v1 import StaffModelV1
from ai.balck_v1 import BalckAIV1


class HardingKernelV1:
    """
    Phase 8 HARDING kernel, reusable by harness + production bridge adapters.
    Keeps the Phase 8 command surface stable.
    Envelope: {"ok": bool, ...}
    """

    def __init__(self, scenario_dir: str):
        self.scenario_dir = scenario_dir
        self.sim_time = SimTime()
        self.event_queue = EventQueue()
        self.staff = StaffModelV1()
        self.scenario = None

        # Phase 8.6/8.7 AI
        self.ai_enabled = False
        self.ai = BalckAIV1(side="AXIS")
        self.ai_last_submit_hour = -999
        self.ai_min_interval_hours = 6

        # Phase 8.9: intelligence lag (temporal fog)
        self.report_delay_hours = 6
        self._pending_reports = []  # list of {available_at:int, report:dict}

    def _staff_reset(self) -> None:
        if hasattr(self.staff, "reset") and callable(self.staff.reset):
            self.staff.reset()
            return
        if hasattr(self.staff, "load"):
            self.staff.load = 0.0
            return
        if hasattr(self.staff, "staff_load"):
            self.staff.staff_load = 0.0

    def handle(self, cmd: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if cmd == "ping":
            return {"ok": True}

        if cmd == "list_scenarios":
            names = list_scenarios(self.scenario_dir)
            return {"ok": True, "scenarios": names}

        if cmd == "load_scenario":
            name = args["name"]
            self.scenario = read_scenario(name, self.scenario_dir)
            self._staff_reset()
            self.ai_enabled = False
            self.sim_time = SimTime()
            self.event_queue = EventQueue()
            return {"ok": True, "scenario": self.scenario}

        if cmd == "ai.enable":
            self.ai_enabled = bool(args.get("enabled", False))
            return {"ok": True, "ai_enabled": self.ai_enabled}

        if cmd == "ai.status":
            return {"ok": True, "ai_enabled": bool(self.ai_enabled)}

        if cmd == "reports.get":
            # Return only reports that are already available at current time
            now = int(self.sim_time.now())
            ready = []
            remaining = []
            for pr in self._pending_reports:
                if int(pr.get("available_at", 0)) <= now:
                    ready.append(pr.get("report"))
                else:
                    remaining.append(pr)
            self._pending_reports = remaining
            return {"ok": True, "time": now, "reports": ready}

        if cmd == "orders.submit":
            base_eta_hours = float(args["eta_hours"])
            effective_eta_hours = float(self.staff.estimate_latency(base_eta_hours))
            self.staff.submit_order()

            issued_at = int(self.sim_time.now())
            event = make_order_event(
                kind=str(args.get("kind", "")),
                unit_id=str(args.get("unit_id", "")),
                issued_at=issued_at,
                eta_hours=int(effective_eta_hours),
                intent=str(args.get("intent", "")),
            )
            scheduled = self.event_queue.schedule(event)
            return {
                "ok": True,
                "base_eta_hours": base_eta_hours,
                "effective_eta_hours": effective_eta_hours,
                "staff_load": int(getattr(self.staff, "load", 0)),
                "scheduled": scheduled,
            }

        if cmd == "clock.step":
            dt_hours = int((args or {}).get("dt_hours", 0))
            if dt_hours <= 0:
                return {"ok": False, "error": "dt_hours must be int > 0"}

            now = int(self.sim_time.advance(dt_hours))
            self.staff.advance_time(dt_hours)

            # Phase 8.7 AI cadence/backpressure
            ai_submitted = []

            def _has_pending_ai_event() -> bool:
                try:
                    pending = self.event_queue.pending()
                    return isinstance(pending, list) and any(isinstance(ev, dict) and ev.get("issuer") == "ai" for ev in pending)
                except Exception:
                    return False

            staff_load = int(getattr(self.staff, "load", 0))
            staff_cap = int(getattr(self.staff, "staff_capacity", 4))
            staff_overloaded = staff_load > (staff_cap + 1)
            cadence_ok = (now - int(getattr(self, "ai_last_submit_hour", -999))) >= int(getattr(self, "ai_min_interval_hours", 6))
            pending_ok = not _has_pending_ai_event()

            if self.ai_enabled and cadence_ok and pending_ok and (not staff_overloaded):
                intents = self.ai.decide_orders(self, now)
                if intents:
                    o = intents[0]
                    base_eta = float(o.get("eta_hours", 6))
                    effective_eta = float(self.staff.estimate_latency(base_eta))
                    self.staff.submit_order()

                    ev = make_order_event(
                        kind=str(o.get("kind", "")),
                        unit_id=str(o.get("unit_id", "")),
                        issued_at=int(self.sim_time.now()),
                        eta_hours=int(effective_eta),
                        intent=str(o.get("intent", "")),
                    )
                    ev["issuer"] = "ai"
                    scheduled = self.event_queue.schedule(ev)
                    ai_submitted.append(scheduled)
                    self.ai_last_submit_hour = now
            resolved = self.event_queue.resolve_up_to(now)

            # Phase 8.9: convert resolved events into delayed reports
            for ev in resolved:
                report = {
                    "t_resolved": now,
                    "type": "event_resolved",
                    "event": ev,
                }
                self._pending_reports.append({
                    "available_at": now + int(self.report_delay_hours),
                    "report": report,
                })

            # Deliver reports that have arrived
            reports_ready = []
            remaining_reports = []
            for pr in self._pending_reports:
                if int(pr.get("available_at", 0)) <= now:
                    reports_ready.append(pr.get("report"))
                else:
                    remaining_reports.append(pr)
            self._pending_reports = remaining_reports

            return {
                "ok": True,
                "time": now,
                "reports": reports_ready,
                "staff_load": int(getattr(self.staff, "load", 0)),
                "ai_submitted": ai_submitted,
                "pending_reports": len(self._pending_reports),
            }

        return {"ok": False, "error": f"unknown cmd: {cmd}"}
