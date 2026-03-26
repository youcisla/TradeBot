"""Tests for AnalysisAgent."""

from agents.analysis_agent import AnalysisAgent
from models.market_data import MarketData
from tests.conftest import make_candles


class TestAnalysisAgent:
    def test_analyze_returns_context(self, crucix_agent):
        agent = AnalysisAgent(crucix_agent)
        candles = make_candles(60, base=1.1000, trend=0.0001)
        data = MarketData(
            symbol="EURUSD", bid=1.1060, ask=1.1062,
            spread=0.0002, volume=2000, candles=candles,
        )
        ctx = agent.analyze(data)
        assert ctx.symbol == "EURUSD"
        assert ctx.current_price == data.mid_price

    def test_sma_values_computed(self, crucix_agent):
        agent = AnalysisAgent(crucix_agent)
        candles = make_candles(60, base=1.1000, trend=0.0001)
        data = MarketData(
            symbol="EURUSD", bid=1.1060, ask=1.1062,
            spread=0.0002, volume=2000, candles=candles,
        )
        ctx = agent.analyze(data)
        assert ctx.sma_fast > 0
        assert ctx.sma_slow > 0

    def test_rsi_in_range(self, crucix_agent):
        agent = AnalysisAgent(crucix_agent)
        candles = make_candles(60, base=1.1000, trend=0.0001)
        data = MarketData(
            symbol="EURUSD", bid=1.1060, ask=1.1062,
            spread=0.0002, volume=2000, candles=candles,
        )
        ctx = agent.analyze(data)
        assert 0 <= ctx.rsi <= 100

    def test_atr_positive(self, crucix_agent):
        agent = AnalysisAgent(crucix_agent)
        candles = make_candles(60, base=1.1000, trend=0.0001)
        data = MarketData(
            symbol="EURUSD", bid=1.1060, ask=1.1062,
            spread=0.0002, volume=2000, candles=candles,
        )
        ctx = agent.analyze(data)
        assert ctx.atr > 0

    def test_trend_direction_bullish_on_uptrend(self, crucix_agent):
        agent = AnalysisAgent(crucix_agent)
        # Strong uptrend: sma_fast (last 10) >> sma_slow (last 50)
        candles = make_candles(60, base=1.0800, trend=0.0005)
        data = MarketData(
            symbol="EURUSD", bid=1.1100, ask=1.1102,
            spread=0.0002, volume=2000, candles=candles,
        )
        ctx = agent.analyze(data)
        assert ctx.trend_direction == "bullish"
        assert ctx.sma_fast > ctx.sma_slow

    def test_empty_candles_returns_safe_defaults(self, crucix_agent):
        agent = AnalysisAgent(crucix_agent)
        data = MarketData(
            symbol="EURUSD", bid=1.1060, ask=1.1062,
            spread=0.0002, volume=100, candles=[],
        )
        ctx = agent.analyze(data)
        assert ctx.sma_fast == 0
        assert ctx.sma_slow == 0
        assert ctx.atr == 0

    def test_sma_helper(self):
        assert AnalysisAgent._sma([1, 2, 3, 4, 5], 3) == round((3 + 4 + 5) / 3, 5)
        assert AnalysisAgent._sma([1, 2], 5) == 0.0

    def test_rsi_helper_insufficient_data(self):
        assert AnalysisAgent._rsi([1.0, 2.0], 14) == 50.0
