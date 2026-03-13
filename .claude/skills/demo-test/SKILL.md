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
- [ ] Data validation (stuck quotes, spikes, and gaps are detected and rejected)
- [ ] Strategy logic (signals fire correctly based on conditions)
- [ ] Duplicate signal guard (same setup on consecutive ticks doesn't open twice)
- [ ] Risk control (position sizing, max trades, daily limits enforced)
- [ ] Spread check (signals rejected when live spread exceeds threshold)
- [ ] Drawdown circuit breaker (all trading halts when daily loss limit hit)
- [ ] News blackout filter (no trades within N minutes of high-impact events)
- [ ] Execution correctness (orders placed with correct SL + 3 TPs, partial fills handled)
- [ ] Trade management (partial closes via MT5, breakeven with spread offset, trailing stops)
- [ ] State persistence (bot recovers open trades correctly after restart)
- [ ] Position reconciliation (bot detects drift between its state and broker's)
- [ ] Remote kill switch (Telegram `/kill` closes all positions and stops loop)
- [ ] Daily summary (Telegram digest sent at configured time)
- [ ] Error handling (graceful recovery from disconnects, bad data)

## Daily Schedule

### Day 1 — System Connectivity & State Persistence
- Start the bot on demo account
- Verify broker connection established
- Verify market data feed is live and passes sanity checks
- Verify database logging works
- Monitor for connection drops over 24h
- **Crash recovery test:** While bot has open trades, kill the process. Restart and verify it recovers all open positions from DB and reconciles with broker.
- **Pass criteria:** No unhandled disconnects, all data logged, crash recovery works

### Day 2 — Strategy Validation & Duplicate Guard
- Verify strategy signals match expected conditions
- Check that signals include correct entry, SL, TP1, TP2, TP3
- Manually compare signals to chart to validate logic
- **Duplicate test:** Verify that two consecutive loop ticks seeing the same setup do NOT open two trades
- **Data validation test:** Feed a stuck quote / spike and verify the bot rejects it
- **Pass criteria:** All signals logically correct, no duplicates, bad data rejected

### Day 3 — Trade Management & MT5 Execution
- Let the bot open trades on demo
- Verify partial closes execute at TP1 (via MT5 counter-order, not a nonexistent `close_partial`)
- Verify SL moves to breakeven = entry + spread + commission (NOT raw entry price)
- Verify trailing stop activates after TP2
- **Partial fill test:** If possible, test with small lot sizes at illiquid times to trigger partial fills
- **Pass criteria:** Trade lifecycle follows spec exactly, breakeven is correct

### Day 4 — Risk Guards & News Filter
- Verify session detection (London, NY, Asian)
- Verify bot respects session filters (if configured)
- Test behavior during high-spread periods (spread spike rejection)
- **News blackout test:** Schedule a test during a known high-impact event; verify no trades open within the blackout window
- **Correlation test:** If running multiple strategies, verify two BUY signals on the same symbol don't double exposure
- **Drawdown test:** Manually trigger losses to approach the daily limit; verify circuit breaker fires and halts trading
- **Pass criteria:** No trades in excluded conditions, spread check works at signal time, drawdown breaker fires correctly

### Day 5 — Behavior Consistency & Reconciliation
- Run the bot for full 24h without intervention
- Check for memory leaks or growing resource usage
- Verify loop timing is time-corrected (no drift under slow API conditions)
- **Reconciliation test:** Manually close a trade on the broker platform (not via bot), verify the bot detects the mismatch and reconciles
- **Periodic reconciliation:** Verify the bot runs reconciliation every N loops as configured
- **Pass criteria:** Stable 24h, no drift, reconciliation catches all mismatches

### Day 6 — Learning System & Remote Control
- Review all scored trades from the week
- Verify **objective scoring** matches expected outcomes (check entry snapshots)
- Check confidence adjustments are sensible
- **Telegram commands test:** Send `/kill`, verify all positions close. Send `/status`, verify response. Send `/pause` and `/resume`.
- **Daily summary test:** Verify the Telegram daily digest arrives at the configured time with correct data
- **Pass criteria:** Scores computed automatically (not manually), confidence aligns with trade quality, all Telegram commands work

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
- Crash recovery: PASS/FAIL
- Reconciliation mismatches found: ___

DATA VALIDATION
- Stuck quotes detected: ___
- Price spikes rejected: ___
- Candle gaps found: ___

STRATEGY
- Signals generated: ___
- Signals correct: ___
- False signals: ___
- Duplicate signals blocked: ___

EXECUTION
- Trades opened: ___
- Orders correct (SL+TPs): ___
- Execution errors: ___
- Partial fills handled: ___

TRADE MANAGEMENT
- TP1 partial closes (via MT5 counter-order): ___
- Breakevens triggered (with spread offset): ___
- Trailing stops activated: ___
- Full closes: ___

RISK
- Max risk violated: YES/NO
- Position sizing correct: YES/NO
- Daily limit respected: YES/NO
- Drawdown breaker fired: YES/NO (if tested)
- Spread rejections: ___
- News blackout rejections: ___
- Correlation/duplicate rejections: ___

LEARNING
- Trades scored (automatically): ___
- Entry snapshots captured: ___
- Confidence adjustments: ___
- Strategy status: [active/reduced/disabled]

REMOTE CONTROL
- /kill tested: PASS/FAIL
- /status tested: PASS/FAIL
- /pause + /resume tested: PASS/FAIL
- Daily summary received: PASS/FAIL

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
