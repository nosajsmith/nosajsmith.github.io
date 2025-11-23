"""
G-3 Operations Staff Section (Gary-mode v2)

- Manages movement orders
- Resolves multi-round battles with terrain, supply, readiness, fatigue, morale
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

from engine.core.time_system import GameTime
from engine.core.unit_model import (
    UnitRepository,
    UnitState,
    Side,
    Posture,
)
from engine.core.map_model import GameMap, Terrain
from engine.staff.base_staff import StaffSection


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class OperationOrder:
    unit_id: str
    target_location_id: str
    desired_posture: Posture
    issued_day: int
    notes: str = ""


@dataclass
class BattleRound:
    round_index: int
    allied_loss: int
    axis_loss: int
    notes: str = ""


@dataclass
class BattleReport:
    location_id: str
    attacker_side: Side
    defender_side: Side
    rounds: List[BattleRound] = field(default_factory=list)
    defender_retreat: bool = False
    defender_shattered: bool = False
    pursuit_losses_allied: int = 0
    pursuit_losses_axis: int = 0
    final_allied_strength: int = 0
    final_axis_strength: int = 0
    summary: str = ""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _clamp(v: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, v))


def _terrain_profile(terrain: Terrain) -> Dict[str, float]:
    """
    Returns modifiers for a given terrain.
    Values are tuned for a "Gary-ish" harshness.
    """
    if terrain == Terrain.JUNGLE:
        return {
            "attacker_mult": 0.55,
            "defender_mult": 1.25,
            "max_frontage": 3.0,
            "pursuit_mult": 0.2,
        }
    if terrain == Terrain.MOUNTAIN:
        return {
            "attacker_mult": 0.45,
            "defender_mult": 1.35,
            "max_frontage": 2.0,
            "pursuit_mult": 0.05,
        }
    if terrain == Terrain.URBAN:
        return {
            "attacker_mult": 0.6,
            "defender_mult": 1.3,
            "max_frontage": 3.0,
            "pursuit_mult": 0.15,
        }
    if terrain == Terrain.COAST:
        return {
            "attacker_mult": 0.8,
            "defender_mult": 1.1,
            "max_frontage": 5.0,
            "pursuit_mult": 0.4,
        }
    if terrain == Terrain.OCEAN:
        return {
            "attacker_mult": 0.3,
            "defender_mult": 1.0,
            "max_frontage": 1.5,
            "pursuit_mult": 0.7,
        }
    # PLAINS and default
    return {
        "attacker_mult": 1.0,
        "defender_mult": 1.0,
        "max_frontage": 6.0,
        "pursuit_mult": 0.6,
    }


def _unit_frontage_cost(u: UnitState) -> float:
    from engine.core.unit_model import UnitType  # avoid circular import at top
    if u.unit_type == UnitType.ARMORED:
        return 2.0
    if u.unit_type == UnitType.HQ:
        return 0.5
    if u.unit_type == UnitType.SUPPORT:
        return 0.75
    # Infantry, naval, air (abstracted)
    return 1.0


def _side_stats(units: List[UnitState]) -> Tuple[int, float, float, float]:
    """
    Returns (total_strength, avg_supply, avg_readiness, avg_fatigue)
    """
    if not units:
        return 0, 50.0, 50.0, 50.0
    total_str = sum(u.strength for u in units)
    avg_sup = sum(u.supply for u in units) / len(units)
    avg_read = sum(u.readiness for u in units) / len(units)
    avg_fat = sum(u.fatigue for u in units) / len(units)
    return total_str, avg_sup, avg_read, avg_fat


# ---------------------------------------------------------------------------
# G-3 Implementation
# ---------------------------------------------------------------------------

class G3Operations(StaffSection):
    def __init__(self, units: UnitRepository, game_map: GameMap) -> None:
        super().__init__("G-3 Operations", units)
        self.game_map = game_map
        self.orders: Dict[str, OperationOrder] = {}
        self.last_battles: List[BattleReport] = []

    # Time hook ---------------------------------------------------------------

    def on_day_start(self, t: GameTime) -> None:
        self.run_daily_cycle(t)

    def run_daily_cycle(self, t: GameTime) -> None:
        self.last_battles.clear()
        self._execute_orders(t)
        self._check_for_battles(t)

    # Orders ------------------------------------------------------------------

    def issue_move_order(
        self,
        unit_id: str,
        target_location_id: str,
        desired_posture: Posture,
        t: Optional[GameTime] = None,
    ) -> None:
        day = t.day if t is not None else 0
        self.orders[unit_id] = OperationOrder(
            unit_id=unit_id,
            target_location_id=target_location_id,
            desired_posture=desired_posture,
            issued_day=day,
        )

    def _execute_orders(self, t: GameTime) -> None:
        for unit_id, order in list(self.orders.items()):
            u = self.units.get(unit_id)
            if u is None:
                del self.orders[unit_id]
                continue

            # Too exhausted or undersupplied to move
            if u.readiness < 40 or u.supply < 30:
                u.posture = Posture.DEFEND
                continue

            # In a full engine we'd pathfind; for now, one-hex jump
            u.location_id = order.target_location_id
            u.posture = order.desired_posture

            # Movement cost to the body
            u.fatigue = _clamp(u.fatigue + 12)
            u.readiness = _clamp(u.readiness - 10)
            u.morale = _clamp(u.morale - 1)

            del self.orders[unit_id]

    # Battle detection --------------------------------------------------------

    def _check_for_battles(self, t: GameTime) -> None:
        # Group units by location
        by_loc: Dict[str, List[UnitState]] = {}
        for u in self.units.all_units():
            by_loc.setdefault(u.location_id, []).append(u)

        for loc, units in by_loc.items():
            allies = [u for u in units if u.side == Side.ALLIED and u.strength > 0]
            axis = [u for u in units if u.side == Side.AXIS and u.strength > 0]
            if allies and axis:
                report = self._resolve_battle(loc, allies, axis, t)
                if report is not None:
                    self.last_battles.append(report)

    # Battle resolution -------------------------------------------------------

    def _resolve_battle(
        self,
        location_id: str,
        allies: List[UnitState],
        axis: List[UnitState],
        t: GameTime,
    ) -> Optional[BattleReport]:
        tile = self.game_map.get(location_id)
        terrain = tile.terrain if tile is not None else Terrain.PLAINS
        terr = _terrain_profile(terrain)

        # Weather modifiers
        weather = getattr(t, "weather", "Clear")
        if weather == "Rain":
            terr["attacker_mult"] *= 0.9
            terr["defender_mult"] *= 0.95
            terr["max_frontage"] *= 0.9
        elif weather == "Storm":
            terr["attacker_mult"] *= 0.75
            terr["defender_mult"] *= 0.9
            terr["max_frontage"] *= 0.7
        elif weather == "Monsoon":
            terr["attacker_mult"] *= 0.6
            terr["defender_mult"] *= 0.85
            terr["max_frontage"] *= 0.5

        # Decide attacker/defender
        attacker_side, defender_side = self._determine_roles(allies, axis)
        ...


        # Split into attacker/defender lists
        if attacker_side == Side.ALLIED:
            atk_units = allies
            def_units = axis
        else:
            atk_units = axis
            def_units = allies

        report = BattleReport(
            location_id=location_id,
            attacker_side=attacker_side,
            defender_side=defender_side,
        )

        max_rounds = 5  # can tune later
        for r in range(1, max_rounds + 1):
            if not atk_units or not def_units:
                break

            # Pick frontline based on frontage
            atk_front, atk_reserve = self._pick_frontline(
                atk_units, terr["max_frontage"]
            )
            def_front, def_reserve = self._pick_frontline(
                def_units, terr["max_frontage"]
            )

            if not atk_front or not def_front:
                break

            # Compute effective power
            atk_power, def_power, round_notes = self._compute_round_power(
                atk_front, def_front, terr
            )
            if atk_power <= 0 or def_power <= 0:
                break

            force_ratio = atk_power / max(1.0, def_power)

            # Losses
            atk_loss, def_loss = self._compute_round_losses(
                atk_power, def_power, force_ratio
            )

            # Apply losses
            self._distribute_losses(atk_front, atk_loss)
            self._distribute_losses(def_front, def_loss)

            # Post-round morale/fatigue/readiness effects
            self._apply_round_aftereffects(
                atk_front, atk_reserve, atk_loss, role="attacker"
            )
            self._apply_round_aftereffects(
                def_front, def_reserve, def_loss, role="defender"
            )

            # Build round record
            total_allied = sum(u.strength for u in allies)
            total_axis = sum(u.strength for u in axis)
            round_note = (
                f"{round_notes} | Ratio={force_ratio:.2f}, "
                f"AlliedStr={total_allied}, AxisStr={total_axis}"
            )

            # Map losses to Allied/Axis for logging
            if attacker_side == Side.ALLIED:
                allied_loss = atk_loss
                axis_loss = def_loss
            else:
                allied_loss = def_loss
                axis_loss = atk_loss

            report.rounds.append(
                BattleRound(
                    round_index=r,
                    allied_loss=allied_loss,
                    axis_loss=axis_loss,
                    notes=round_note,
                )
            )

            # Check for defender collapse
            if self._check_defender_collapse(def_units, def_loss, force_ratio):
                report.defender_retreat = True
                if self._check_defender_shatter(def_units):
                    report.defender_shattered = True
                break

        # Summary and final strengths
        report.final_allied_strength = sum(u.strength for u in allies)
        report.final_axis_strength = sum(u.strength for u in axis)

        report.summary = (
            f"Battle at {location_id} ({terrain.value}): "
            f"Rounds={len(report.rounds)}, "
            f"AlliedStr={report.final_allied_strength}, "
            f"AxisStr={report.final_axis_strength}, "
            f"Defender {'SHATTERED' if report.defender_shattered else ('retreated' if report.defender_retreat else 'held')}"
        )

        return report

    # Role determination ------------------------------------------------------

    def _determine_roles(
        self, allies: List[UnitState], axis: List[UnitState]
    ) -> Tuple[Side, Side]:
        """
        Decide who is attacking/defending.
        Priority:
        - If one side has ATTACK posture present, they're the attacker.
        - Else higher total strength is attacker.
        """
        if any(u.posture == Posture.ATTACK for u in allies):
            return Side.ALLIED, Side.AXIS
        if any(u.posture == Posture.ATTACK for u in axis):
            return Side.AXIS, Side.ALLIED

        total_allied = sum(u.strength for u in allies)
        total_axis = sum(u.strength for u in axis)
        if total_allied >= total_axis:
            return Side.ALLIED, Side.AXIS
        return Side.AXIS, Side.ALLIED

    # Frontline selection -----------------------------------------------------

    def _pick_frontline(
        self, units: List[UnitState], max_frontage: float
    ) -> Tuple[List[UnitState], List[UnitState]]:
        """
        Choose frontline units up to frontage limit, rest are reserves.
        """
        frontline: List[UnitState] = []
        reserve: List[UnitState] = []
        used = 0.0

        # Sort: put higher strength & readiness units first
        ordered = sorted(
            units,
            key=lambda u: (u.strength, u.readiness),
            reverse=True,
        )

        for u in ordered:
            cost = _unit_frontage_cost(u)
            if used + cost <= max_frontage or not frontline:
                frontline.append(u)
                used += cost
            else:
                reserve.append(u)

        return frontline, reserve

    # Round power / losses ----------------------------------------------------

    def _compute_round_power(
        self,
        atk_front: List[UnitState],
        def_front: List[UnitState],
        terr: Dict[str, float],
    ) -> Tuple[float, float, str]:
        atk_str, atk_sup, atk_read, atk_fat = _side_stats(atk_front)
        def_str, def_sup, def_read, def_fat = _side_stats(def_front)

        # Base factors
        def supply_factor(s: float) -> float:
            # 50 supply ~ 0.8, 100 ~ 1.1
            return 0.4 + (s / 100.0) * 0.7

        def readiness_factor(r: float) -> float:
            # 30 ~ 0.7, 70 ~ 1.0, 100 ~ 1.1
            return 0.5 + (r / 100.0) * 0.6

        def fatigue_factor(f: float) -> float:
            # 0-40 minimal, 80+ bad
            if f <= 30:
                return 1.0
            if f <= 60:
                return 0.9
            if f <= 80:
                return 0.75
            return 0.6

        atk_power = (
            atk_str
            * supply_factor(atk_sup)
            * readiness_factor(atk_read)
            * fatigue_factor(100 - atk_fat)  # fresh is better
            * terr["attacker_mult"]
        )

        def_power = (
            def_str
            * supply_factor(def_sup)
            * readiness_factor(def_read)
            * fatigue_factor(100 - def_fat)
            * terr["defender_mult"]
        )

        note = (
            f"AtkStr={atk_str}, DefStr={def_str}, "
            f"AtkSup={atk_sup:.1f}, DefSup={def_sup:.1f}, "
            f"AtkRead={atk_read:.1f}, DefRead={def_read:.1f}"
        )

        return atk_power, def_power, note

    def _compute_round_losses(
        self, atk_power: float, def_power: float, force_ratio: float
    ) -> Tuple[int, int]:
        """
        Gary-ish harsh losses:
        - Base intensity ~ 3% of opposing power
        - Attacker loss reduced when attacking with good odds
        - Defender loss increased when outgunned
        """
        base_intensity = 0.03

        # Clamp ratio range
        r = max(0.3, min(force_ratio, 4.0))

        # Defender gets hammered at high ratios
        def_loss = int(def_power * base_intensity * r)
        # Attacker loss higher at bad odds, lower at good odds
        if r >= 1.0:
            atk_loss = int(atk_power * base_intensity * (1.0 / math.sqrt(r)))
        else:
            atk_loss = int(atk_power * base_intensity * (1.0 + (1.0 - r)))

        # Minimum 1 loss on each side if there is any power
        if def_power > 0 and def_loss <= 0:
            def_loss = 1
        if atk_power > 0 and atk_loss <= 0:
            atk_loss = 1

        return atk_loss, def_loss

    def _distribute_losses(self, units: List[UnitState], loss_total: int) -> None:
        if not units or loss_total <= 0:
            return

        total_strength = sum(u.strength for u in units)
        if total_strength <= 0:
            return

        remaining = loss_total
        for i, u in enumerate(units):
            if i == len(units) - 1:
                loss = remaining
            else:
                share = u.strength / total_strength
                loss = int(math.floor(loss_total * share))
                remaining -= loss
            if loss <= 0:
                continue
            u.strength = max(1, u.strength - loss)

    # Aftereffects & collapse -------------------------------------------------

    def _apply_round_aftereffects(
        self,
        frontline: List[UnitState],
        reserve: List[UnitState],
        loss_total: int,
        role: str,
    ) -> None:
        """
        Apply fatigue, readiness, morale changes per round.
        """
        # Frontline gets hammered
        for u in frontline:
            u.fatigue = _clamp(u.fatigue + 18)
            u.readiness = _clamp(u.readiness - 12)
            if loss_total > 0:
                if role == "attacker":
                    u.morale = _clamp(u.morale - 2)
                else:
                    u.morale = _clamp(u.morale - 3)

        # Reserves feel it but less
        for u in reserve:
            u.fatigue = _clamp(u.fatigue + 8)
            u.readiness = _clamp(u.readiness - 5)
            if loss_total > 0:
                u.morale = _clamp(u.morale - 1)

    def _check_defender_collapse(
        self,
        defenders: List[UnitState],
        loss_last_round: int,
        force_ratio: float,
    ) -> bool:
        """
        Check if defender collapses and retreats.
        """
        if not defenders:
            return False

        total_str, avg_sup, avg_read, avg_fat = _side_stats(defenders)
        avg_mor = sum(u.morale for u in defenders) / len(defenders)

        # Strong force ratio + poor morale/fatigue triggers retreat
        if avg_mor < 15:
            return True
        if avg_mor < 30 and force_ratio > 1.5:
            return True
        if total_str < 0.4 * 100 and force_ratio > 2.0:  # <40 pts strength AND badly outgunned
            return True
        if avg_read < 20 and avg_fat > 80:
            return True

        return False

    def _check_defender_shatter(self, defenders: List[UnitState]) -> bool:
        """
        Check if defender 'shatters' (severe collapse).
        """
        if not defenders:
            return False

        total_str, avg_sup, avg_read, avg_fat = _side_stats(defenders)
        avg_mor = sum(u.morale for u in defenders) / len(defenders)

        if avg_mor <= 8 and avg_read < 15:
            # Apply harsh penalties
            for u in defenders:
                u.readiness = _clamp(u.readiness - 20)
                u.morale = _clamp(u.morale - 10)
                u.supply = max(0, u.supply - 10)
            return True

        return False
