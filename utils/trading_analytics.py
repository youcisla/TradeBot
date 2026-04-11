"""Trading Analytics — rolling performance metrics from closed trades.

Computes professional-grade statistics: win rate, expectancy, Sharpe/Sortino/
Calmar ratios, drawdown metrics, Kelly criterion, SQN, and streaks.

Inspired by: Algosphere TradingAnalyticsSuite.mq5
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.trade import Trade

RISK_FREE_RATE = 0.02   # 2% annual — used for Sharpe/Sortino
TRADING_DAYS_PER_YEAR = 252


@dataclass
class TradingMetrics:
    # ── Basic counts ───────────────────────────────────────────
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0        # percent

    # ── Profit / Loss ─────────────────────────────────────────
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0    # gross_profit / gross_loss
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # ── Expectancy ────────────────────────────────────────────
    expectancy: float = 0.0       # $ per trade
    expectancy_pct: float = 0.0   # as % of starting equity
    payoff_ratio: float = 0.0   # avg_win / avg_loss

    # ── Risk Metrics ──────────────────────────────────────────
    max_drawdown_pct: float = 0.0
    avg_drawdown_pct: float = 0.0
    recovery_factor: float = 0.0
    ulcer_index: float = 0.0

    # ── Risk-Adjusted Ratios ─────────────────────────────────
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    sqn: float = 0.0            # System Quality Number

    # ── Position Sizing ────────────────────────────────────────
    kelly_pct: float = 0.0
    safe_f: float = 0.0           # half-Kelly
    optimal_f: float = 0.0

    # ── Streaks ────────────────────────────────────────────────
    max_win_streak: int = 0
    max_loss_streak: int = 0
    current_streak: int = 0
    on_win_streak: bool = False

    # ── Time Analysis ─────────────────────────────────────────
    trading_days: int = 0
    profit_per_day: float = 0.0
    avg_trade_duration_h: float = 0.0

    # ── Distribution buckets ─────────────────────────────────
    # 10 buckets: <-50%, -40-50%, ..., 40-50%, >50% (buckets 0-9)
    profit_distribution: list[int] = field(default_factory=lambda: [0] * 10)


def _pct_bucket(pct: float) -> int:
    """Map a percentage return to a bucket index 0-9."""
    bucket = 4 + int(pct / 10)
    return max(0, min(9, bucket))


class TradingAnalytics:
    """Compute rolling performance metrics from a list of closed trades.

    Usage::

        analytics = TradingAnalytics(starting_equity=10_000.0)
        analytics.add_trades(closed_trades)   # list[Trade]
        metrics = analytics.metrics
        print(f"Sharpe: {metrics.sharpe_ratio:.2f}")
        print(f"SQN: {metrics.sqn:.1f}")
    """

    def __init__(self, starting_equity: float = 10_000.0) -> None:
        self._equity = starting_equity
        self._peak = starting_equity
        self._trades: list[dict] = []  # {pnl, close_time, open_time}

        # Drawdown tracking
        self._max_dd_pct = 0.0
        self._dd_sum = 0.0
        self._dd_count = 0
        self._dd_sq_sum = 0.0

        # Streaks
        self._win_streak = 0
        self._loss_streak = 0
        self._max_win_streak = 0
        self._max_loss_streak = 0

        # Distribution
        self._distribution = [0] * 10

    def add_trades(self, trades: list["Trade"]) -> None:
        """Feed a list of closed Trade objects to the analytics engine."""
        for t in trades:
            pnl = float(t.pnl or 0.0)
            close = t.close_time
            open_ = t.open_time

            entry = {"pnl": pnl, "close_time": close, "open_time": open_}
            self._trades.append(entry)

            # Update equity curve
            self._equity += pnl
            if self._equity > self._peak:
                self._peak = self._equity

            dd = (self._peak - self._equity) / self._peak * 100.0 if self._peak > 0 else 0.0
            if dd > 0:
                self._dd_sum += dd
                self._dd_sq_sum += dd * dd
                self._dd_count += 1
            if dd > self._max_dd_pct:
                self._max_dd_pct = dd

            # Streaks
            if pnl > 0:
                self._win_streak += 1
                self._loss_streak = 0
                self._max_win_streak = max(self._max_win_streak, self._win_streak)
            elif pnl < 0:
                self._loss_streak += 1
                self._win_streak = 0
                self._max_loss_streak = max(self._max_loss_streak, self._loss_streak)

            # Distribution (% return relative to 10k base)
            pct_return = pnl / 10_000.0 * 100.0
            self._distribution[_pct_bucket(pct_return)] += 1

    @property
    def metrics(self) -> TradingMetrics:
        """Compute and return all metrics."""
        n = len(self._trades)
        if n == 0:
            return TradingMetrics()

        wins = [e["pnl"] for e in self._trades if e["pnl"] > 0]
        losses = [e["pnl"] for e in self._trades if e["pnl"] <= 0]

        m = TradingMetrics()
        m.total_trades = n
        m.wins = len(wins)
        m.losses = len(losses)
        m.win_rate = (m.wins / n * 100.0) if n > 0 else 0.0

        m.gross_profit = sum(wins)
        m.gross_loss = abs(sum(losses))
        m.net_profit = sum(e["pnl"] for e in self._trades)
        m.profit_factor = m.gross_profit / m.gross_loss if m.gross_loss > 0 else 0.0
        m.avg_win = m.gross_profit / m.wins if m.wins > 0 else 0.0
        m.avg_loss = m.gross_loss / m.losses if m.losses > 0 else 0.0
        m.largest_win = max(wins) if wins else 0.0
        m.largest_loss = min(losses) if losses else 0.0

        # Expectancy
        p_win = m.win_rate / 100.0
        p_loss = 1.0 - p_win
        m.expectancy = (p_win * m.avg_win) - (p_loss * m.avg_loss) if m.wins and m.losses else 0.0
        m.expectancy_pct = m.expectancy / 10_000.0 * 100.0
        m.payoff_ratio = m.avg_win / m.avg_loss if m.avg_loss > 0 else 0.0

        # Drawdown
        m.max_drawdown_pct = self._max_dd_pct
        m.avg_drawdown_pct = self._dd_sum / self._dd_count if self._dd_count > 0 else 0.0
        m.ulcer_index = (
            math.sqrt(self._dd_sq_sum / self._dd_count) if self._dd_count > 0 else 0.0
        )
        m.recovery_factor = (
            (m.net_profit / 10_000.0 * 100.0) / self._max_dd_pct
            if self._max_dd_pct > 0 else 0.0
        )

        # Risk-adjusted ratios (per-trade % returns)
        returns = [e["pnl"] / 10_000.0 * 100.0 for e in self._trades]
        avg_return = sum(returns) / n
        neg_returns = [r for r in returns if r < 0]

        std_dev = 0.0
        if n >= 2:
            variance = sum((r - avg_return) ** 2 for r in returns) / n
            std_dev = math.sqrt(max(0.0, variance))

        downside_dev = 0.0
        if neg_returns:
            downside_dev = math.sqrt(sum(r**2 for r in neg_returns) / len(neg_returns))

        risk_free_daily = RISK_FREE_RATE / TRADING_DAYS_PER_YEAR
        m.sharpe_ratio = (std_dev > 0) * ((avg_return - risk_free_daily) / std_dev) or 0.0
        m.sortino_ratio = (downside_dev > 0) * ((avg_return - risk_free_daily) / downside_dev) or 0.0

        annualized_return = avg_return * TRADING_DAYS_PER_YEAR
        m.calmar_ratio = (
            (annualized_return / self._max_dd_pct) if self._max_dd_pct > 0 else 0.0
        )

        # SQN (System Quality Number)
        if std_dev > 0:
            m.sqn = math.sqrt(n) * (avg_return / std_dev)
        else:
            m.sqn = 0.0

        # Kelly Criterion
        if m.payoff_ratio > 0 and p_loss > 0:
            kelly_raw = p_win - (p_loss / m.payoff_ratio)
            m.kelly_pct = max(0.0, kelly_raw * 100.0)
        else:
            m.kelly_pct = 0.0
        m.safe_f = m.kelly_pct / 2.0

        # Optimal f (simplified: expectancy / largest loss)
        if m.largest_loss < 0:
            m.optimal_f = max(0.0, min(100.0, m.expectancy / abs(m.largest_loss) * 100.0))

        # Streaks
        m.max_win_streak = self._max_win_streak
        m.max_loss_streak = self._max_loss_streak
        last_pnl = self._trades[-1]["pnl"] if self._trades else 0.0
        m.on_win_streak = last_pnl > 0
        m.current_streak = self._win_streak if last_pnl > 0 else -self._loss_streak

        # Time analysis
        if len(self._trades) >= 2:
            first_close = self._trades[0]["close_time"]
            last_close = self._trades[-1]["close_time"]
            if isinstance(first_close, datetime) and isinstance(last_close, datetime):
                delta = last_close - first_close
                m.trading_days = max(1, delta.days)
                m.profit_per_day = m.net_profit / m.trading_days if m.trading_days > 0 else 0.0

                durations = [
                    (e["close_time"] - e["open_time"]).total_seconds() / 3600.0
                    for e in self._trades
                    if e["close_time"] and e["open_time"]
                ]
                m.avg_trade_duration_h = sum(durations) / len(durations) if durations else 0.0

        m.profit_distribution = self._distribution[:]
        return m

    @staticmethod
    def sqn_rating(sqn: float) -> str:
        """Return a human-readable SQN quality label."""
        if sqn >= 5.0: return "Holy Grail"
        if sqn >= 3.0: return "Excellent"
        if sqn >= 2.5: return "Very Good"
        if sqn >= 2.0: return "Good"
        if sqn >= 1.6: return "Average"
        if sqn >= 0.0: return "Poor"
        return "Losing"
