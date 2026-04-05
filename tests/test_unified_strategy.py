"""Tests for UnifiedStrategy."""

from datetime import UTC, datetime

from models.market_data import MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy
from strategies.unified_strategy import UnifiedStrategy


class _StaticStrategy(BaseStrategy):
    def __init__(self, name: str, signal: Signal | None):
        self.name = name
        self._signal = signal

    def detect(self, context: MarketContext):
        return self._signal

    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        return 0.0

    def calculate_tps(self, context: MarketContext, entry: float, sl: float, direction: str):
        return (0.0, 0.0, 0.0)


def _signal(strategy: str, direction: str, confidence: float) -> Signal:
    return Signal(
        strategy=strategy,
        symbol="EURUSD",
        direction=direction,
        entry_price=1.1000,
        stop_loss=1.0950,
        take_profit_1=1.1050,
        take_profit_2=1.1100,
        take_profit_3=1.1150,
        confidence=confidence,
        timestamp=datetime.now(UTC),
        reason="test",
        entry_snapshot=EntrySnapshot(),
    )


class TestUnifiedStrategy:
    def test_returns_none_when_all_components_none(self):
        strategy = UnifiedStrategy([
            _StaticStrategy("a", None),
            _StaticStrategy("b", None),
        ])
        ctx = MarketContext(symbol="EURUSD", current_price=1.1)
        assert strategy.detect(ctx) is None

    def test_prefers_confirmed_direction_cluster(self):
        strategy = UnifiedStrategy([
            _StaticStrategy("deepseek", _signal("deepseek", "BUY", 0.70)),
            _StaticStrategy("ict_smc", _signal("ict_smc", "BUY", 0.64)),
            _StaticStrategy("sma_crossover", _signal("sma_crossover", "SELL", 0.85)),
        ])
        ctx = MarketContext(symbol="EURUSD", current_price=1.1)

        result = strategy.detect(ctx)

        assert result is not None
        assert result.direction == "BUY"
        assert result.strategy == "unified_alpha"

    def test_uses_anchor_tp_and_sl_from_best_signal(self):
        anchor = _signal("deepseek", "BUY", 0.80)
        anchor.stop_loss = 1.0900
        anchor.take_profit_1 = 1.1200
        anchor.take_profit_2 = 1.1300
        anchor.take_profit_3 = 1.1400

        strategy = UnifiedStrategy([
            _StaticStrategy("deepseek", anchor),
            _StaticStrategy("sma_crossover", _signal("sma_crossover", "BUY", 0.60)),
        ])
        ctx = MarketContext(symbol="EURUSD", current_price=1.1)

        result = strategy.detect(ctx)

        assert result is not None
        assert result.stop_loss == 1.0900
        assert result.take_profit_1 == 1.1200
        assert result.take_profit_2 == 1.1300
        assert result.take_profit_3 == 1.1400
