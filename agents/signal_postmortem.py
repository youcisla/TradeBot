"""signal_postmortem.py — retrospective signal quality analyser.

After a trade is closed, ``SignalPostmortem.analyse()`` scores the original
signal against the actual trade outcome. The result is appended to the
EventLog and optionally fed back into the LearningAgent's confidence model.

Metrics produced:

    - ``entry_timing_score``  — how close to the actual swing low/high
    - ``direction_correct``   — did the signal direction match outcome
    - ``rr_achieved``         — actual R:R vs planned R:R
    - ``label``               — "great" | "ok" | "poor" | "wrong_direction"

Usage::

    from agents.signal_postmortem import SignalPostmortem

    pm = SignalPostmortem(event_log=log)
    result = pm.analyse(signal=sig, trade=closed_trade)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.signal import Signal
    from models.trade import Trade
    from state.event_log import EventLog

logger = logging.getLogger(__name__)


@dataclass
class PostmortemResult:
    symbol: str
    direction: str
    direction_correct: bool
    entry_timing_score: float   # 0.0 (worst) … 1.0 (perfect)
    rr_achieved: float          # actual R:R; negative = loss
    rr_planned: float
    rr_efficiency: float        # rr_achieved / rr_planned; 1 = hit TP fully
    confidence_at_entry: float
    label: str
    analysed_at: datetime


class SignalPostmortem:
    """Scores closed trades against their originating signals."""

    def __init__(self, event_log: "EventLog | None" = None) -> None:
        self._log = event_log

    def analyse(self, signal: "Signal", trade: "Trade") -> PostmortemResult:
        """Produce a postmortem for one closed trade.

        Falls back gracefully when attributes are missing (older Trade objects).
        """
        symbol = getattr(signal, "symbol", "")
        direction = getattr(signal, "direction", "unknown")
        confidence = getattr(signal, "confidence", 0.5)

        # ── Direction correctness ─────────────────────────────────────────
        pnl = getattr(trade, "pnl", None) or getattr(trade, "profit", None) or 0.0
        direction_correct = pnl > 0

        # ── Entry timing score ────────────────────────────────────────────
        # How close was the entry price to the optimal swing level?
        # Uses signal.entry_price vs signal.stop_loss distance as ATR proxy.
        entry_score = self._entry_timing_score(signal)

        # ── R:R achieved ──────────────────────────────────────────────────
        entry_price = getattr(signal, "entry_price", 0.0) or getattr(trade, "entry_price", 0.0)
        sl = getattr(signal, "stop_loss", 0.0) or getattr(trade, "stop_loss", 0.0)
        tp = getattr(signal, "take_profit", 0.0) or getattr(trade, "take_profit", 0.0)
        exit_price = getattr(trade, "exit_price", None) or getattr(trade, "close_price", 0.0)

        risk_dist = abs(entry_price - sl) if entry_price and sl else 1.0
        reward_dist = abs(tp - entry_price) if tp and entry_price else 0.0
        rr_planned = reward_dist / risk_dist if risk_dist > 0 else 1.0

        if exit_price and entry_price and risk_dist:
            actual_move = abs(exit_price - entry_price)
            signed_move = (exit_price - entry_price) * (1 if direction == "BUY" else -1)
            rr_achieved = signed_move / risk_dist
        else:
            rr_achieved = 1.0 if pnl > 0 else -1.0

        rr_efficiency = (rr_achieved / rr_planned) if rr_planned > 0 else 0.0

        # ── Label ─────────────────────────────────────────────────────────
        label = self._classify(direction_correct, rr_achieved, entry_score)

        result = PostmortemResult(
            symbol=symbol,
            direction=direction,
            direction_correct=direction_correct,
            entry_timing_score=round(entry_score, 3),
            rr_achieved=round(rr_achieved, 3),
            rr_planned=round(rr_planned, 3),
            rr_efficiency=round(rr_efficiency, 3),
            confidence_at_entry=round(confidence, 3),
            label=label,
            analysed_at=datetime.now(timezone.utc),
        )

        self._log_result(result)
        return result

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _entry_timing_score(signal: "Signal") -> float:
        """Score entry precision using ICT zone proximity."""
        # If signal carries an `fvg_proximity` attribute (0-1) use it.
        fvg_prox = getattr(signal, "fvg_proximity", None)
        if fvg_prox is not None:
            return float(max(0.0, min(1.0, fvg_prox)))
        # Fall back to confidence as a rough proxy.
        return float(getattr(signal, "confidence", 0.5))

    @staticmethod
    def _classify(correct: bool, rr: float, entry_score: float) -> str:
        if not correct:
            return "wrong_direction"
        if rr >= 1.5 and entry_score >= 0.7:
            return "great"
        if rr >= 0.5:
            return "ok"
        return "poor"

    def _log_result(self, result: PostmortemResult) -> None:
        if self._log is None:
            return
        try:
            self._log.emit("signal_postmortem", {
                "symbol": result.symbol,
                "direction": result.direction,
                "direction_correct": result.direction_correct,
                "rr_achieved": result.rr_achieved,
                "rr_planned": result.rr_planned,
                "rr_efficiency": result.rr_efficiency,
                "entry_timing_score": result.entry_timing_score,
                "confidence": result.confidence_at_entry,
                "label": result.label,
            })
        except Exception as exc:  # noqa: BLE001
            logger.debug("SignalPostmortem log failed: %s", exc)
