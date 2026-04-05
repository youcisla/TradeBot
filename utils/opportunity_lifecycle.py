from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

from config import settings
from models.market_data import MarketContext
from models.signal import Signal
from models.trade import Trade


@dataclass
class OpportunityState:
    symbol: str
    phase: str = "WATCHING"
    bucket_start_ts: float = 0.0
    window_end_ts: float = 0.0
    phase_since_ts: float = 0.0
    leg1_direction: str = ""


class OpportunityLifecycleManager:
    """Tracks short-horizon opportunity state per symbol.

    Phase flow:
      WATCHING -> WAITING_HEDGE -> CYCLE_COMPLETE
    """

    def __init__(self) -> None:
        self._states: dict[str, OpportunityState] = {}

    def _is_enabled(self) -> bool:
        if not settings.OPPORTUNITY_PHASE_ENABLED:
            return False
        if settings.DEMO_MODE:
            return True
        return settings.OPPORTUNITY_LIVE_ENABLED

    @staticmethod
    def _bucket_start(now_ts: float) -> float:
        size = max(60, settings.OPPORTUNITY_ROLLOVER_SECONDS)
        return float(int(now_ts // size) * size)

    def _ensure_state(self, symbol: str, now_ts: float) -> OpportunityState:
        state = self._states.get(symbol)
        bucket_start = self._bucket_start(now_ts)
        if state is None:
            state = OpportunityState(
                symbol=symbol,
                bucket_start_ts=bucket_start,
                window_end_ts=bucket_start + max(30, settings.OPPORTUNITY_WATCH_WINDOW_SECONDS),
                phase_since_ts=now_ts,
            )
            self._states[symbol] = state
            return state

        if state.bucket_start_ts != bucket_start:
            state.phase = "WATCHING"
            state.bucket_start_ts = bucket_start
            state.window_end_ts = bucket_start + max(30, settings.OPPORTUNITY_WATCH_WINDOW_SECONDS)
            state.phase_since_ts = now_ts
            state.leg1_direction = ""

        return state

    def on_iteration_start(self, symbols: Iterable[str], open_trades: list[Trade]) -> list[str]:
        """Initialize/roll states each loop. Returns symbols rolled to new bucket."""
        if not self._is_enabled():
            return []

        now_ts = time.time()
        rolled: list[str] = []
        open_by_symbol = {t.symbol for t in open_trades if t.is_open()}

        for symbol in symbols:
            state = self._states.get(symbol)
            prev_bucket = state.bucket_start_ts if state else None
            state = self._ensure_state(symbol, now_ts)
            if prev_bucket is not None and prev_bucket != state.bucket_start_ts:
                rolled.append(symbol)

            # If cycle was waiting but no position is open anymore, close cycle.
            if state.phase == "WAITING_HEDGE" and symbol not in open_by_symbol:
                state.phase = "CYCLE_COMPLETE"
                state.phase_since_ts = now_ts

            # Timeout waiting hedge -> complete cycle for this bucket.
            if state.phase == "WAITING_HEDGE":
                wait_s = now_ts - state.phase_since_ts
                if wait_s >= max(30, settings.OPPORTUNITY_HEDGE_TIMEOUT_SECONDS):
                    state.phase = "CYCLE_COMPLETE"
                    state.phase_since_ts = now_ts

        return rolled

    def filter_ranked_signals(
        self,
        ranked: list[Signal],
        signal_contexts: dict[int, MarketContext],
    ) -> tuple[list[Signal], list[tuple[Signal, str]]]:
        """Filter signals based on phase state + shock gate.

        Returns: (approved_signals, rejected_with_reason)
        """
        if not self._is_enabled():
            return ranked, []

        now_ts = time.time()
        approved: list[Signal] = []
        rejected: list[tuple[Signal, str]] = []

        for sig in ranked:
            state = self._ensure_state(sig.symbol, now_ts)
            ctx = signal_contexts.get(id(sig))

            if state.phase == "WATCHING" and now_ts > state.window_end_ts:
                rejected.append((sig, "watch-window-expired"))
                continue

            if state.phase == "WAITING_HEDGE":
                # During waiting phase, only accept opposite direction with minimum confidence.
                if sig.direction == state.leg1_direction:
                    rejected.append((sig, "same-direction-during-hedge-wait"))
                    continue
                if sig.confidence < settings.OPPORTUNITY_MIN_RECOVERY_CONFIDENCE:
                    rejected.append((sig, "recovery-confidence-too-low"))
                    continue
                if ctx and ctx.current_price > 0:
                    spread_pct = (ctx.spread / ctx.current_price)
                    if spread_pct > settings.OPPORTUNITY_FALLBACK_MAX_SPREAD_PCT:
                        rejected.append((sig, "fallback-spread-cap-exceeded"))
                        continue

            if (
                settings.OPPORTUNITY_REQUIRE_SHOCK_FOR_FAST_LANE
                and sig.confidence >= settings.INSTANT_ENTRY_MIN_CONFIDENCE
            ):
                if not ctx or not ctx.shock_detected:
                    rejected.append((sig, "fast-lane-shock-required"))
                    continue

            approved.append(sig)

        return approved, rejected

    def register_trade_open(self, signal: Signal) -> None:
        if not self._is_enabled():
            return
        now_ts = time.time()
        state = self._ensure_state(signal.symbol, now_ts)
        state.phase = "WAITING_HEDGE"
        state.phase_since_ts = now_ts
        state.leg1_direction = signal.direction

    def register_trade_close(self, trade: Trade) -> None:
        if not self._is_enabled():
            return
        now_ts = time.time()
        state = self._ensure_state(trade.symbol, now_ts)
        state.phase = "CYCLE_COMPLETE"
        state.phase_since_ts = now_ts

    def snapshot(self, symbol: str) -> OpportunityState | None:
        return self._states.get(symbol)
