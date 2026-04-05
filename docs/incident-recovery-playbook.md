# Incident Recovery Playbook

## Scope

This playbook covers bot-side operational failures for the Python runtime, broker execution, risk gate behavior, and orchestration latency.

## Severity Levels

- SEV-1: Uncontrolled risk exposure, repeated unintended orders, or inability to close positions
- SEV-2: Bot down, broker disconnected, or no orders executed despite valid signals
- SEV-3: Performance degradation, elevated rejections, dashboard mismatch, delayed updates

## Immediate Safety Actions

1. Stop new entries:
   - Set BOT_PROFILE to live-safe or paper.
   - Restart bot.
2. Freeze execution if needed:
   - Set FAST_LANE_ENABLED=false and INSTANT_ENTRY_ENABLED=false.
3. Force strict risk:
   - Set RISK_VALIDATION_PROFILE=strict.
4. If broker unstable:
   - Stop launcher and verify MT5 terminal connectivity.

## Standard Triage Checklist

1. Confirm process state:
   - Python process running
   - Crucix healthy (if enabled)
   - Web dashboard reachable
2. Check recent logs:
   - logs/bot_YYYY-MM-DD.log
   - agent_events table for risk/execution/council messages
3. Verify broker state:
   - Active account credentials
   - MT5 autotrading enabled
   - Symbol availability
4. Validate DB health:
   - DATABASE_URL reachable
   - trades and bot_status writable
5. Reenact on historical data before resuming live:
   - Run `python scripts/replay_session.py --symbol EURUSD --data backtesting/data/EURUSD_H1.csv`
   - If parity check fails, keep bot in paper or live-safe.

## Common Incidents

### 1) Repeated execution failures

Symptoms:
- Frequent execution errors in logs
- risk passed but no fills

Actions:
1. Switch to live-safe profile.
2. Confirm MT5 autotrading and account permissions.
3. Reconcile open trades on restart.
4. Temporarily disable fast lane.

Exit criteria:
- New valid signal can execute and appears in trades table.

### 2) Risk rejects spike unexpectedly

Symptoms:
- risk_rejections surge
- Very low trade throughput

Actions:
1. Inspect risk rejection reasons in KPI logs.
2. Check spread limits and market session.
3. Confirm profile did not become overly strict unintentionally.
4. If market is volatile, keep strict mode and reduce symbols.

Exit criteria:
- Rejection reason distribution returns to expected baseline.

### 3) Orchestration budget overruns

Symptoms:
- budget_scan_hits / budget_exec_hits increasing
- Council frequently skipped due to budget pressure

Actions:
1. Reduce symbol count temporarily.
2. Tighten SCAN_COOLDOWN settings.
3. Reduce non-critical tools/autorun frequency.
4. Keep hard budgets enabled.

Exit criteria:
- last_scan_latency_ms, last_execution_latency_ms stable below targets.

### 4) Dashboard shows stale or inconsistent state

Symptoms:
- API returns stale bot status
- trades table updated but UI lags

Actions:
1. Verify Next.js API route health.
2. Verify DB connectivity from both bot and web.
3. Restart web process.
4. Inspect command queue and status update intervals.

Exit criteria:
- Dashboard open trades and status match DB.

## Recovery Validation

After mitigation, run:

1. tests/test_risk_agent.py
2. tests/test_strategy_agent.py
3. tests/test_trade_manager.py
4. tests/test_deepseek_strategy.py
5. tests/test_unified_strategy.py

Then monitor one full trading loop and verify:

- No execution errors
- Risk gate messages are sensible
- Metrics snapshot updates normally
- No duplicate orders

## Post-Incident Notes

For each incident, record:

- UTC timestamp and severity
- Trigger condition
- Config/profile at incident time
- Commands/actions taken
- Recovery time
- Follow-up prevention tasks
