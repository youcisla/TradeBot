"""Session Range Breakout Strategy.

Exploits the predictable volatility expansion that occurs at the open of major
forex sessions (London, Overlap, NY).  The logic:

  1. PRE-SESSION CONSOLIDATION  — track the H/L of the N candles immediately
     before a session open.
  2. BREAKOUT CONFIRMATION      — when the first session candle closes beyond
     that range, the range is expanding in that direction.
  3. ENTRY / SL / TPs           — enter on the close of the confirming candle,
     SL just inside the consolidation boundary, TPs at 1R / 2R / 3R.

This is orthogonal to both ICT (no HTF bias required) and PairsSpread
(no cointegration needed).  Session-range breakouts are driven by
liquidity — not by mean-reversion or momentum indicators — making them a
genuinely separate alpha source.

Compatible timeframes: M15 (primary).
Compatible symbols: forex majors and minors.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional

from models.market_data import Candle, MarketContext
from models.signal import Signal, SignalIntent
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


# ── Config ────────────────────────────────────────────────────────────────────

PRE_CANDLES            = 3    # M15 candles before open to measure consolidation
ATR_FILTER_MULTIPLIER  = 0.8  # breakout must be ≥ this many ATRs from range boundary
MIN_CANDLES            = 5    # minimum m15_candles to run detection
MIN_RANGE_PIPS        = 3    # skip if consolidation is tighter than this
MAX_RANGE_PIPS         = 50  # skip if consolidation is wider than this (chop)


# ── Session definition ──────────────────────────────────────────────────────────

# Each tracked session: open time in HHMM UTC, duration in M15 candle count
SESSIONS = [
    {"id": "london",  "open_hm": 700,  "duration_bars": 36},   # 07:00–16:00
    {"id": "overlap", "open_hm": 1200, "duration_bars": 16},   # 12:00–16:00
    {"id": "ny",      "open_hm": 1600, "duration_bars": 20},   # 16:00–21:00
]


@dataclass
class SessionRange:
    """Pre-session high/low recorded when a session opens."""
    session_id: str
    range_high: float
    range_low: float
    open_bar_ts: datetime
    breakout_dir: str = ""     # set when breakout is confirmed
    fired: bool = False        # True once we've emitted a signal for this range


class SessionRangeTracker:
    """Tracks pre-session range for all sessions per symbol.

    Maintains a rolling deque of M15 candles.  On every `evaluate()` call:
      - Detects if we're at the open of a new session → records the range.
      - Detects if the first session candle just closed beyond that range →
        emits a Signal.
    """

    def __init__(self, pre_candles: int = PRE_CANDLES) -> None:
        self._pre = pre_candles
        self._candles: deque[Candle] = deque(maxlen=300)
        self._pending: SessionRange | None = None   # range waiting for confirmation

    def update(self, candle: Candle) -> None:
        self._candles.append(candle)

    def _hm(self, ts: datetime) -> int:
        """HHMM integer from a UTC-aware datetime."""
        return ts.hour * 100 + ts.minute

    def _new_session_open(self, candle_ts: datetime, open_hm: int) -> bool:
        """True when candle_ts is the first bar ON or AFTER the session open.

        For M15 candles: the bar with ts >= open_hm, where the prior bar had
        ts < open_hm.  We approximate by checking if candle_ts.hour*100+minute
        equals the open_hm (the first bar of the session) and the prior bar's
        ts is in the prior 15-minute window.
        """
        cur_hm = self._hm(candle_ts)
        if cur_hm != open_hm:
            return False
        # Prior candle must be from the pre-open window (open_hm - 15 or lower)
        if len(self._candles) < 2:
            return True   # first candle of the day — treat as potential open
        prev_ts = self._candles[-2].timestamp
        prev_hm = self._hm(prev_ts)
        # Accept if prior bar is from the half-hour before open or earlier
        return prev_hm < open_hm

    def _within_session(self, candle_ts: datetime, open_hm: int, duration_bars: int) -> bool:
        """True while we are still inside the session window."""
        cur_hm  = self._hm(candle_ts)
        open_h  = open_hm // 100
        open_m  = open_hm % 100
        # Minutes since midnight of session open
        cur_min_from_midnight = candle_ts.hour * 60 + candle_ts.minute
        open_min_from_midnight = open_h * 60 + open_m
        elapsed_bars = (cur_min_from_midnight - open_min_from_midnight) / 15
        return 0 <= elapsed_bars < duration_bars

    def evaluate(self, candles: list[Candle]) -> Optional[Signal]:
        """Return a Signal if a session-range breakout just confirmed, else None."""
        if len(candles) < MIN_CANDLES:
            return None

        # Feed all new candles into the rolling window
        for c in candles:
            if not self._candles or self._candles[-1].timestamp != c.timestamp:
                self._candles.append(c)

        latest = self._candles[-1]
        latest_hm = self._hm(latest.timestamp)

        # ── 1. Check if we're at a new session open → record range ────────────
        for sess in SESSIONS:
            open_hm = sess["open_hm"]
            sid = sess["id"]

            if self._new_session_open(latest.timestamp, open_hm):
                # Collect the PRE_CANDLES before this open
                pre_bars = [c for c in self._candles if self._hm(c.timestamp) < open_hm]
                pre_bars = pre_bars[-self._pre:] if len(pre_bars) >= self._pre else []
                if len(pre_bars) < self._pre:
                    continue

                self._pending = SessionRange(
                    session_id=sid,
                    range_high=max(c.high for c in pre_bars),
                    range_low=min(c.low  for c in pre_bars),
                    open_bar_ts=latest.timestamp,
                )
                return None   # open detected, wait for confirmation next candle

        # ── 2. Do we have a pending range to confirm? ────────────────────────
        if self._pending is None or self._pending.fired:
            return None

        sess_def = next((s for s in SESSIONS if s["id"] == self._pending.session_id), None)
        if sess_def is None:
            self._pending = None
            return None

        # Has the session expired before we confirmed?
        if not self._within_session(
            latest.timestamp,
            sess_def["open_hm"],
            sess_def["duration_bars"],
        ):
            self._pending = None
            return None

        # We need at least 2 bars to confirm: the open bar + the confirming bar
        if len(self._candles) < 2:
            return None
        open_bar    = self._candles[-2]   # first bar of the session
        confirm_bar = self._candles[-1]   # second bar of the session — the confirm

        # Only evaluate on the CONFIRMING bar (first close after the session open)
        if self._hm(confirm_bar.timestamp) - self._hm(open_bar.timestamp) > 30:
            return None   # this is not the confirming candle — skip

        range_high = self._pending.range_high
        range_low  = self._pending.range_low

        # ── 3. Detect breakout direction ──────────────────────────────────────
        direction  = ""
        sl_price   = 0.0
        breakout_r = 0.0

        # Use the confirming bar's close as entry; use ATR from context
        atr = 0.001  # will be overridden by ctx.atr in the strategy call

        if confirm_bar.close > range_high:
            breakout_r  = (confirm_bar.close - range_high) / atr if atr > 0 else 0
            if breakout_r < ATR_FILTER_MULTIPLIER:
                return None
            direction = "BUY"
            sl_price = range_low
        elif confirm_bar.close < range_low:
            breakout_r  = (range_low - confirm_bar.close) / atr if atr > 0 else 0
            if breakout_r < ATR_FILTER_MULTIPLIER:
                return None
            direction = "SELL"
            sl_price = range_high

        if not direction:
            return None   # still inside range

        # ── 4. Build Signal ─────────────────────────────────────────────────
        entry_price = confirm_bar.close
        risk = abs(entry_price - sl_price)
        if risk <= 0:
            return None

        tp1 = round(entry_price + risk * 1.0, 5) if direction == "BUY" else round(entry_price - risk * 1.0, 5)
        tp2 = round(entry_price + risk * 2.0, 5) if direction == "BUY" else round(entry_price - risk * 2.0, 5)
        tp3 = round(entry_price + risk * 3.0, 5) if direction == "BUY" else round(entry_price - risk * 3.0, 5)

        range_pips = (range_high - range_low) / entry_price * 10000

        # Suppress if consolidation is too tight or too wide
        if range_pips < MIN_RANGE_PIPS or range_pips > MAX_RANGE_PIPS:
            self._pending = None
            return None

        self._pending.fired = True   # mark so we don't re-fire for this range

        reason = (
            f"SessionRange: {self._pending.session_id} breakout {direction} "
            f"@ {entry_price:.5f} "
            f"(consolidation={range_pips:.1f}pips, ATR={atr:.5f}, breakout={breakout_r:.2f}×ATR)"
        )

        return Signal(
            strategy="session_range",
            symbol="",         # filled by strategy layer
            direction=direction,
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=0.65,
            timestamp=datetime.now(UTC),
            reason=reason,
            signal_intent=SignalIntent.EXECUTION,
            metadata={
                "session": f"{self._pending.session_id}_session",
                "range_high": round(range_high, 5),
                "range_low": round(range_low, 5),
                "range_pips": round(range_pips, 1),
                "breakout_atr": round(breakout_r, 2),
            },
        )


# ── Strategy ────────────────────────────────────────────────────────────────────

class SessionRangeStrategy(BaseStrategy):
    """Session-range breakout — fires at the open of major forex sessions."""

    name = "session_range"

    def __init__(
        self,
        broker=None,
        db=None,
        pre_candles: int = PRE_CANDLES,
        atr_filter: float = ATR_FILTER_MULTIPLIER,
        min_confidence: float = 0.55,
    ) -> None:
        self._broker = broker
        self._db      = db
        self._pre_candles = pre_candles
        self._atr_filter  = atr_filter
        self._min_confidence = min_confidence
        self._trackers: dict[str, SessionRangeTracker] = {}

    def _tracker_for(self, symbol: str) -> SessionRangeTracker:
        if symbol not in self._trackers:
            self._trackers[symbol] = SessionRangeTracker(pre_candles=self._pre_candles)
        return self._trackers[symbol]

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if not self._db:
            return
        try:
            self._db.log_agent_event("strategy", level, msg, data)
        except Exception:
            logger.debug("Failed to emit strategy event", exc_info=True)

    # ── BaseStrategy ─────────────────────────────────────────────────────────

    def detect(self, context: MarketContext) -> Optional[Signal]:
        try:
            return self._detect_inner(context)
        except Exception:
            logger.exception("SessionRangeStrategy.detect failed on %s", context.symbol)
            return None

    def _detect_inner(self, ctx: MarketContext) -> Optional[Signal]:
        if not ctx.m15_candles:
            return None

        tracker = self._tracker_for(ctx.symbol)
        for candle in ctx.m15_candles[-20:]:
            tracker.update(candle)

        sig = tracker.evaluate(ctx.m15_candles)
        if sig is None:
            return None

        # Override ATR with context value (more accurate than placeholder)
        atr = ctx.atr if ctx.atr > 0 else 0.001
        sig.symbol = ctx.symbol

        # Recalculate SL/TPs with real ATR
        entry = sig.entry_price
        direction = sig.direction
        raw_sl = sig.stop_loss

        # Re-strike SL to use ATR distance from range boundary
        if direction == "BUY":
            raw_sl = sig.metadata.get("range_low", ctx.current_price - atr * 1.5)
            sl_price = round(float(raw_sl) - 0.2 * atr, 5)
        else:
            raw_sl = sig.metadata.get("range_high", ctx.current_price + atr * 1.5)
            sl_price = round(float(raw_sl) + 0.2 * atr, 5)

        risk = abs(entry - sl_price)
        sig.stop_loss = sl_price
        sig.take_profit_1 = round(entry + risk * 1.0, 5) if direction == "BUY" else round(entry - risk * 1.0, 5)
        sig.take_profit_2 = round(entry + risk * 2.0, 5) if direction == "BUY" else round(entry - risk * 2.0, 5)
        sig.take_profit_3 = round(entry + risk * 3.0, 5) if direction == "BUY" else round(entry - risk * 3.0, 5)

        # Recompute breakout_r with real ATR
        if direction == "BUY":
            breakout_r = (entry - sig.metadata.get("range_high", entry)) / atr
        else:
            breakout_r = (sig.metadata.get("range_low", entry) - entry) / atr
        sig.metadata["breakout_atr"] = round(breakout_r, 2)

        self._emit("info", sig.reason, sig.metadata)
        return sig

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
                round(entry + risk * 1.0, 5),
                round(entry + risk * 2.0, 5),
                round(entry + risk * 3.0, 5),
            )
        return (
            round(entry - risk * 1.0, 5),
            round(entry - risk * 2.0, 5),
            round(entry - risk * 3.0, 5),
        )
