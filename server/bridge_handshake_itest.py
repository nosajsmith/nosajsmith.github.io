from typing import Any, Dict, List

from ai.balck_v1 import BalckAIV1

from sim_time import SimTime
from event_queue import EventQueue
from orders_v1 import make_order_event
from scenario_store import list_scenarios, read_scenario
from staff_model_v1 import StaffModelV1


class BridgeShell:
    def __init__(self, scenario_dir: str):
        self.scenario_dir = scenario_dir

        # Core engine systems
        self.sim_time = SimTime()
        self.event_queue = EventQueue()
        # Phase 8.4: Staff Friction v1 (delay-only)
        # Default capacity, no config lookup
        self.staff = StaffModelV1()

        self.scenario = None

        # Phase 8.6: Balck AI v1 (harness)
        self.ai_enabled = False
        self.ai = BalckAIV1(side="AXIS")

        # Phase 8.7: AI cadence/backpressure
        self.ai_last_submit_hour = -999
        self.ai_min_interval_hours = 6

    # ---- Staff helpers (local, minimal, non-invasive) ----

    def _staff_reset(self) -> None:
        """Reset staff load to zero on scenario load."""
        if hasattr(self.staff, "reset") and callable(self.staff.reset):
            self.staff.reset()
            return
        if hasattr(self.staff, "load"):
            self.staff.load = 0.0
            return
        if hasattr(self.staff, "staff_load"):
            self.staff.staff_load = 0.0

    def _staff_load_value(self) -> float:
        if hasattr(self.staff, "load"):
            return float(self.staff.load)
        if hasattr(self.staff, "staff_load"):
            return float(self.staff.staff_load)
        return 0.0

    # ---- Command dispatcher ----

    def handle(self, cmd: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if cmd == "ping":
            return {"ok": True}

        if cmd == "ai.enable":
            self.ai_enabled = bool(args.get("enabled", False))
            return {"ok": True, "ai_enabled": self.ai_enabled}

        if cmd == "ai.status":
            return {"ok": True, "ai_enabled": bool(self.ai_enabled)}

        if cmd == "list_scenarios":
            names = list_scenarios(self.scenario_dir)
            return {"ok": True, "scenarios": names}

        if cmd == "load_scenario":
            name = args["name"]
            self.scenario = read_scenario(name, self.scenario_dir)

            # Phase 8.4 requirement: reset staff on scenario load
            self._staff_reset()

            # Phase 8.6: reset AI on scenario load
            self.ai_enabled = False

            return {"ok": True, "scenario": self.scenario}

        if cmd == "orders.submit":
            # Phase 8.4: delay-only staff friction
            base_eta_hours = float(args["eta_hours"])

            effective_eta_hours = float(
                self.staff.estimate_latency(base_eta_hours)
            )

            # Increment staff load for each submitted order
            self.staff.submit_order()

            # Schedule order using effective ETA
            sched_args = dict(args)
            sched_args["eta_hours"] = effective_eta_hours
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
                "staff_load": int(self.staff.load),
                "scheduled": scheduled,
            }

        if cmd == "clock.step":
            dt_hours = int((args or {}).get("dt_hours", 0))
            if dt_hours <= 0:
                return {"ok": False, "error": "dt_hours must be int > 0"}

            # Advance time normally (SimTime uses advance())
            result = self.sim_time.advance(dt_hours)

            # Phase 8.4: bleed staff load after time advances
            self.staff.advance_time(dt_hours)
            # Phase 8.6/8.7: AI submits orders after time + staff update (with cadence/backpressure)
            ai_submitted: list[dict] = []

            def _has_pending_ai_event() -> bool:
                try:
                    pending = self.event_queue.pending()
                    if isinstance(pending, list):
                        return any(isinstance(ev, dict) and ev.get("issuer") == "ai" for ev in pending)
                except Exception:
                    pass
                return False

            now_hr = int(result)
            staff_load = int(getattr(self.staff, "load", 0))
            staff_cap = int(getattr(self.staff, "staff_capacity", 4))
            staff_overloaded = staff_load > (staff_cap + 1)

            cadence_ok = (now_hr - int(getattr(self, "ai_last_submit_hour", -999))) >= int(getattr(self, "ai_min_interval_hours", 6))
            pending_ok = not _has_pending_ai_event()

            if self.ai_enabled and cadence_ok and pending_ok and (not staff_overloaded):
                intents = self.ai.decide_orders(self, now_hr)
                if intents:
                    # One order max per cadence window (restraint)
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

                    # Record cadence timestamp
                    self.ai_last_submit_hour = now_hr

            # Resolve events as before
            ready = self.event_queue.resolve_up_to(int(result))

            return {"ok": True, "time": int(result), "resolved": ready, "staff_load": int(self.staff.load), "ai_submitted": ai_submitted}

        return {"ok": False, "error": f"unknown cmd: {cmd}"}


# ---------------------------------------------------------------------
# Integration-test style handshake payloads (kept intact)
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # Example manual test sequence
    shell = BridgeShell("scenarios")

    print(shell.handle("ping", {}))
    print(shell.handle("list_scenarios", {}))
    print(shell.handle("load_scenario", {"name": "mini_gc_1942.json"}))

    print(
        shell.handle(
            "orders.submit",
            {
                "kind": "attack",
                "unit_id": "US-1MAR",
                "eta_hours": 12,
                "intent": "Probe",
            },
        )
    )

    print(shell.handle("clock.step", {"dt_hours": 6}))
