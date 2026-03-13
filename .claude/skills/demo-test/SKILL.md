---
name: demo-test
description: Plan and execute the 1-week demo testing phase. Covers daily test objectives, validation criteria, and the final report. Use when preparing for or running demo testing on the PU Prime demo account.
disable-model-invocation: true
---

# Demo Testing Phase

Run a **1-week demo test** on the PU Prime demo account before any live deployment.

## Purpose

The goal is **NOT to prove profitability**. It is to **validate the system works correctly**.

## Test Objectives

- [ ] Connection stability (bot stays connected to broker)
- [ ] Data accuracy (prices match broker platform)
- [ ] Strategy logic (signals fire correctly based on conditions)
- [ ] Risk control (position sizing, max trades, daily limits enforced)
- [ ] Execution correctness (orders placed with correct SL + 3 TPs)
- [ ] Trade management (partial closes, breakeven, trailing stops work)
- [ ] Error handling (graceful recovery from disconnects, bad data)

## Daily Schedule

### Day 1 — System Connectivity
- Start the bot on demo account
- Verify broker connection established
- Verify market data feed is live
- Verify database logging works
- Monitor for connection drops over 24h
- **Pass criteria:** No unhandled disconnects, all data logged

### Day 2 — Strategy Validation
- Verify strategy signals match expected conditions
- Check that signals include correct entry, SL, TP1, TP2, TP3
- Manually compare signals to chart to validate logic
- **Pass criteria:** All signals logically correct when reviewed

### Day 3 — Trade Management Testing
- Let the bot open trades on demo
- Verify partial closes execute at TP1
- Verify SL moves to breakeven after TP1
- Verify trailing stop activates after TP2
- **Pass criteria:** Trade lifecycle follows spec exactly

### Day 4 — News and Session Filters
- Verify session detection (London, NY, Asian)
- Verify bot respects session filters (if configured)
- Test behavior during high-spread periods
- **Pass criteria:** No trades in excluded sessions/conditions

### Day 5 — Behavior Consistency
- Run the bot for full 24h without intervention
- Check for memory leaks or growing resource usage
- Verify loop timing is consistent
- **Pass criteria:** Stable performance for 24h, no drift

### Day 6 — Learning System Evaluation
- Review all scored trades from the week
- Verify scoring matches expected outcomes
- Check confidence adjustments are sensible
- **Pass criteria:** Scores and confidence align with trade quality

### Day 7 — Final Report and Improvements
- Generate full performance report
- Document all bugs, issues, edge cases found
- Prioritize fixes
- Decide: ready for more testing or needs rework

## Final Report Template

```
DEMO TEST REPORT — Week of [DATE]

CONNECTIVITY
- Uptime: ___%
- Disconnects: ___
- Data gaps: ___

STRATEGY
- Signals generated: ___
- Signals correct: ___
- False signals: ___

EXECUTION
- Trades opened: ___
- Orders correct (SL+TPs): ___
- Execution errors: ___

TRADE MANAGEMENT
- TP1 partial closes: ___
- Breakevens triggered: ___
- Trailing stops activated: ___
- Full closes: ___

RISK
- Max risk violated: YES/NO
- Position sizing correct: YES/NO
- Daily limit respected: YES/NO

LEARNING
- Trades scored: ___
- Confidence adjustments: ___
- Strategy status: [active/reduced/disabled]

ISSUES FOUND
1. ...
2. ...

VERDICT: [PASS / NEEDS REWORK]
```

## Rules

1. Never skip demo testing
2. Fix all critical issues before extending the test
3. If a day fails its criteria, repeat that day's tests after fixing
4. All test results must be logged in the database
5. Demo phase must pass before ANY live deployment
