---
name: trading-bot-overview
description: Full architecture and design reference for the Python trading bot project. Use when discussing architecture, understanding the system, or making decisions about any module. Covers agents, loop flow, execution model, learning system, infrastructure, LSTM neural model, ICT/SMC engine, and scan-rank-execute pipeline.
user-invocable: false
---

# Trading Bot — Architecture Overview

This project is a **modular Python trading bot** that connects to a **PU Prime trading account** via MetaTrader 5. It is composed of independent agents collaborating in a continuous loop. The primary strategy is now a **per-symbol LSTM neural network** trained on 2 years of H1 OHLCV history. The ICT/SMC engine is retained as a reference/alternative strategy.

Features a **scan-all → rank → execute-best** pipeline across **30 symbols** in 5 asset classes, and a **Next.js web dashboard** with a dark terminal (cyberpunk) aesthetic.

---

## Agent Pipeline

```
PIPELINE:  market → analysis → strategy → neural → council → risk → execution → trade_manager
SUPPORT:   learning · model_manager · logging
```

### Agent Responsibilities

| Agent | Key | Question | Responsibility |
|---|---|---|---|
| Market Agent | `market` | What is the market doing? | 250 H1 candles, spread, volume, data validation |
| Analysis Agent | `analysis` | What does it mean? | SMA, RSI, ATR, regime, session detection |
| Strategy Agent | `strategy` | Is there a signal? | Orchestrates registered strategies, calls detect_all() |
| **Neural Strategy** | `neural` | LSTM prediction? | Wraps ModelManager, returns BUY/SELL/HOLD signal |
| Council Agent | `council` | Consensus check? | 3-expert vote (ICT, DanialFX, Traditional) for confirmation |
| Risk Agent | `risk` | Is it safe? | 7-step validation gate |
| Execution Agent | `execution` | Can we execute it? | Places trade with SL + 3 TPs |
| Trade Manager | `trade_manager` | What do we do with it? | Partial closes, breakeven, trailing stops, reconciliation |
| Learning Agent | `learning` | What did we learn? | Reviews results, adjusts confidence |
| **Model Manager** | `model_manager` | Is the LSTM ready? | Downloads history, trains/fine-tunes per-symbol LSTM |
| Logging Agent | `logging` | (Records everything) | DB + CSV + Telegram |

---

## LSTM Neural Strategy (Primary)

### Architecture

```python
class LSTMTradingModel(nn.Module):
    input_size  = 9     # 9 features per timestep
    hidden_size = 64
    num_layers  = 2
    output_size = 3     # BUY=0, SELL=1, HOLD=2
    seq_len     = 50    # last 50 H1 bars
    dropout     = 0.2
```

### 9 Input Features (per bar)

| # | Feature | Formula |
|---|---|---|
| 1 | close_ret | log(close / prev_close) |
| 2 | high_body | (high - close) / ATR |
| 3 | low_body | (close - low) / ATR |
| 4 | candle_body | (close - open) / ATR |
| 5 | volume_z | (volume - vol_mean) / vol_std |
| 6 | rsi_centered | (RSI - 50) / 50 |
| 7 | sma_ratio | (sma_fast - sma_slow) / ATR |
| 8 | atr_pct | ATR / close |
| 9 | spread_atr | spread / ATR |

### Auto-Labeling Logic (training data)

For each bar `i` (needs `i + 20` bars ahead):
- Look 20 bars forward (horizon = 20)
- If first 1.5×ATR move is **upward** → label **BUY**
- If first 1.5×ATR move is **downward** → label **SELL**
- Neither → label **HOLD**

### Training Details

- **Data:** 2 years of H1 candles per symbol
- **Split:** 80/20 temporal (NO random shuffle)
- **Loss:** CrossEntropyLoss with class-frequency weighting
- **Optimizer:** Adam, lr=0.001, 20 epochs, early stopping (patience=3)
- **Batch:** 32
- **Normalization:** per-feature mean/std fitted on train set, saved to JSON

### Fine-Tuning (online learning)

- **Trigger:** every 20 new trade closures per symbol
- **Buffer:** 200 most recent closed trades (ring buffer)
- **Steps:** 5 epochs, lr=0.0001

### Model Storage

