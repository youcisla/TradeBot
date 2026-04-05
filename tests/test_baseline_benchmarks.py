from datetime import UTC, datetime, timedelta

from backtesting.baseline_benchmarks import evaluate_baselines
from models.market_data import Candle


def _candles(n: int = 600) -> list[Candle]:
  base = datetime(2026, 1, 1, tzinfo=UTC)
  candles: list[Candle] = []
  price = 1.2000
  for i in range(n):
    drift = 0.0003 if (i // 30) % 2 == 0 else -0.0002
    price += drift
    candles.append(
      Candle(
        timestamp=base + timedelta(hours=i),
        open=price - 0.0002,
        high=price + 0.0007,
        low=price - 0.0007,
        close=price,
        volume=500 + (i % 50),
      )
    )
  return candles


def test_evaluate_baselines_returns_ranked_results():
  results = evaluate_baselines(_candles())
  assert len(results) == 3

  names = {r.model for r in results}
  assert names == {"momentum_baseline", "mean_reversion_baseline", "linear_score_baseline"}

  avg_returns = [r.avg_strategy_return for r in results]
  assert avg_returns == sorted(avg_returns, reverse=True)

  assert all(0.0 <= r.accuracy <= 1.0 for r in results)
  assert all(r.trades >= 0 for r in results)
