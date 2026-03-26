"""Tests for RiskAgent."""

from unittest.mock import patch

from agents.risk_agent import RiskAgent
from models.trade import Trade
from tests.conftest import make_signal, make_trade


class TestRiskAgent:
    def _make_agent(self, broker, open_trades=None, crucix_agent=None):
        trades = open_trades or []
        return RiskAgent(
            broker=broker,
            get_open_trades=lambda: trades,
            crucix_agent=crucix_agent,
        )

    def test_validate_passes_clean_signal(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = make_signal()
        assert agent.validate(signal) is True

    def test_rejects_duplicate(self, broker, crucix_agent):
        existing = make_trade(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = make_signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is False

    def test_allows_different_direction(self, broker, crucix_agent):
        existing = make_trade(symbol="EURUSD", direction="SELL", strategy="sma_crossover")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = make_signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is True

    def test_rejects_correlation(self, broker, crucix_agent):
        """Same symbol + direction from another strategy should be blocked."""
        existing = make_trade(symbol="EURUSD", direction="BUY", strategy="other_strategy")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = make_signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is False

    def test_rejects_max_trades(self, broker, crucix_agent):
        trades = [
            make_trade(symbol="EURUSD", direction="BUY", broker_ticket=100_001),
            make_trade(symbol="GBPUSD", direction="SELL", broker_ticket=100_002),
            make_trade(symbol="USDJPY", direction="BUY", broker_ticket=100_003),
        ]
        agent = self._make_agent(broker, open_trades=trades, crucix_agent=crucix_agent)
        signal = make_signal(symbol="XAUUSD", direction="BUY")
        # 3 open >= MAX_OPEN_TRADES (3) → should fail
        assert agent.validate(signal) is False

    def test_rejects_high_spread(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = make_signal(spread=0.0005)  # 5 pips > MAX_SPREAD_PIPS (3.0)
        assert agent.validate(signal) is False

    def test_position_size_positive(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = make_signal()
        size = agent.calculate_position_size(signal)
        assert size >= 0.01

    def test_confidence_scaling_reduces_size(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal_high = make_signal()
        signal_high.confidence = 0.9
        size_high = agent.calculate_position_size(signal_high)

        signal_low = make_signal()
        signal_low.confidence = 0.3
        size_low = agent.calculate_position_size(signal_low)

        assert size_low <= size_high

    @patch("utils.telegram_bot.send_message")
    def test_drawdown_circuit_breaker(self, mock_tg, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        # First call sets day_start_equity
        signal = make_signal()
        agent.validate(signal)

        # Simulate drawdown by reducing broker equity
        agent._day_start_equity = 10_000.0
        broker._balance = 9_400.0  # 6% loss > 5% limit

        assert agent.validate(signal) is False
        assert agent._circuit_breaker_active is True