```
models/neural/
  EURUSD_H1.pt       ← PyTorch state dict
  EURUSD_H1.json     ← FeatureNormalizer (mean/std per feature)
  GBPUSD_H1.pt
  GBPUSD_H1.json
  ...
```

### Signal Threshold

`settings.NEURAL_MIN_CONFIDENCE` (default 0.60) — model must predict with ≥60% probability to generate a signal.

SL = 2×ATR from entry; TP1/2/3 = 1R/2R/3R (risk-based).

---

## Strategies

### NeuralStrategy (Primary — Active)

`agents/neural_strategy.py` wrapping `agents/model_manager.py`.
- Registered in `main.py` as the primary/only strategy
- Returns `None` if model not yet trained for that symbol
- Symbols train in background; bot skips them until ready

### ICT/SMC Strategy (Reference — NOT active in main loop)

Full ICT engine in `strategies/ict/` with 10 modules:
- `structure.py` — Swing points, BOS/MSS, dealing ranges
- `liquidity.py` — BSL/SSL mapping, sweep detection
- `displacement.py` — Impulsive candle detection
- `fvg.py` — Fair Value Gap detection + fill tracking
- `orderblock.py` — Order Block detection + validation
- `session.py` — Killzones, macros, PDH/PDL/PWH/PWL
- `bias.py` — HTF bias, regime, premium/discount
- `scoring.py` — 0–100 weighted confidence
- `setups.py` — 6 setup models
- `engine.py` — Unified orchestrator

Minimum ICT confidence: 55/100. Uses 200 H4 candles for HTF.

### SMA Crossover (Legacy — NOT active in main loop)

Simple moving average crossover in `strategies/sma_crossover.py`. Kept for reference.

---

## Core Loop — Scan-Rank-Execute Pipeline

```python
ModelManager.initialize(active_symbols)  # kicks off background LSTM training

TradeManager.reconcile()  # startup reconciliation

while True:
    loop_start = time.monotonic()

    TradeManager.monitor()  # monitor existing trades

    # PHASE 1: SCAN
    all_signals = []
    for symbol in active_symbols:
        if not is_market_open(symbol): continue
        data    = MarketAgent.get_data(symbol)
        context = AnalysisAgent.analyze(data)
        signals = StrategyAgent.detect_all(context)  # NeuralStrategy.detect()
        all_signals.extend(signals)

    # PHASE 2: RANK
    all_signals.sort(key=lambda s: s.confidence, reverse=True)
    ranked = deduplicate_by_symbol_direction(all_signals)

    # PHASE 3: EXECUTE
    for signal in ranked:
        if RiskAgent.validate(signal):
            trade = ExecutionAgent.open_trade(signal)

    elapsed = time.monotonic() - loop_start
    time.sleep(max(0, LOOP_INTERVAL_SECONDS - elapsed))
```

**Key features:**
- No first-come-first-served — a 95% GBPUSD beats a 61% EURUSD regardless of scan order
- Symbols without a trained model are skipped automatically
- As models finish training, they become active mid-session

---

## Trade Execution Model

Every trade: **1 SL + 3 TPs**

| Event | Action |
|---|---|
| Open | SL + TP1 + TP2 + TP3 placed |
| TP1 hit | Partial close (40%), SL → breakeven + spread offset |
| TP2 hit | Partial close (30%), trail SL begins |
| TP3 hit | Final close (30%) |
| SL hit | Full close at any point |

---

## Learning System

After each trade close:

| Outcome | Score |
|---|---|
| Clean profitable setup | +3 |
| Profit but messy setup | +1 |
| Small loss | -2 |
| Bad loss | -5 |
| Rule violation | -10 |

Confidence adjustments drive strategy enable/disable thresholds.
Also triggers LSTM fine-tuning: every 20 trade closures per symbol → 5 fine-tune epochs.

---

## Safety Systems

| System | Where |
|---|---|
| State persistence | Trade Manager → DB on every state change |
| Position reconciliation | Trade Manager on startup + periodic |
| Duplicate signal guard | Risk Agent |
| News blackout filter | Risk Agent + `filters/news_filter.py` |
| Spread spike detection | Risk Agent (live check at signal time) |
| Drawdown circuit breaker | Risk Agent |
| Data feed validation | Market Agent + `filters/data_validator.py` |
| Remote kill switch | Telegram `/kill` → Trade Manager |

