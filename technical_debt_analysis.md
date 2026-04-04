# Technical Debt Analysis and Remediation - TradeBot

Generated: 2026-04-04
Scope analyzed: Python bot core and Next.js dashboard in this repository (excluding third-party skill bundles)

Assumptions used for cost estimates:
- Engineering blended rate: $120/hour
- Release cadence: 20 production pushes/month
- Current baseline incident triage effort: 4-8 hours/issue depending on area

## 1) Debt Inventory

### A. Code Debt

#### 1. Complex and oversized modules

Measured hotspots:

- main.py: 1181 lines, 11 function defs
- database/db.py: 1108 lines, 49 function defs
- agents/risk_agent.py: 586 lines
- agents/council_agent.py: 580 lines
- strategies/ict_strategy.py: 462 lines
- agents/trade_manager.py: 440 lines

Risk pattern:
- Monolithic coordination and persistence modules increase regression blast radius.
- Change coupling likely high in orchestration and DB layers.

Debt score: High

#### 2. Defensive exception density and silent handling

Measured indicators in core Python code:
- except Exception occurrences: 64
- pass keyword occurrences: 37

Not all are harmful (some are intentional graceful degradation), but density is high enough to hide true failures and reduce debuggability.

Debt score: High

#### 3. Duplication and repeated rule paths

Qualitative hotspots:
- Repeated risk gating and post-validation branching across orchestration and risk/trade manager paths.
- Similar fallback patterns in market, strategy, and telemetry paths.

Quantification (proxy):
- Multiple large files with overlapping responsibilities (orchestration, risk, persistence, monitoring), which usually correlates with repeated business rules.

Debt score: Medium

### B. Architecture Debt

#### 1. Boundary leakage / orchestration concentration

Evidence:
- main.py handles lifecycle, scheduling, ranking, command queue, heartbeat, profiling, reconciliation, and execution gating.
- database/db.py acts as broad service layer for many concerns.

Impact:
- Harder local reasoning and testing.
- Higher chance of unrelated breakage when modifying one concern.

Debt score: High

#### 2. Operational policy mixed with business flow

Evidence:
- Runtime resilience behavior, command handling, monitoring updates, and trade decisions are tightly interleaved.

Debt score: Medium

### C. Technology Debt

#### 1. Floating dependency ranges in Python

requirements.txt uses mostly >= constraints without upper bounds.

Impact:
- Non-deterministic upgrades and subtle breakages from transitive changes.

Debt score: Medium

#### 2. UI stack modernization mismatch risk

Web dependencies are relatively modern, but test/lint stack focuses on type-check only in web scripts.

Debt score: Medium

### D. Testing Debt

Measured:
- Python files in analyzed scope: 72
- Test files: 16
- Unit tests: 16
- Integration tests: 0
- E2E tests: 0
- Performance tests: 0

Full suite signal:
- 19 failed, 185 passed in 104.53s
- Failures concentrated in trade lifecycle, risk behavior, DB resilience, deepseek strategy expectations

Debt score: High

### E. Documentation Debt

Strengths:
- Strong root README and architecture overview.

Gaps:
- Missing maintainers-facing module boundary maps and ownership for high-risk core modules.
- Missing explicit debt budget and refactor policy docs.

Debt score: Medium

### F. Infrastructure Debt

Evidence:
- CI exists for tests and ruff lint, but no explicit performance baseline gate or rollback rehearsal checks.
- No enforced dependency audit/security gate in CI.

Debt score: Medium

---

## 2) Impact Analysis (Cost and Risk)

### Velocity impact examples

1) Oversized orchestration module (main.py)
- Estimated extra review/debug overhead: 6 hours/week
- Annual cost: 6 * 52 * $120 = $37,440

2) Monolithic DB layer (database/db.py)
- Estimated schema/DAO change friction: 5 hours/week
- Annual cost: 5 * 52 * $120 = $31,200

3) High exception/pass density
- Estimated hidden-failure triage overhead: 3 incidents/month * 4 hours
- Annual cost: 3 * 4 * 12 * $120 = $17,280

### Quality impact

Current full-test signal suggests meaningful regression pressure:
- 19 failing tests in core lifecycle areas
- If each failure cluster costs 2-4 engineer hours to isolate/fix/verify:
- Estimated immediate stabilization effort: 60-100 hours ($7,200-$12,000)

### Risk levels

Critical
- Trade lifecycle and risk validation regressions (business-impacting behavior drift)

High
- Main loop concentration and DB monolith
- Missing integration/E2E/perf test layers

Medium
- Floating dependency strategy
- CI observability/perf gate gaps

Low
- Cosmetic style and minor naming consistency

---

## 3) Debt Metrics Dashboard (Current vs Target)

```yaml
metrics:
  code_size_hotspots:
    main_py_lines: 1181
    db_py_lines: 1108
    large_module_threshold: 500
    files_above_threshold: 4
    target_files_above_threshold: 1

  reliability_signals:
    except_exception_count: 64
    pass_keyword_count: 37
    target_except_exception_count: 35
    target_pass_keyword_count: 15

  testing:
    test_files_total: 16
    unit_tests: 16
    integration_tests: 0
    e2e_tests: 0
    performance_tests: 0
    full_suite_last_run:
      passed: 185
      failed: 19
      duration_seconds: 104.53
    target_90_days:
      integration_tests: 8
      e2e_tests: 4
      performance_tests: 3
      failing_tests: 0

  dependency_health:
    python_constraints_style: "mostly >= without upper bounds"
    ci_security_audit_gate: false
    target:
      lock_or_constraints_file: true
      ci_security_audit_gate: true
```

