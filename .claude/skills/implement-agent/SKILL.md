---
name: implement-agent
description: Implement or modify one of the trading bot agents (Market, Analysis, Strategy, Neural, ModelManager, Risk, Execution, Trade Manager, Learning, Logging). Provides the specification and contract for each agent. Use when building, extending, or debugging any agent module.
argument-hint: <agent-name> (market|analysis|strategy|neural|model-manager|risk|execution|trade-manager|learning|logging)
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
- **Validate data quality before returning** (sanity checks)

**Interface:**
```python
class MarketAgent:
    def get_data(self, symbol: str) -> MarketData:
        """Returns current market snapshot for a symbol. Raises DataValidationError if data is stale or corrupt."""
    
    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        """Returns historical candles."""
```

**Data validation rules (filters/data_validator.py):**
- **Stuck quote detection:** If bid/ask hasn't changed for N consecutive reads (configurable, e.g. 10), mark data as stale and skip analysis
- **Spike detection:** If price moves > X% in a single tick (configurable, e.g. 2%), reject the data point and log it
- **Candle continuity:** Verify candle timestamps are sequential with no gaps; log missing candles
- **Spread sanity:** If spread is negative or > max realistic value, reject

The Market Agent must never silently return bad data. If validation fails, it raises an exception that the main loop catches and logs (no trade signals generated on that tick).

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
- Run ALL active strategies against the context
- Collect ALL valid signals (not just the first match)
- Check strategy confidence score from Learning Agent before running each strategy
- Return all signals for ranking by the main loop

**Interface:**
```python
class StrategyAgent:
    def detect(self, context: MarketContext) -> Optional[Signal]:
        """Returns the highest-confidence signal or None. Backward-compatible wrapper."""
    
    def detect_all(self, context: MarketContext) -> list[Signal]:
        """Returns ALL valid signals from ALL strategies for this context.
        Used by the scan-rank-execute pipeline in main.py."""
    
    def _collect_signals(self, context: MarketContext) -> list[Signal]:
        """Internal: iterates all strategies, collects every valid signal."""
```

The main loop calls `detect_all()` for each symbol, collects all signals across all symbols, ranks by confidence, then executes the best ones. This ensures no high-confidence setup is missed because another symbol was processed first.

Each strategy must define: entry conditions, SL calculation, TP1/TP2/TP3 levels.

Registered strategies: ICT/SMC (primary), SMA Crossover (fallback).

---

## Risk Agent (`agents/risk_agent.py`)

**Question:** Is it safe?

**Responsibilities:**
- Validate position size against account balance
- Check max risk per trade (% of account)
- Check max number of open trades
- Check correlation with existing positions
- Verify spread is acceptable **at signal time (live check, not just config)**
- Reject if daily loss limit reached
- **Duplicate signal guard** — reject if already holding same symbol + direction + strategy
- **Correlation guard** — reject if already holding same symbol + direction from ANY strategy
- **Drawdown circuit breaker** — halt all trading if daily equity drawdown exceeds limit
- **News blackout filter** — reject signals within N minutes of high-impact events on the symbol

**Interface:**
```python
class RiskAgent:
    def validate(self, signal: Signal) -> bool:
        """Returns True if the trade is safe to execute. Runs ALL checks below."""
    
    def calculate_position_size(self, signal: Signal, balance: float) -> float:
        """Returns the lot size based on risk parameters."""
    
    def check_drawdown(self) -> bool:
        """Returns True if daily drawdown limit hit. Halts all trading for 24h."""
    
    def check_duplicate(self, signal: Signal) -> bool:
        """Returns True if a duplicate position already exists."""
    
    def check_news_blackout(self, symbol: str) -> bool:
        """Returns True if within blackout window of high-impact event."""
```

**Validation order (fail fast):**
1. `check_drawdown()` — if True, reject immediately
2. `check_duplicate()` — is this trade already open?
3. Correlation guard — same symbol+direction from another strategy?
4. `check_news_blackout()` — is a high-impact event imminent?
5. Live spread check — is current spread > `MAX_SPREAD`?
6. Max open trades check
7. Position size vs. balance check

