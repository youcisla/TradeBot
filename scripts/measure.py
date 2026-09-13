"""Walk-forward measurement CLI.

The corrected replacement for ``scripts/backtest.py``.  The model — as-of
slicing, real spread and commission, touched-fill requirement, true 40/30/30
scale-out, per-position statistics — lives in ``backtesting/measure.py``; this
file only fetches data, drives it, and prints the report.

Usage
-----
    python scripts/measure.py
    python scripts/measure.py --symbols EURUSD,GBPUSD --candles 20000
    python scripts/measure.py --folds 6 --holdout-pct 25

Every number produced here is out-of-sample in the sense that matters: nothing
in this file tunes a parameter.  The holdout block at the end is separated by
time so it can stay untouched while parameters are explored elsewhere.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from backtesting import measure  # noqa: E402
from models.market_data import Candle  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("measure")

# Liquid majors that exist on PU Prime.  Deliberately NOT the full SYMBOLS list —
# scanning 1,000+ instruments by accident is slow and tempts symbol selection.
DEFAULT_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
    "USDCAD", "USDCHF", "NZDUSD", "EURJPY",
]

RULE = "-" * 132


def fetch_series(conn, symbol: str, h1_bars: int) -> dict[str, list[Candle]]:
    """Fetch every timeframe the strategy reads, as real bars from MT5.

    M15 comes from the broker rather than being resampled from H1: duplicating
    each H1 bar into four identical M15 bars fabricates intra-hour structure
    that never existed, which any M15-based entry logic would then trade on.
    """
    return {
        "H1": conn.get_candles(symbol, "H1", h1_bars),
        "H4": conn.get_candles(symbol, "H4", h1_bars // 4 + 250),
        "D1": conn.get_candles(symbol, "D1", h1_bars // 24 + 120),
        "M30": conn.get_candles(symbol, "M30", h1_bars * 2 + 250),
        "M15": conn.get_candles(symbol, "M15", h1_bars * 4 + 250),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward measurement")
    parser.add_argument("--symbols", default="", help="Comma-separated (default: 8 majors)")
    parser.add_argument("--candles", type=int, default=20_000, help="H1 bars per symbol")
    parser.add_argument("--folds", type=int, default=5, help="Sequential stability folds")
    parser.add_argument("--holdout-pct", type=float, default=20.0, help="Frozen holdout size")
    parser.add_argument(
        "--optimistic",
        action="store_true",
        help=(
            "Assume targets hit before the stop within a bar.  Flatters results; "
            "use only as a sensitivity check against the pessimistic default."
        ),
    )
    parser.add_argument(
        "--invert",
        action="store_true",
        help=(
            "Trade the exact opposite of every signal (same entry, mirrored "
            "stop and targets).  If losses are a sign error, this profits."
        ),
    )
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] or DEFAULT_SYMBOLS

    from broker.mt5_connector import MT5Connector
    from strategies.ict_strategy import ICTStrategy

    conn = MT5Connector()
    if not conn.connect():
        logger.error("MT5 connection failed — is the terminal running?")
        sys.exit(1)

    def factory(broker):
        return ICTStrategy(broker=broker)

    all_positions: list[measure.Position] = []
    print()
    print(f"PER SYMBOL — {len(symbols)} symbols, {args.candles} H1 bars, strategy: ICT")
    print(RULE)
    try:
        for sym in symbols:
            series = fetch_series(conn, sym, args.candles)
            h1 = series.get("H1") or []
            if not h1:
                logger.warning("%s: no H1 data — skipping", sym)
                continue
            positions = measure.run_symbol(
                sym,
                series,
                strategy_factory=factory,
                pessimistic=not args.optimistic,
                invert=args.invert,
            )
            all_positions.extend(positions)
            print(measure.summarise(positions, h1, label=sym).render())
    finally:
        conn.disconnect()

    if not all_positions:
        print()
        print("No positions were produced.  The strategy fired no signals on this data —")
        print("which is itself the answer: there is nothing here to measure.")
        return

    all_positions.sort(key=lambda p: p.opened_at)

    print()
    print("POOLED — every position, all symbols (B&H n/a: no single price series)")
    print(RULE)
    print(measure.compute_metrics(all_positions, label="ALL pooled").render())

    print()
    print(f"SEQUENTIAL FOLDS (n={args.folds}) — is the result stable, or one lucky stretch?")
    print(RULE)
    for i, fold in enumerate(measure.split_folds(all_positions, args.folds), 1):
        if fold:
            print(measure.compute_metrics(fold, label=f"fold {i}").render())

    cut = int(len(all_positions) * (1.0 - args.holdout_pct / 100.0))
    holdout = all_positions[cut:]
    print()
    print(f"FROZEN HOLDOUT — last {args.holdout_pct:.0f}% by time, never tuned against")
    print(RULE)
    if holdout:
        print(measure.compute_metrics(holdout, label="holdout").render())
    else:
        print("  (no positions in the holdout window)")
    print()


if __name__ == "__main__":
    main()
