"""
G-5 Plans / Long-Range Planning Staff

Modes:
- advisor: produces recommendations only (no orders issued)
- semi_auto: prepares orders; could be executed based on a flag
- full_auto: directly issues move/attack orders to G-3

Personality:
- macarthur (default, aggressive)
- nimitz
- slim
- plus any other personalities defined in rules/planning.json
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

        # Output
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
        Load planning personality from rules/planning.json.
        Falls back to a hard-coded MacArthur-like default if file missing.
        """
        rules_path = os.path.join(self._rules_dir(), "planning.json")
        default_mac = {
            "label": "MacArthur – Aggressive Offensive (built-in default)",
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
        except FileNotFoundError:
            pass
        except Exception:
            # If file is corrupted, don't crash the engine
            pass

        return default_mac

    # ----------------------------------------------------------------- timing

    def on_day_start(self, t: GameTime) -> None:
        # Plans at start of day, before G-3 executes operations
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        self.last_recommendations.clear()
        self.last_briefing = ""

        # For now, we assume Allies = "our side"
        friendly = [u for u in self.units.all_units() if u.side == Side.ALLIED]
        enemy = [u for u in self.units.all_units() if u.side == Side.AXIS]

        if not friendly or not enemy:
            self.last_briefing = "G-5: No meaningful planning (one side missing)."
            return

        # Evaluate candidate attacks and rests
        attack_rec = self._evaluate_best_attack(friendly, enemy)
        rest_rec = self._evaluate_best_rest(friendly)

        # Build recommendations list based on personality balance
        rest_priority = float(self.personality.get("rest_priority", 0.3))
        if attack_rec is not None:
            self.last_recommendations.append(attack_rec)
        if rest_rec is not None and rest_priority > 0.2:
            self.last_recommendations.append(rest_rec)

        # Possibly issue orders automatically
        if self.mode in ("semi_auto", "full_auto") and self.g3 is not None:
            self._maybe_issue_orders(t)

        # Build a readable briefing
        self._build_briefing_text(t, attack_rec, rest_rec)

    # ------------------------------------------------------- core evaluation

    def _evaluate_best_attack(
        self,
        friendly: List[UnitState],
        enemy: List[UnitState],
    ) -> Optional[PlanRecommendation]:
        """
        Very simple early-war offensive logic:
        - Find a strong-enough friendly unit
        - Find an enemy-held location with decent value
        - Estimate force ratio
        - If above threshold, recommend attack
        """
        # Group enemy by location
        enemy_by_loc: Dict[str, List[UnitState]] = {}
        for e in enemy:
            enemy_by_loc.setdefault(e.location_id, []).append(e)

        if not enemy_by_loc:
            return None

        # Heuristic: value ports/airfields more later; for now, anything with enemy is targetable
        min_rr = float(self.personality.get("min_attack_force_ratio", 1.0))
        min_read = float(self.personality.get("min_readiness_to_attack", 40))
        min_mor = float(self.personality.get("min_morale_to_attack", 40))

        best_score = 0.0
        best_unit: Optional[UnitState] = None
        best_target_loc: Optional[str] = None

        for u in friendly:
            # Basic health checks
            if u.readiness < min_read or u.morale < min_mor or u.fatigue > 90:
                continue
            if u.supply < 40:
                continue

            # Consider each enemy location as potential target
            for loc, enemy_units in enemy_by_loc.items():
                enemy_strength = sum(e.strength for e in enemy_units)
                if enemy_strength <= 0:
                    continue
                ratio = u.strength / enemy_strength

                # Heuristic score: ratio + morale + readiness + supply weighting
                score = ratio * 50.0
                score += (u.morale - 50) * 0.5
                score += (u.readiness - 50) * 0.5
                # Slight preference for already-adjacent / same-loc
                if u.location_id == loc:
                    score += 20.0

                if ratio >= min_rr and score > best_score:
                    best_score = score
                    best_unit = u
                    best_target_loc = loc

        if best_unit is None or best_target_loc is None:
            return None

        return PlanRecommendation(
            unit_id=best_unit.id,
            action="attack",
            target_location_id=best_target_loc,
            reason=(
                f"Force ratio and readiness acceptable; "
                f"u={best_unit.id} vs enemy at {best_target_loc}"
            ),
        )

    def _evaluate_best_rest(self, friendly: List[UnitState]) -> Optional[PlanRecommendation]:
        """
        Identify the most exhausted unit that should REST.
        """
        worst_score = -9999.0
        worst_unit: Optional[UnitState] = None

        for u in friendly:
            # Score: fatigue high, readiness low, morale low -> needs rest
            score = (u.fatigue - 50) + (50 - u.readiness) + (50 - u.morale)
            if score > worst_score:
                worst_score = score
                worst_unit = u

        if worst_unit is None:
            return None

        return PlanRecommendation(
            unit_id=worst_unit.id,
            action="rest",
            target_location_id=None,
            reason="High fatigue / low readiness; G-1 recommends rest/refit.",
        )

    # ------------------------------------------------------- order issuance

    def _maybe_issue_orders(self, t: GameTime) -> None:
        """
        Convert recommendations into concrete orders to G-3, depending on mode.
        For now:
        - semi_auto: we *prepare* orders but only issue attacks; rest remains advisory
        - full_auto: we issue both attack and rest (posture) orders
        """
        if self.g3 is None:
            return

        for rec in self.last_recommendations:
            if rec.action == "attack" and rec.target_location_id is not None:
                # For now, full-auto and semi-auto behave similarly here.
                self.g3.issue_move_order(
                    rec.unit_id,
                    rec.target_location_id,
                    Posture.ATTACK,
                    t=t,
                )
            elif rec.action == "rest" and self.mode == "full_auto":
                u = self.units.get(rec.unit_id)
                if u is not None:
                    u.posture = Posture.REST

    # ------------------------------------------------------------- briefing

    def _build_briefing_text(
        self,
        t: GameTime,
        attack_rec: Optional[PlanRecommendation],
        rest_rec: Optional[PlanRecommendation],
    ) -> None:
        lines: List[str] = []
        lines.append(f"G-5 WAR PLAN BRIEFING — Day {t.day}")
        lines.append(f"Personality: {self.personality_key} ({self.personality.get('label', '')})")
        lines.append(f"Mode: {self.mode}")
        lines.append("")

        if attack_rec is not None:
            lines.append(
                f"- Recommended attack: Unit {attack_rec.unit_id} "
                f"→ {attack_rec.target_location_id} "
                f"({attack_rec.reason})"
            )
        else:
            lines.append("- No offensive action recommended today.")

        if rest_rec is not None:
            lines.append(
                f"- Recommended rest: Unit {rest_rec.unit_id} "
                f"({rest_rec.reason})"
            )
        else:
            lines.append("- No specific rest/refit priority identified.")

        if self.mode in ("semi_auto", "full_auto"):
            lines.append("")
            lines.append("NOTE: Some recommendations may have been auto-issued to G-3.")

        self.last_briefing = "\n".join(lines)