Trend risk without intervention:
- Regression triage and hotfix overhead likely rises as orchestration and persistence complexity continue to accrete.

---

## 4) Prioritized Roadmap (Quarter-by-Quarter)

### Q1 (0-4 weeks): Stabilize and de-risk

1) Test stabilization sprint
- Fix 19 currently failing tests
- Add regression coverage for trade lifecycle transitions and DB resilience mocks
- Effort: 70 hours
- Benefit: immediate confidence and reduced breakage churn

2) Exception handling hardening pass
- Replace silent pass in core runtime paths with typed handling and structured logs
- Effort: 24 hours
- Benefit: faster root cause detection (estimated 25-35% triage reduction)

3) DB test contract alignment
- Standardize mock DB interface used by trade manager/risk paths
- Effort: 16 hours
- Benefit: fewer false negatives in core tests

### Q2 (1-3 months): Structural decomposition

1) Split database/db.py into repositories/services by domain
- Trades, status/events, commands, analytics
- Effort: 90 hours
- Benefit: lower coupling and change blast radius

2) Extract orchestration services from main.py
- Scheduling, ranking, command processing, heartbeat as separate modules
- Effort: 100 hours
- Benefit: improved maintainability + testability

3) Introduce integration test layer
- End-to-end bot loop with mock broker + DB harness
- Effort: 60 hours
- Benefit: catches lifecycle regressions earlier

### Q3-Q4 (3-9 months): Continuous debt control

1) Add performance baseline tests for main loop latency and scan throughput
- Effort: 40 hours

2) Dependency governance
- Constraints/lock strategy + CI audit gate
- Effort: 24 hours

3) Architecture conformance checks
- Lightweight boundaries and ownership docs for core modules
- Effort: 30 hours

---

## 5) Quick Wins (This Sprint)

### Quick Win 1: Fail-test burn-down for trade lifecycle cluster
- Effort: 24 hours
- Savings: 8 hours/week of recurring triage and rework
- 1-month ROI: (32h - 24h) / 24h = 33%

### Quick Win 2: Replace top 10 silent pass sites in runtime paths
- Effort: 10 hours
- Savings: 4 hours/month incident diagnosis
- 1-month ROI: (4h - 10h)/10h = negative month 1, positive by month 3

### Quick Win 3: Add CI stage for dependency vulnerability audit
- Effort: 6 hours
- Savings: avoids emergency patch windows and surprise breakage
- Risk ROI: high despite uncertain direct hourly savings

### Quick Win 4: Introduce constraints file for Python dependencies
- Effort: 8 hours
- Savings: fewer stochastic CI/prod breakages from transitive updates
- 2-3 month payoff expected

---

## 6) Implementation Guide (Step-by-Step)

### Stream A: Testing debt remediation

1. Stabilize failing tests by category:
   - trade_manager / trade_lifecycle
   - risk_agent
   - deepseek_strategy
   - db_resilience
2. Add dedicated fixtures that implement full DB mock contract (including update_live_state).
3. Add mutation-focused tests for TP/SL transitions and post-entry validation branches.

### Stream B: Structural refactoring

1. Extract modules from main.py incrementally:
   - loop_scheduler.py
   - signal_ranker.py
   - command_processor.py
   - heartbeat_service.py
2. Preserve behavior with feature flags and side-by-side wiring before final cutover.
3. Add contract tests for each extracted component.

### Stream C: Reliability and observability

1. Replace bare pass with explicit fallback + reason code logging in runtime-critical paths.
2. Add error taxonomy for recoverable vs terminal failures.
3. Emit metrics counters for fallback activations and suppressed exceptions.

---

## 7) Prevention Plan

### Quality gates (CI/CD)

```yaml
python_quality_gates:
  ruff: required
  mypy_or_pyright: required_for_core_modules
  tests:
    unit: required
    integration: required_on_main_branch
  fail_if:
    - new bare except Exception without justification tag
    - new pass in runtime-critical modules without comment and issue link

dependency_gates:
  python:
    constraints_file_required: true
    vulnerability_scan_required: true
  web:
    npm_audit_high_block: true

architecture_gates:
  module_size_limit_lines:
    warning: 400
    fail: 700
  ownership_required_for:
    - main orchestration
    - db access layer
```

### Debt budget

```yaml
debt_budget:
  max_new_core_debt_per_sprint:
    oversized_modules: 0
    untyped_broad_exceptions: +2 max
    silent_pass_sites: +0
  mandatory_reduction_target:
    exception_density: -15% per quarter
    failing_tests: 0 each sprint end
    integration_tests: +2 per sprint until baseline reached
```

---

## ROI Projection

Conservative 12-month projection if roadmap is executed:
- Velocity reclaimed: 350-500 engineering hours
- Direct value: $42,000-$60,000
- Additional upside: lower production risk and faster release confidence

---

## Recommended Next Sprint Backlog

1. Fix failing test clusters and lock regression coverage (highest ROI)
2. Implement DB mock contract consistency to stop repeated false negatives
3. Add dependency audit + constraints governance in CI
4. Refactor first extraction from main.py (command processor)
