"""Exposure Coach — synthesises 8 market-environment signals into a single
exposure directive.

Answers: *How much capital should we risk right now?*

Directives:
- NEW_ENTRY_ALLOWED — full position sizing; all checks pass.
- REDUCE_ONLY       — no new entries; existing positions may remain.
- CASH_PRIORITY     — close everything and hold cash.

The coach is fail-open: any exception returns
``ExposureDecision(skipped=True)`` so trading is never blocked by a
monitoring failure.  Enable with ``EXPOSURE_ENABLED=true``.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from config import settings

if TYPE_CHECKING:
    from agents.crucix_agent import CrucixAgent
    from database.db import Database
    from models.signal import Signal
    from models.trade import Trade

logger = logging.getLogger(__name__)

# ── Session liquidity scores (higher = better / more liquid) ──────────────
_SESSION_SCORES: dict[str, float] = {
    "London-NY": 1.0,
    "London/NY": 1.0,
    "London NY": 1.0,
    "overlap":   1.0,
    "London":    0.85,
    "NY":        0.80,
    "New York":  0.80,
    "Asian":     0.50,
}
_SESSION_SCORE_DEFAULT: float = 0.30  # off-hours / unknown sessions

# ── Base-currency correlation proxy ──────────────────────────────────────
# Two EUR-denominated pairs in the same direction are considered correlated.
# This is coarser than RiskAgent's full table but requires no extra imports.
_BASE_CURRENCIES: dict[str, str] = {
    "EURUSD": "EUR", "EURGBP": "EUR", "EURJPY": "EUR", "EURCHF": "EUR",
    "EURCAD": "EUR", "EURAUD": "EUR", "EURNZD": "EUR",
    "GBPUSD": "GBP", "GBPJPY": "GBP", "GBPCHF": "GBP",
    "GBPCAD": "GBP", "GBPAUD": "GBP", "GBPNZD": "GBP",
    "USDJPY": "USD", "USDCHF": "USD", "USDCAD": "USD",
    "AUDUSD": "AUD", "AUDNZD": "AUD", "AUDJPY": "AUD",
    "NZDUSD": "NZD", "NZDJPY": "NZD",
    "XAUUSD": "XAU", "XAGUSD": "XAG",
    "US30":   "IDX", "US500":  "IDX", "US100":  "IDX",
    "BTCUSD": "BTC", "ETHUSD": "ETH",
}

# ── Score weights (total = 12.0) ──────────────────────────────────────────
_WEIGHTS: dict[str, float] = {
    "pnl":         2.0,  # realised P&L protection (critical)
    "open_count":  1.5,  # capacity headroom
    "garch_vol":   1.5,  # volatility environment
    "crucix":      2.0,  # macro regime (critical)
    "correlation": 1.0,  # portfolio concentration
    "session":     1.0,  # liquidity timing
    "win_rate":    1.0,  # recent edge quality
    "lgbm_conf":   1.0,  # model conviction
}


@dataclass
class ExposureDecision:
    """Exposure directive for the current trading environment.

    ``skipped=True`` means evaluation failed or is disabled — caller should
    proceed normally (fail-open).
    """

    directive: Literal[
        "NEW_ENTRY_ALLOWED", "REDUCE_ONLY", "CASH_PRIORITY"
    ] = "NEW_ENTRY_ALLOWED"
    exposure_ceiling_pct: float = 1.0   # 0.0 → 1.0
    reason: str = ""
    contributing_signals: dict[str, float] = field(default_factory=dict)
    skipped: bool = False


class ExposureCoach:
    """Synthesises 8 environment signals into a single ``ExposureDecision``.

    Parameters
    ----------
    db:
        Database instance for P&L and win-rate queries.
    crucix_agent:
        CrucixAgent for live macro-regime scoring (optional).
    """

    def __init__(
        self,
        db: "Database | None" = None,
        crucix_agent: "CrucixAgent | None" = None,
    ) -> None:
        self._db = db
        self._crucix = crucix_agent

    # ── public API ────────────────────────────────────────────────────────

    def evaluate(
        self,
        signal: "Signal",
        open_trades: "list[Trade] | None" = None,
        account_equity: float | None = None,
        garch_vol_ratio: float | None = None,
    ) -> ExposureDecision:
        """Return an ``ExposureDecision`` for the current market environment.

        Always succeeds — exceptions produce ``ExposureDecision(skipped=True)``
        so trading is never blocked by a monitoring failure.

        Parameters
        ----------
        signal:
            The candidate trade signal.
        open_trades:
            Currently open trades (pass the caller's cached list to avoid
            a redundant broker IPC call).
        account_equity:
            Current equity in account currency (used for P&L % calculation).
        garch_vol_ratio:
            ``current_garch_vol / 30d_rolling_avg``.  Pass ``None`` when not
            available — the signal is scored neutrally (0.5).
        """
        try:
            if not settings.EXPOSURE_ENABLED:
                return ExposureDecision(skipped=True, reason="disabled")

            _open: list = open_trades if open_trades is not None else []
            scores: dict[str, float] = {
                "pnl":         self._score_pnl(account_equity),
                "open_count":  self._score_open_count(_open),
                "garch_vol":   self._score_garch_vol(garch_vol_ratio),
                "crucix":      self._score_crucix(signal),
                "correlation": self._score_correlation(signal, _open),
                "session":     self._score_session(signal),
                "win_rate":    self._score_win_rate(),
                "lgbm_conf":   self._score_lgbm_confidence(signal),
            }
            return self._compute_directive(scores)
        except Exception:
            logger.exception("ExposureCoach.evaluate failed — skipping (fail-open)")
            return ExposureDecision(skipped=True, reason="exception")

    # ── individual signal scorers (0.0 = dangerous, 1.0 = safe) ─────────

    def _score_pnl(self, account_equity: float | None) -> float:
        """Score based on today's realised P&L vs. the daily loss limit.

        Returns 1.0 when there is no realised loss today, decreasing linearly
        toward 0.0 as losses approach ``settings.MAX_DAILY_LOSS``.
        """
        try:
            if self._db is None:
                return 0.5  # neutral — no DB access
            trades_today = self._db.get_trades_closed_today()
            if not trades_today:
                return 1.0

            realised_loss = sum(
                t.pnl for t in trades_today if t.pnl is not None and t.pnl < 0
            )
            if realised_loss >= 0:
                return 1.0  # only profitable closes today

            equity = account_equity or 1.0
            loss_pct = abs(realised_loss) / max(equity, 1.0)
            daily_limit = max(settings.MAX_DAILY_LOSS, 0.001)
            score = max(0.0, 1.0 - (loss_pct / daily_limit))
            return round(score, 4)
        except Exception:
            logger.debug("ExposureCoach._score_pnl failed", exc_info=True)
            return 0.5

    def _score_open_count(self, open_trades: list) -> float:
        """Score inversely proportional to current open-trade count vs. cap."""
        try:
            n = len(open_trades)
            max_n = settings.MAX_OPEN_TRADES
            if max_n <= 0:
                return 1.0
            return max(0.0, round(1.0 - (n / max_n), 4))
        except Exception:
            logger.debug("ExposureCoach._score_open_count failed", exc_info=True)
            return 0.5

    def _score_garch_vol(self, garch_vol_ratio: float | None) -> float:
        """Score based on GARCH volatility relative to its 30-day rolling average.

        ``garch_vol_ratio`` = current_vol / 30d_avg.

        - ratio ≤ 1.0 (at or below average) → 1.0
        - ratio ≥ ``GARCH_HIGH_VOL_THRESHOLD`` → 0.0
        - linear interpolation between the two bounds.

        Returns 0.5 when no ratio is provided (neutral / unknown).
        """
        if garch_vol_ratio is None:
            return 0.5

        try:
            threshold = max(settings.GARCH_HIGH_VOL_THRESHOLD, 1.001)
            if garch_vol_ratio <= 1.0:
                return 1.0
            if garch_vol_ratio >= threshold:
                return 0.0
            score = 1.0 - (garch_vol_ratio - 1.0) / (threshold - 1.0)
            return round(max(0.0, min(1.0, score)), 4)
        except Exception:
            logger.debug("ExposureCoach._score_garch_vol failed", exc_info=True)
            return 0.5

    def _score_crucix(self, signal: "Signal") -> float:
        """Score based on the Crucix macro risk tier."""
        try:
            if self._crucix is None:
                return 0.5
            macro = self._crucix.get_context()
            tier = (macro.risk_tier or "").lower()
            tier_map: dict[str, float] = {
                "low":      1.0,
                "medium":   0.65,
                "high":     0.30,
                "critical": 0.05,
                "blackout": 0.0,
            }
            return tier_map.get(tier, 0.5)
        except Exception:
            logger.debug("ExposureCoach._score_crucix failed", exc_info=True)
            return 0.5

    def _score_correlation(self, signal: "Signal", open_trades: list) -> float:
        """Score based on how many correlated positions are already open.

        Uses a base-currency proxy: two pairs sharing the same base currency
        in the same direction are counted as correlated.
        """
        try:
            if not open_trades:
                return 1.0
            sig_base = _BASE_CURRENCIES.get(signal.symbol.upper(), "")
            if not sig_base:
                return 0.8  # unknown symbol — mild penalty

            correlated = sum(
                1
                for t in open_trades
                if (
                    _BASE_CURRENCIES.get(
                        (getattr(t, "symbol", None) or "").upper(), ""
                    ) == sig_base
                    and getattr(t, "direction", "") == signal.direction
                )
            )
            score = max(0.0, 1.0 - correlated * 0.35)
            return round(score, 4)
        except Exception:
            logger.debug("ExposureCoach._score_correlation failed", exc_info=True)
            return 0.5

    def _score_session(self, signal: "Signal") -> float:
        """Score based on the hour-of-day / session liquidity profile."""
        try:
            snapshot = getattr(signal, "entry_snapshot", None)
            sess = (snapshot.session if snapshot else "") or ""
            if not sess:
                from utils.helpers import current_session
                sess = current_session()
            return _SESSION_SCORES.get(sess, _SESSION_SCORE_DEFAULT)
        except Exception:
            logger.debug("ExposureCoach._score_session failed", exc_info=True)
            return 0.5

    def _score_win_rate(self) -> float:
        """Score based on win-rate over the last N closed trades.

        Scale: ≥ 60 % win-rate → 1.0, ≤ 30 % win-rate → 0.0 (linear).
        Returns 0.5 when DB is unavailable or history is insufficient.
        """
        try:
            if self._db is None:
                return 0.5
            lookback = max(1, settings.EXPOSURE_WIN_RATE_LOOKBACK)
            since = datetime.now(UTC) - timedelta(days=max(7, lookback))
            trades = self._db.get_closed_trades_since(since, limit=lookback)
            if not trades:
                return 0.5

            wins = sum(1 for t in trades if t.pnl is not None and t.pnl > 0)
            win_rate = wins / len(trades)
            # Linear: 30 % → 0.0, 60 % → 1.0
            score = max(0.0, min(1.0, (win_rate - 0.30) / 0.30))
            return round(score, 4)
        except Exception:
            logger.debug("ExposureCoach._score_win_rate failed", exc_info=True)
            return 0.5

    def _score_lgbm_confidence(self, signal: "Signal") -> float:
        """Signal confidence from the LGBM ensemble (already in [0.0, 1.0])."""
        try:
            return max(0.0, min(1.0, float(signal.confidence)))
        except Exception:
            return 0.5

    # ── directive computation ─────────────────────────────────────────────

    def _compute_directive(self, scores: dict[str, float]) -> ExposureDecision:
        """Map a score dict to an ``ExposureDecision`` via weighted average."""
        total_weight = sum(_WEIGHTS.values())
        weighted_sum = sum(
            scores.get(k, 0.5) * w for k, w in _WEIGHTS.items()
        )
        composite = max(0.0, min(1.0, weighted_sum / total_weight))

        if composite < settings.EXPOSURE_CASH_THRESHOLD:
            return ExposureDecision(
                directive="CASH_PRIORITY",
                exposure_ceiling_pct=0.0,
                reason=(
                    f"composite score {composite:.3f} below cash threshold "
                    f"{settings.EXPOSURE_CASH_THRESHOLD:.2f}"
                ),
                contributing_signals=scores,
            )
        if composite < settings.EXPOSURE_REDUCE_THRESHOLD:
            return ExposureDecision(
                directive="REDUCE_ONLY",
                exposure_ceiling_pct=round(composite, 3),
                reason=(
                    f"composite score {composite:.3f} below reduce threshold "
                    f"{settings.EXPOSURE_REDUCE_THRESHOLD:.2f}"
                ),
                contributing_signals=scores,
            )
        return ExposureDecision(
            directive="NEW_ENTRY_ALLOWED",
            exposure_ceiling_pct=min(1.0, round(composite * 1.1, 3)),
            reason=f"composite score {composite:.3f}",
            contributing_signals=scores,
        )
