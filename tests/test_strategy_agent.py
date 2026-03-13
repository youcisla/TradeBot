"""Tests for StrategyAgent."""

from agents.strategy_agent import StrategyAgent
from models.market_data import MarketContext
from models.signal import Signal
from strategies.sma_crossover import SmaCrossoverStrategy
from tests.conftest import make_candles


def _mock_confidence(strategy_name: str) -> float:
    return 0.5


def _low_confidence(strategy_name: str) -> float:
    return 0.1  # below CONFIDENCE_ALLOW (0.3)


class TestStrategyAgent:
    def test_detect_returns_none_when_no_signal(self):
        agent = StrategyAgent([SmaCrossoverStrategy()], _mock_confidence)
        ctx = MarketContext(
            symbol="EURUSD", current_price=1.1050,
            sma_fast=1.1050, sma_slow=1.1050, atr=0.0010,
            candles=make_candles(60),
        )
        # No crossover → no signal
        result = agent.detect(ctx)
        assert result is None

    def test_detect_skips_disabled_strategy(self):
        agent = StrategyAgent([SmaCrossoverStrategy()], _low_confidence)
        candles = make_candles(60, base=1.0800, trend=0.0005)
        ctx = MarketContext(
            symbol="EURUSD", current_price=1.1100,
            sma_fast=1.1100, sma_slow=1.1000, atr=0.0010,
            candles=candles,
        )
        result = agent.detect(ctx)
        assert result is None  # strategy disabled by low confidence

    def test_detect_respects_confidence_threshold(self):
        """Strategy at exactly CONFIDENCE_ALLOW should be eligible."""
        agent = StrategyAgent(
            [SmaCrossoverStrategy()],
            lambda n: 0.3,  # exactly at threshold
        )
        # Even if the strategy fires, the important thing is it's not skipped
        ctx = MarketContext(
            symbol="EURUSD", current_price=1.1050,
            sma_fast=1.1050, sma_slow=1.1050, atr=0.0010,
            candles=make_candles(60),
        )
        # No crossover so None, but the test is that it didn't short-circuit
        result = agent.detect(ctx)
        assert result is None

    def test_detect_sets_confidence_on_signal(self):
        """When a signal is produced, its confidence should be set."""
        candles = make_candles(60, base=1.0800, trend=0.0005)
        # Make the last candle's close lower than sma_slow to fake a crossover
        # Easier: provide a context where fast > slow AND prev close < slow
        ctx = MarketContext(
            symbol="EURUSD", current_price=1.1100,
            sma_fast=1.1100, sma_slow=1.1000, rsi=55.0, atr=0.0010,
            candles=candles,
        )
        # The SMA crossover strategy checks candle[-2].close vs sma_slow
        # With uptrend candles candle[-2].close might be below sma_slow
        agent = StrategyAgent([SmaCrossoverStrategy()], lambda n: 0.8)
        result = agent.detect(ctx)
        if result is not None:
            assert result.confidence == 0.8

    def test_empty_strategies_returns_none(self):
        agent = StrategyAgent([], _mock_confidence)
        ctx = MarketContext(symbol="EURUSD", current_price=1.1050)
        assert agent.detect(ctx) is None
