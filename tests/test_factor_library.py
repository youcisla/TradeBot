from datetime import UTC, datetime, timedelta

from backtesting.factor_library import extract_factor_rows
from models.market_data import Candle


def _candles(n: int = 80) -> list[Candle]:
  base = datetime(2026, 1, 1, tzinfo=UTC)
  candles: list[Candle] = []
  price = 1.1000
  for i in range(n):
    price += 0.0005 if i % 2 == 0 else -0.0002
    candles.append(
      Candle(
        timestamp=base + timedelta(hours=i),
        open=price - 0.0003,
        high=price + 0.0008,
        low=price - 0.0009,
        close=price,
        volume=100 + i,
      )
    )
  return candles


def test_extract_factor_rows_shape_and_keys():
  rows = extract_factor_rows(_candles(), lookback=30)
  assert len(rows) > 0

  expected = {
    "idx",
    "close",
    "ret_1",
    "ret_5",
    "range_hl",
    "oc_delta",
    "close_location",
    "range_expansion_5",
    "vol_z",
    "volume_impulse",
    "realized_vol_5",
    "realized_vol_20",
    "volatility_regime",
    "trend_persistence_5",
    "rsi_14",
    "atr_norm",
  }
  assert expected.issubset(set(rows[0].keys()))


def test_extract_factor_rows_rsi_bounds():
  rows = extract_factor_rows(_candles(), lookback=25)
  assert all(0.0 <= row["rsi_14"] <= 100.0 for row in rows)


def test_extract_factor_rows_microstructure_proxies_have_reasonable_ranges():
  rows = extract_factor_rows(_candles(), lookback=30)
  assert all(0.0 <= row["close_location"] <= 1.0 for row in rows)
  assert all(row["range_expansion_5"] >= 0.0 for row in rows)
  assert all(row["volume_impulse"] >= 0.0 for row in rows)
