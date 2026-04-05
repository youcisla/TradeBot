"""exposure_coach.py — portfolio-level exposure advisor.

Scans open trades and emits over-concentration warnings and sizing
recommendations. Does NOT block trades — it advises the ExecutionAgent
and logs alerts via EventLog.

Usage::

    from agents.exposure_coach import ExposureCoach

    coach = ExposureCoach()
    advice = coach.evaluate(open_trades, new_signal)
    if advice.is_overexposed:
        adjusted_lots = advice.suggested_lots
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.signal import Signal
    from models.trade import Trade

logger = logging.getLogger(__name__)

# ── Correlated currency pairs ─────────────────────────────────────────────
# Pairs sharing a base or quote currency with high positive correlation.
_CORR_GROUPS: list[frozenset[str]] = [
    frozenset({"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"}),   # USD shorts
    frozenset({"USDCHF", "USDJPY", "USDCAD"}),             # USD longs
    frozenset({"XAUUSD", "XAGUSD"}),                        # metals
    frozenset({"BTCUSD", "ETHUSD", "LTCUSD"}),             # crypto
    frozenset({"EURJPY", "GBPJPY", "AUDJPY"}),             # JPY pairs
]

_MAX_CORR_EXPOSURE_LOTS = 0.20   # max cumulative lots in same correlation group
_MAX_TOTAL_EXPOSURE_LOTS = 0.50  # max total lots across all open positions
_MAX_SAME_SYMBOL_LOTS = 0.10     # max lots in one symbol


@dataclass
class ExposureAdvice:
    is_overexposed: bool
    reason: str
    suggested_lots: float          # ≥ 0; 0 means "do not open"
    current_total_lots: float
    current_symbol_lots: float
    correlation_group_lots: float


class ExposureCoach:
    """Evaluates whether a new trade would create dangerous concentration."""

    def evaluate(
        self,
        open_trades: list,
        signal: "Signal",
        requested_lots: float,
    ) -> ExposureAdvice:
        """Return sizing advice for *signal* given the current open book.

        Parameters
        ----------
        open_trades: list of Trade objects (need .symbol, .lot_size attributes)
        signal: proposed signal being evaluated
        requested_lots: lot size the execution agent wants to use
        """
        symbol = getattr(signal, "symbol", "")

        # Aggregate exposure
        total_lots = sum(getattr(t, "lot_size", 0.0) for t in open_trades)
        same_symbol_lots = sum(
            getattr(t, "lot_size", 0.0)
            for t in open_trades
            if getattr(t, "symbol", "") == symbol
        )
        corr_lots = self._correlated_lots(open_trades, symbol)

        reason = ""
        is_over = False
        suggested = requested_lots

        # Check total portfolio cap
        if total_lots + requested_lots > _MAX_TOTAL_EXPOSURE_LOTS:
            headroom = max(0.0, _MAX_TOTAL_EXPOSURE_LOTS - total_lots)
            if headroom < 0.01:
                is_over = True
                reason = (
                    f"Total portfolio exposure {total_lots:.3f} lots "
                    f"would exceed {_MAX_TOTAL_EXPOSURE_LOTS:.2f} limit"
                )
                suggested = 0.0
            else:
                suggested = min(suggested, headroom)
                reason = f"Sizing capped to {headroom:.3f}L (portfolio cap)"

        # Check same-symbol cap
        if not is_over and same_symbol_lots + suggested > _MAX_SAME_SYMBOL_LOTS:
            headroom = max(0.0, _MAX_SAME_SYMBOL_LOTS - same_symbol_lots)
            if headroom < 0.01:
                is_over = True
                reason = (
                    f"{symbol} already at {same_symbol_lots:.3f}L "
                    f"(max {_MAX_SAME_SYMBOL_LOTS:.2f})"
                )
                suggested = 0.0
            else:
                suggested = min(suggested, headroom)
                reason = f"{symbol} sizing capped to {headroom:.3f}L"

        # Check correlated group cap
        if not is_over and corr_lots + suggested > _MAX_CORR_EXPOSURE_LOTS:
            headroom = max(0.0, _MAX_CORR_EXPOSURE_LOTS - corr_lots)
            if headroom < 0.01:
                is_over = True
                reason = (
                    f"Correlated group exposure {corr_lots:.3f}L "
                    f"would breach {_MAX_CORR_EXPOSURE_LOTS:.2f}L limit"
                )
                suggested = 0.0
            else:
                suggested = min(suggested, headroom)
                reason = f"Correlated group sizing capped to {headroom:.3f}L"

        if not reason:
            reason = "ok"

        if reason != "ok":
            logger.info("ExposureCoach [%s]: %s", symbol, reason)

        return ExposureAdvice(
            is_overexposed=is_over,
            reason=reason,
            suggested_lots=round(suggested, 3),
            current_total_lots=total_lots,
            current_symbol_lots=same_symbol_lots,
            correlation_group_lots=corr_lots,
        )

    @staticmethod
    def _correlated_lots(open_trades: list, symbol: str) -> float:
        """Sum lots for all trades in the same correlation group as *symbol*."""
        group: frozenset[str] | None = None
        for g in _CORR_GROUPS:
            if symbol in g:
                group = g
                break
        if group is None:
            return 0.0
        return sum(
            getattr(t, "lot_size", 0.0)
            for t in open_trades
            if getattr(t, "symbol", "") in group
        )
