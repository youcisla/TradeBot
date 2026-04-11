"""SniperEntryGuard — confidence-split Fibonacci sniper entry gate.

Replaces the CouncilAgent / DeepSeek LLM gate with a deterministic,
no-API-required sniper entry logic:

  CONFIDENT (conf >= SNIPER_CONF_THRESHOLD)
      → instant execution, no waiting

  UNCERTAIN (conf < SNIPER_CONF_THRESHOLD)
      → add to sniper watchlist
      → each iteration: has price pulled back into Fibonacci zone?
          YES + within ATR distance → execute (sniper entry)
          NO  → keep waiting until SNIPER_TIMEOUT_MINUTES, then skip

The Fibonacci check uses the existing strategies/ict/fibonacci.py engine.
No external API calls — fully autonomous.
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from models.market_data import Candle, MarketContext
from models.signal import Signal

if TYPE_CHECKING:
    from strategies.ict.engine import ICTEngine

logger = logging.getLogger(__name__)


class SniperVerdict(Enum):
    APPROVED = "approved"        # confident → execute immediately
    HOLD = "hold"                # uncertain → watchlist pending pullback
    SNIPER_CONFIRMED = "sniper_confirmed"  # pullback detected → execute sniper
    EXPIRED = "expired"          # timeout reached → skip
    SKIPPED = "skipped"          # price moved past zone → skip


@dataclass
class SniperCandidate:
    signal: Signal
    added_at: float                    # time.time() when added to watchlist
    entry_price: float                 # snapshotted at detect time
    atr: float                          # ATR at detect time
    direction: str                      # BUY or SELL
    symbol: str
    fib_depth: str = ""                # last known retracement depth


class SniperEntryGuard:
    """Fibonacci-backed sniper entry gate.

    Operates in two modes:
    - Instant: confidence >= threshold → execute immediately
    - Sniper:  confidence <  threshold → wait for pullback into Fibonacci zone
    """

    def __init__(
        self,
        broker=None,
        db=None,
        threshold: float = 0.65,
        timeout_minutes: float = 30.0,
        max_entry_atr_distance: float = 0.55,
        fib_min_depth: str = "acceptable",   # minimum retracement to accept
        fib_max_depth: str = "deep",        # maximum retracement before skipping
    ) -> None:
        self._broker = broker
        self._db = db
        self._threshold = threshold
        self._timeout_seconds = timeout_minutes * 60.0
        self._max_entry_atr = max_entry_atr_distance
        self._fib_min_depth = fib_min_depth
        self._fib_max_depth = fib_max_depth
        self._watchlist: list[SniperCandidate] = []
        # Ordered from best to worst retracement quality.
        # index() gives the ordinal rank — lower is better.
        self._depth_ordinal: tuple[str, ...] = (
            "golden_zone", "acceptable", "deep",
            "too_shallow", "too_deep", "outside",
        )
        self._engine: Optional[ICTEngine] = None  # lazily created
        self._load_watchlist()

    # ── Watchlist persistence (bot_memory table) ─────────────────────

    _WATCHLIST_BLOCK = "sniper_watchlist"

    def _candidate_to_dict(self, c: SniperCandidate) -> dict:
        """Serialize a SniperCandidate to a JSON-safe dict."""
        return {
            "added_at": c.added_at,
            "entry_price": c.entry_price,
            "atr": c.atr,
            "direction": c.direction,
            "symbol": c.symbol,
            "fib_depth": c.fib_depth,
            # Store only the essential signal fields needed for re-evaluation
            "signal_strategy": c.signal.strategy,
            "signal_direction": c.signal.direction,
            "signal_entry_price": c.signal.entry_price,
            "signal_stop_loss": c.signal.stop_loss,
            "signal_tp1": c.signal.take_profit_1,
            "signal_confidence": c.signal.confidence,
            "signal_reason": c.signal.reason,
            "signal_timestamp": c.signal.timestamp.isoformat() if c.signal.timestamp else "",
        }

    def _dict_to_candidate(self, d: dict) -> SniperCandidate:
        """Reconstruct a SniperCandidate from a serialized dict."""
        # Reconstruct a minimal Signal
        sig = Signal(
            strategy=d["signal_strategy"],
            symbol=d["symbol"],          # restore symbol that was saved separately
            direction=d["signal_direction"],
            entry_price=d["signal_entry_price"],
            stop_loss=d["signal_stop_loss"],
            take_profit_1=d["signal_tp1"],
            confidence=d["signal_confidence"],
            reason=d["signal_reason"],
            timestamp=datetime.fromisoformat(d["signal_timestamp"]) if d.get("signal_timestamp") else datetime.now(UTC),
        )
        return SniperCandidate(
            signal=sig,
            added_at=d["added_at"],
            entry_price=d["entry_price"],
            atr=d["atr"],
            direction=d["direction"],
            symbol=d["symbol"],
            fib_depth=d.get("fib_depth", ""),
        )

    def _save_watchlist(self) -> None:
        """Persist current watchlist to bot_memory so it survives bot restarts."""
        if not self._db:
            return
        try:
            data = [self._candidate_to_dict(c) for c in self._watchlist]
            self._db.write_memory_block(self._WATCHLIST_BLOCK, json.dumps(data))
            logger.debug("SniperEntryGuard: saved %d candidates to DB", len(data))
        except Exception as exc:
            logger.debug("SniperEntryGuard: could not save watchlist: %s", exc)

    def _load_watchlist(self) -> None:
        """Restore watchlist from bot_memory on startup."""
        if not self._db:
            return
        try:
            raw = self._db.read_memory_block(self._WATCHLIST_BLOCK)
            if not raw:
                return
            items = json.loads(raw)
            if not items:
                return
            self._watchlist = [self._dict_to_candidate(d) for d in items]
            logger.info(
                "SniperEntryGuard: restored %d candidates from persistent watchlist "
                "(timeout=%.0fmin)",
                len(self._watchlist), self._timeout_seconds / 60,
            )
        except Exception as exc:
            logger.debug("SniperEntryGuard: could not load watchlist: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────

    def review(self, signal: Signal, context: MarketContext) -> SniperVerdict:
        """Main entry point — called once per signal per iteration.

        Returns:
          APPROVED         — confident signal, execute immediately
          HOLD             — uncertain signal, added to watchlist
          SNIPER_CONFIRMED — watchlisted signal has pulled back into Fibonacci zone
          EXPIRED          — watchlisted signal timed out
          SKIPPED          — price moved past zone for a watchlisted signal
        """
        if signal.confidence >= self._threshold:
            logger.info(
                "SniperGuard CONFIDENT %s %s conf=%.2f >= %.2f → APPROVED",
                signal.symbol, signal.direction, signal.confidence, self._threshold,
            )
            return SniperVerdict.APPROVED

        # Uncertain — check if already on watchlist
        existing = self._find(signal.symbol, signal.direction)
        if existing is not None:
            verdict = self._check_watchlist(existing, context)
            return verdict

        # New uncertain signal — add to watchlist
        candidate = SniperCandidate(
            signal=signal,
            added_at=time.time(),
            entry_price=signal.entry_price,
            atr=context.atr if context.atr > 0 else 0.001,
            direction=signal.direction,
            symbol=signal.symbol,
        )
        self._watchlist.append(candidate)
        self._save_watchlist()
        logger.info(
            "SniperGuard UNCERTAN %s %s conf=%.2f < %.2f → HOLD (watchlist, timeout=%.0fm)",
            signal.symbol, signal.direction, signal.confidence, self._threshold,
            self._timeout_seconds / 60,
        )
        return SniperVerdict.HOLD

    def on_iteration(self, contexts: dict[str, MarketContext]) -> list[SniperVerdict]:
        """Called every iteration to advance the watchlist.

        Returns list of verdicts for signals that changed state.
        """
        changed: list[tuple[SniperVerdict, SniperCandidate]] = []

        for candidate in self._watchlist:
            ctx = contexts.get(candidate.symbol)
            if ctx is None:
                continue

            verdict = self._check_watchlist(candidate, ctx)
            if verdict == SniperVerdict.HOLD:
                continue  # stays on watchlist
            else:
                changed.append((verdict, candidate))

        # Remove confirmed/skipped/expired candidates and persist
        if changed:
            executed_symbols = {c.symbol for _, c in changed}
            self._watchlist = [c for c in self._watchlist if c.symbol not in executed_symbols]
            self._save_watchlist()

        return changed

    def prune_expired(self) -> list[SniperCandidate]:
        """Remove and return all expired candidates."""
        now = time.time()
        expired = [c for c in self._watchlist if now - c.added_at >= self._timeout_seconds]
        self._watchlist = [c for c in self._watchlist if now - c.added_at < self._timeout_seconds]
        if expired:
            logger.info("SniperGuard: pruned %d expired watchlist entries", len(expired))
            self._save_watchlist()
        return expired

    def get_watchlist_size(self) -> int:
        return len(self._watchlist)

    def get_watchlist(self) -> list[SniperCandidate]:
        return list(self._watchlist)

    # ── Internal ────────────────────────────────────────────────────────

    def _find(self, symbol: str, direction: str) -> SniperCandidate | None:
        for c in self._watchlist:
            if c.symbol == symbol and c.direction == direction:
                return c
        return None

    def remove(self, symbol: str, direction: str) -> None:
        """Remove a candidate from the watchlist by symbol and direction."""
        self._watchlist = [
            c for c in self._watchlist
            if not (c.symbol == symbol and c.direction == direction)
        ]
        self._save_watchlist()

    def _check_watchlist(
        self, candidate: SniperCandidate, ctx: MarketContext
    ) -> SniperVerdict:
        """Re-evaluate a watchlisted candidate against current market context."""
        now = time.time()
        age = now - candidate.added_at

        # Timeout check
        if age >= self._timeout_seconds:
            logger.info(
                "SniperGuard EXPIRED %s %s after %.0fs on watchlist",
                candidate.symbol, candidate.direction, age,
            )
            return SniperVerdict.EXPIRED

        current_price = ctx.current_price
        entry = candidate.entry_price
        atr = candidate.atr
        direction = candidate.direction

        # Has price moved past the zone?
        stale_reason = self._is_stale(current_price, entry, atr, direction)
        if stale_reason:
            logger.info(
                "SniperGuard SKIPPED %s %s — price %s (entry=%.5f current=%.5f)",
                candidate.symbol, candidate.direction, stale_reason, entry, current_price,
            )
            return SniperVerdict.SKIPPED

        # Check Fibonacci retracement depth
        fib_depth = self._get_fib_depth(ctx, candidate)
        candidate.fib_depth = fib_depth

        try:
            fib_ord = self._depth_ordinal.index(fib_depth)
            max_ord = self._depth_ordinal.index(self._fib_max_depth)
            min_ord = self._depth_ordinal.index(self._fib_min_depth)
            depth_ok = min_ord <= fib_ord <= max_ord
        except ValueError:
            depth_ok = True  # fail open — allow entry if depth classification is ambiguous
        if not depth_ok:
            logger.debug(
                "SniperGuard HOLD %s %s — fib_depth=%s not in [%s, %s]",
                candidate.symbol, candidate.direction, fib_depth,
                self._fib_min_depth, self._fib_max_depth,
            )
            return SniperVerdict.HOLD

        # Price is in a valid Fibonacci zone and within ATR distance → sniper execute
        logger.info(
            "SniperGuard SNIPER_CONFIRMED %s %s — fib_depth=%s price=%.5f "
            "entry=%.5f age=%.0fs → execute",
            candidate.symbol, candidate.direction, fib_depth, current_price, entry, age,
        )
        return SniperVerdict.SNIPER_CONFIRMED

    def _is_stale(
        self, current_price: float, entry_price: float, atr: float, direction: str
    ) -> str | None:
        """Return None if fresh, or a reason string if price moved past zone."""
        if atr <= 0:
            atr = 0.001

        overshoot = abs(current_price - entry_price)
        max_allowed = self._max_entry_atr * atr

        if overshoot > max_allowed:
            return f"price {overshoot/atr:.2f}× ATR past zone (max={self._max_entry_atr})"

        # Direction-specific staleness
        if direction == "BUY" and current_price < entry_price - max_allowed:
            return f"price pulled back too far (%.5f < entry %.5f)" % (current_price, entry_price)
        if direction == "SELL" and current_price > entry_price + max_allowed:
            return f"price bounced too far (%.5f > entry %.5f)" % (current_price, entry_price)

        return None

    def _get_fib_depth(self, ctx: MarketContext, candidate: SniperCandidate) -> str:
        """Run a lightweight Fibonacci depth check on current candles."""
        try:
            from strategies.ict.fibonacci import (
                detect_fib_levels,
                validate_retracement_depth,
            )

            # Lazily create and reuse the ICTEngine instance across calls
            if self._engine is None:
                from strategies.ict.engine import ICTEngine
                self._engine = ICTEngine(min_confidence=35.0)

            # Get HTF candles for the fib anchor
            htf_candles: list[Candle] = []
            if candidate.atr > 10:
                # Crypto: use H4 HTF
                try:
                    htf_candles = self._broker.get_candles(candidate.symbol, "H4", 100)
                except Exception:
                    pass

            # Build a minimal displacement list from the current candles
            # We need displacement to anchor Fibonacci — use ICTEngine to get it
            ict_ctx, _, _ = self._engine.analyze(
                symbol=candidate.symbol,
                candles=ctx.candles[-200:] if len(ctx.candles) >= 200 else ctx.candles,
                htf_candles=htf_candles,
                current_price=ctx.current_price,
                bid=ctx.bid,
                ask=ctx.ask,
                atr=candidate.atr,
                timeframe="H1",
            )

            fib = detect_fib_levels(
                candles=ctx.candles,
                displacements=ict_ctx.displacements,
                swing_highs=ict_ctx.swing_highs,
                swing_lows=ict_ctx.swing_lows,
                htf_bias=ict_ctx.htf_bias,
            )

            if fib is None:
                return "acceptable"  # Fallback: allow entry if fib can't be computed

            depth = validate_retracement_depth(fib, ctx.current_price)
            return depth

        except Exception as exc:
            logger.debug("Fib depth check failed for %s: %s", candidate.symbol, exc)
            return "acceptable"  # Fail open — allow sniper entry if fib check errors

    # ── Settings interface ─────────────────────────────────────────────

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def timeout_minutes(self) -> float:
        return self._timeout_seconds / 60.0
