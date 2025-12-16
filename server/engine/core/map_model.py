# engine/core/map_model.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Optional


class Terrain(str, Enum):
    CLEAR = "CLEAR"
    JUNGLE = "JUNGLE"
    MOUNTAIN = "MOUNTAIN"
    URBAN = "URBAN"
    SWAMP = "SWAMP"
    DESERT = "DESERT"
    WATER = "WATER"

    @staticmethod
    def coerce(value: str) -> "Terrain":
        """Coerce scenario strings into canonical Terrain values."""
        if value is None:
            return Terrain.CLEAR
        v = str(value).strip().upper()

        # Common aliases / legacy names
        aliases = {
            "PLAINS": "CLEAR",
            "PLAIN": "CLEAR",
            "OPEN": "CLEAR",
            "FOREST": "JUNGLE",
            "WOODS": "JUNGLE",
            "CITY": "URBAN",
            "TOWN": "URBAN",
        }
        v = aliases.get(v, v)

        try:
            return Terrain(v)
        except ValueError:
            # Fail-soft: default to CLEAR rather than blowing up a load
            return Terrain.CLEAR


@dataclass(frozen=True)
class MapTile:
    """
    The canonical tile model for MWE.

    IMPORTANT:
    - The first positional argument is tile_id.
    - scenario_loader should pass tile_id positionally to avoid "multiple values" errors.
    """
    tile_id: str
    name: str
    terrain: Terrain = Terrain.CLEAR

    # Basic movement / combat / supply knobs (safe defaults)
    base_move_cost: int = 1
    defense_bonus: int = 0
    supply_bonus: int = 0

    # Feature flags
    is_port: bool = False
    is_airfield: bool = False


class GameMap:
    def __init__(self) -> None:
        self._tiles: Dict[str, MapTile] = {}

    def add_tile(self, tile: MapTile) -> None:
        self._tiles[tile.tile_id] = tile

    def get_tile(self, tile_id: str) -> Optional[MapTile]:
        return self._tiles.get(tile_id)

    def tiles(self) -> Iterable[MapTile]:
        return self._tiles.values()

    def tile_ids(self) -> Iterable[str]:
        return self._tiles.keys()

    def to_dict(self) -> Dict[str, Dict]:
        return {
            tid: {
                "tile_id": t.tile_id,
                "name": t.name,
                "terrain": t.terrain.value,
                "base_move_cost": t.base_move_cost,
                "defense_bonus": t.defense_bonus,
                "supply_bonus": t.supply_bonus,
                "is_port": t.is_port,
                "is_airfield": t.is_airfield,
            }
            for tid, t in self._tiles.items()
        }
