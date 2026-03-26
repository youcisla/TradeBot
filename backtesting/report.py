"""Backtesting Reporting Module.

Calculates standard trading metrics from a list of simulated closed trades,
including drawdown, expectancy, and per-model breakdowns.
"""

from __future__ import annotations

import logging
import math

from broker.connector import PositionInfo

logger = logging.getLogger(__name__)


def generate_report(closed_positions: list[PositionInfo],
                    initial_balance: float) -> dict:
    """Generate trading metrics from a completed backtest run."""

    # ── Basic aggregates ─────────────────────────────────────────────────
    total = len(closed_positions)
    wins  = [p for p in closed_positions if p.pnl > 0]
    losses = [p for p in closed_positions if p.pnl <= 0]

    win_rate     = (len(wins) / total * 100.0) if total > 0 else 0.0
    gross_profit = sum(p.pnl for p in wins)
    gross_loss   = abs(sum(p.pnl for p in losses))
    net_profit   = gross_profit - gross_loss
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    avg_win  = (gross_profit / len(wins))   if wins   else 0.0
    avg_loss = (gross_loss   / len(losses)) if losses else 0.0
    # Expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    expectancy = ((len(wins) / total) * avg_win - (len(losses) / total) * avg_loss) if total > 0 else 0.0

    final_balance = initial_balance + net_profit

    # ── Max drawdown (running equity high-water mark) ────────────────────
    equity       = initial_balance
    peak         = initial_balance
    max_dd       = 0.0       # absolute $
    max_dd_pct   = 0.0       # percentage of peak

    for p in closed_positions:
        equity += p.pnl
        if equity > peak:
            peak = equity
        dd_pct = ((peak - equity) / peak * 100.0) if peak > 0 else 0.0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            max_dd     = peak - equity

    # ── Sharpe ratio (simplified: trade-by-trade returns) ────────────────
    sharpe = 0.0
    if total > 1:
        returns = [p.pnl / initial_balance for p in closed_positions]
        mean_r  = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std_r   = math.sqrt(variance) if variance > 0 else 0.0
        if std_r > 0:
            sharpe = round(mean_r / std_r, 3)  # not annualised — trade-basis

    # ── Assemble report ──────────────────────────────────────────────────
    report: dict = {
        "Total Trades":     total,
        "Winning Trades":   len(wins),
        "Losing Trades":    len(losses),
        "Win Rate (%)":     round(win_rate, 2),
        "Gross Profit":     round(gross_profit, 2),
        "Gross Loss":       round(gross_loss, 2),
        "Net Profit":       round(net_profit, 2),
        "Avg Win":          round(avg_win, 2),
        "Avg Loss":         round(avg_loss, 2),
        "Expectancy":       round(expectancy, 2),
        "Profit Factor":    round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "Max Drawdown ($)": round(max_dd, 2),
        "Max Drawdown (%)": round(max_dd_pct, 2),
        "Sharpe Ratio":     sharpe,
        "Initial Balance":  initial_balance,
        "Final Balance":    round(final_balance, 2),
        "Return (%)":       round((net_profit / initial_balance) * 100.0, 2) if initial_balance > 0 else 0.0,
        "Models":           {},
    }

    # ── Per-model breakdown (strategy name stored in comment) ────────────
    models: dict[str, list[PositionInfo]] = {}
    for p in closed_positions:
        # Strip _TP1/_TP2/_TP3/_partial suffixes to get clean model name
        name = (p.comment or "unknown").split("_TP")[0].split("_partial")[0] or "unknown"
        models.setdefault(name, []).append(p)

    for name, trades in models.items():
        m_wins   = [t for t in trades if t.pnl > 0]
        m_losses = [t for t in trades if t.pnl <= 0]
        m_wr     = (len(m_wins) / len(trades) * 100.0) if trades else 0.0
        m_gp     = sum(t.pnl for t in m_wins)
        m_gl     = abs(sum(t.pnl for t in m_losses))
        m_pf     = (m_gp / m_gl) if m_gl > 0 else float("inf")
        m_exp    = ((len(m_wins) / len(trades)) * (m_gp / len(m_wins) if m_wins else 0)
                    - (len(m_losses) / len(trades)) * (m_gl / len(m_losses) if m_losses else 0)) if trades else 0.0

        report["Models"][name] = {
            "Trades":        len(trades),
            "Win Rate (%)":  round(m_wr, 2),
            "Profit Factor": round(m_pf, 2) if m_pf != float("inf") else 99.0,
            "Net Profit":    round(m_gp - m_gl, 2),
            "Expectancy":    round(m_exp, 2),
        }

    # ── Log summary ──────────────────────────────────────────────────────
    logger.info("=== BACKTEST REPORT ===")
    for k, v in report.items():
        if k not in ("Models",):
            logger.info("  %-22s %s", k + ":", v)
    logger.info("--- Model Breakdown ---")
    for name, stats in report["Models"].items():
        logger.info("  %-28s %3d trades | WR:%5.1f%% | PF:%5.2f | E:%6.2f | PnL:%8.2f",
                    name, stats["Trades"], stats["Win Rate (%)"],
                    stats["Profit Factor"], stats["Expectancy"], stats["Net Profit"])
    logger.info("=======================")

    return report


def derive_confidence_from_model_stats(pf: float, wr: float) -> float:
    """Convert backtest Profit Factor and Win Rate to an agent confidence (0.1–1.0)."""
    conf = 0.5
    if pf >= 2.0:   conf += 0.3
    elif pf >= 1.5: conf += 0.2
    elif pf >= 1.2: conf += 0.1
    elif pf < 0.8:  conf -= 0.2
    elif pf < 0.5:  conf -= 0.4
    if wr >= 60.0:   conf += 0.2
    elif wr >= 50.0: conf += 0.1
    elif wr < 40.0:  conf -= 0.1
    elif wr < 30.0:  conf -= 0.2
    return max(0.1, min(1.0, conf))


def inject_report_to_db(report: dict, db) -> None:
    """Persist derived backtest confidences to the database so live agents use them."""
    for model_name, stats in report.get("Models", {}).items():
        if model_name == "unknown":
            continue
        pf     = stats["Profit Factor"]
        wr     = stats["Win Rate (%)"]
        trades = stats["Trades"]
        conf   = derive_confidence_from_model_stats(
            pf if isinstance(pf, float) else 99.0, wr
        )
        strategy_slug = f"ict_smc:{model_name}"
        db.upsert_confidence(strategy_slug, conf, trades, 0)
        logger.info("Injected backtest confidence: %s → %.2f (PF:%.2f WR:%.1f%%)",
                    strategy_slug, conf, pf if isinstance(pf, float) else 99.0, wr)
