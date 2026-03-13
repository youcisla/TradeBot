---
name: add-strategy
description: Add a new trading strategy to the bot. Provides the base strategy interface, rules for integration, and the template every strategy must follow. Use when creating, modifying, or reviewing trading strategies.
argument-hint: <strategy-name>
---

# Add Strategy: $ARGUMENTS

Create a new trading strategy following the standard template.

## Strategy Base Class

Every strategy must inherit from `BaseStrategy`:

```python
# strategies/base_strategy.py
from abc import ABC, abstractmethod
from models.market_data import MarketContext
from models.signal import Signal
from typing import Optional

class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    name: str = "unnamed"
    
    @abstractmethod
    def detect(self, context: MarketContext) -> Optional[Signal]:
        """
        Analyze market context and return a Signal if a setup is found.
        Return None if no trade setup detected.
        """
        pass
    
    @abstractmethod
    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        """Calculate stop loss price for this setup."""
        pass
    
    @abstractmethod
    def calculate_tps(self, context: MarketContext, entry: float, sl: float, direction: str) -> tuple[float, float, float]:
        """Calculate TP1, TP2, TP3 prices."""
        pass
```

## Signal Data Model

Every signal must include:

```python
# models/signal.py
@dataclass
class Signal:
    strategy: str       # Name of the strategy that generated it
    symbol: str
    direction: str      # "BUY" or "SELL"
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    confidence: float   # From learning system (0.0 to 1.0)
    timestamp: datetime
    reason: str         # Human-readable explanation of why
```

## Strategy Template

Create new strategies in `strategies/` directory:

```python
# strategies/my_new_strategy.py
from strategies.base_strategy import BaseStrategy
from models.market_data import MarketContext
from models.signal import Signal
from typing import Optional

class MyNewStrategy(BaseStrategy):
    name = "my_new_strategy"
    
    def detect(self, context: MarketContext) -> Optional[Signal]:
        # 1. Check preconditions (session, spread, volatility)
        # 2. Check entry conditions
        # 3. If setup found, calculate levels
        # 4. Return Signal or None
        
        if not self._preconditions_met(context):
            return None
        
        if not self._entry_conditions_met(context):
            return None
        
        direction = self._determine_direction(context)
        entry = context.current_price
        sl = self.calculate_sl(context, direction)
        tp1, tp2, tp3 = self.calculate_tps(context, entry, sl, direction)
        
        return Signal(
            strategy=self.name,
            symbol=context.symbol,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=0.5,  # Will be overridden by learning system
            timestamp=datetime.now(),
            reason="Description of why this signal was generated"
        )
    
    def calculate_sl(self, context, direction):
        # Define SL logic (e.g., below recent swing low for BUY)
        pass
    
    def calculate_tps(self, context, entry, sl, direction):
        # Define TP logic
        # Common: TP1 = 1:1 RR, TP2 = 2:1 RR, TP3 = 3:1 RR
        risk = abs(entry - sl)
        if direction == "BUY":
            return entry + risk, entry + risk * 2, entry + risk * 3
        else:
            return entry - risk, entry - risk * 2, entry - risk * 3
```

## Registration

Register new strategies in the Strategy Agent:

```python
# agents/strategy_agent.py
class StrategyAgent:
    def __init__(self, strategies: list[BaseStrategy], learning_agent):
        self.strategies = strategies
        self.learning = learning_agent
    
    def detect(self, context: MarketContext) -> Optional[Signal]:
        for strategy in self.strategies:
            confidence = self.learning.get_confidence(strategy.name)
            if confidence < CONFIDENCE_ALLOW:
                continue  # Strategy disabled by learning system
            
            signal = strategy.detect(context)
            if signal:
                signal.confidence = confidence
                return signal
        return None
```

## V1 Strategy Requirements

For the minimum viable version:
- **1 symbol only** (e.g., EURUSD or XAUUSD)
- **1 timeframe only** (e.g., 15min or 1H)
- **Simple, well-known setup** (e.g., moving average crossover, breakout, or support/resistance bounce)
- Must define clear entry, SL, and TP1/TP2/TP3 rules
- Must include a `reason` string explaining the signal

## Strategy Checklist

Before activating any strategy:

- [ ] Inherits from `BaseStrategy`
- [ ] Implements `detect()`, `calculate_sl()`, `calculate_tps()`
- [ ] Returns complete `Signal` with all fields
- [ ] Has a unique `name`
- [ ] Includes precondition checks (spread, session, volatility)
- [ ] TP levels use at least 1:1 risk-reward ratio
- [ ] Logged via the Logging Agent
- [ ] Registered in Strategy Agent
- [ ] Tested on demo account before live
