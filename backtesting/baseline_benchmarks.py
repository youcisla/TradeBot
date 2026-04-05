"""Baseline model benchmark harness for ML4T workflow parity checks."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from backtesting.factor_library import extract_factor_rows
from backtesting.walk_forward import generate_purged_walk_forward_slices
from models.market_data import Candle


@dataclass
class BaselineResult:
  model: str
  accuracy: float
  avg_strategy_return: float
  trades: int


def _target_return(closes: list[float], idx: int, horizon: int) -> float:
  if idx + horizon >= len(closes):
    return 0.0
  entry = closes[idx]
  exit_ = closes[idx + horizon]
  return (exit_ - entry) / entry if entry else 0.0


def _predict_momentum(row: dict[str, float]) -> int:
  return 1 if row["ret_5"] >= 0 else -1


def _predict_mean_reversion(row: dict[str, float]) -> int:
  if row["rsi_14"] >= 60:
    return -1
  if row["rsi_14"] <= 40:
    return 1
  return 1 if row["ret_1"] >= 0 else -1


def _predict_linear_score(row: dict[str, float]) -> int:
  score = (
    0.55 * row["ret_5"]
    + 0.25 * row["ret_1"]
    - 0.15 * row["atr_norm"]
    + 0.05 * row["vol_z"]
  )
  return 1 if score >= 0 else -1


def _evaluate_model(
  rows: list[dict[str, float]],
  closes: list[float],
  slices,
  predictor,
) -> BaselineResult:
  wins = 0
  total = 0
  strategy_returns: list[float] = []

  for wf_slice in slices:
    for i in wf_slice.test_indices:
      if i >= len(rows):
        continue
      row = rows[i]
      idx = int(row["idx"])
      realized = _target_return(closes, idx, horizon=1)
      pred = predictor(row)

      if realized == 0:
        continue

      total += 1
      correct = (pred > 0 and realized > 0) or (pred < 0 and realized < 0)
      if correct:
        wins += 1

      strategy_returns.append(pred * realized)

  accuracy = (wins / total) if total else 0.0
  avg_ret = mean(strategy_returns) if strategy_returns else 0.0
  return BaselineResult(model="", accuracy=accuracy, avg_strategy_return=avg_ret, trades=total)


def evaluate_baselines(
  candles: list[Candle],
  *,
  lookback: int = 30,
  train_size: int = 300,
  test_size: int = 100,
  purge_size: int = 5,
  embargo_size: int = 3,
) -> list[BaselineResult]:
  """Run baseline directional models with purged walk-forward validation."""
  rows = extract_factor_rows(candles, lookback=lookback)
  if not rows:
    return []

  closes = [c.close for c in candles]
  sample_count = len(rows)

  slices = generate_purged_walk_forward_slices(
    sample_count,
    train_size=min(train_size, max(1, sample_count // 2)),
    test_size=min(test_size, max(1, sample_count // 4)),
    purge_size=purge_size,
    embargo_size=embargo_size,
  )
  if not slices:
    return []

  momentum = _evaluate_model(rows, closes, slices, _predict_momentum)
  momentum.model = "momentum_baseline"

  mean_rev = _evaluate_model(rows, closes, slices, _predict_mean_reversion)
  mean_rev.model = "mean_reversion_baseline"

  linear = _evaluate_model(rows, closes, slices, _predict_linear_score)
  linear.model = "linear_score_baseline"

  return sorted([momentum, mean_rev, linear], key=lambda r: r.avg_strategy_return, reverse=True)
