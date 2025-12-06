"""
G-5 Plans / Long-Range Planning Staff

Modes:
- advisor: produces recommendations only (no orders issued)
- semi_auto: prepares orders; could be executed based on a flag
- full_auto: directly issues move/attack orders to G-3

Personality definitions in rules/planning.json override defaults.
"""

from __future__ import annotations
import os
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Literal, Any, TYPE_CHECKING

from engine.core.time_system import GameTime
from engine.core.unit_model import UnitRepository, UnitState, Side, Posture
from engine.core.map_model import GameMap
from engine.staff.base_staff import StaffSection

if TYPE_CHECKING:
    from engine.staff.g3_operations import G3Operations


G5Mode = Literal["advisor", "semi_auto", "full_auto"]


@dataclass
class PlanRecommendation:
    unit_id: str
    action: str              # "rest" or "attack"
    target_location_id: Optional[str]
    reason: str


class G5Plans(StaffSection):
    def __init__(
        self,
        units: UnitRepository,
        game_map: GameMap,
        g3: Optional["G3Operations"] = None,
        mode: G5Mode = "advisor",
        personality: str = "macarthur",
    ) -> None:
        super().__init__("G-5 Plans", units)
        self.game_map = game_map
        self.g3 = g3
        self.mode: G5Mode = mode
        self.personality_key = personality
        self.personality: Dict[str, Any] = self._load_personality(personality)

        # Output state
        self.last_recommendations: List[PlanRecommendation] = []
        self.last_briefing: str = ""

    # ------------------------------------------------------------------ utils

    def _rules_dir(self) -> str:
        # engine/staff -> engine -> server -> rules
        staff_dir = os.path.dirname(os.path.abspath(__file__))
        engine_dir = os.path.dirname(staff_dir)
        rules_dir = os.path.join(engine_dir, "..", "rules")
        return os.path.abspath(rules_dir)

    def _load_personality(self, key: str) -> Dict[str, Any]:
        """
        Load planning personalities from rules/planning.json.
        """
        rules_path = os.path.join(self._rules_dir(), "planning.json")
        default_mac = {
            "label": "MacArthur – Aggressive Offensive (built-in default)",
            "portrait": "macarthur.png",
            "aggressiveness": 0.85,
            "risk_tolerance": 0.85,
            "rest_priority": 0.30,
            "supply_weight": 0.50,
            "min_attack_force_ratio": 0.85,
            "preferred_operational_range_days": 5,
            "min_readiness_to_attack": 35,
            "min_morale_to_attack": 35,
        }

        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            personalities = data.get("personalities", {})
            if key in personalities:
                return personalities[key]
        except:
            pass

        return default_mac

    # ------------------------------------------------------------------ portraits

    @property
    def portrait_path(self) -> str:
        portrait = self.personality.get("portrait")
        if not portrait:
            return ""

        rules_dir = self._rules_dir()  # .../server/rules
        assets_dir = os.path.join(rules_dir, "..", "assets", "portraits")
        full_path = os.path.join(assets_dir, portrait)
        return os.path.abspath(full_path)

    # ----------------------------------------------------------------- timing

    def on_day_start(self, t: GameTime) -> None:
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        self.last_recommendations.clear()
        self.last_briefing = ""

        friendly = [u for u in self.units.all_units() if u.side == Side.ALLIED]
        enemy = [u for u in self.units.all_units() if u.side == Side.AXIS]

        if not friendly or not enemy:
            self.last_briefing = "No planning possible — one side not present."
            return

        attack_rec = self._evaluate_best_attack(friendly, enemy)
        rest_rec = self._evaluate_best_rest(friendly)

        rest_priority = float(self.personality.get("rest_priority", 0.3))

        if attack_rec:
            self.last_recommendations.append(attack_rec)
        if rest_rec and rest_priority > 0.2:
            self.last_recommendations.append(rest_rec)

        if self.mode in ("semi_auto", "full_auto") and self.g3:
            self._maybe_issue_orders(t)

        self._build_briefing_text(t, attack_rec, rest_rec)

    # ----------------------------------------------------------- evaluations

    def _evaluate_best_attack(
        self, friendly: List[UnitState], enemy: List[UnitState]
    ) -> Optional[PlanRecommendation]:

        enemy_by_loc: Dict[str, List[UnitState]] = {}
        for e in enemy:
            enemy_by_loc.setdefault(e.location_id, []).append(e)

        if not enemy_by_loc:
            return None

        min_rr = float(self.personality.get("min_attack_force_ratio", 1.0))
        min_read = float(self.personality.get("min_readiness_to_attack", 40))
        min_mor = float(self.personality.get("min_morale_to_attack", 40))

        best_score = -9999
        best_unit = None
        best_loc = None

        for u in friendly:
            if u.readiness < min_read or u.morale < min_mor or u.fatigue > 90:
                continue
            if u.supply < 40:
                continue

            for loc, enemy_units in enemy_by_loc.items():
                e_str = sum(e.strength for e in enemy_units)
                if e_str <= 0:
                    continue

                ratio = u.strength / e_str
                score = ratio * 50
                score += (u.morale - 50) * 0.5
                score += (u.readiness - 50) * 0.5
                if u.location_id == loc:
                    score += 20

                if ratio >= min_rr and score > best_score:
                    best_score = score
                    best_unit = u
                    best_loc = loc

        if not best_unit or not best_loc:
            return None

        return PlanRecommendation(
            unit_id=best_unit.id,
            action="attack",
            target_location_id=best_loc,
            reason=f"Acceptable force ratio; unit {best_unit.id} vs {best_loc}.",
        )

    def _evaluate_best_rest(
        self, friendly: List[UnitState]
    ) -> Optional[PlanRecommendation]:
        worst_score = -9999
        worst = None

        for u in friendly:
            score = (u.fatigue - 50) + (50 - u.readiness) + (50 - u.morale)
            if score > worst_score:
                worst_score = score
                worst = u

        if not worst:
            return None

        return PlanRecommendation(
            unit_id=worst.id,
            action="rest",
            target_location_id=None,
            reason="High fatigue / low readiness / low morale; needs rest.",
        )

    # ------------------------------------------------------- issuing orders

    def _maybe_issue_orders(self, t: GameTime) -> None:
        if not self.g3:
            return

        for rec in self.last_recommendations:
            if rec.action == "attack" and rec.target_location_id:
                self.g3.issue_move_order(
                    rec.unit_id,
                    rec.target_location_id,
                    Posture.ATTACK,
                    t=t,
                )
            elif rec.action == "rest" and self.mode == "full_auto":
                u = self.units.get(rec.unit_id)
                if u:
                    u.posture = Posture.REST

    # ----------------------------------------------------------- briefing text

    def _build_briefing_text(
        self,
        t: GameTime,
        attack_rec: Optional[PlanRecommendation],
        rest_rec: Optional[PlanRecommendation],
    ) -> None:

        lines = []
        lines.append(f"G-5 WAR PLAN BRIEFING — Day {t.day}")
        lines.append(
            f"Personality: {self.personality_key} "
            f"({self.personality.get('label', '')})"
        )
        lines.append(f"Mode: {self.mode}\n")

        if attack_rec:
            lines.append(
                f"- Recommended attack: {attack_rec.unit_id} "
                f"→ {attack_rec.target_location_id} "
                f"({attack_rec.reason})"
            )
        else:
            lines.append("- No offensive actions recommended today.")

        if rest_rec:
            lines.append(
                f"- Recommended rest: {rest_rec.unit_id} ({rest_rec.reason})"
            )
        else:
            lines.append("- No rest/refit priorities identified.")

        if self.mode in ("semi_auto", "full_auto"):
            lines.append(
                "\nNOTE: Some recommendations may have been auto-issued to G-3."
            )

        self.last_briefing = "\n".join(lines)

    # ----------------------------------------------------------- EngineAPI compatibility

    def generate_briefing(self, t: GameTime) -> str:
        """
        Called by EngineAPI.process_turn() in Phase 8.
        Updates recommendation and returns briefing text.
        """
        self.run_daily_cycle(t)
        return self.last_briefing
