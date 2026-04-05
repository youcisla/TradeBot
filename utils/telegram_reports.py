from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import BytesIO

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from config import settings
from database.db import Database


def build_pnl_curve_png(db: Database, days: int | None = None) -> tuple[str, bytes] | None:
    """Build a cumulative PnL chart image for Telegram.

    Returns:
        (caption, png_bytes) or None when not enough data.
    """
    lookback_days = max(1, int(days or settings.TELEGRAM_CHART_DAYS))
    since = datetime.now(UTC) - timedelta(days=lookback_days)
    trades = db.get_closed_trades_since(since, limit=700)
    if not trades:
        return None

    x_vals: list[datetime] = []
    y_vals: list[float] = []
    cumulative = 0.0
    wins = 0
    losses = 0
    for t in trades:
        if t.close_time is None:
            continue
        pnl = float(t.pnl)
        cumulative += pnl
        x_vals.append(t.close_time)
        y_vals.append(cumulative)
        if pnl >= 0:
            wins += 1
        else:
            losses += 1

    if not x_vals:
        return None

    fig = plt.figure(figsize=(8.2, 4.2), dpi=130)
    ax = fig.add_subplot(111)
    ax.plot(x_vals, y_vals, linewidth=2.2, color="#00b894")
    ax.axhline(0, linewidth=1.0, color="#7f8c8d", linestyle="--")
    ax.set_title(f"Cumulative PnL (last {lookback_days}d)")
    ax.set_xlabel("Close Time")
    ax.set_ylabel("PnL")
    ax.grid(alpha=0.22)
    fig.autofmt_xdate()

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    trades_count = wins + losses
    win_rate = (wins / trades_count) if trades_count else 0.0
    caption = (
        f"📈 Performance ({lookback_days}d)\n"
        f"Trades: {trades_count} | Wins: {wins} | Losses: {losses}\n"
        f"Win rate: {win_rate:.0%} | Net PnL: {cumulative:.2f}"
    )
    return caption, buf.getvalue()
