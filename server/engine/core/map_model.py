from __future__ import annotations

"""
Compatibility re-export for the canonical map model in `mwe_map_model`.

This keeps `server.engine.*` imports aligned with the active `engine.*` import
surface without relying on namespace-package ordering between `engine/` and
`server/engine/`.
"""

from mwe_map_model import GameMap, MapTile, Terrain

__all__ = ["Terrain", "MapTile", "GameMap"]
