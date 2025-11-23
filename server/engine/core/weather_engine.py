"""
Weather engine for MWE.

Model C: Pacific-style seasonal weather, by day range.

Weather types:
- Clear
- Rain
- Storm
- Monsoon
"""

from __future__ import annotations
import os
import json
import random
from typing import Dict, Any, List


class WeatherEngine:
    def __init__(self, start_weather: str = "Clear") -> None:
        self.current_weather: str = start_weather
        self.rules: Dict[str, Any] = self._load_rules()

    # ------------------------------------------------------------------ rules

    def _rules_dir(self) -> str:
        # engine/core -> engine -> server -> rules
        core_dir = os.path.dirname(os.path.abspath(__file__))
        engine_dir = os.path.dirname(core_dir)
        rules_dir = os.path.join(engine_dir, "..", "rules")
        return os.path.abspath(rules_dir)

    def _load_rules(self) -> Dict[str, Any]:
        path = os.path.join(self._rules_dir(), "weather.json")
        defaults: Dict[str, Any] = {
            "seasons": [
                {
                    "name": "Dry",
                    "start_day": 1,
                    "end_day": 60,
                    "weights": {
                        "Clear": 0.5,
                        "Rain": 0.3,
                        "Storm": 0.15,
                        "Monsoon": 0.05
                    }
                },
                {
                    "name": "Transition",
                    "start_day": 61,
                    "end_day": 120,
                    "weights": {
                        "Clear": 0.4,
                        "Rain": 0.35,
                        "Storm": 0.2,
                        "Monsoon": 0.05
                    }
                },
                {
                    "name": "Wet",
                    "start_day": 121,
                    "end_day": 180,
                    "weights": {
                        "Clear": 0.25,
                        "Rain": 0.4,
                        "Storm": 0.25,
                        "Monsoon": 0.10
                    }
                }
            ],
            "default_weights": {
                "Clear": 0.6,
                "Rain": 0.25,
                "Storm": 0.10,
                "Monsoon": 0.05
            }
        }
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            defaults.update(data)
        except FileNotFoundError:
            pass
        except Exception:
            # corrupted or invalid, keep defaults
            pass
        return defaults

    # ------------------------------------------------------------------ logic

    def _weights_for_day(self, day: int) -> Dict[str, float]:
        seasons: List[Dict[str, Any]] = self.rules.get("seasons", [])
        for s in seasons:
            if s.get("start_day", 0) <= day <= s.get("end_day", 99999):
                return s.get("weights", {})
        return self.rules.get("default_weights", {})

    def advance_day(self, day: int) -> str:
        """
        Determine weather for the given day based on weighted random.
        """
        weights = self._weights_for_day(day)
        if not weights:
            self.current_weather = "Clear"
            return self.current_weather

        weather_types = list(weights.keys())
        probs = list(weights.values())
        total = sum(probs)
        if total <= 0:
            self.current_weather = "Clear"
            return self.current_weather

        # Normalize
        probs = [p / total for p in probs]
        r = random.random()
        acc = 0.0
        choice = weather_types[-1]
        for w, p in zip(weather_types, probs):
            acc += p
            if r <= acc:
                choice = w
                break

        self.current_weather = choice
        return self.current_weather
