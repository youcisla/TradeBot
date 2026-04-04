# Technical Debt Backlog (Execution-Ready)

## P0 - Stabilization (Sprint 1)

- [ ] Fix failing tests in:
  - tests/test_trade_manager.py
  - tests/test_trade_lifecycle.py
  - tests/test_risk_agent.py
  - tests/test_deepseek_strategy.py
  - tests/test_db_resilience.py
- [ ] Align mock DB test contract with runtime usage (add/update update_live_state and related methods).
- [ ] Add regression tests for TP1/TP2/SL transitions and post-entry full validation paths.

## P1 - Reliability and Observability (Sprint 1-2)

- [ ] Replace top 10 silent pass sites in runtime-critical modules with explicit fallback logging.
- [ ] Introduce reason codes for graceful-degradation paths.
- [ ] Add counters for fallback activations and suppressed exception paths.

## P2 - Structural Refactor (Sprint 2-4)

- [ ] Extract command queue processing from main.py into dedicated module.
- [ ] Extract heartbeat/status updater from main.py into dedicated service.
- [ ] Split database/db.py into domain repositories (trades, status/events, commands, analytics).

## P3 - Prevention Gates (Sprint 2)

- [ ] Add dependency vulnerability audit step in CI.
- [ ] Introduce Python constraints/lock strategy for reproducible dependency resolution.
- [ ] Add policy check to block new bare except Exception and silent pass in core runtime modules without documented justification.

## Success Criteria

- [ ] Full test suite: 0 failing tests on main branch.
- [ ] At least 2 integration tests added for end-to-end bot loop behavior.
- [ ] except Exception count in core runtime reduced by >=15% quarter-over-quarter.
- [ ] pass keyword usage in core runtime reduced by >=40% in first two sprints.
