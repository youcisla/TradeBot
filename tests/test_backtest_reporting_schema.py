"""Tests for standardized backtest/replay run artifacts."""

from backtesting.report import generate_report, generate_run_artifact
from broker.connector import PositionInfo


def _closed_position(ticket: int, pnl: float, comment: str) -> PositionInfo:
  return PositionInfo(
    ticket=ticket,
    symbol="EURUSD",
    direction="BUY",
    lot_size=0.10,
    entry_price=1.1000,
    stop_loss=1.0950,
    take_profit=1.1050,
    current_price=1.1020,
    pnl=pnl,
    comment=comment,
  )


def test_generate_run_artifact_has_required_structure():
  closed = [
    _closed_position(1, 12.5, "ict_smc_TP1"),
    _closed_position(2, -8.0, "ict_smc_TP2"),
  ]
  report = generate_report(closed, initial_balance=10000.0)

  artifact = generate_run_artifact(
    closed,
    initial_balance=10000.0,
    symbol="EURUSD",
    profile="paper",
    mode="replay",
    source_data="data/EURUSD_H1.csv",
    report=report,
  )

  assert artifact["schema_version"] == "1.0"
  assert artifact["run"]["mode"] == "replay"
  assert artifact["run"]["symbol"] == "EURUSD"
  assert "metrics" in artifact
  assert "trade_ledger" in artifact
  assert "equity_curve" in artifact
  assert len(artifact["trade_ledger"]) == 2
  assert artifact["metrics"]["total_trades"] == 2
  assert artifact["metrics"]["winning_trades"] == 1
  assert artifact["metrics"]["losing_trades"] == 1


def test_generate_run_artifact_equity_curve_starts_at_initial_balance():
  closed = [_closed_position(1, 5.0, "sma_crossover_TP1")]
  artifact = generate_run_artifact(
    closed,
    initial_balance=5000.0,
    symbol="EURUSD",
    profile="dev",
    mode="backtest",
    source_data="data/mock.csv",
  )

  assert artifact["equity_curve"][0]["step"] == 0
  assert artifact["equity_curve"][0]["balance"] == 5000.0
  assert artifact["equity_curve"][1]["balance"] == 5005.0
