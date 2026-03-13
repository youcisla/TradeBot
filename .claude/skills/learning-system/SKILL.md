---
name: learning-system
description: Implement or modify the learning and reward system. Covers trade scoring, confidence adjustment, strategy enabling/disabling, and performance tracking by symbol, session, and market condition. Use when building or tuning the feedback loop.
---

# Learning System

The learning system is the feedback loop that makes the bot improve over time. It does NOT rewrite strategies — it adjusts **confidence levels** to control which strategies run and when.

## Trade Scoring

After every closed trade, assign a score:

| Outcome | Score | Description |
|---|---|---|
| Good trade (clean setup, profit) | **+3** | Strategy conditions met, positive result |
| Profit but messy setup | **+1** | Made money but entry wasn't clean |
| Small loss (SL hit, normal) | **-2** | Expected loss within risk parameters |
| Bad loss (large or avoidable) | **-5** | Loss due to poor conditions or ignored filters |
| Rule violation | **-10** | Trade violated risk rules or was forced |

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
