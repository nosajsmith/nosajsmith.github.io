# hq_refit.py — HQ refit / recovery scaled by supply performance
from __future__ import annotations

import io
import json
import os
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8", errors="replace")

from typing import Dict, List, Any


class RefitEngine:
    """
    Turn-based refit that:
      * Reads (optional) HQ pools from JSON (infantry/armor/supplies) per side
      * Computes a per-side 'perf' factor from SupplyEngine routes:
            perf = mean( effective_throughput / capacity ) for that side’s routes
        (falls back to 1.0 if no routes or on error)
      * Applies simple recovery to each unit (fatigue down, cohesion up) scaled by perf
    Returns a list of row dicts used by summary_table().
    """

    def __init__(self, pool_path: str = "hq_pools.json"):
        self.pool_path = pool_path
        self.pools = self._load_pools(pool_path)

    # --------------------- public API ---------------------

    def apply(self, dispatcher, game_state, supply_engine) -> List[Dict[str, Any]]:
        """
        Apply per-turn refit effects to all units in game_state.
        This version is compatible with the new SupplyEngine (state.routes).
        """
        perf = self._compute_perf_from_routes(supply_engine)
        rows: List[Dict[str, Any]] = []

        for u in game_state.all_units():
            side = getattr(u, "side", "BLUE").upper()
            factor = float(perf.get(side, 1.0))

            # Simple recovery model (tune as needed)
            recovered = max(0, round(5 * factor))  # 0..5+ per turn depending on supply
            # Fatigue decreases, cohesion increases
            u.fatigue = max(0, int(getattr(u, "fatigue", 0) - recovered))
            u.cohesion = min(100, int(getattr(u, "cohesion", 70) + recovered))

            rows.append({
                "unit": getattr(u, "unit_id", "?"),
                "side": side,
                "recovered": recovered,
                "perf": round(factor, 2)
            })

        return rows

    @staticmethod
    def summary_table(rows: List[Dict[str, Any]]) -> str:
        """HTML table for the report."""
        if not rows:
            return "<p>No refit actions this turn.</p>"

        out = [
            "<table>",
            "<thead><tr><th>Unit</th><th>Side</th><th>Recovered</th><th>Perf</th></tr></thead>",
            "<tbody>"
        ]
        for r in rows:
            out.append(
                f"<tr>"
                f"<td>{r.get('unit','?')}</td>"
                f"<td>{r.get('side','?')}</td>"
                f"<td>{r.get('recovered',0)}</td>"
                f"<td>{r.get('perf',1.0)}</td>"
                f"</tr>"
            )
        out.append("</tbody></table>")
        return "".join(out)

    # --------------------- internals ----------------------

    def _compute_perf_from_routes(self, supply_engine) -> Dict[str, float]:
        """
        Compute per-side performance as mean(effective_throughput / capacity)
        over that side’s routes. Robust to missing data; returns 1.0 defaults.
        """
        try:
            routes = getattr(getattr(supply_engine, "state", None), "routes", None)
            if not routes:
                return {"BLUE": 1.0, "RED": 1.0}

            blue_vals, red_vals = [], []
            for r in routes:
                try:
                    cap = max(1.0, float(getattr(r, "capacity", 0.0)))
                    eff = float(r.effective_throughput())  # also caches last_effective
                    val = max(0.0, min(1.0, eff / cap))
                    if getattr(r, "side", "BLUE").upper() == "BLUE":
                        blue_vals.append(val)
                    else:
                        red_vals.append(val)
                except Exception:
                    continue

            def mean(xs): return (sum(xs) / len(xs)) if xs else 1.0
            return {
                "BLUE": round(mean(blue_vals), 3),
                "RED": round(mean(red_vals), 3)
            }
        except Exception:
            return {"BLUE": 1.0, "RED": 1.0}

    def _load_pools(self, path: str) -> Dict[str, Dict[str, int]]:
        """Optional HQ pool file; safe defaults if missing or malformed."""
        default = {
            "BLUE": {"infantry": 100, "armor": 50, "supplies": 300},
            "RED":  {"infantry": 120, "armor": 60, "supplies": 280},
        }
        if not path or not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # shallow-merge with defaults
            for side in ("BLUE", "RED"):
                if side not in data or not isinstance(data[side], dict):
                    data[side] = default[side].copy()
                else:
                    for k, v in default[side].items():
                        data[side].setdefault(k, v)
            return data
        except Exception:
            return default
