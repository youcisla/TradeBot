---
name: implement-agent
description: Implement or modify one of the trading bot agents (Market, Analysis, Strategy, Risk, Execution, Trade Manager, Learning, Logging). Provides the specification and contract for each agent. Use when building, extending, or debugging any agent module.
argument-hint: <agent-name> (market|analysis|strategy|risk|execution|trade-manager|learning|logging)
---

# Implement Agent: $ARGUMENTS

Implement the specified agent following its contract below. Each agent has a **single responsibility** and communicates through well-defined inputs/outputs.

---

## Market Agent (`agents/market_agent.py`)

**Question:** What is the market doing?

**Responsibilities:**
- Connect to market data source (API or broker feed)
- Fetch current price, bid/ask, spread
- Fetch OHLCV candles for configured timeframes
- Fetch volume data
- Handle connection errors and data gaps

**Interface:**
```python
class MarketAgent:
    def get_data(self, symbol: str) -> MarketData:
        """Returns current market snapshot for a symbol."""
    
    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        """Returns historical candles."""
```

**Data sources (free tier):** Alpha Vantage, Twelve Data, or broker's own feed.

---

## Analysis Agent (`agents/analysis_agent.py`)

**Question:** What does it mean?

**Responsibilities:**
- Receive raw market data from Market Agent
- Calculate technical indicators (moving averages, RSI, ATR, etc.)
- Determine market regime (trending, ranging, volatile)
- Identify key support/resistance levels
- Assess current session (London, NY, Asian)

**Interface:**
```python
class AnalysisAgent:
    def analyze(self, market_data: MarketData) -> MarketContext:
        """Returns interpreted market context."""
```

---

## Strategy Agent (`agents/strategy_agent.py`)

**Question:** Is there a trade?

**Responsibilities:**
- Receive market context from Analysis Agent
- Run active strategies against the context
- Generate trade signals with entry price, direction, SL, TP1, TP2, TP3
- Only return signals that pass the strategy's own quality filter
- Check strategy confidence score from Learning Agent before signaling

**Interface:**
```python
class StrategyAgent:
    def detect(self, context: MarketContext) -> Optional[Signal]:
        """Returns a trade signal or None."""
```

Each strategy must define: entry conditions, SL calculation, TP1/TP2/TP3 levels.

---

## Risk Agent (`agents/risk_agent.py`)

**Question:** Is it safe?

**Responsibilities:**
- Validate position size against account balance
- Check max risk per trade (% of account)
- Check max number of open trades
- Check correlation with existing positions
- Verify spread is acceptable
- Reject if daily loss limit reached

**Interface:**
```python
class RiskAgent:
    def validate(self, signal: Signal) -> bool:
        """Returns True if the trade is safe to execute."""
    
    def calculate_position_size(self, signal: Signal, balance: float) -> float:
        """Returns the lot size based on risk parameters."""
```

**Key parameters (from config):**
- `MAX_RISK_PER_TRADE` (e.g., 1-2% of account)
- `MAX_OPEN_TRADES` (e.g., 3-5)
- `MAX_DAILY_LOSS` (e.g., 5% of account)
- `MAX_SPREAD` (in pips)

---

## Execution Agent (`agents/execution_agent.py`)

**Question:** Can we execute it?

**Responsibilities:**
- Receive approved signal from Risk Agent
- Calculate final position size
- Place market or limit order via broker
- Attach Stop Loss
- Attach Take Profit 1 (partial close target)
- Attach Take Profit 2 (partial close target)
- Attach Take Profit 3 (final close target)
- Confirm order was filled
- Return trade record

**Interface:**
```python
class ExecutionAgent:
    def open_trade(self, signal: Signal) -> Trade:
        """Opens a trade with SL + 3 TPs. Returns trade record."""
```

**TP distribution** (configurable):
- TP1: close 40% of position
- TP2: close 30% of position
- TP3: close remaining 30%

---

## Trade Manager Agent (`agents/trade_manager.py`)

**Question:** What do we do with the trade?

**Responsibilities:**
- Monitor all open positions continuously
- Execute partial closes when TPs are hit
- Move SL to breakeven after TP1
- Trail stop loss after TP2
- Handle emergency close (kill switch)
- Detect and handle broker disconnects

**Interface:**
```python
class TradeManagerAgent:
    def monitor(self) -> None:
        """Check all open trades and take action as needed."""
    
    def close_trade(self, trade_id: str, reason: str) -> None:
        """Force close a specific trade."""
    
    def close_all(self, reason: str) -> None:
        """Emergency close all positions."""
```

**Trade lifecycle:**
1. Trade opens → SL + TP1 + TP2 + TP3 active
2. TP1 hit → partial close, SL → breakeven
3. TP2 hit → partial close, trail SL
4. TP3 hit → final close
5. OR SL hit → full close at any point

---

## Learning Agent (`agents/learning_agent.py`)

**Question:** What did we learn?

**Responsibilities:**
- Review every closed trade
- Assign reward/penalty score
- Track performance by strategy, symbol, session, market condition
- Adjust strategy confidence scores
- Disable strategies with very low confidence
- Generate performance summaries

**Interface:**
```python
class LearningAgent:
    def review_trade(self, trade: Trade) -> None:
        """Score a closed trade and update confidence."""
    
    def get_confidence(self, strategy: str) -> float:
        """Returns current confidence for a strategy (0.0 to 1.0)."""
    
    def get_report(self) -> dict:
        """Returns performance summary."""
```

**Scoring:** See the learning-system skill for full scoring details.

---

## Logging Agent (`agents/logging_agent.py`)

**Question:** (Records everything)

**Responsibilities:**
- Log every bot event (startup, signal, trade, error)
- Write trade records to SQLite database
- Log market conditions at time of each trade
- Maintain structured log files (rotated daily)
- Support different log levels (DEBUG, INFO, WARNING, ERROR)

**Interface:**
```python
class LoggingAgent:
    def record(self, event: str, data: dict = None) -> None:
        """Log an event with optional data."""
    
    def log_trade(self, trade: Trade) -> None:
        """Record a trade in the database."""
```

---

## Implementation Rules

1. Each agent is a single Python class in its own file under `agents/`
2. Agents communicate through data models defined in `models/`
3. No agent should directly call another agent — the main loop orchestrates
4. All config values come from `config/settings.py`
5. Every agent must handle its own errors gracefully and log them
6. Use type hints throughout