**Key parameters (from config):**
- `MAX_RISK_PER_TRADE` (e.g., 1-2% of account)
- `MAX_OPEN_TRADES` (e.g., 3-5)
- `MAX_DAILY_LOSS` (e.g., 5% of account)
- `MAX_SPREAD` (in pips) — checked LIVE at signal time
- `NEWS_BLACKOUT_MINUTES` (e.g., 15 min before/after)
- `DRAWDOWN_COOLDOWN_HOURS` (e.g., 24h after circuit breaker triggers)

**News filter integration:**
- Use `filters/news_filter.py` which queries an economic calendar
- Sources: Forex Factory scraper, Finnhub calendar API, or a static weekly JSON file
- Filter applies per-currency (e.g., USD events block EURUSD, XAUUSD, etc.)

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
- **Handle partial fills** (recalculate TP volumes if not fully filled)
- Return trade record
- **Persist trade to DB immediately after successful fill**

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

**Partial fill handling:**
If the broker fills only part of the requested lot size:
1. Check actual filled size from the broker response
2. Recalculate TP portion volumes based on the actual fill (not the requested size)
3. If filled size is below minimum tradeable lot, cancel and log
4. Never assume the requested size was fully filled — always verify

```python
filled = broker.get_fill_size(order_id)
if filled < MIN_LOT_SIZE:
    broker.close_order(order_id)
    raise PartialFillError(f"Only {filled} filled, below minimum")
# Recalculate portions based on actual fill
tp1_lots = round(filled * TP1_CLOSE_PERCENT, 2)
tp2_lots = round(filled * TP2_CLOSE_PERCENT, 2)
tp3_lots = filled - tp1_lots - tp2_lots  # remainder to avoid rounding errors
```

---

## Trade Manager Agent (`agents/trade_manager.py`)

**Question:** What do we do with the trade?

**Responsibilities:**
- Monitor all open positions continuously
- Execute partial closes when TPs are hit
- Move SL to breakeven after TP1 **(with spread + commission offset)**
- Trail stop loss after TP2
- Handle emergency close (kill switch)
- Detect and handle broker disconnects
- **Persist every state change to DB** (crash recovery)
- **Reconcile on startup** — compare DB state to broker's actual positions
- **Periodic reconciliation** — every N iterations, verify state matches broker
- **Listen for remote kill commands** (Telegram `/kill`)

**Interface:**
```python
class TradeManagerAgent:
    def monitor(self) -> None:
        """Check all open trades and take action as needed."""
    
    def close_trade(self, trade_id: str, reason: str) -> None:
        """Force close a specific trade."""
    
    def close_all(self, reason: str) -> None:
        """Emergency close all positions."""
    
    def reconcile(self) -> None:
        """Compare DB state to broker positions. Adopt broker state as truth on mismatch."""
    
    def persist_state(self, trade: Trade) -> None:
        """Write current trade state to DB. Called after every change."""
```

**Trade lifecycle:**
1. Trade opens → SL + TP1 + TP2 + TP3 active → **persisted to DB**
2. TP1 hit → partial close, SL → breakeven **(entry + spread + commission)** → **persisted**
3. TP2 hit → partial close, trail SL → **persisted**
4. TP3 hit → final close → **persisted**
5. OR SL hit → full close at any point → **persisted**

**Reconciliation logic:**
```python
def reconcile(self):
    db_trades = self.state.get_open_trades()      # what bot thinks is open
    broker_trades = self.broker.get_open_positions()  # what broker actually has
    
    # Trades in DB but not on broker → mark as closed (broker closed them)
    # Trades on broker but not in DB → adopt and track (orphaned positions)
    # Trades in both but with different SL/lot → adopt broker values, log diff
```

**Remote kill switch:**
- Telegram bot listens for `/kill` command
- On receive: calls `close_all("REMOTE_KILL")`, stops the loop, sends confirmation
- On `/status`: sends current open positions, equity, daily P&L
- Must work even when bot is on a VPS at 3am

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
- **Send daily P&L summary via Telegram** (scheduled at configurable time, e.g., market close)

**Interface:**
```python
class LoggingAgent:
    def record(self, event: str, data: dict = None) -> None:
        """Log an event with optional data."""
    
    def log_trade(self, trade: Trade) -> None:
        """Record a trade in the database."""
    
    def send_daily_summary(self) -> None:
        """Generate and send daily digest: trades, P&L, equity, open positions."""
```

