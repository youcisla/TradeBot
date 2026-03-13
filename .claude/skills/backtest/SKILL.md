---
name: backtest
description: Run a CSV-based backtest of a strategy before deploying to demo. Validates strategy logic on historical data without touching any live or demo account. Use when creating a new strategy, tuning parameters, or validating changes.
argument-hint: <strategy-name> [symbol] [timeframe]
disable-model-invocation: true
---

# Backtest Strategy: $ARGUMENTS

Run a historical backtest to validate strategy logic before it touches any account (even demo).

## Why Backtest First

The original design jumped from "write strategy" to "run on demo." This wastes days of demo testing on obviously broken logic. A simple CSV-based backtester catches:
- Strategies that never signal (conditions too strict)
- Strategies that signal on every bar (conditions too loose)
- Strategies with negative expectancy (bad SL/TP ratio)
- Off-by-one errors in indicator calculations
- Edge cases (gaps, weekend opens, flat markets)

## Data Format

Historical data is stored as CSV files in `backtesting/data/`:

```
backtesting/data/EURUSD_H1.csv
backtesting/data/XAUUSD_M15.csv
```

CSV columns:

```csv
datetime,open,high,low,close,volume,spread
2024-01-02 09:00:00,1.10432,1.10489,1.10401,1.10455,1234,1.2
2024-01-02 10:00:00,1.10455,1.10512,1.10430,1.10490,1567,1.1
```

**Data sources:**
- Export from MT5 (free, any timeframe)
- Download from Twelve Data or Alpha Vantage API
- Minimum: 3 months of data for meaningful results

## Backtesting Engine (`backtesting/engine.py`)

```python
class BacktestEngine:
    def __init__(self, strategy: BaseStrategy, data_path: str):
        self.strategy = strategy
        self.candles = self._load_csv(data_path)
    
    def run(self) -> BacktestResult:
        """
        Walk forward through candles, feeding each bar to the strategy.
        Simulate trade execution with SL + 3 TPs.
        Track all trades and produce summary statistics.
        """
        trades = []
        open_trades = []
        
        for i in range(lookback, len(self.candles)):
            context = self._build_context(self.candles[:i+1])
            
            # Check open trades against current bar's high/low
            for trade in open_trades:
                self._check_sl_tp(trade, self.candles[i])
            
            # Remove closed trades
            closed = [t for t in open_trades if t.status == "CLOSED"]
            trades.extend(closed)
            open_trades = [t for t in open_trades if t.status != "CLOSED"]
            
            # Check for new signals
            signal = self.strategy.detect(context)
            if signal:
                trade = self._simulate_entry(signal)
                open_trades.append(trade)
        
        return self._compute_results(trades)
```

## Simulation Rules

The backtester must simulate the real execution model:

1. **Entry:** At the close of the signal bar (no lookahead bias)
2. **SL check:** If the bar's low (for BUY) or high (for SELL) reaches SL → trade closed at SL price
3. **TP check:** Check TP1 → TP2 → TP3 in order. If a bar hits TP1 first, partial close at TP1
4. **SL/TP order on same bar:** If both SL and TP could be hit on the same bar, assume **SL is hit first** (conservative)
5. **Spread:** Subtract spread from entry price for realistic fills
6. **Partial close simulation:** Track remaining lot portions like the real Trade Manager
7. **Breakeven:** After TP1, move SL to entry + spread (matching real logic)
8. **No duplicate trades:** Same duplicate guard logic as production

## Result Output

```python
@dataclass
class BacktestResult:
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float       # gross profit / gross loss
    max_drawdown: float        # peak-to-trough in equity
    avg_trade_duration: timedelta
    trades_per_day: float
    expectancy: float          # avg PnL per trade
    tp1_hit_rate: float        # % of trades that reached TP1
    tp2_hit_rate: float
    tp3_hit_rate: float
    equity_curve: list[float]  # for visual inspection
```

Print a summary:

```
BACKTEST REPORT — my_strategy on EURUSD H1
Period: 2024-01-01 to 2024-03-31

Total trades:    87
Win rate:        58.6%
Profit factor:   1.82
Total P&L:       +342.5 pips
Avg win:         +18.2 pips
Avg loss:        -12.1 pips
Max drawdown:    -89.3 pips
Expectancy:      +3.94 pips/trade

TP1 hit rate:    71.3%
TP2 hit rate:    48.2%
TP3 hit rate:    31.0%

VERDICT: [VIABLE / NOT VIABLE]
```

## Viability Criteria

A strategy should NOT proceed to demo testing unless:

| Metric | Minimum |
|---|---|
| Total trades | >= 50 (enough sample size) |
| Win rate | >= 40% (with 1:2+ RR) or >= 55% (with 1:1 RR) |
| Profit factor | >= 1.3 |
| Max drawdown | < 15% of simulated account |
| Expectancy | > 0 |

## Rules

1. **Always backtest before demo** — no exceptions
2. No lookahead bias — the strategy only sees bars up to the current one
3. Conservative assumptions on same-bar SL/TP conflicts
4. Include spread in all calculations
5. Minimum 3 months of historical data
6. Results do NOT guarantee demo or live performance — they only catch broken logic
7. Store all backtest results in `backtesting/results/` as JSON for comparison