---

## Infrastructure

| Component | Solution |
|---|---|
| Database | PostgreSQL via Supabase (7 tables) |
| Broker | MetaTrader 5 (PU Prime) |
| ML Framework | PyTorch (`torch>=2.0`) |
| Dashboard | Next.js 14 App Router (Vercel) |
| Alerts | Telegram bot (two-way: `/kill`, `/status`, `/pause`, `/resume`) |
| Launcher | `start.ps1` (Windows) or `python main.py` |

### DB Tables

```sql
trades              -- open and closed trades (with commission, lot limits)
trade_scores        -- learning system scores
strategy_confidence -- per-strategy confidence (0.0 to 1.0)
agent_events        -- pipeline events (market/analysis/neural/... events)
bot_commands        -- remote commands (pause/resume/kill)
bot_status          -- current state (running/paused)
ict_setups          -- ICT pattern detections (legacy reference)
```

### New Config Settings (LSTM)

```python
NEURAL_MIN_CONFIDENCE = 0.60   # minimum model confidence to generate signal
NEURAL_SEQ_LEN        = 50     # number of H1 bars per inference
NEURAL_TRAIN_YEARS    = 2      # years of history for initial training
NEURAL_RETRAIN_EVERY  = 20     # fine-tune after N new trade closures
NEURAL_MODELS_DIR     = "models/neural"
```

---

## Symbols (30 total)

- **Forex Majors** (6): EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
- **Forex Crosses** (12): EURGBP, EURJPY, GBPJPY, AUDJPY, NZDUSD, EURAUD, GBPAUD, EURCHF, GBPCHF, AUDNZD, CADJPY, CHFJPY
- **Commodities** (4): XAUUSD, XAGUSD, USOIL, UKOIL
- **Crypto** (5): BTCUSD, ETHUSD, LTCUSD, XRPUSD, SOLUSD
- **Exotics** (2): USDZAR, USDMXN

---

## Web Dashboard (Next.js)

**Aesthetic:** Dark terminal / cyberpunk — JetBrains Mono, #080808 background, neon accents

**Pages:**
| Route | Purpose |
|---|---|
| `/dashboard` | Main: BotStatusBar + AgentFeed + CommandPanel + EquityCurve + OpenPositions |
| `/dashboard/analytics` | KPI cards + charts (cumulative PnL, drawdown, by-symbol) |
| `/dashboard/trades` | Full trade history table with TpDot indicators |
| `/dashboard/learning` | Strategy confidence bars + recent trade scores |
| `/dashboard/strategy` | LSTM architecture documentation |
| `/dashboard/ict` | ICT setup detection stats (legacy reference) |
| `/dashboard/settings` | Broker account management |
| `/dashboard/chart` | Live lightweight-charts candlestick view |

**Key components:**
- `AgentFeed.tsx` — live agent event stream with pixel-art bots
- `BotStatusBar.tsx` — HUD showing bot state + account metrics
- `DashNav.tsx` — client nav with `usePathname()` active detection
- `SymbolFilter.tsx` — chip filter for all data tables

**Design rule:** ALL styling uses React inline styles. No Tailwind (`className`) on any new code.

---

## Development Status

1. ✅ Core structure (agents, main loop, config, state persistence)
2. ✅ Broker connection (MT5, MockConnector for testing)
3. ✅ Market data (price feed, candles, spread, volume)
4. ✅ First strategy (SMA crossover)
5. ✅ Risk engine (position sizing, SL/TP, spread check, drawdown)
6. ✅ Trade management (partial closes, breakeven, trailing stops)
7. ✅ Learning system (trade review, scoring, confidence)
8. ✅ Monitoring (alerts, Telegram, kill switch)
9. ✅ News filter (economic calendar)
10. ✅ Backtesting
11. ✅ ICT/SMC strategy engine (10 modules, 6 models)
12. ✅ Multi-asset expansion (30 symbols)
13. ✅ Scan-rank-execute pipeline
14. ✅ Web dashboard (cyberpunk terminal aesthetic)
15. ✅ Commission tracking + lot size limits
16. 🔄 LSTM Neural Model (architecture complete, integration in progress)
