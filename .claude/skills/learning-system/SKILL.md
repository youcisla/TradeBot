---
name: learning-system
description: Implement or modify the learning and reward system. Covers trade scoring, confidence adjustment, strategy enabling/disabling, and performance tracking by symbol, session, and market condition. Use when building or tuning the feedback loop.
---

# Learning System

The learning system is the feedback loop that makes the bot improve over time. It does NOT rewrite strategies — it adjusts **confidence levels** to control which strategies run and when.

## Trade Scoring

After every closed trade, a score is assigned **objectively by rules — not subjectively by the developer**.

### Scoring Rules (computed automatically at trade-close time)

| Outcome | Score | Objective Rule |
|---|---|---|
| Clean win | **+3** | Profit AND all indicator filters were aligned at entry AND spread was normal |
| Messy win | **+1** | Profit BUT at least one filter was marginal (e.g., RSI borderline, spread near max) |
| Normal loss | **-2** | SL hit AND all entry conditions were met (expected losing trade) |
| Bad loss | **-5** | SL hit AND at least one precondition was violated or marginal at entry |
| Rule violation | **-10** | Trade was forced past a filter (should never happen in production) |

### How "Clean" vs "Messy" is Determined

The scoring engine checks the **entry snapshot** (captured at signal time and stored with the trade):

```python
def compute_score(trade: Trade, entry_snapshot: EntrySnapshot) -> int:
    is_profit = trade.pnl > 0
    
    # Check every precondition that was true at entry time
    filters_aligned = all([
        entry_snapshot.spread <= config.MAX_SPREAD * 0.8,    # spread well within limit (not borderline)
        entry_snapshot.rsi_aligned,                           # RSI not overbought/oversold against direction
        entry_snapshot.trend_aligned,                         # higher-TF trend matches direction
        entry_snapshot.volume_sufficient,                     # volume above minimum threshold
        not entry_snapshot.near_news_event,                   # not within extended news window
    ])
    
    if is_profit and filters_aligned:
        return +3   # Clean win
    elif is_profit and not filters_aligned:
        return +1   # Messy win
    elif not is_profit and filters_aligned:
        return -2   # Normal loss (setup was valid, market just moved against us)
    elif not is_profit and not filters_aligned:
        return -5   # Bad loss (shouldn't have entered)
    # -10 is only assigned if a rule violation flag is set
```

### Entry Snapshot (captured at signal time)

Every signal must capture and store the market conditions at entry. This is what the scoring engine evaluates later:

```python
@dataclass
class EntrySnapshot:
    spread: float               # spread in pips at signal time
    rsi_aligned: bool           # was RSI supporting the direction?
    trend_aligned: bool         # was higher-TF trend aligned?
    volume_sufficient: bool     # was volume above threshold?
    near_news_event: bool       # was there a nearby high-impact event?
    market_condition: str       # trending / ranging / volatile
    session: str                # London / NY / Asian / overlap
    day_of_week: str
```

This snapshot is stored alongside the trade in the DB and is immutable — it represents the conditions at entry, not at close.

Scores are stored in the database per trade.

## Confidence System

Each strategy has a confidence score from **0.0 to 1.0**:

```python
# Starting confidence for any new strategy
DEFAULT_CONFIDENCE = 0.5

# Confidence thresholds
CONFIDENCE_ALLOW = 0.3      # Below this → strategy disabled
CONFIDENCE_REDUCED = 0.5    # Below this → reduced position size
CONFIDENCE_FULL = 0.7       # Above this → full position size
```

### Confidence Adjustment Logic

```python
def update_confidence(strategy: str, trade_score: int):
    current = get_confidence(strategy)
    
    # Normalize score to adjustment factor
    adjustment = trade_score * 0.02  # each point = 2% change
    
    new_confidence = max(0.0, min(1.0, current + adjustment))
    save_confidence(strategy, new_confidence)
```

### How Confidence Affects Trading

| Confidence | Effect |
|---|---|
| >= 0.7 | Full position size, all signals accepted |
| 0.5 - 0.7 | Reduced position size (50-70% of normal) |
| 0.3 - 0.5 | Minimum position size, extra filters required |
| < 0.3 | **Strategy disabled** — no signals accepted |

## Tracking Dimensions

The learning agent tracks performance across multiple dimensions to discover favorable conditions:

### By Strategy
- Win rate, average PnL, total score per strategy

### By Symbol
- Which instruments perform best with each strategy

### By Session
- London, New York, Asian, overlap periods
- Which sessions produce the best results

### By Market Condition
- Trending vs ranging vs volatile
- Performance in each regime

### By Spread Condition
- Normal spread vs widened spread
- Reject trades when spread/performance correlation is poor

### By Day of Week
- Monday through Friday patterns

## Database Schema

```sql
CREATE TABLE trade_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    session TEXT,
    market_condition TEXT,
    spread_at_entry REAL,
    day_of_week TEXT,
    score INTEGER NOT NULL,
    pnl REAL,
    -- Entry snapshot fields (immutable record of conditions at signal time)
    rsi_aligned INTEGER,          -- 0 or 1
    trend_aligned INTEGER,        -- 0 or 1
    volume_sufficient INTEGER,    -- 0 or 1
    near_news_event INTEGER,      -- 0 or 1
    filters_aligned INTEGER,      -- 0 or 1 (all preconditions met)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE strategy_confidence (
    strategy TEXT PRIMARY KEY,
    confidence REAL NOT NULL DEFAULT 0.5,
    total_trades INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Performance Reports

The Learning Agent should generate summaries on demand:

```python
class LearningAgent:
    def get_report(self) -> dict:
        """
        Returns:
        {
            "overall": {"total_trades": N, "win_rate": %, "total_pnl": $},
            "by_strategy": {...},
            "by_symbol": {...},
            "by_session": {...},
            "by_condition": {...},
            "confidence_levels": {"strategy_name": 0.72, ...}
        }
        """
```

## Rules

1. Never adjust strategy logic directly — only adjust confidence
2. A strategy must have at least 10 trades before confidence changes are meaningful
3. Confidence resets are manual only (not automatic)
4. All scoring data is preserved forever for analysis
5. The learning system is passive — it does not change parameters, only confidence
6. **Scores are computed by objective rules, not manually assigned** — the entry snapshot determines "clean" vs "messy"
7. Every trade must have an `EntrySnapshot` captured at signal time — no snapshot = no score
8. V1 can use simplified filter checks; the framework must support adding more filters later
