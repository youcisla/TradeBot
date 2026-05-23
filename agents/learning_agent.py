"""Learning Agent — scores closed trades, adjusts confidence, issues rewards.

Continuous improvement loop
----------------------------
Every closed trade is compared against three benchmarks:

1. **Per-trade** — is this score above the rolling 10-trade average for this
   strategy?  If so, a reward multiplier is applied to the confidence update.
   Win streaks (3+ and 5+) add further multipliers.

2. **Daily** — called once per day.  Compares today's PnL and win-rate to
   yesterday's snapshot.  A day better than the previous day fires a Telegram
   reward alert and boosts the active-strategy confidence.

3. **Weekly / Monthly** — same pattern.  Called on Sunday (week) and the 1st
   of each month (month).  Larger time windows, proportionally larger boosts.

Reward multipliers are applied only to the *positive* side of the confidence
update — losses still penalise at the base rate so the bot can't "earn" its
way out of a losing streak.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from config import settings
from utils.mesh_bus import record_call
from config.symbols import contract_size
from adapters.db.db import Database
from models.trade import Trade

if TYPE_CHECKING:
    from agents.reflector import Reflector
    from agents.hku_client import HKUClient

logger = logging.getLogger(__name__)

# ── Reward multiplier caps ────────────────────────────────────────────────────

_BEAT_ROLLING_AVG_BONUS   = 0.50   # score > rolling-10 average
_STREAK_3_BONUS           = 0.25   # 3+ consecutive wins
_STREAK_5_BONUS           = 0.50   # 5+ consecutive wins (replaces streak-3)
_DAY_IMPROVEMENT_BOOST    = 0.04   # extra confidence per active strategy
_WEEK_IMPROVEMENT_BOOST   = 0.06
_MONTH_IMPROVEMENT_BOOST  = 0.10
_MAX_MULTIPLIER           = 2.50   # cap so a single trade can't spike confidence
_SIMILAR_CONTEXT_POSITIVE_BONUS = 0.15
_SIMILAR_CONTEXT_NEGATIVE_CAP = 1.25


class LearningAgent:
    """Reviews closed trades objectively and tunes confidence with rewards."""

    # ── scoring constants ────────────────────────────────────────────────
    SCORE_CLEAN_WIN  =  3    # Profit ≥ 2R
    SCORE_MESSY_WIN  =  1    # Profit > 0 but < 2R
    SCORE_NORMAL_LOSS = -2   # Normal SL loss
    SCORE_BAD_LOSS   = -5    # Loss > 1.5 × initial risk

    CONFIDENCE_STEP  = 0.02  # Base per-score confidence delta
    CONFIDENCE_MIN   = 0.10
    CONFIDENCE_MAX   = 1.00

    def __init__(self, db: Database, hku_client: "HKUClient | None" = None) -> None:
        self._db = db
        self._reflector: "Reflector | None" = None
        self._hku_client = hku_client

    def set_reflector(self, reflector: "Reflector") -> None:
        """Attach the Reflector so post-trade lessons are generated automatically."""
        self._reflector = reflector

    def set_hku_client(self, client: "HKUClient") -> None:
        """Inject the HKU client once it's been initialized in bot startup()."""
        self._hku_client = client

    # ── public API ───────────────────────────────────────────────────────

    def review_trade(self, trade: Trade, context: dict | None = None) -> float:
        """Score a closed trade, apply reward multiplier, adjust confidence.

        Args:
            trade:   The closed trade to review.
            context: Optional signal-time context dict (regime, MTF bias, etc.)
                     forwarded to the Reflector for richer post-trade lessons.

        Returns the raw score.
        """
        _t0 = time.monotonic()
        score = self._compute_score(trade)

        # Persist the score record
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

        context_memory = self._build_context_memory(trade)

        # Update win streak and compute reward multiplier
        streak = self._update_streak(trade.strategy, score)
        multiplier = self._reward_multiplier(trade.strategy, score, streak, context_memory)

        # Apply confidence delta (multiplier only amplifies positive deltas)
        current = self.get_confidence(trade.strategy)
        base_delta = score * self.CONFIDENCE_STEP
        delta = base_delta * multiplier if base_delta > 0 else base_delta
        proposed = max(self.CONFIDENCE_MIN,
                       min(self.CONFIDENCE_MAX, current + delta))
        # EMA smoothing: blend proposed value with current to prevent per-trade oscillation
        new_conf = round(0.3 * proposed + 0.7 * current, 4)
        self._db.upsert_confidence(trade.strategy, new_conf, 1, int(score))

        # Log
        self._emit(
            "info",
            f"Trade {trade.id}: score={score:+.1f} "
            f"mult={multiplier:.2f}x "
            f"streak={streak} "
            f"conf {trade.strategy} {current:.2f}->{new_conf:.2f}",
            {"trade_id": trade.id, "score": score,
             "multiplier": multiplier, "streak": streak,
               "old_conf": current, "new_conf": new_conf,
               "context_memory": context_memory},
        )
        logger.info(
            "Trade %s scored %+.1f (x%.2f, streak=%d) | %s conf %.2f→%.2f",
            trade.id, score, multiplier, streak,
            trade.strategy, current, new_conf,
        )

        # Trigger async post-trade reflection (non-blocking)
        if self._reflector is not None:
            self._reflector.reflect_async(trade, context)

        # Report HKU outcome if this trade was sourced from an external HKU signal
        if self._hku_client is not None and trade.metadata.get("source") == "hku":
            self._update_hku_reputation(trade, score)

        # Check adaptive LGBM retrain threshold (non-blocking)
        self._maybe_retrain_lgbm()

        record_call("learning", (time.monotonic() - _t0) * 1000.0, True)
        return score

    # ── period snapshots (call from main loop) ───────────────────────────

    def snapshot_daily(self, for_date: date | None = None) -> None:
        """Save today's performance snapshot and compare to yesterday.

        Call this once per day from the main loop daily-summary block.
        """
        today = for_date or date.today()
        key   = today.isoformat()                         # e.g. '2026-03-22'
        since = datetime(today.year, today.month, today.day, tzinfo=UTC)
        until = since + timedelta(days=1)

        stats = self._db.get_period_stats(since, until)
        self._db.save_performance_snapshot(
            period_type="day",
            period_key=key,
            **stats,
        )

        prev = self._db.get_previous_snapshot("day", key)
        if prev and stats["trades"] > 0:
            self._check_period_improvement("day", stats, prev, today.strftime("%A %d %b"))

    def snapshot_weekly(self, for_date: date | None = None) -> None:
        """Save this ISO week's snapshot and compare to last week.

        Call on Sunday from the main loop.
        """
        today    = for_date or date.today()
        iso_cal  = today.isocalendar()
        key      = f"{iso_cal[0]}-W{iso_cal[1]:02d}"     # e.g. '2026-W12'
        # week runs Mon–Sun; today is Sunday
        since    = datetime(today.year, today.month, today.day, tzinfo=UTC) - timedelta(days=6)
        until    = datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=1)

        stats = self._db.get_period_stats(since, until)
        self._db.save_performance_snapshot(
            period_type="week",
            period_key=key,
            **stats,
        )

        prev = self._db.get_previous_snapshot("week", key)
        if prev and stats["trades"] > 0:
            self._check_period_improvement("week", stats, prev, f"week {key}")

    def snapshot_monthly(self, for_date: date | None = None) -> None:
        """Save last month's snapshot and compare to the month before.

        Call on the 1st of each month from the main loop.
        """
        today       = for_date or date.today()
        # last month
        first_today = today.replace(day=1)
        last_month  = first_today - timedelta(days=1)
        key         = last_month.strftime("%Y-%m")        # e.g. '2026-02'
        since       = datetime(last_month.year, last_month.month, 1, tzinfo=UTC)
        until       = datetime(today.year, today.month, 1, tzinfo=UTC)

        stats = self._db.get_period_stats(since, until)
        self._db.save_performance_snapshot(
            period_type="month",
            period_key=key,
            **stats,
        )

        prev = self._db.get_previous_snapshot("month", key)
        if prev and stats["trades"] > 0:
            self._check_period_improvement(
                "month", stats, prev, last_month.strftime("%B %Y")
            )

    # ── period comparison + reward ────────────────────────────────────────

    def _check_period_improvement(
        self,
        period_type: str,
        current: dict,
        previous: dict,
        label: str,
    ) -> None:
        """Compare current vs previous period; fire reward if improved."""
        pnl_improved  = current["total_pnl"]  > previous["total_pnl"]
        rate_improved = current["win_rate"]    > previous["win_rate"]
        score_improved= current["avg_score"]   > previous["avg_score"]

        improvements = sum([pnl_improved, rate_improved, score_improved])
        if improvements == 0:
            return

        boost = {
            "day":   _DAY_IMPROVEMENT_BOOST,
            "week":  _WEEK_IMPROVEMENT_BOOST,
            "month": _MONTH_IMPROVEMENT_BOOST,
        }[period_type]

        # Scale boost by how many metrics improved
        total_boost = boost * improvements / 3

        # Apply to all active strategies
        self._apply_period_boost(total_boost)

        # Build reward message
        lines = [f"📈 *{label.upper()} IMPROVEMENT REWARD*"]
        if pnl_improved:
            diff = current["total_pnl"] - previous["total_pnl"]
            lines.append(
                f"  PnL: {previous['total_pnl']:+.2f} → {current['total_pnl']:+.2f} "
                f"({diff:+.2f})"
            )
        if rate_improved:
            lines.append(
                f"  Win rate: {previous['win_rate']:.0%} → {current['win_rate']:.0%}"
            )
        if score_improved:
            lines.append(
                f"  Avg score: {previous['avg_score']:.1f} → {current['avg_score']:.1f}"
            )
        lines.append(
            f"  Confidence boost: +{total_boost:.3f} applied to all strategies 🎯"
        )

        msg = "\n".join(lines)
        logger.info("REWARD: %s", msg.replace("*", ""))
        self._emit("info", msg.replace("*", "").replace("\n", " | "),
                   {"period": period_type, "boost": total_boost, "improvements": improvements})

        from utils import telegram_bot
        telegram_bot.send_message(msg)

    def _apply_period_boost(self, boost: float) -> None:
        """Apply a flat confidence boost to all strategies that have been seen."""
        self._db.boost_all_strategy_confidence(boost)

    # ── per-trade reward multiplier ───────────────────────────────────────

    def _reward_multiplier(self, strategy: str, score: float,
                           streak: int,
                           context_memory: dict | None = None) -> float:
        """Compute how much to amplify a positive confidence delta.

        Only affects wins; losses always use base multiplier = 1.0.
        """
        if score <= 0:
            return 1.0

        multiplier = 1.0

        # Beat rolling 10-trade average?
        avg = self._db.get_rolling_avg_score(strategy, n=10)
        if avg is not None and score > avg:
            multiplier += _BEAT_ROLLING_AVG_BONUS
            logger.debug(
                "Reward: %s score %.1f > avg %.1f (+%.2f mult)",
                strategy, score, avg, _BEAT_ROLLING_AVG_BONUS,
            )

        # Win streak milestone
        if streak >= 5:
            multiplier += _STREAK_5_BONUS
        elif streak >= 3:
            multiplier += _STREAK_3_BONUS

        # Situation memory retrieval: use outcomes from similar setups.
        if context_memory and int(context_memory.get("trades", 0)) >= 3:
            avg_score = float(context_memory.get("avg_score", 0.0))
            win_rate = float(context_memory.get("win_rate", 0.0))
            if avg_score > 0.75 and win_rate >= 0.55:
                multiplier += _SIMILAR_CONTEXT_POSITIVE_BONUS
            elif avg_score < 0 or win_rate < 0.40:
                multiplier = min(multiplier, _SIMILAR_CONTEXT_NEGATIVE_CAP)

        return min(multiplier, _MAX_MULTIPLIER)

    def _build_context_memory(self, trade: Trade) -> dict | None:
        """Retrieve recent outcomes for a setup with similar context."""
        try:
            memory = self._db.get_recent_context_outcomes(
                strategy=trade.strategy,
                symbol=trade.symbol,
                session=trade.snap_session or "",
                market_condition=trade.snap_market_condition or "",
                lookback_days=30,
                limit=50,
            )
            return memory
        except Exception:
            logger.exception("Learning memory retrieval failed for %s", trade.id)
            return None

    # ── streak tracking ───────────────────────────────────────────────────

    def _update_streak(self, strategy: str, score: float) -> int:
        """Increment win streak on positive score, reset on loss.

        Returns the updated streak count.
        """
        current_streak = self._db.get_strategy_streak(strategy)
        if score > 0:
            new_streak = current_streak + 1
        else:
            new_streak = 0
        self._db.update_strategy_streak(strategy, new_streak, score)

        # Fire streak milestone alerts
        if new_streak in (3, 5, 10, 20):
            medals = {3: "🥉", 5: "🥈", 10: "🥇", 20: "🏆"}
            msg = (
                f"{medals[new_streak]} *{new_streak}-TRADE WIN STREAK* — {strategy}\n"
                f"Confidence multiplier active: x{_STREAK_5_BONUS + 1.0:.2f}"
                if new_streak >= 5 else
                f"{medals[new_streak]} *{new_streak}-TRADE WIN STREAK* — {strategy}\n"
                f"Confidence multiplier active: x{_STREAK_3_BONUS + 1.0:.2f}"
            )
            logger.info("STREAK MILESTONE: %s %d", strategy, new_streak)
            self._emit("info", f"Streak milestone: {strategy} {new_streak} wins",
                       {"strategy": strategy, "streak": new_streak})
            from utils import telegram_bot
            telegram_bot.send_message(msg)

        return new_streak

    # ── getters ──────────────────────────────────────────────────────────

    def get_confidence(self, strategy: str) -> float:
        val = self._db.get_confidence(strategy)
        return val if val is not None else settings.INITIAL_CONFIDENCE

    def is_strategy_enabled(self, strategy: str) -> bool:
        return self.get_confidence(strategy) >= settings.CONFIDENCE_DISABLE_THRESHOLD

    def get_report(self) -> dict:
        """Summary stats for the daily digest."""
        closed = self._db.get_trades_closed_today()
        if not closed:
            return {"trades_today": 0}

        wins      = [t for t in closed if (t.pnl or 0) >= 0]
        losses    = [t for t in closed if (t.pnl or 0) < 0]
        total_pnl = sum(t.pnl or 0 for t in closed)

        return {
            "trades_today": len(closed),
            "wins":         len(wins),
            "losses":       len(losses),
            "win_rate":     round(len(wins) / len(closed), 2) if closed else 0,
            "total_pnl":    round(total_pnl, 2),
            "avg_pnl":      round(total_pnl / len(closed), 2) if closed else 0,
        }

    # ── walk-forward optimization check ──────────────────────────────────

    def run_wfo_assessment(
        self,
        strategy: str = "all",
        lookback_days: int = 90,
    ) -> dict:
        """Run a walk-forward optimization check on recent closed-trade PnL.

        Detects model overfitting and parameter fragility emerging from live
        trading.  Returns the raw WFO result dict so the **caller** (main loop
        or weekly scheduler) can decide how to act on it, e.g.::

            result = learning_agent.run_wfo_assessment()
            if result.get("avg_overfitting", 0) > 1.5:
                risk_agent.set_emergency_caps(max_risk_per_trade=0.01,
                                              max_open_trades=3)

        **Thresholds** (from :class:`~utils.walk_forward_optimizer.WalkForwardOptimizer`):

        * ``avg_overfitting > 1.5``  — strategy is fitting to noise, not edge.
        * ``parameter_stability < 0.6`` — optimal parameters shift each window,
          indicating fragility.

        At least 30 closed trades must exist in *lookback_days* (default 90);
        fewer returns ``{"skipped": True, …}``.
        """
        try:
            import pandas as pd  # optional — only needed for WFO
            from utils.walk_forward_optimizer import WalkForwardOptimizer, WFOConfig
        except ImportError as exc:
            logger.warning("WFO skipped: missing dependency (%s)", exc)
            return {"skipped": True, "reason": "import_error", "error": str(exc)}

        since = datetime.now(UTC) - timedelta(days=lookback_days)
        trades = self._db.get_closed_trades_since(since, limit=2000)

        if len(trades) < 30:
            logger.info(
                "WFO skipped: only %d closed trades in the %d-day window (need ≥30).",
                len(trades), lookback_days,
            )
            return {
                "skipped": True,
                "reason": "insufficient_trades",
                "count": len(trades),
            }

        # Build a minimal, sorted PnL time-series for the WFO engine.
        records = [
            {"close_time": t.close_time, "pnl": t.pnl or 0.0}
            for t in trades
            if t.close_time is not None
        ]
        bars = (
            pd.DataFrame(records)
            .sort_values("close_time")
            .reset_index(drop=True)
        )

        # No parameter grid — just walk PnL forward to check for regime drift.
        def fitness_fn(window_bars: "pd.DataFrame", _params: dict) -> float:  # noqa: ANN001
            return float(window_bars["pnl"].sum())

        n = len(bars)
        config = WFOConfig(
            train_window=max(10, min(50, n // 3)),
            test_window=max(5, n // 10),
            reoptimize_freq=max(5, n // 10),
            param_ranges={},           # no optimisation — pure regime check
        )
        wfo    = WalkForwardOptimizer(config)
        result = wfo.run_walk_forward(bars, fitness_fn)
        result["strategy"] = strategy

        overfitting = result.get("avg_overfitting", 0.0)
        stability   = result.get("parameter_stability", 1.0)
        num_windows = result.get("num_windows", 0)

        logger.info(
            "WFO [%s]: windows=%d  overfitting=%.2f  stability=%.2f",
            strategy, num_windows, overfitting, stability,
        )

        # Fire alert when either threshold is breached.
        if overfitting > 1.5 or stability < 0.6:
            problems: list[str] = []
            if overfitting > 1.5:
                problems.append(f"overfitting={overfitting:.2f} (>1.5)")
            if stability < 0.6:
                problems.append(f"stability={stability:.2f} (<0.6)")

            alert = (
                f"⚠️ WFO ALERT [{strategy}]: {', '.join(problems)}\n"
                f"Caller should call risk_agent.set_emergency_caps() to tighten risk."
            )
            logger.warning(alert.replace("\n", " | "))
            self._emit(
                "warn",
                f"WFO alert: {'; '.join(problems)}",
                {
                    "strategy":    strategy,
                    "overfitting": overfitting,
                    "stability":   stability,
                    "num_windows": num_windows,
                },
            )
            from utils import telegram_bot
            telegram_bot.send_message(alert)

        return result

    # ── scoring engine ────────────────────────────────────────────────────

    def _compute_score(self, trade: Trade) -> float:
        """Objective score from PnL + snapshot flags."""
        pnl          = trade.pnl or 0.0
        initial_risk = self._initial_risk(trade)

        if pnl >= 0:
            r_multiple = pnl / initial_risk if initial_risk > 0 else 0
            base = self.SCORE_CLEAN_WIN if r_multiple >= 2 else self.SCORE_MESSY_WIN
        else:
            base = (self.SCORE_BAD_LOSS
                    if abs(pnl) > 1.5 * initial_risk
                    else self.SCORE_NORMAL_LOSS)

        bonus = 0.0
        if trade.snap_rsi_aligned:      bonus += 0.5
        if trade.snap_trend_aligned:    bonus += 0.5
        if trade.snap_volume_sufficient:bonus += 0.5
        if not trade.snap_near_news_event: bonus += 0.5
        if trade.spread_at_entry > settings.MAX_SPREAD_PIPS * 0.8:
            bonus -= 0.5

        return round(base + bonus, 1)

    @staticmethod
    def _initial_risk(trade: Trade) -> float:
        if trade.entry_price and trade.stop_loss:
            sl_distance = abs(trade.entry_price - trade.stop_loss)
            cs = contract_size(trade.symbol)
            return sl_distance * (trade.lot_size or 0) * cs
        return 1.0

    def _update_hku_reputation(self, trade: Trade, score: float) -> None:
        """Send trade outcome back to HKU marketplace to update agent reputation.

        Fire-and-forget — failures are logged but never raised.
        """
        try:
            hku_signal_id = trade.metadata.get("hku_signal_id")
            if hku_signal_id and self._hku_client:
                self._hku_client.report_outcome(hku_signal_id, score > 0)
        except Exception as exc:
            logger.debug("HKU reputation update failed: %s", exc)

    # ── adaptive LGBM retraining ──────────────────────────────────────────

    def _maybe_retrain_lgbm(self) -> None:
        """Check the adaptive threshold and trigger a background retrain if due."""
        try:
            from models.lgbm_train_state import get_state
            state = get_state()
            total = self._db.count_closed_trades()
            if not state.should_train(total):
                return

            threshold = state.next_threshold
            next_threshold = state.bump()   # advance now so concurrent calls don't double-fire

            logger.info(
                "LGBM auto-retrain triggered: %d closed trades >= threshold %d "
                "(next threshold: %d)",
                total, threshold, next_threshold,
            )
            self._emit(
                "info",
                f"LGBM auto-retrain triggered ({total} trades >= {threshold}); "
                f"next threshold: {next_threshold}",
                {"total_trades": total, "threshold": threshold,
                 "next_threshold": next_threshold, "train_count": state.train_count},
            )

            threading.Thread(
                target=self._run_lgbm_training,
                args=(total, threshold),
                daemon=True,
                name="lgbm-retrain",
            ).start()

        except Exception:
            logger.exception("LearningAgent: adaptive LGBM check failed")

    def _run_lgbm_training(self, total_trades: int, threshold: int) -> None:
        """Background thread: run LGBM training and notify via Telegram."""
        from utils import telegram_bot
        try:
            from scripts.train_lgbm import load_closed_trades, train
            from pathlib import Path

            telegram_bot.send_message(
                f"🤖 *LGBM Auto-Retrain Started*\n"
                f"{total_trades} closed trades ≥ threshold {threshold}"
            )

            rows = load_closed_trades()
            output = Path("models/lgbm_model.pkl")
            ok = train(rows, output)

            if ok:
                logger.info("LGBM auto-retrain complete (%d samples).", len(rows))
                telegram_bot.send_message(
                    f"✅ *LGBM Retrained* — {len(rows)} trades\n"
                    f"Model saved to {output}"
                )
                self._emit("info", "LGBM auto-retrain succeeded",
                           {"samples": len(rows), "model": str(output)})
            else:
                logger.warning("LGBM auto-retrain returned False.")
                telegram_bot.send_message("⚠️ LGBM auto-retrain failed — check logs.")
                self._emit("warn", "LGBM auto-retrain failed")

        except Exception as exc:
            logger.exception("LGBM auto-retrain thread crashed")
            from utils import telegram_bot as _tg
            _tg.send_message(f"❌ LGBM auto-retrain crashed: {exc}")

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("learning", level, msg, data)
