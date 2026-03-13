"""Strategy Agent — runs registered strategies and produces signals.

Answers: *Is there a trade?*
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

from config import settings
from models.market_data import MarketContext
from models.signal import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyAgent:
    """Iterates through active strategies and returns the first valid signal."""

    def __init__(
        self,
        strategies: Sequence[BaseStrategy],
        get_confidence: Callable[[str], float],
    ) -> None:
        self._strategies = strategies
        self._get_confidence = get_confidence  # fn(strategy_name) -> float

    def detect(self, context: MarketContext) -> Optional[Signal]:
        try:
            return self._detect_inner(context)
        except Exception:
            logger.exception("StrategyAgent.detect failed")
            return None

    def _detect_inner(self, context: MarketContext) -> Optional[Signal]:
        for strategy in self._strategies:
            confidence = self._get_confidence(strategy.name)
            if confidence < settings.CONFIDENCE_ALLOW:
                logger.debug(
                    "Strategy %s disabled (confidence=%.2f < %.2f)",
                    strategy.name, confidence, settings.CONFIDENCE_ALLOW,
                )
                continue

            signal = strategy.detect(context)
            if signal is not None:
                signal.confidence = confidence
                logger.info(
                    "Signal from %s: %s %s @ %.5f  SL=%.5f  TP1=%.5f",
                    strategy.name, signal.direction, signal.symbol,
                    signal.entry_price, signal.stop_loss, signal.take_profit_1,
                )
                return signal
        return None
