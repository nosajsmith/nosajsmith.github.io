"""
Prototype supply tracing / evaluation for Operation Cashflow.

Right now this is VERY simple:
- Each turn, we score each unit as:
    - in_supply: True/False
    - distance_to_nearest_source: stubbed (0 or 1 for now)

Later we can:
- Implement real graph search over the map
- Model interdiction, ZOC, ports, etc.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from engine.core.map_model import GameMap
from engine.core.unit_model import UnitRepository, UnitState, Side


@dataclass
class SupplyStatus:
    unit_id: str
    in_supply: bool
    distance_to_source: int
    source_location_id: Optional[str]


class SupplyTracer:
    def __init__(
        self,
        game_map: GameMap,
        units: UnitRepository,
        supply_sources: List[Dict],
    ) -> None:
        self.game_map = game_map
        self.units = units
        self.supply_sources = supply_sources

    def evaluate_all(self) -> Dict[str, SupplyStatus]:
        """
        For now, a stub:
        - A unit is 'in supply' if it sits exactly on a friendly supply source.
        - distance_to_source = 0 if on source, 1 if same side has *any* source on map
          (later this becomes path distance)
        """
        by_side_sources = self._group_sources_by_side()

        results: Dict[str, SupplyStatus] = {}
        for u in self.units.all_units():
            src_loc, dist = self._nearest_source_stub(u, by_side_sources)
            in_supply = dist == 0
            results[u.id] = SupplyStatus(
                unit_id=u.id,
                in_supply=in_supply,
                distance_to_source=dist,
                source_location_id=src_loc,
            )
        return results

    def _group_sources_by_side(self) -> Dict[Side, List[Dict]]:
        from engine.core.unit_model import Side as SideEnum

        by_side: Dict[SideEnum, List[Dict]] = {}
        for src in self.supply_sources:
            side_str = src.get("side")
            loc = src.get("location_id")
            if not side_str or not loc:
                continue
            try:
                side = SideEnum(side_str)
            except ValueError:
                continue
            by_side.setdefault(side, []).append(src)
        return by_side

    def _nearest_source_stub(
        self,
        u: UnitState,
        by_side_sources: Dict[Side, List[Dict]],
    ) -> (Optional[str], int):
        """
        Stub distance rule:
        - If unit is on a source hex for its side: dist=0
        - Else if its side has any source at all: dist=1
        - Else: dist=999 (no source)
        """
        sources = by_side_sources.get(u.side, [])
        if not sources:
            return None, 999

        for src in sources:
            if src.get("location_id") == u.location_id:
                return src["location_id"], 0

        # We know at least one source exists somewhere else
        return sources[0]["location_id"], 1
