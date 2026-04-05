"""Tests for MarketAgent."""

import pytest

from agents.market_agent import MarketAgent
from filters.data_validator import DataValidationError


class TestMarketAgent:
    def test_get_data_returns_market_data(self, broker):
        agent = MarketAgent(broker)
        data = agent.get_data("EURUSD")
        assert data.symbol == "EURUSD"
        assert data.bid > 0
        assert data.ask > 0
        assert data.spread >= 0
        assert len(data.candles) > 0

    def test_mid_price_is_average(self, broker):
        agent = MarketAgent(broker)
        data = agent.get_data("EURUSD")
        expected = round((data.bid + data.ask) / 2, 5)
        assert data.mid_price == expected

    def test_candles_count(self, broker):
        agent = MarketAgent(broker)
        data = agent.get_data("EURUSD")
        assert len(data.candles) == 100  # default count

    def test_validator_rejects_negative_price(self, broker):
        """Patch broker to return bad data and verify rejection."""
        agent = MarketAgent(broker)
        original_get_tick = broker.get_tick

        def bad_tick(symbol):
            return {"bid": -1.0, "ask": -1.0, "spread": 0.0, "volume": 0.0}

        broker.get_tick = bad_tick
        with pytest.raises(DataValidationError):
            agent.get_data("EURUSD")

        broker.get_tick = original_get_tick

    def test_validator_rejects_negative_spread(self, broker):
        agent = MarketAgent(broker)

        def neg_spread_tick(symbol):
            return {"bid": 1.1050, "ask": 1.1049, "spread": -0.0001, "volume": 100}

        broker.get_tick = neg_spread_tick
        with pytest.raises(DataValidationError):
            agent.get_data("EURUSD")

    def test_per_symbol_validators_are_separate(self, broker):
        agent = MarketAgent(broker)
        agent.get_data("EURUSD")
        agent.get_data("GBPUSD")
        assert "EURUSD" in agent._validators
        assert "GBPUSD" in agent._validators
        assert agent._validators["EURUSD"] is not agent._validators["GBPUSD"]

    def test_crypto_stuck_quote_threshold_is_more_lenient(self, broker):
        agent = MarketAgent(broker)

        # Warm up validator state for BTCUSD with unchanged price sequence.
        static_bid = 50000.0
        static_ask = 50000.5

        def static_tick(symbol):
            return {
                "bid": static_bid,
                "ask": static_ask,
                "spread": static_ask - static_bid,
                "volume": 100,
            }

        broker.get_tick = static_tick

        # Crypto threshold defaults to 14, so first 13 validations should pass.
        for _ in range(13):
            data = agent.get_data("BTCUSD")
            assert data.symbol == "BTCUSD"

        # 14th unchanged tick should raise a stuck-quote rejection.
        with pytest.raises(DataValidationError):
            agent.get_data("BTCUSD")
