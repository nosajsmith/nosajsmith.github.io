# morale.py — simple morale/cohesion system with routs and rally
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import math
import random

@dataclass
class MoraleEvent:
    turn: int
    unit_id: str
    kind: str              # "cohesion_loss" | "shaken" | "routed" | "rally" | "fallback"
    delta: Optional[int]   # change in cohesion or morale when relevant
    note: str

def _ensure_fields(unit) -> None:
    # Attach morale/cohesion fields if the Unit object doesn’t have them yet.
    if not hasattr(unit, "morale"): unit.morale = 70          # 0..100
    if not hasattr(unit, "cohesion"): unit.cohesion = 70      # 0..100
    if not hasattr(unit, "routed"): unit.routed = False
    if not hasattr(unit, "shaken"): unit.shaken = False
    if not hasattr(unit, "last_rally_turn"): unit.last_rally_turn = -999

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def _adjacent_hexes(x: int, y: int) -> List[Tuple[int,int]]:
    return [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]

def _fallback_one(game_state, unit) -> Optional[Tuple[int,int]]:
    """Try to fall back to the first non-enemy-occupied adjacent hex with lower exposure."""
    ux, uy = unit.position
    # Prefer tiles with lower exposure / not adjacent to many enemies (very simple heuristic)
    candidates = []
    for hx, hy in _adjacent_hexes(ux, uy):
        if hx < 0 or hy < 0: 
            continue
        # can move if not occupied by friendly or enemy
        if game_state.get_unit_at((hx, hy)) is None:
            # count adjacent enemies to candidate
            enemy_count = 0
            for ax, ay in _adjacent_hexes(hx, hy):
                u2 = game_state.get_unit_at((ax, ay))
                if u2 and u2.side != unit.side:
                    enemy_count += 1
            candidates.append(((hx,hy), enemy_count))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[1])  # fewer adjacent enemies preferred
    return candidates[0][0]

def _post_battle_cohesion_drop(atk_losses: int, def_losses: int, outcome: str, is_attacker: bool) -> int:
    """
    Translate combat losses/outcome into a cohesion delta.
    Positive return means *loss* (delta will be subtracted from cohesion).
    """
    base = 0
    # scale with losses (light heuristic: every 1 loss ~ 2 cohesion points)
    loss_factor = (atk_losses if is_attacker else def_losses)
    base += int(loss_factor * 2)

    # outcome shock
    if is_attacker:
        if outcome.lower() in ("repulsed", "stalemate"):
            base += 6
        elif outcome.lower() in ("attacker rout", "defender holds"):
            base += 10
    else:
        if outcome.lower() in ("defender rout", "attacker breakthrough", "breakthrough"):
            base += 12
        elif outcome.lower() in ("retreat", "fallback"):
            base += 7
        elif outcome.lower() in ("stalemate",):
            base += 4
    return base

def apply_post_combat_effects(game_state, battle_results: List[Any], turn: int) -> List[MoraleEvent]:
    """
    After combat resolution, reduce cohesion/morale, set shaken/routed, and perform immediate fallbacks for routed units.
    Expects battle_results entries with fields: attackers, defender_id, outcome, atk_losses, def_losses.
    """
    events: List[MoraleEvent] = []

    # index attackers → fast lookup
    def _get(u_id: str):
        u = game_state.get_unit(u_id)
        if u: _ensure_fields(u)
        return u

    for r in battle_results or []:
        outcome = str(r.outcome)
        atk_losses = int(getattr(r, "atk_losses", 0))
        def_losses = int(getattr(r, "def_losses", 0))

        # attackers
        for aid in r.attackers:
            u = _get(aid)
            if not u: continue
            drop = _post_battle_cohesion_drop(atk_losses, def_losses, outcome, is_attacker=True)
            if drop:
                old = u.cohesion
                u.cohesion = int(_clamp(u.cohesion - drop, 0, 100))
                events.append(MoraleEvent(turn, u.unit_id, "cohesion_loss", -drop,
                                          f"Attacker cohesion {old}→{u.cohesion} (losses/outcome)"))
            # shaken / routed checks
            if u.cohesion <= 25 and not u.routed:
                u.shaken = True
                events.append(MoraleEvent(turn, u.unit_id, "shaken", None, "Attacker shaken"))
            if u.cohesion <= 10 and not u.routed:
                u.routed = True
                u.shaken = False
                events.append(MoraleEvent(turn, u.unit_id, "routed", None, "Attacker routed"))
        # defender
        d = _get(r.defender_id)
        if d:
            drop = _post_battle_cohesion_drop(atk_losses, def_losses, outcome, is_attacker=False)
            if drop:
                old = d.cohesion
                d.cohesion = int(_clamp(d.cohesion - drop, 0, 100))
                events.append(MoraleEvent(turn, d.unit_id, "cohesion_loss", -drop,
                                          f"Defender cohesion {old}→{d.cohesion} (losses/outcome)"))
            if d.cohesion <= 25 and not d.routed:
                d.shaken = True
                events.append(MoraleEvent(turn, d.unit_id, "shaken", None, "Defender shaken"))
            if d.cohesion <= 10 and not d.routed:
                d.routed = True
                d.shaken = False
                events.append(MoraleEvent(turn, d.unit_id, "routed", None, "Defender routed"))

    # immediate fallback for any newly-routed units
    for u in game_state.all_units():
        _ensure_fields(u)
        if u.routed:
            dest = _fallback_one(game_state, u)
            if dest:
                game_state.set_unit_position(u.unit_id, dest)
                events.append(MoraleEvent(turn, u.unit_id, "fallback", None, f"Routed fallback to {dest}"))
    return events

def rally_phase(game_state, supply_engine, turn: int) -> List[MoraleEvent]:
    """
    End-of-turn rally checks. Routed units may become shaken; shaken units may recover.
    Chance depends on supply and fatigue. Near-future: factor HQ distance, route state, experience.
    """
    evs: List[MoraleEvent] = []
    for u in game_state.all_units():
        _ensure_fields(u)

        # base rally chance
        # supply helps, fatigue hurts
        base = 0.25 + (u.supply / 400.0) - (u.fatigue / 300.0)
        if u.routed:
            base -= 0.10   # harder to rally from routed to shaken
        base = _clamp(base, 0.05, 0.85)
        roll = random.random()

        if u.routed:
            if roll < base:
                u.routed = False
                u.shaken = True
                # partial cohesion recovery on rally
                add = 10
                u.cohesion = int(_clamp(u.cohesion + add, 0, 100))
                u.last_rally_turn = turn
                evs.append(MoraleEvent(turn, u.unit_id, "rally", +add, f"Routed → Shaken (cohesion +{add})"))
        elif u.shaken:
            if roll < base:
                u.shaken = False
                add = 15
                u.cohesion = int(_clamp(u.cohesion + add, 0, 100))
                u.last_rally_turn = turn
                evs.append(MoraleEvent(turn, u.unit_id, "rally", +add, f"Shaken → Steady (cohesion +{add})"))
        else:
            # steady: small cohesion bounce if well supplied and resting
            if u.fatigue <= 30 and u.supply >= 60:
                if random.random() < 0.25:
                    add = 5
                    old = u.cohesion
                    u.cohesion = int(_clamp(u.cohesion + add, 0, 100))
                    evs.append(MoraleEvent(turn, u.unit_id, "cohesion_loss", +add, f"Recovered cohesion {old}→{u.cohesion}"))
    return evs
