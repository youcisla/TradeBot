"""Tests for RiskAgent."""

from unittest.mock import patch

from agents.risk_agent import RiskAgent
from models.trade import Trade
from tests.conftest import make_signal, make_trade


class TestRiskAgent:
    @staticmethod
    def _signal(**kwargs):
        sig = make_signal(**kwargs)
        sig.entry_snapshot.session = "london"
        return sig

    def _make_agent(self, broker, open_trades=None, crucix_agent=None):
        trades = open_trades or []
        return RiskAgent(
            broker=broker,
            get_open_trades=lambda: trades,
            crucix_agent=crucix_agent,
        )

    def test_validate_passes_clean_signal(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        assert agent.validate(signal) is True

    def test_rejects_duplicate(self, broker, crucix_agent):
        existing = make_trade(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is False

    def test_allows_different_direction(self, broker, crucix_agent):
        existing = make_trade(symbol="EURUSD", direction="SELL", strategy="sma_crossover")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is True

    def test_rejects_correlation(self, broker, crucix_agent):
        """Same symbol + direction from another strategy should be blocked."""
        existing = make_trade(symbol="EURUSD", direction="BUY", strategy="other_strategy")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is False

    def test_rejects_max_trades(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings
        monkeypatch.setattr(_settings, "MAX_OPEN_TRADES", 3)
        trades = [
            make_trade(symbol="EURUSD", direction="BUY", broker_ticket=100_001),
            make_trade(symbol="GBPUSD", direction="SELL", broker_ticket=100_002),
            make_trade(symbol="USDJPY", direction="BUY", broker_ticket=100_003),
        ]
        agent = self._make_agent(broker, open_trades=trades, crucix_agent=crucix_agent)
        signal = self._signal(symbol="XAUUSD", direction="BUY")
        # 3 open >= MAX_OPEN_TRADES (3) → should fail
        assert agent.validate(signal) is False

    def test_rejects_high_spread(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_SPREAD_PIPS", 3.0)
        # T2-6: live spread is fetched via get_tick() — ensure it matches the
        # high snapshot spread so the test isn't overridden by MockConnector's
        # random 0.5–2.5 pip response.
        monkeypatch.setattr(
            broker, "get_tick",
            lambda sym: {"bid": 1.1050, "ask": 1.1055, "spread": 0.0005, "volume": 1000},
        )
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal(spread=0.0005)  # 5 pips > MAX_SPREAD_PIPS (3.0)
        assert agent._check_spread(signal) is False

    def test_spread_reject_sets_symbol_cooldown(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_SPREAD_PIPS", 3.0)
        monkeypatch.setattr(_settings, "SPREAD_REJECT_COOLDOWN_HITS", 2)
        monkeypatch.setattr(_settings, "SPREAD_REJECT_COOLDOWN_SECONDS", 120)
        monkeypatch.setattr(
            broker,
            "get_tick",
            lambda sym: {"bid": 1.1050, "ask": 1.1055, "spread": 0.0005, "volume": 1000},
        )

        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", spread=0.0005)

        assert agent._check_spread(signal) is False
        assert signal.symbol not in agent._spread_reject_until

        assert agent._check_spread(signal) is False
        assert signal.symbol in agent._spread_reject_until

    def test_position_size_positive(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        size = agent.calculate_position_size(signal)
        assert size >= 0.01

    def test_confidence_scaling_reduces_size(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal_high = self._signal()
        signal_high.confidence = 0.9
        size_high = agent.calculate_position_size(signal_high)

        signal_low = self._signal()
        signal_low.confidence = 0.3
        size_low = agent.calculate_position_size(signal_low)

        assert size_low <= size_high

    @patch("utils.telegram_bot.send_message")
    def test_drawdown_circuit_breaker(self, mock_tg, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_DAILY_LOSS", 0.05)
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        # First call sets day_start_equity
        signal = self._signal()
        agent.validate(signal)

        # Simulate drawdown by reducing broker equity
        agent._day_start_equity = 10_000.0
        monkeypatch.setattr(broker, "get_equity", lambda: 9_400.0)  # 6% loss > 5% limit
        agent._equity_cache = (0.0, 0.0)

        assert agent._check_drawdown() is True
        assert agent._circuit_breaker_active is True
