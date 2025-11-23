"""
G-6 Signals / Command & Control

Adds realistic command delays between higher HQ (player / G-5)
and execution (G-3 Operations).

- Orders are queued with a delay (in days)
- Delay can depend on HQ quality, disruption, and distance (stubbed for now)
- Each day, G-6 checks which orders are ready and forwards them to G-3
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import os
import json
import random

from engine.core.time_system import GameTime
from engine.core.unit_model import Posture, UnitRepository, UnitState
from engine.staff.base_staff import StaffSection

if True:  # for type checkers only
    from engine.staff.g3_operations import G3Operations


@dataclass
class PendingOrder:
    unit_id: str
    target_location_id: str
    posture: Posture
    issued_day: int
    deliver_day: int
    via_hq_id: Optional[str] = None
    disrupted: bool = False
    notes: str = ""


class G6Signals(StaffSection):
    """
    G-6 sits between higher-level planning (player / G-5) and G-3.
    You tell G-6 what you *want* done; it decides when the order
    actually reaches the field commanders.
    """

    def __init__(
        self,
        units: UnitRepository,
        g3: "G3Operations",
    ) -> None:
        super().__init__("G-6 Signals", units)
        self.g3 = g3
        self.pending: List[PendingOrder] = []
        self.rules: Dict[str, Any] = self._load_rules()
        self.last_log: List[str] = []

    # ------------------------------------------------------------------ rules

    def _rules_dir(self) -> str:
        # engine/staff -> engine -> server -> rules
        staff_dir = os.path.dirname(os.path.abspath(__file__))
        engine_dir = os.path.dirname(staff_dir)
        rules_dir = os.path.join(engine_dir, "..", "rules")
        return os.path.abspath(rules_dir)

    def _load_rules(self) -> Dict[str, Any]:
        """
        Load command & control rules from rules/command.json.
        """
        rules_path = os.path.join(self._rules_dir(), "command.json")
        defaults: Dict[str, Any] = {
            "base_delay_days": 1,
            "max_delay_days": 4,
            "disruption_chance": 0.15,
            "extra_delay_on_disruption": 1,
            "hq_quality_factor": 0.5,
            "distance_delay_per_step": 1,
        }
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            defaults.update(data)
        except FileNotFoundError:
            pass
        except Exception:
            # If invalid/corrupt, just use defaults
            pass
        return defaults

    # ----------------------------------------------------------------- timing

    def on_day_start(self, t: GameTime) -> None:
        # Each morning, deliver any orders whose time has come
        self.last_log.clear()
        self._deliver_due_orders(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        # Nothing additional for now
        return

    # ----------------------------------------------------------------- public

    def issue_delayed_move_order(
        self,
        unit_id: str,
        target_location_id: str,
        posture: Posture,
        t: GameTime,
        via_hq_id: Optional[str] = None,
        notes: str = "",
    ) -> None:
        """
        Queue an order to be delivered to G-3 after a delay.

        - via_hq_id: HQ through which the order is routed (if any)
        """
        delay, disrupted = self._compute_delay(unit_id, via_hq_id)
        deliver_day = t.day + delay

        po = PendingOrder(
            unit_id=unit_id,
            target_location_id=target_location_id,
            posture=posture,
            issued_day=t.day,
            deliver_day=deliver_day,
            via_hq_id=via_hq_id,
            disrupted=disrupted,
            notes=notes,
        )
        self.pending.append(po)

        msg = (
            f"G-6: Queued order for {unit_id} -> {target_location_id}, "
            f"posture={posture.name}, issued D+{t.day}, ETA D+{deliver_day}"
        )
        if via_hq_id:
            msg += f" via HQ {via_hq_id}"
        if disrupted:
            msg += " (disruption caused extra delay)"
        self.last_log.append(msg)

    # ---------------------------------------------------------------- internal

    def _compute_delay(self, unit_id: str, via_hq_id: Optional[str]) -> (int, bool):
        """
        Compute order delay based on:
        - base delay
        - HQ quality (if any)
        - simple distance (stubbed)
        - chance of disruption
        """
        base_delay = int(self.rules.get("base_delay_days", 1))
        max_delay = int(self.rules.get("max_delay_days", 4))
        dist_step = int(self.rules.get("distance_delay_per_step", 1))
        hq_factor = float(self.rules.get("hq_quality_factor", 0.5))
        disruption_chance = float(self.rules.get("disruption_chance", 0.15))
        extra_delay_on_disruption = int(self.rules.get("extra_delay_on_disruption", 1))

        delay = base_delay
        disrupted = False

        # Simple distance: 0 if same location, 1 otherwise (stub)
        unit = self.units.get(unit_id)
        hq: Optional[UnitState] = self.units.get(via_hq_id) if via_hq_id else None

        if unit and hq:
            if unit.location_id != hq.location_id:
                delay += dist_step

            # Better HQ (higher readiness/morale) reduces delay
            avg_quality = (hq.readiness + hq.morale) / 2.0
            # Normalize ~ [0,1], 50 = baseline
            quality_factor = (avg_quality - 50.0) / 50.0  # -1 .. +1-ish
            delay_adjust = int(round(-quality_factor * hq_factor))
            delay += delay_adjust

        # Disruption chance (radio problems, weather, etc.)
        if random.random() < disruption_chance:
            delay += extra_delay_on_disruption
            disrupted = True

        # Clamp delay
        delay = max(0, min(max_delay, delay))
        return delay, disrupted

    def _deliver_due_orders(self, t: GameTime) -> None:
        still_pending: List[PendingOrder] = []
        for po in self.pending:
            if po.deliver_day <= t.day:
                self.g3.issue_move_order(
                    po.unit_id,
                    po.target_location_id,
                    po.posture,
                    t=t,
                )
                msg = (
                    f"G-6: Delivered order to {po.unit_id} at D+{t.day} "
                    f"(issued D+{po.issued_day}, via HQ={po.via_hq_id})"
                )
                self.last_log.append(msg)
            else:
                still_pending.append(po)
        self.pending = still_pending
