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
    from models.lgbm_ensemble import LGBMEnsemble
    from models.lgbm_price_model import LGBMPriceModel

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
        self._lgbm_instance: "LGBMEnsemble | None" = None
        self._price_lgbm_instance: "LGBMPriceModel | None" = None

    @property
    def _lgbm(self) -> "LGBMEnsemble":
        """Lazy singleton for the LGBM ensemble (loaded once on first signal)."""
        if self._lgbm_instance is None:
            from models.lgbm_ensemble import LGBMEnsemble  # local to avoid circular import
            self._lgbm_instance = LGBMEnsemble()
        return self._lgbm_instance

    # ── LGBM encoding helpers (must match scripts/train_lgbm.py exactly) ──

    _SESSION_MAP: dict[str, float] = {
        "london": 0.0, "ny": 1.0, "new york": 1.0, "newyork": 1.0,
        "asian": 2.0, "asia": 2.0, "overlap": 3.0,
    }
    _DAY_MAP: dict[str, float] = {
        "monday": 0.0, "tuesday": 1.0, "wednesday": 2.0,
        "thursday": 3.0, "friday": 4.0, "saturday": 5.0, "sunday": 6.0,
    }
    _STRATEGY_MAP: dict[str, float] = {
        "deepseek": 0.0, "ict": 1.0, "sma": 2.0, "neural": 3.0,
    }

    @classmethod
    def _encode_session(cls, session: str) -> float:
        return cls._SESSION_MAP.get((session or "").lower().strip(), -1.0)

    @classmethod
    def _encode_day(cls, day: str) -> float:
        return cls._DAY_MAP.get((day or "").lower().strip(), -1.0)

    @classmethod
    def _encode_strategy(cls, strategy_name: str) -> float:
        name = (strategy_name or "").lower().strip()
        for key, val in cls._STRATEGY_MAP.items():
            if key in name:
                return val
        return -1.0

    @staticmethod
    def _encode_direction(direction: str) -> float:
        d = (direction or "").upper().strip()
        return 1.0 if d == "BUY" else (-1.0 if d == "SELL" else 0.0)

    @staticmethod
    def _build_lgbm_features(context: MarketContext, signal: Signal) -> list[float]:
        """Build the 11-feature vector that matches training (scripts/train_lgbm.py)."""
        snap = signal.entry_snapshot
        rsi = float(context.rsi or 50.0)
        direction = signal.direction or ""

        # Replicate DeepSeekStrategy snap logic as fallback
        if snap is not None:
            rsi_aligned = float(snap.rsi_aligned)
            trend_aligned = float(snap.trend_aligned)
            volume_sufficient = float(snap.volume_sufficient)
            near_news = float(snap.near_news_event)
        else:
            rsi_aligned = float((40.0 <= rsi <= 70.0) if direction == "BUY"
                                else (30.0 <= rsi <= 60.0))
            trend_aligned = float(
                (context.trend_direction == "bullish" and direction == "BUY")
                or (context.trend_direction == "bearish" and direction == "SELL")
            )
            volume_sufficient = float(bool(context.volume and context.volume > 0))
            near_news = float(context.near_news_event)

        session_enc = StrategyAgent._SESSION_MAP.get(
            (context.session or "").lower().strip(), -1.0
        )
        day_enc = StrategyAgent._DAY_MAP.get(
            (context.day_of_week or "").lower().strip(), -1.0
        )
        strategy_enc = StrategyAgent._encode_strategy(signal.strategy or "")
        direction_enc = StrategyAgent._encode_direction(direction)

        return [
            rsi_aligned,
            trend_aligned,
            volume_sufficient,
            near_news,
            session_enc,
            day_enc,
            float(context.spread or 0.0),
            float(signal.expected_edge_pct or 0.0),
            strategy_enc,
            direction_enc,
            float(context.mtf_alignment or 0.5),
        ]

    def _apply_lgbm_filter(self, signal: Signal, context: MarketContext) -> Signal:
        """Adjust signal confidence based on LGBM ensemble prediction.

        Never blocks a signal outright — confidence adjustments are capped to [0, 1].
        Fails open on any error so LGBM issues never halt trading.
        """
        if not getattr(settings, "LGBM_ENSEMBLE_ENABLED", False):
            return signal
        try:
            features = self._build_lgbm_features(context, signal)
            pred = self._lgbm.predict(features, [])
            if not pred.model_trained:
                return signal  # model not yet trained, pass through

            if pred.direction == signal.direction:
                # Agreement: boost confidence up to 10%
                signal.confidence = min(1.0, signal.confidence * 1.10)
                logger.debug(
                    "LGBM agrees %s %s -> boost to %.3f",
                    pred.direction, signal.symbol, signal.confidence,
                )
            elif pred.direction == "HOLD" and pred.confidence > 0.60:
                # LGBM strongly says avoid: reduce 15%
                signal.confidence = max(0.0, signal.confidence * 0.85)
                logger.debug(
                    "LGBM HOLD (%s, conf=%.2f) -> damp to %.3f",
                    signal.symbol, pred.confidence, signal.confidence,
                )
            else:
                # Contradiction: reduce 10%
                signal.confidence = max(0.0, signal.confidence * 0.90)
                logger.debug(
                    "LGBM contradicts %s vs %s -> damp to %.3f",
                    pred.direction, signal.direction, signal.confidence,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("LGBM filter failed (fail-open): %s", exc)
        return signal

    @property
    def _price_lgbm(self) -> "LGBMPriceModel":
        """Lazy singleton for the price-based per-symbol LGBM model."""
        if self._price_lgbm_instance is None:
            from models.lgbm_price_model import LGBMPriceModel
            self._price_lgbm_instance = LGBMPriceModel()
        return self._price_lgbm_instance

    def _apply_price_lgbm_filter(self, signal: Signal, context: MarketContext) -> Signal:
        """Second-opinion filter using per-symbol price-bar LGBM (12-feature vector).

        Trained on thousands of OHLCV bars, giving genuine market-structure signal.
        Confidence adjustments mirror the trade-history LGBM (±10-15%).  Fails open.
        """
        if not getattr(settings, "LGBM_ENSEMBLE_ENABLED", False):
            return signal
        try:
            pred = self._price_lgbm.predict_from_context(context)
            if not pred.model_trained:
                return signal   # no model for this symbol yet — pass through

            if pred.direction == signal.direction:
                signal.confidence = min(1.0, signal.confidence * 1.10)
                logger.debug(
                    "PriceLGBM agrees %s %s -> boost to %.3f",
                    pred.direction, signal.symbol, signal.confidence,
                )
            elif pred.direction == "HOLD" and pred.confidence > 0.60:
                signal.confidence = max(0.0, signal.confidence * 0.85)
                logger.debug(
                    "PriceLGBM HOLD (%s conf=%.2f) -> damp to %.3f",
                    signal.symbol, pred.confidence, signal.confidence,
                )
            else:
                signal.confidence = max(0.0, signal.confidence * 0.90)
                logger.debug(
                    "PriceLGBM contradicts %s vs %s -> damp to %.3f",
                    pred.direction, signal.direction, signal.confidence,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("PriceLGBM filter failed (fail-open): %s", exc)
        return signal

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

                # LGBM ensemble filter: adjusts confidence ±10-15% based on model prediction.
                signal = self._apply_lgbm_filter(signal, context)
                # Price-bar LGBM: second opinion from per-symbol OHLCV history.
                signal = self._apply_price_lgbm_filter(signal, context)
                # Bull/Bear Debate (DISABLED — DEBATE_ENABLED=false) no-op stub

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
