"""Learning Agent — scores closed trades and adjusts strategy confidence.

Answers: *How good was that trade, objectively?*

Responsibilities:
- Compute objective score from EntrySnapshot fields
- Adjust per-strategy confidence (clamped 0.1–1.0)
- Enable/disable strategies based on confidence threshold
- Provide per-symbol/session/regime performance stats
"""

from __future__ import annotations

import logging
from datetime import date

from config import settings
from database.db import Database
from models.trade import Trade

logger = logging.getLogger(__name__)


class LearningAgent:
    """Reviews closed trades objectively and tunes confidence."""

    # ── scoring constants ────────────────────────────────────────────────
    SCORE_CLEAN_WIN = 3       # Profit ≥ 2R
    SCORE_MESSY_WIN = 1       # Profit > 0 but < 2R
    SCORE_NORMAL_LOSS = -2    # Normal SL loss
    SCORE_BAD_LOSS = -5       # Loss > 1.5 × initial risk

    CONFIDENCE_STEP = 0.02    # Per-score multiplier
    CONFIDENCE_MIN = 0.1
    CONFIDENCE_MAX = 1.0

    def __init__(self, db: Database) -> None:
        self._db = db

    # ── public API ───────────────────────────────────────────────────────

    def review_trade(self, trade: Trade) -> float:
        """Score a closed trade and adjust strategy confidence.

        Returns the computed score.
        """
        score = self._compute_score(trade)
        self._db.insert_score(
            trade_id=trade.id,
            strategy=trade.strategy,
            symbol=trade.symbol,
            session=trade.snap_session or "",
            market_condition=trade.snap_market_condition or "",
            spread_at_entry=trade.spread_at_entry,
            day_of_week=trade.snap_day_of_week or "",
            score=int(score),
            pnl=trade.pnl or 0.0,
            rsi_aligned=trade.snap_rsi_aligned,
            trend_aligned=trade.snap_trend_aligned,
            volume_sufficient=trade.snap_volume_sufficient,
            near_news_event=trade.snap_near_news_event,
            filters_aligned=trade.snap_rsi_aligned and trade.snap_trend_aligned,
        )

        # Adjust confidence
        current = self.get_confidence(trade.strategy)
        delta = score * self.CONFIDENCE_STEP
        new_conf = max(self.CONFIDENCE_MIN, min(self.CONFIDENCE_MAX, current + delta))
        self._db.upsert_confidence(trade.strategy, new_conf, 0, 0)

        self._emit("info",
                   f"Reviewed trade {trade.id}: score={score:.1f}, "
                   f"confidence {trade.strategy} {current:.2f}→{new_conf:.2f}",
                   {"trade_id": trade.id, "score": score,
                    "old_conf": current, "new_conf": new_conf})
        logger.info(
            "Trade %s scored %.1f | confidence %s: %.2f → %.2f",
            trade.id, score, trade.strategy, current, new_conf,
        )
        return score

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("learning", level, msg, data)

    def get_confidence(self, strategy: str) -> float:
        val = self._db.get_confidence(strategy)
        return val if val is not None else settings.INITIAL_CONFIDENCE

    def is_strategy_enabled(self, strategy: str) -> bool:
        return self.get_confidence(strategy) >= settings.CONFIDENCE_DISABLE_THRESHOLD

    def get_report(self) -> dict:
        """Return summary stats for daily digest."""
        today = date.today().isoformat()
        closed = self._db.get_trades_closed_today()
        if not closed:
            return {"trades_today": 0}

        wins = [t for t in closed if (t.pnl or 0) > 0]
        losses = [t for t in closed if (t.pnl or 0) <= 0]
        total_pnl = sum(t.pnl or 0 for t in closed)

        return {
            "trades_today": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed), 2) if closed else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / len(closed), 2) if closed else 0,
        }

    # ── scoring engine ───────────────────────────────────────────────────

    def _compute_score(self, trade: Trade) -> float:
        """Objective score from PnL + snapshot data."""
        pnl = trade.pnl or 0.0
        initial_risk = self._initial_risk(trade)

        # Base PnL score
        if pnl > 0:
            r_multiple = pnl / initial_risk if initial_risk > 0 else 0
            base = self.SCORE_CLEAN_WIN if r_multiple >= 2 else self.SCORE_MESSY_WIN
        else:
            base = self.SCORE_BAD_LOSS if abs(pnl) > 1.5 * initial_risk else self.SCORE_NORMAL_LOSS

        # Objective modifiers from EntrySnapshot
        bonus = 0.0
        if trade.snap_rsi_aligned:
            bonus += 0.5
        if trade.snap_trend_aligned:
            bonus += 0.5
        if trade.snap_volume_sufficient:
            bonus += 0.5
        if not trade.snap_near_news_event:
            bonus += 0.5  # reward clean entry away from news

        # Penalise high-spread entries
        if trade.spread_at_entry > settings.MAX_SPREAD_PIPS * 0.8:
            bonus -= 0.5

        return round(base + bonus, 1)

    @staticmethod
    def _initial_risk(trade: Trade) -> float:
        """Estimate initial risk in money terms."""
        if trade.entry_price and trade.stop_loss:
            pips_risk = abs(trade.entry_price - trade.stop_loss)
            return pips_risk * (trade.lot_size or 0) * 100_000
        return 1.0  # fallback to avoid divide-by-zero
