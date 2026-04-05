"""Deterministic replay runner with parity checks.

Replays one symbol from a historical CSV through the same scan-rank-execute
pipeline used in backtesting, exports a standardized artifact, and validates
basic parity/risk assumptions before live rollout.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
  sys.path.insert(0, str(_REPO))

from backtesting.engine import BacktestEngine
from config import settings


_REQUIRED_REPORT_KEYS = {
  "Total Trades",
  "Winning Trades",
  "Losing Trades",
  "Win Rate (%)",
  "Net Profit",
  "Profit Factor",
  "Max Drawdown (%)",
  "Initial Balance",
  "Final Balance",
}


def _parity_checks(report: dict) -> list[str]:
  errors: list[str] = []

  missing = sorted(_REQUIRED_REPORT_KEYS - set(report.keys()))
  if missing:
    errors.append(f"missing report keys: {', '.join(missing)}")

  total = int(report.get("Total Trades", 0))
  wins = int(report.get("Winning Trades", 0))
  losses = int(report.get("Losing Trades", 0))
  if total != wins + losses:
    errors.append("trade count mismatch: total != winning + losing")

  win_rate = float(report.get("Win Rate (%)", 0.0))
  if win_rate < 0.0 or win_rate > 100.0:
    errors.append("win rate out of bounds (expected 0..100)")

  max_dd = float(report.get("Max Drawdown (%)", 0.0))
  if max_dd < 0.0:
    errors.append("max drawdown cannot be negative")

  initial_balance = float(report.get("Initial Balance", 0.0))
  final_balance = float(report.get("Final Balance", 0.0))
  net_profit = float(report.get("Net Profit", 0.0))
  if round(initial_balance + net_profit, 2) != round(final_balance, 2):
    errors.append("balance mismatch: initial + net_profit != final")

  if settings.REQUIRE_RISK_APPROVAL is not True:
    errors.append("risk parity failed: REQUIRE_RISK_APPROVAL must be True")

  if settings.MAX_RISK_PER_TRADE > 0.02:
    errors.append("risk parity failed: MAX_RISK_PER_TRADE must be <= 0.02")

  return errors


def main() -> int:
  parser = argparse.ArgumentParser(description="Replay one symbol from historical CSV")
  parser.add_argument("--symbol", required=True, help="Instrument symbol (e.g., EURUSD)")
  parser.add_argument("--data", required=True, help="Path to CSV candle data")
  parser.add_argument("--profile", default=settings.BOT_PROFILE, help="Runtime profile label")
  parser.add_argument("--initial-balance", type=float, default=10_000.0)
  parser.add_argument(
    "--artifact-out",
    default="",
    help="Artifact JSON path (default: backtesting/runs/<symbol>_replay_artifact.json)",
  )
  parser.add_argument(
    "--skip-parity-check",
    action="store_true",
    help="Export replay artifact without parity gate checks",
  )
  args = parser.parse_args()

  engine = BacktestEngine(args.data, initial_balance=args.initial_balance)
  report = engine.run(
    args.symbol,
    profile=args.profile,
    mode="replay",
    export_artifact=True,
    artifact_path=args.artifact_out or None,
  )

  print("Replay completed")
  print(json.dumps({
    "symbol": args.symbol,
    "profile": args.profile,
    "total_trades": report.get("Total Trades", 0),
    "net_profit": report.get("Net Profit", 0.0),
    "max_drawdown_pct": report.get("Max Drawdown (%)", 0.0),
    "artifact_path": report.get("Artifact Path", ""),
  }, indent=2))

  if args.skip_parity_check:
    return 0

  errors = _parity_checks(report)
  if errors:
    print("\nParity check failed:")
    for err in errors:
      print(f"- {err}")
    return 1

  print("\nParity check passed")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
