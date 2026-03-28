---
name: add-strategy
description: "Creating or modifying a trading strategy in NeuralFX — BaseStrategy interface, ICT engine integration, signal construction."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# Adding or Modifying a Trading Strategy

## BaseStrategy Interface (`strategies/base_strategy.py`)

Every strategy must implement:
```python
class MyStrategy(BaseStrategy):
    name = "my_strategy"   # used as signal.strategy prefix

    def detect(self, context: MarketContext) -> Optional[Signal]:
        """Return Signal or None. Must never raise."""

    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        """Return stop-loss price."""

    def calculate_tps(self, context: MarketContext, entry: float,
                      sl: float, direction: str) -> tuple[float, float, float]:
        """Return (tp1, tp2, tp3)."""
```

## Building a Signal

```python
from models.signal import Signal, EntrySnapshot

signal = Signal(
    strategy=f"{self.name}:MODEL_NAME",   # e.g. "ict_smc:TREND_CONTINUATION_LONG"
    symbol=context.symbol,
    direction="BUY",      # or "SELL"
    entry_price=entry,
    stop_loss=sl,
    take_profit_1=tp1,
    take_profit_2=tp2,
    take_profit_3=tp3,
    take_profit_4=tp4,          # 0.0 if no runner
    structural_be=structural_be, # 0.0 if no structural BE
    confidence=0.75,             # 0.0 – 1.0
    reason="ICT FVG + OB confluence at London open",
    entry_snapshot=EntrySnapshot(
        spread=context.spread,
        rsi_aligned=True,
        trend_aligned=True,
        volume_sufficient=context.volume > 0,
        near_news_event=context.near_news_event,
        market_condition=context.regime.value,
        session=context.session.value,
        day_of_week=day_of_week(),
    ),
)
```

## ICT Strategy Structure (`strategies/ict_strategy.py`)

The ICT strategy wraps the ICT engine (`strategies/ict/engine.py`). The engine:
1. Receives `symbol, candles, htf_candles, current_price, bid, ask, atr, timeframe`
2. Returns `(ict_ctx, best_setup, rejected_setup)`
3. `best_setup` is the highest-scoring `SetupModel` above `min_confidence`

### ICT Setup models (`models/ict_models.py`):
```
TREND_CONTINUATION_LONG, TREND_CONTINUATION_SHORT
RANGE_DEALING_LONG, RANGE_DEALING_SHORT
REVERSAL_LONG, REVERSAL_SHORT
```

### ICT scoring components:
- HTF bias alignment
- Premium/discount zone
- Liquidity swept
- MSS confirmed
- Displacement present
- FVG present
- Order Block present
- Session valid (London/NY killzone)

## StrategyAgent Integration

`StrategyAgent` iterates over all strategies in priority order and returns the highest-confidence Signal:
```python
# In main.py
strategy_agent = StrategyAgent(
    strategies=[deepseek_strategy, ict_strategy, neural_strategy],
    db=db,
    min_confidence=settings.DEEPSEEK_MIN_CONFIDENCE,
)
```

To add a new strategy: instantiate it and include it in the strategies list.

## Council Weighting

If your strategy has a domain-specific expert in CouncilAgent, add strategy-aware weighting in `agents/council_agent.py`:
```python
is_ict_signal = signal.strategy.startswith("ict_smc")
is_my_signal = signal.strategy.startswith("my_strategy")
if is_ict_signal:
    confidence = ict.score * 0.50 + ...
elif is_my_signal:
    confidence = my_expert.score * 0.50 + ...
```

## Adding a New ICT Setup Model

1. Add model enum value in `models/ict_models.py`
2. Add scoring logic in `strategies/ict/scoring.py`
3. Add detection logic in appropriate ICT sub-module
4. Update engine to recognize the new model

## Confidence Scores

Signal confidence flows through:
1. Strategy's own scoring (0–100 in ICT engine, normalized to 0–1)
2. Historical confidence from DB (`db.get_confidence(model_slug)`)
3. Blended: `(historical + realtime) / 2`
4. Council vote (strategy-aware weighting)
5. Final approval at `COUNCIL_MIN_CONFIDENCE=0.60`

## What NOT to Do
- Don't access the broker directly from a strategy (use candles from context)
- Don't store state between calls (strategies are called per-symbol per-loop)
- Don't raise exceptions from `detect()` — always catch internally
- Don't hardcode symbol-specific logic — use `context.symbol` and settings
