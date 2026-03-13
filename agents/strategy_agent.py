"""Strategy Agent — runs registered strategies and produces signals.

Answers: *Is there a trade?*
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional, Sequence

from config import settings
from models.market_data import MarketContext
from models.signal import Signal
from strategies.base_strategy import BaseStrategy

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)


class StrategyAgent:
    """Iterates through active strategies and returns the first valid signal."""

    def __init__(
        self,
        strategies: Sequence[BaseStrategy],
        get_confidence: Callable[[str], float],
        db: Database | None = None,
    ) -> None:
        self._strategies = strategies
        self._get_confidence = get_confidence
        self._db = db

    def detect(self, context: MarketContext) -> Optional[Signal]:
        try:
            sig = self._detect_inner(context)
            if sig is None:
                self._emit("info", f"No trade on {context.symbol} — nothing looks right.")
            return sig
        except Exception:
            logger.exception("StrategyAgent.detect failed")
            self._emit("error", "Strategy scan crashed — skipping this tick.")
            return None

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("strategy", level, msg, data)

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
                self._emit("info",
                           f"Signal detected! {strategy.name} says {signal.direction} "
                           f"{signal.symbol} @ {signal.entry_price:.5f} (conf={confidence:.2f})",
                           {"strategy": strategy.name, "direction": signal.direction,
                            "symbol": signal.symbol, "confidence": confidence})
                logger.info(
                    "Signal from %s: %s %s @ %.5f  SL=%.5f  TP1=%.5f",
                    strategy.name, signal.direction, signal.symbol,
                    signal.entry_price, signal.stop_loss, signal.take_profit_1,
                )
                return signal
        return None
