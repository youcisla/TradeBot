---
name: learning-system
description: "Reward scoring, confidence adjustment, and strategy performance tracking in PulseTrade."
category: project
risk: none
source: project
date_added: "2026-03-28"
---

# Learning System

## Overview
The learning system tracks per-strategy win/loss performance and adjusts confidence scores to suppress underperforming strategies and reward profitable ones.

## Key Files
- `agents/learning_agent.py` — LearningAgent class
- `database/db.py` — `update_confidence()`, `get_confidence()`, `get_learning_report()`
- `config/settings.py` — confidence thresholds

## Confidence Thresholds (`config/settings.py`)
```python
DEFAULT_CONFIDENCE    = 0.5   # Starting value for new strategies
INITIAL_CONFIDENCE    = 0.5   # Reset value
CONFIDENCE_ALLOW      = 0.3   # Below this → strategy suppressed (returns None)
CONFIDENCE_REDUCED    = 0.5   # "Reduced mode" — trades at smaller size
CONFIDENCE_FULL       = 0.7   # Above this → full size trading
CONFIDENCE_DISABLE_THRESHOLD = 0.2  # Below this → strategy fully disabled
```

## Strategy Key Format
Strategy keys in DB use the format: `{strategy_name}:{model_name}`
```
ict_smc:TREND_CONTINUATION_LONG
ict_smc:TREND_CONTINUATION_SHORT
ict_smc:RANGE_DEALING_LONG
deepseek_engine
neural_lstm:EURUSD
```

## Reward Scoring (LearningAgent)

Called when a trade closes. Calculates a reward multiplier:

```python
def score_trade(self, trade: Trade) -> float:
    if trade.pnl > 0:
        # Win — reward based on how many TPs hit
        tps_hit = sum([trade.tp1_hit, trade.tp2_hit, trade.tp3_hit, trade.tp4_hit])
        base_reward = 0.1 * tps_hit   # +0.1 per TP level
        return min(1.0, base_reward + 0.5)
    else:
        # Loss — penalize more for large losses
        loss_ratio = abs(trade.pnl) / max(trade.lot_size * 100, 1)
        return max(0.0, 0.4 - loss_ratio * 0.1)
```

## Confidence Update Flow
```
Trade closes → LearningAgent.on_trade_closed(trade)
    → score_trade(trade)  → reward (0.0–1.0)
    → db.update_confidence(strategy_key, wins/losses)
    → new_conf = (old_conf * decay + reward * (1 - decay))
    → if new_conf < CONFIDENCE_ALLOW: suppress strategy
```

## DB Operations
```python
# Read confidence for a strategy
conf = db.get_confidence("ict_smc:TREND_CONTINUATION_LONG")
# Returns float 0.0–1.0, default 0.5 if not found

# Update after trade closes
db.update_confidence(
    strategy="ict_smc:TREND_CONTINUATION_LONG",
    wins=1,   # 1 if win, 0 if loss
    losses=0, # 0 if win, 1 if loss
)

# Get full learning report (for daily summary)
report = db.get_learning_report()
# Returns: {trades_today, wins, losses, win_rate, total_pnl, avg_pnl}
```

## Strategy Suppression in ICTStrategy
```python
historical_conf = self._db.get_confidence(model_slug)  # e.g. 0.25
if historical_conf < settings.CONFIDENCE_ALLOW:  # 0.25 < 0.30
    self._emit("info", f"Rejecting {model} — poor historical conf ({historical_conf:.2f})")
    return None  # Signal suppressed

# Blend with realtime score
realtime_conf = max(0.1, min(1.0, best.confidence / 100.0))
final_conf = (historical_conf + realtime_conf) / 2.0
```

## Daily Summary
Sent at `DAILY_SUMMARY_HOUR=17` (Europe/Paris time):
```
📊 Daily summary (2026-03-28)
Trades: 5 (W 3 / L 2)
Win rate: 60%
Total PnL: +$42.50
Avg PnL: +$8.50
```

## Dashboard Learning Page (`/dashboard/learning`)
Reads from `/api/learning` → returns `{ confidences: [...] }`
Each entry: `{ strategy, confidence, wins, losses }`