**Daily summary** (sent via Telegram):
- Trades taken today (count, wins, losses)
- Total P&L for the day
- Current account equity
- Open positions with current P&L
- Any strategies that changed confidence state
- Any anomalies (data gaps, reconnects, rejected signals)

---

## Neural Strategy Agent (`agents/neural_strategy.py`)

**Key:** `neural`
**Question:** What does the LSTM model predict?

**Responsibilities:**
- Wrap ModelManager to provide a `BaseStrategy`-compatible interface
- Call `model_manager.predict(symbol, candles, context)` → (direction, confidence) or None
- Return `Signal` if confidence ≥ `settings.NEURAL_MIN_CONFIDENCE`
- Return `None` if model not trained yet for this symbol, or confidence too low
- SL = 2×ATR; TP1/2/3 = 1R/2R/3R (risk-based)
- Capture EntrySnapshot at signal time for learning system

**Interface:**
```python
class NeuralStrategy(BaseStrategy):
    name = "neural"

    def __init__(self, model_manager: "ModelManager"):
        self.model_manager = model_manager

    def detect(self, context: MarketContext) -> Optional[Signal]:
        result = self.model_manager.predict(context.symbol, context.candles, context)
        if result is None:
            return None
        direction, confidence = result
        if confidence < settings.NEURAL_MIN_CONFIDENCE:
            return None
        # Build signal with ATR-based SL/TP, EntrySnapshot, return Signal
        ...

    def calculate_sl(self, context, direction): ...  # 2×ATR
    def calculate_tps(self, context, entry, sl, direction): ...  # 1R, 2R, 3R
```

---

## Model Manager (`agents/model_manager.py`)

**Key:** `model_manager`
**Question:** Is the LSTM model trained and ready? Can we infer?

**Responsibilities:**
- Download 2yr H1 history per symbol at startup (via `backtesting/data_downloader`)
- Auto-label candles (BUY/SELL/HOLD using 20-bar forward horizon)
- Train `LSTMTradingModel` per symbol (80/20 temporal split)
- Save model weights + normalizer params to `models/neural/`
- Load cached models if < 7 days old (skip re-train)
- Provide `predict()` for inference (last 50 candles → softmax)
- Maintain replay buffer (200 most recent closed trades per symbol)
- Fine-tune model every 20 new trade closures (5 epochs, lr=0.0001)
- Log training progress via `agent_events` DB table (key: `model_manager`)

**Interface:**
```python
class ModelManager:
    def initialize(self, symbols: list[str]) -> None:
        """Start background training for all symbols. Non-blocking."""

    def get_model(self, symbol: str) -> Optional[LSTMTradingModel]:
        """Returns trained model or None if not ready yet."""

    def predict(self, symbol: str, candles: list[Candle], context: MarketContext) -> Optional[tuple[str, float]]:
        """Returns (direction, confidence) or None if model not ready."""

    def record_outcome(self, symbol: str, candle_window: np.ndarray, label: int) -> None:
        """Add a closed trade outcome to the replay buffer. Trigger fine-tune if ready."""

    def _train_symbol(self, symbol: str) -> None:
        """Background: download → label → train → save."""

    def _fine_tune(self, symbol: str) -> None:
        """Background: fine-tune on replay buffer for 5 epochs."""
```

**Storage layout:**
```
models/neural/
  {SYMBOL}_H1.pt    ← PyTorch state dict (LSTMTradingModel)
  {SYMBOL}_H1.json  ← FeatureNormalizer: {"mean": [...9], "std": [...9]}
```

**Thread safety:** Training runs in a `ThreadPoolExecutor(max_workers=4)`. Use `threading.Lock()` per-symbol to protect model loading during inference.

---

## Implementation Rules

1. Each agent is a single Python class in its own file under `agents/`
2. Agents communicate through data models defined in `models/` (including `models/ict_models.py` for ICT structures)
3. No agent should directly call another agent — the main loop orchestrates via the scan-rank-execute pipeline
4. All config values come from `config/settings.py`
5. Every agent must handle its own errors gracefully and log them
6. Use type hints throughout
7. Database is PostgreSQL via Supabase (7 tables: trades, trade_scores, strategy_confidence, agent_events, bot_commands, bot_status, ict_setups)
