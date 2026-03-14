"""Backtesting Reporting Module.

Calculates standard trading metrics from a list of simulated closed trades.
"""

from __future__ import annotations

import logging

from broker.connector import PositionInfo

logger = logging.getLogger(__name__)

def generate_report(closed_positions: list[PositionInfo], initial_balance: float) -> dict:
    """Generate basic trading metrics."""
    # This is a stub for the actual implementation in report.py
    
    total_trades = len(closed_positions)
    
    wins = [p for p in closed_positions if p.pnl > 0]
    losses = [p for p in closed_positions if p.pnl <= 0]
    
    win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
    
    gross_profit = sum(w.pnl for w in wins)
    gross_loss = abs(sum(l.pnl for l in losses))
    net_profit = gross_profit - gross_loss
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
    
    final_balance = initial_balance + net_profit
    
    report = {
        "Total Trades": total_trades,
        "Winning Trades": len(wins),
        "Losing Trades": len(losses),
        "Win Rate (%)": round(win_rate, 2),
        "Gross Profit": round(gross_profit, 2),
        "Gross Loss": round(gross_loss, 2),
        "Net Profit": round(net_profit, 2),
        "Profit Factor": round(profit_factor, 2) if profit_factor != float("inf") else "inf",
        "Initial Balance": initial_balance,
        "Final Balance": round(final_balance, 2),
        "Return (%)": round((net_profit / initial_balance) * 100.0, 2) if initial_balance > 0 else 0.0,
        "Models": {}
    }
    
    # --- Group by Model (stored in comment) ---
    models: dict[str, list[PositionInfo]] = {}
    for p in closed_positions:
        m = p.comment or "unknown"
        if m not in models:
            models[m] = []
        models[m].append(p)
        
    for m, m_trades in models.items():
        m_wins = [p for p in m_trades if p.pnl > 0]
        m_losses = [p for p in m_trades if p.pnl <= 0]
        m_win_rate = (len(m_wins) / len(m_trades) * 100.0) if m_trades else 0.0
        m_gp = sum(w.pnl for w in m_wins)
        m_gl = abs(sum(l.pnl for l in m_losses))
        m_pf = (m_gp / m_gl) if m_gl > 0 else float("inf")
        
        report["Models"][m] = {
            "Trades": len(m_trades),
            "Win Rate (%)": round(m_win_rate, 2),
            "Profit Factor": round(m_pf, 2) if m_pf != float("inf") else 99.0,
            "Net Profit": round(m_gp - m_gl, 2)
        }
    
    logger.info("=== BACKTEST REPORT ===")
    for k, v in report.items():
        if k != "Models":
            logger.info("%-20s %s", k + ":", v)
            
    logger.info("--- Model Breakdown ---")
    for m, m_stats in report["Models"].items():
        logger.info("  %-25s %3d trades | WR: %5.1f%% | PF: %4.2f | PnL: %6.2f",
                    m, m_stats["Trades"], m_stats["Win Rate (%)"], m_stats["Profit Factor"], m_stats["Net Profit"])
    logger.info("=======================")
        
    return report

def derive_confidence_from_model_stats(pf: float, wr: float) -> float:
    """Heuristic to convert historical Profit Factor and Win Rate to Agent Confidence (0.1 - 1.0)"""
    # Baseline 0.5
    conf = 0.5
    
    # Adjust for Profit Factor 
    if pf >= 2.0: conf += 0.3
    elif pf >= 1.5: conf += 0.2
    elif pf >= 1.2: conf += 0.1
    elif pf < 0.8: conf -= 0.2
    elif pf < 0.5: conf -= 0.4
    
    # Adjust for Win Rate
    if wr >= 60.0: conf += 0.2
    elif wr >= 50.0: conf += 0.1
    elif wr < 40.0: conf -= 0.1
    elif wr < 30.0: conf -= 0.2
    
    return max(0.1, min(1.0, conf))

def inject_report_to_db(report: dict, db) -> None:
    """Save the derived backtest confidences to the database so live agents use them."""
    for model_name, stats in report.get("Models", {}).items():
        if model_name == "unknown":
            continue
            
        pf = stats["Profit Factor"]
        wr = stats["Win Rate (%)"]
        trades = stats["Trades"]
        
        derived_conf = derive_confidence_from_model_stats(pf, wr)
        
        # Strategy pattern matches what ICTStrategy will query (e.g., 'ict_smc:trend_continuation_long')
        strategy_slug = f"ict_smc:{model_name}"
        
        # We don't have cumulative "total_score" logic cleanly for backtest injection, just pass 0
        db.upsert_confidence(strategy_slug, derived_conf, trades, 0)
        logger.info("Injected backtest confidence: %s => %.2f (PF:%.2f WR:%.1f%%)", strategy_slug, derived_conf, pf, wr)
