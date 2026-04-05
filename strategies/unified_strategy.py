"""Unified Strategy.

A single connected strategy that orchestrates multiple signal engines and
returns one coherent decision.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime
from typing import Optional, Sequence

from config import settings
from models.market_data import MarketContext
from models.signal import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class UnifiedStrategy(BaseStrategy):
    """Single strategy wrapper that fuses multiple signal engines.

    Components can stay specialized internally (LLM/ICT/SMA), but the bot sees
    one strategy with one decision pipeline and one output signal.
    """

    name = "unified_alpha"

    def __init__(self, components: Sequence[BaseStrategy]) -> None:
        self._components = list(components)

    def detect(self, context: MarketContext) -> Optional[Signal]:
        candidates: list[Signal] = []
        for component in self._components:
            try:
                signal = component.detect(context)
            except Exception:
                logger.exception("UnifiedStrategy component %s failed", component.name)
                continue
            if signal is None:
                continue
            if signal.direction not in {"BUY", "SELL"}:
                continue
            candidates.append(signal)

        if not candidates:
            return None

        # Score by direction cluster to reward agreement.
        by_direction: dict[str, list[Signal]] = defaultdict(list)
        for signal in candidates:
            by_direction[signal.direction].append(signal)

        best_direction = "BUY"
        best_cluster_score = float("-inf")
        for direction, cluster in by_direction.items():
            cluster_score = self._cluster_score(cluster)
            if cluster_score > best_cluster_score:
                best_cluster_score = cluster_score
                best_direction = direction

        winners = by_direction[best_direction]
        anchor = max(winners, key=self._signal_anchor_score)

        # Confidence fusion: anchor dominates, agreement adds a bounded bonus.
        avg_conf = sum(s.confidence for s in winners) / len(winners)
        agreement_bonus = min(0.12, 0.04 * (len(winners) - 1))
        fused_conf = max(0.0, min(1.0, (anchor.confidence * 0.7) + (avg_conf * 0.3) + agreement_bonus))

        component_names = [s.strategy for s in winners]
        merged_reason = (
            f"Unified decision ({best_direction}) from {', '.join(component_names)} | "
            f"anchor={anchor.strategy} conf={anchor.confidence:.2f} "
            f"cluster={best_cluster_score:.2f} fused={fused_conf:.2f}"
        )

        return Signal(
            strategy=self.name,
            symbol=anchor.symbol,
            direction=anchor.direction,
            entry_price=anchor.entry_price,
            stop_loss=anchor.stop_loss,
            take_profit_1=anchor.take_profit_1,
            take_profit_2=anchor.take_profit_2,
            take_profit_3=anchor.take_profit_3,
            take_profit_4=anchor.take_profit_4,
            structural_be=anchor.structural_be,
            confidence=fused_conf,
            timestamp=datetime.now(UTC),
            reason=merged_reason,
            entry_snapshot=anchor.entry_snapshot,
        )

    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        # Fallback when called directly; detect() usually provides SL from anchor.
        atr = context.atr or 0.0
        if atr <= 0:
            return 0.0
        if direction == "BUY":
            return round(context.current_price - 2.0 * atr, 5)
        return round(context.current_price + 2.0 * atr, 5)

    def calculate_tps(
        self,
        context: MarketContext,
        entry: float,
        sl: float,
        direction: str,
    ) -> tuple[float, float, float]:
        risk = abs(entry - sl)
        if risk <= 0:
            return (0.0, 0.0, 0.0)
        if direction == "BUY":
            return (
                round(entry + risk, 5),
                round(entry + 2.0 * risk, 5),
                round(entry + 3.0 * risk, 5),
            )
        return (
            round(entry - risk, 5),
            round(entry - 2.0 * risk, 5),
            round(entry - 3.0 * risk, 5),
        )

    def _cluster_score(self, signals: Sequence[Signal]) -> float:
        """Direction-level score combining confidence and strategy impact."""
        if not signals:
            return float("-inf")

        score = 0.0
        for signal in signals:
            score += self._signal_anchor_score(signal)

        # Strongly reward independent confirmation across engines.
        score += 0.08 * (len(signals) - 1)
        return score

    @staticmethod
    def _signal_anchor_score(signal: Signal) -> float:
        """Single-signal score with high-impact strategy weighting."""
        base = signal.confidence
        strategy = (signal.strategy or "").lower()

        # High-impact priority: deepseek + ict > legacy crossover.
        if "deepseek" in strategy:
            weight = 0.12
        elif "ict" in strategy:
            weight = 0.08
        elif "sma" in strategy:
            weight = 0.02
        else:
            weight = 0.0

        # Penalize if the reason text indicates weak quality hints.
        reason = (signal.reason or "").lower()
        quality_penalty = 0.05 if "missing" in reason else 0.0

        return base + weight - quality_penalty
