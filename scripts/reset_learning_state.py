"""Reset historical learning/scoring state.

This clears tables used by the learning loop so confidence scoring starts fresh:
- trade_scores
- strategy_confidence
- performance_snapshots

Usage:
  c:/Users/Youcef/Downloads/TradeBot/.venv/Scripts/python.exe scripts/reset_learning_state.py --yes
"""

from __future__ import annotations

import argparse
import json
import sys

from database.db import Database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset historical learning state")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm reset without interactive prompt",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.yes:
        answer = input(
            "This will DELETE trade_scores, strategy_confidence, and performance_snapshots. Continue? [y/N]: "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.")
            return 1

    db = Database()
    try:
        result = db.reset_learning_state()
        print("Learning state reset complete:")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
