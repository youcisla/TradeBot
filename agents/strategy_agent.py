"""Strategy Agent — runs registered strategies and produces signals.

Answers: *Is there a trade?*
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable, Optional, Sequence

from config import settings
from config.symbols import asset_class
from models.market_data import MarketContext
from models.signal import Signal
from strategies.base_strategy import BaseStrategy
from utils.mesh_bus import mesh_span

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)


class StrategyAgent:
    """Runs all active strategies and collects signals.

    ``detect()`` returns the single best signal (backward-compatible).
    ``detect_all()`` returns every valid signal for ranking across symbols.
    """

    def __init__(
        self,
        strategies: Sequence[BaseStrategy],
        get_confidence: Callable[[str], float],
        db: Database | None = None,
    ) -> None:
        self._strategies = strategies
        self._get_confidence = get_confidence
        self._db = db

    # ── Public API ───────────────────────────────────────────────────────

    def detect(self, context: MarketContext) -> Optional[Signal]:
        """Return the single best signal for one symbol (legacy API)."""
        try:
            signals = self._collect_signals(context)
            if not signals:
                self._emit("info", f"No trade on {context.symbol} — nothing looks right.")
                return None
            # Return highest confidence
            return max(signals, key=lambda s: s.confidence)
        except Exception:
            logger.exception("StrategyAgent.detect failed")
            self._emit("error", "Strategy scan crashed — skipping this tick.")
            return None

    def detect_all(self, context: MarketContext) -> list[Signal]:
        """Return ALL valid signals from ALL strategies for one symbol.

        Used by the ranking pipeline to compare signals across symbols
        before choosing which to execute.
        """
        try:
            return self._collect_signals(context)
        except Exception:
            logger.exception("StrategyAgent.detect_all failed")
            return []

    # ── Internal ─────────────────────────────────────────────────────────

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("strategy", level, msg, data)

    def _collect_signals(self, context: MarketContext) -> list[Signal]:
        """Run every strategy and collect all valid signals."""
        signals: list[Signal] = []
        min_conf = self._min_confidence_for_context(context)

        for strategy in self._strategies:
            confidence = self._get_confidence(strategy.name)
            if confidence < settings.CONFIDENCE_ALLOW:
                logger.debug(
                    "Strategy %s disabled (confidence=%.2f < %.2f)",
                    strategy.name, confidence, settings.CONFIDENCE_ALLOW,
                )
                continue

            with mesh_span(strategy.name):
                signal = strategy.detect(context)
            if signal is not None:
                # If strategy provides its own dynamic confidence (e.g. from ICT setups with historical backtest), keep it
                # Otherwise, fallback to the generic strategy confidence
                final_confidence = signal.confidence if signal.confidence != 0.5 else confidence
                signal.confidence = max(0.0, min(1.0, final_confidence))

                # Dynamic confidence floor by regime + asset class.
                if signal.confidence < min_conf:
                    self._emit(
                        "info",
                        (
                            f"Signal skipped on {signal.symbol}: conf={signal.confidence:.2f} "
                            f"< min={min_conf:.2f} for regime={context.regime}"
                        ),
                        {
                            "symbol": signal.symbol,
                            "confidence": signal.confidence,
                            "min_confidence": min_conf,
                            "regime": context.regime,
                        },
                    )
                    continue

                self._emit("info",
                           f"Signal detected! {signal.strategy or strategy.name} says {signal.direction} "
                           f"{signal.symbol} @ {signal.entry_price:.5f} (conf={final_confidence:.2f})",
                           {"strategy": signal.strategy or strategy.name, "direction": signal.direction,
                            "symbol": signal.symbol, "confidence": final_confidence})
                logger.info(
                    "Signal from %s: %s %s @ %.5f  SL=%.5f  TP1=%.5f",
                    strategy.name, signal.direction, signal.symbol,
                    signal.entry_price, signal.stop_loss, signal.take_profit_1,
                )
                signals.append(signal)

        return signals

    @staticmethod
    def _min_confidence_for_context(context: MarketContext) -> float:
        """Return a regime-aware confidence floor with asset-class adjustments."""
        regime = (context.regime or "unknown").lower()
        if regime == "trending":
            floor = settings.MIN_CONF_TRENDING
        elif regime == "ranging":
            floor = settings.MIN_CONF_RANGING
        elif regime == "volatile":
            floor = settings.MIN_CONF_VOLATILE
        else:
            floor = settings.MIN_CONF_UNKNOWN

        ac = asset_class(context.symbol)
        if ac == "crypto":
            floor += settings.MIN_CONF_CRYPTO_BONUS
        elif ac == "exotic":
            floor += settings.MIN_CONF_EXOTIC_BONUS

        return max(settings.CONFIDENCE_ALLOW, min(0.95, floor))
