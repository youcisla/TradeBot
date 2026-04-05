"""Reusable alpha factor feature extraction for ML4T-style experiments."""

from __future__ import annotations

import math
from statistics import mean, pstdev

from models.market_data import Candle


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
  if denominator == 0:
    return default
  return numerator / denominator


def _rsi(closes: list[float], period: int = 14) -> float:
  if len(closes) < period + 1:
    return 50.0
  deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
  recent = deltas[-period:]
  gains = [d for d in recent if d > 0]
  losses = [-d for d in recent if d < 0]
  avg_gain = sum(gains) / period if gains else 0.0
  avg_loss = sum(losses) / period if losses else 0.0001
  rs = avg_gain / avg_loss
  return 100.0 - (100.0 / (1.0 + rs))


def _atr(candles: list[Candle], period: int = 14) -> float:
  if len(candles) < period + 1:
    return 0.0
  true_ranges: list[float] = []
  for i in range(1, len(candles)):
    cur = candles[i]
    prev = candles[i - 1]
    tr = max(
      cur.high - cur.low,
      abs(cur.high - prev.close),
      abs(cur.low - prev.close),
    )
    true_ranges.append(tr)
  window = true_ranges[-period:]
  return sum(window) / len(window) if window else 0.0


def extract_factor_rows(candles: list[Candle], lookback: int = 30) -> list[dict[str, float]]:
  """Extract one factor row per candle from a rolling lookback window.

  Returns rows with numeric features and metadata keys:
  - idx: source candle index
  - close: current close
  """
  if lookback < 15:
    lookback = 15

  rows: list[dict[str, float]] = []
  closes = [c.close for c in candles]
  volumes = [c.volume for c in candles]

  for idx in range(lookback, len(candles)):
    window = candles[idx - lookback:idx + 1]
    close_now = closes[idx]
    close_prev = closes[idx - 1]

    ret_1 = _safe_div(close_now - close_prev, close_prev)
    close_5 = closes[idx - 5] if idx >= 5 else close_prev
    ret_5 = _safe_div(close_now - close_5, close_5)

    high_now = candles[idx].high
    low_now = candles[idx].low
    range_hl = _safe_div(high_now - low_now, close_now)
    oc_delta = _safe_div(close_now - candles[idx].open, candles[idx].open)

    prev_ranges = [c.high - c.low for c in candles[max(0, idx - 5):idx]]
    avg_prev_range = mean(prev_ranges) if prev_ranges else (high_now - low_now)
    range_expansion_5 = _safe_div(high_now - low_now, avg_prev_range, default=1.0)

    close_location = _safe_div(close_now - low_now, high_now - low_now, default=0.5)

    vol_window = volumes[idx - lookback:idx]
    vol_mu = mean(vol_window) if vol_window else 0.0
    vol_sigma = pstdev(vol_window) if len(vol_window) > 1 else 0.0
    vol_z = _safe_div(volumes[idx] - vol_mu, vol_sigma, default=0.0)

    short_vol_window = volumes[max(0, idx - 5):idx]
    short_vol_mu = mean(short_vol_window) if short_vol_window else volumes[idx]
    volume_impulse = _safe_div(volumes[idx], short_vol_mu, default=1.0)

    ret_1_window_5 = []
    for j in range(max(1, idx - 4), idx + 1):
      ret = _safe_div(closes[j] - closes[j - 1], closes[j - 1])
      ret_1_window_5.append(ret)

    ret_1_window_20 = []
    for j in range(max(1, idx - 19), idx + 1):
      ret = _safe_div(closes[j] - closes[j - 1], closes[j - 1])
      ret_1_window_20.append(ret)

    realized_vol_5 = pstdev(ret_1_window_5) if len(ret_1_window_5) > 1 else 0.0
    realized_vol_20 = pstdev(ret_1_window_20) if len(ret_1_window_20) > 1 else 0.0
    volatility_regime = _safe_div(realized_vol_5, realized_vol_20, default=1.0)

    trend_votes = 0
    for ret in ret_1_window_5:
      if ret > 0:
        trend_votes += 1
      elif ret < 0:
        trend_votes -= 1
    trend_persistence_5 = _safe_div(float(trend_votes), float(len(ret_1_window_5) or 1))

    rsi_14 = _rsi(closes[:idx + 1], period=14)
    atr_14 = _atr(candles[:idx + 1], period=14)
    atr_norm = _safe_div(atr_14, close_now)

    rows.append({
      "idx": float(idx),
      "close": close_now,
      "ret_1": ret_1,
      "ret_5": ret_5,
      "range_hl": range_hl,
      "oc_delta": oc_delta,
      "close_location": close_location,
      "range_expansion_5": range_expansion_5,
      "vol_z": vol_z,
      "volume_impulse": volume_impulse,
      "realized_vol_5": realized_vol_5,
      "realized_vol_20": realized_vol_20,
      "volatility_regime": volatility_regime,
      "trend_persistence_5": trend_persistence_5,
      "rsi_14": rsi_14,
      "atr_norm": atr_norm,
    })

  return rows
