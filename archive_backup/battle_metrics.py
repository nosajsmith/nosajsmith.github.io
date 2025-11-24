# battle_metrics.py — simple, transparent KPIs for combats this turn
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class BattleMetrics:
    attacks_total: int = 0
    attacks_coordinated: int = 0     # >= 2 attackers engaged on frontage
    odds_samples: List[float] = field(default_factory=list)
    atk_losses_sum: int = 0
    def_losses_sum: int = 0

    def reset(self):
        self.attacks_total = 0
        self.attacks_coordinated = 0
        self.odds_samples.clear()
        self.atk_losses_sum = 0
        self.def_losses_sum = 0

    def log(self, engaged_attackers: int, odds: float, atk_losses: int, def_losses: int):
        self.attacks_total += 1
        if engaged_attackers >= 2:
            self.attacks_coordinated += 1
        self.odds_samples.append(max(0.01, float(odds)))
        self.atk_losses_sum += max(0, int(atk_losses))
        self.def_losses_sum += max(0, int(def_losses))

    def summary(self) -> Dict[str, float]:
        n = len(self.odds_samples) or 1
        avg_odds = sum(self.odds_samples) / n
        loss_ratio = (self.atk_losses_sum / self.def_losses_sum) if self.def_losses_sum > 0 else float("inf") if self.atk_losses_sum > 0 else 0.0
        return {
            "attacks_total": self.attacks_total,
            "attacks_coordinated": self.attacks_coordinated,
            "avg_attack_odds": round(avg_odds, 3),
            "loss_ratio": round(loss_ratio, 3)
        }

# module-level singleton
METRICS = BattleMetrics()
