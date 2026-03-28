"""Data Downloader for Historical Backtesting.

Connects to MT5 to download historical candle data and saves it locally
for use by the backtesting engine.
"""

from __future__ import annotations

import csv
import logging
from datetime import UTC, datetime
from pathlib import Path

import MetaTrader5 as mt5

from broker.mt5_connector import _TF_MAP, MT5Connector

logger = logging.getLogger(__name__)

# Directory to store historical data
DATA_DIR = Path(__file__).parent.parent / "data" / "history"


def download_history(
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
) -> Path | None:
    """Download historical candles from MT5 and save to CSV.

    Args:
        symbol: The instrument to download (e.g., 'EURUSD').
        timeframe: The timeframe to download (e.g., 'H1', 'M15').
        start_date: The start datetime (inclusive).
        end_date: The end datetime (inclusive).

    Returns:
        Path to the saved CSV file, or None if download failed.
    """
    if not start_date.tzinfo:
        start_date = start_date.replace(tzinfo=UTC)
    if not end_date.tzinfo:
        end_date = end_date.replace(tzinfo=UTC)

    logger.info("Connecting to MT5 to download %s %s from %s to %s",
                symbol, timeframe, start_date.date(), end_date.date())

    # Reuse MT5Connector to handle symbol variants (e.g., EURUSD.r)
    connector = MT5Connector()
    if not connector.connect():
        logger.error("Failed to connect to MT5 for download")
        return None

    try:
        broker_sym = connector.resolve(symbol)
        mt5.symbol_select(broker_sym, True)

        tf = _TF_MAP.get(timeframe, mt5.TIMEFRAME_H1)

        # copy_rates_range expects timestamps or datetime objects
        # Note: MT5 python API is sometimes picky about timezones,
        # it usually treats naive datetimes as local time.
        rates = mt5.copy_rates_range(broker_sym, tf, start_date, end_date)

        # Fallback: copy_rates_from_pos doesn't require pre-loaded date range history
        if rates is None or len(rates) == 0:
            max_bars = int((end_date - start_date).total_seconds() / 3600)
            rates = mt5.copy_rates_from_pos(broker_sym, tf, 0, min(max_bars, 50_000))

        if rates is None or len(rates) == 0:
            logger.error("No data returned for %s (%s). Check MT5 history availability.", symbol, broker_sym)
            return None

        logger.info("Downloaded %d candles for %s", len(rates), symbol)

        # Save to CSV
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
        filepath = DATA_DIR / filename

        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "open", "high", "low", "close", "tick_volume", "spread"])
            for r in rates:
                writer.writerow([r["time"], r["open"], r["high"], r["low"], r["close"], r["tick_volume"], r["spread"]])

        logger.info("Saved data to %s", filepath)
        return filepath

    finally:
        connector.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Example usage: download 1 month of H1 data
    from datetime import timedelta
    end = datetime.now(UTC)
    start = end - timedelta(days=30)

    download_history("EURUSD", "H1", start, end)
