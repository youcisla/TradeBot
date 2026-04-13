"""Pairs Spread Strategy — Statistical Arbitrage on Correlated Forex Pairs.

Detects mean-reversion opportunities by monitoring the spread between two
cointegrated pairs (e.g. EURUSD vs GBPUSD). When the spread deviates > 2σ
from its rolling mean, we expect a reversion to the mean.

This is a *mean-reversion* signal — orthogonal to ICT's momentum/breakout
approach. It fires on:
  - Spread breaches upper Bollinger band → SELL spread (expect compression)
  - Spread breaches lower Bollinger band → BUY spread (expect expansion)

Usage:
    from strategies.pairs_spread import PairsSpreadStrategy
    strategy = PairsSpreadStrategy(broker=broker, db=db)
    signal = strategy.detect(context)  # MarketContext carries both symbols' candles

Signal metadata carries the spread z-score so the RiskAgent can size
appropriately (z > 3 = extreme deviation = reduce size).
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from models.market_data import MarketContext, Candle
from models.signal import Signal, SignalIntent
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


# ── Canonical pair definitions ────────────────────────────────────────────

@dataclass
class PairDef:
    """Specification for one cointegrated pair."""
    primary: str       # Symbol used for MarketContext (e.g. "EURUSD")
    secondary: str     # Correlated symbol (e.g. "GBPUSD")
    hedge_ratio: float = 1.0  # EURUSD/GBPUSD approximate hedge ratio


PAIRS: list[PairDef] = [
    PairDef(primary="EURUSD", secondary="GBPUSD", hedge_ratio=1.0),
    PairDef(primary="EURUSD", secondary="EURGBP", hedge_ratio=1.0),
    PairDef(primary="GBPUSD", secondary="GBPJPY", hedge_ratio=1.0),
    PairDef(primary="XAUUSD", secondary="XAUUSD.s", hedge_ratio=1.0),  # spot vs S-index
]


# ── Spread state tracker ─────────────────────────────────────────────────

class SpreadState:
    """Rolling spread statistics for one pair."""

    def __init__(
        self,
        lookback: int = 100,
        bb_period: int = 20,
        bb_std: float = 2.0,
    ) -> None:
        self.lookback = lookback
        self.bb_period = bb_period
        self.bb_std = bb_std
        self._spread_history: deque[float] = deque(maxlen=lookback)

    def update(self, primary_px: float, secondary_px: float, hedge_ratio: float) -> None:
        spread = primary_px - hedge_ratio * secondary_px
        self._spread_history.append(spread)

    @property
    def mean(self) -> float:
        if len(self._spread_history) < self.bb_period:
            return 0.0
        return sum(list(self._spread_history)[-self.bb_period:]) / self.bb_period

    @property
    def stdev(self) -> float:
        hist = list(self._spread_history)[-self.bb_period:]
        if len(hist) < 2:
            return 1.0
        m = sum(hist) / len(hist)
        variance = sum((x - m) ** 2 for x in hist) / len(hist)
        return math.sqrt(variance) if variance > 0 else 1.0

    @property
    def zscore(self) -> float:
        if self.stdev == 0:
            return 0.0
        if len(self._spread_history) < self.bb_period:
            return 0.0
        current = self._spread_history[-1]
        return (current - self.mean) / self.stdev

    @property
    def bb_upper(self) -> float:
        return self.mean + self.bb_std * self.stdev

    @property
    def bb_lower(self) -> float:
        return self.mean - self.bb_std * self.stdev

    @property
    def has_data(self) -> bool:
        return len(self._spread_history) >= self.bb_period


# ── Strategy ─────────────────────────────────────────────────────────────

class PairsSpreadStrategy(BaseStrategy):
    """Statistical arbitrage on cointegrated forex pairs.

    Fires when the spread between two correlated instruments deviates
    significantly from its recent mean (Bollinger Band approach).
    """

    name = "pairs_spread"

    def __init__(
        self,
        broker=None,
        db=None,
        min_confidence: float = 0.55,
        min_zscore: float = 2.0,
        max_zscore: float = 3.5,
        bb_period: int = 20,
        bb_std: float = 2.0,
        lookback: int = 100,
    ) -> None:
        self._broker = broker
        self._db = db
        self.min_confidence = min_confidence
        self.min_zscore = min_zscore    # Entry threshold (|z| must exceed this)
        self.max_zscore = max_zscore    # Cap: beyond this, mean-reversion odds drop
        self._states: dict[str, SpreadState] = {}
        self._bb_period = bb_period
        self._bb_std = bb_std
        self._lookback = lookback
        self._symbols: set[str] = set()

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("strategy", level, msg, data)

    # ── BaseStrategy ─────────────────────────────────────────────────────

    def detect(self, context: MarketContext) -> Optional[Signal]:
        try:
            return self._detect_inner(context)
        except Exception:
            logger.exception("PairsSpreadStrategy.detect failed on %s", context.symbol)
            return None

    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        atr = context.atr if context.atr > 0 else 0.001
        if direction == "BUY":
            return round(context.current_price - atr * 1.5, 5)
        return round(context.current_price + atr * 1.5, 5)

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
                round(entry + 3.5 * risk, 5),
            )
        return (
            round(entry - risk, 5),
            round(entry - 2.0 * risk, 5),
            round(entry - 3.5 * risk, 5),
        )

    # ── Internal ────────────────────────────────────────────────────────

    def _detect_inner(self, ctx: MarketContext) -> Optional[Signal]:
        symbol = ctx.symbol

        # Find the PairDef this symbol belongs to
        pair_def = self._pair_for(symbol)
        if pair_def is None:
            return None

        secondary = pair_def.secondary
        hedge_ratio = pair_def.hedge_ratio

        # Get secondary candles from broker if not in context
        sec_candles = self._get_secondary_candles(ctx, secondary)
        if not sec_candles or len(sec_candles) < self._bb_period + 5:
            return None

        # Ensure spread state exists
        key = f"{symbol}/{secondary}"
        if key not in self._states:
            self._states[key] = SpreadState(
                lookback=self._lookback,
                bb_period=self._bb_period,
                bb_std=self._bb_std,
            )

        state = self._states[key]

        # Update spread with latest close prices
        pri_close = ctx.current_price
        sec_close = sec_candles[-1].close
        state.update(pri_close, sec_close, hedge_ratio)

        if not state.has_data:
            return None

        z = state.zscore

        # Determine direction
        # z > min_zscore → spread too wide → expect compression → SELL primary
        # z < -min_zscore → spread too narrow → expect expansion → BUY primary
        abs_z = abs(z)
        if abs_z < self.min_zscore:
            return None

        # Suppress extreme deviations (mean-reversion less reliable > max_zscore)
        if abs_z > self.max_zscore:
            self._emit("info", f"Pair spread {symbol}/{secondary}: z={z:.2f} > {self.max_zscore} — suppressing extreme deviation")
            return None

        direction = "SELL" if z > 0 else "BUY"

        # Confidence: scale with |z|, capped at min_confidence
        # z=2.0 → conf≈0.55, z=2.5 → conf≈0.70, z=3.0 → conf≈0.85
        confidence = min(0.95, self.min_confidence + (abs_z - self.min_zscore) * 0.15)
        if confidence < self.min_confidence:
            confidence = self.min_confidence

        # SL: place just outside the Bollinger band
        atr = ctx.atr if ctx.atr > 0 else 0.001
        entry_price = pri_close
        if direction == "BUY":
            sl_price = round(state.bb_lower - 0.5 * atr, 5)
        else:
            sl_price = round(state.bb_upper + 0.5 * atr, 5)

        # TPs: partial take-profit near the mean
        risk = abs(entry_price - sl_price)
        tp1 = round(entry_price + risk * 1.0, 5) if direction == "BUY" else round(entry_price - risk * 1.0, 5)
        tp2 = round(entry_price + risk * 2.0, 5) if direction == "BUY" else round(entry_price - risk * 2.0, 5)
        tp3 = round(entry_price + risk * 3.5, 5) if direction == "BUY" else round(entry_price - risk * 3.5, 5)

        reason = (
            f"PairsSpread: {symbol}/{secondary} z={z:.2f} "
            f"(spread_mean={state.mean:.5f}, bb_upper={state.bb_upper:.5f}, bb_lower={state.bb_lower:.5f}) → {direction}"
        )

        self._emit("info", reason)

        # Log to DB for backtest analytics
        self._log_spread_signal(symbol, secondary, z, confidence, direction)

        return Signal(
            strategy=self.name,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=confidence,
            timestamp=datetime.now(UTC),
            reason=reason,
            signal_intent=SignalIntent.EXECUTION,
            metadata={"spread_zscore": round(z, 3), "spread_mean": round(state.mean, 5)},
        )

    def _pair_for(self, symbol: str) -> Optional[PairDef]:
        for pd in PAIRS:
            if pd.primary == symbol or pd.secondary == symbol:
                return pd
        return None

    def _get_secondary_candles(self, ctx: MarketContext, secondary: str) -> list[Candle]:
        """Fetch M15 candles for the secondary symbol."""
        if self._broker is None:
            return []
        try:
            return self._broker.get_candles(secondary, "M15", self._bb_period + 10)
        except Exception:
            return []

    def _log_spread_signal(
        self,
        symbol: str,
        secondary: str,
        zscore: float,
        confidence: float,
        direction: str,
    ) -> None:
        """Log spread signal to DB (no-op if DB doesn't support log_indicator)."""
        if not self._db:
            return
        try:
            self._db.log_agent_event(
                "strategy",
                "info",
                f"PairsSpread {symbol}/{secondary} z={zscore:.2f} → {direction}",
                {"zscore": round(zscore, 3), "secondary": secondary, "confidence": confidence},
            )
        except Exception:
            logger.debug("Failed to log pairs spread signal", exc_info=True)
