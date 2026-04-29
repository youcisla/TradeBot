"use client";
// Mock data mirroring handoff data.js structure

export const MOCK = {
  account: {
    equity: 24891.52,
    balance: 24100.00,
    dayPnl: 791.52,
    winrate: 73.1,
    openCount: 3,
    conId: 81123107,
    broker: "PU Prime",
    server: "PUPRIME-Live",
  },
  bot: {
    state: "RUNNING",
    loopMs: 1240,
    loops: 1423,
    lastTs: new Date(Date.now() - 340).toISOString(),
    mode: "LIVE",
  },
  agents: [
    { id: "crucix",        label: "Crucix",        state: "RUNNING", ms: 0  },
    { id: "market",        label: "Market",        state: "RUNNING", ms: 12 },
    { id: "analysis",      label: "Analysis",      state: "RUNNING", ms: 8  },
    { id: "strategy",      label: "Strategy",      state: "RUNNING", ms: 31 },
    { id: "neural",        label: "Neural",        state: "RUNNING", ms: 45 },
    { id: "council",       label: "Council",       state: "RUNNING", ms: 28 },
    { id: "risk",          label: "Risk",          state: "IDLE",    ms: 0  },
    { id: "execution",     label: "Execution",     state: "RUNNING", ms: 19 },
    { id: "trade_manager", label: "Trade Mgr",    state: "RUNNING", ms: 0  },
  ],
  positions: [
    {
      ticket: 504123, symbol: "NAS100",  dir: "BUY",  lots: 0.80,
      entry: 18241.5, act: 18263.8, pnl: 178.40, pnlPct: 1.22,
      tp: 18320.0, sl: 18150.0, ts: "2026-04-27T08:12:00Z",
    },
    {
      ticket: 504124, symbol: "XAUUSD",  dir: "SELL", lots: 0.50,
      entry: 3328.20, act: 3318.50, pnl: 485.00, pnlPct: 2.91,
      tp: 3310.00, sl: 3345.00, ts: "2026-04-27T09:05:00Z",
    },
    {
      ticket: 504125, symbol: "EURUSD",  dir: "BUY",  lots: 1.20,
      entry: 1.12340, act: 1.12480, pnl: 168.00, pnlPct: 1.25,
      tp: 1.12800, sl: 1.11800, ts: "2026-04-27T10:22:00Z",
    },
  ],
  signals: [
    { id: "s1", symbol: "NAS100",  dir: "BUY",  conf: 88, tier: "vh",    verdict: "APPROVED", score: 72, age: "2m"  },
    { id: "s2", symbol: "XAUUSD",  dir: "BUY",  conf: 76, tier: "high", verdict: "APPROVED", score: 61, age: "5m"  },
    { id: "s3", symbol: "EURUSD",  dir: "SELL", conf: 34, tier: "mid",  verdict: "BLOCKED",  score: 28, age: "8m"  },
    { id: "s4", symbol: "US30",    dir: "SELL", conf: 91, tier: "vh",   verdict: "PENDING",  score: 77, age: "1m"  },
    { id: "s5", symbol: "GBPAUD",  dir: "BUY",  conf: 63, tier: "high", verdict: "QUEUED",   score: 54, age: "12m" },
  ],
  macro: {
    session: "London", regime: "TREND", vix: 18.4, dxy: 99.2,
    trend: "BULLISH", bias: "LONG", opportunities: 4,
  },
  learning: {
    drift: 0.02, confidence: 83, epoch: 142, totalTrades: 208,
    lastReward: 0.74,
  },
  exposure: {
    long: 65, short: 35, maxLong: 80, maxShort: 60,
    concentration: "LOW",
  },
  events: [
    { ts: new Date(Date.now() - 12000).toISOString(), agent: "strategy",  msg: "NAS100 BUY signal ranked #1", type: "info" },
    { ts: new Date(Date.now() - 8000 ).toISOString(), agent: "risk",      msg: "Signal approved -- conf 88",    type: "info" },
    { ts: new Date(Date.now() - 5000 ).toISOString(), agent: "execution", msg: "Order 504123 placed",         type: "pos"  },
    { ts: new Date(Date.now() - 2000 ).toISOString(), agent: "neural",   msg: "Model updated -- epoch 142", type: "info" },
  ],
  equity: [
    22000,22100,22350,22200,22500,22800,23100,22900,23400,23800,
    23600,23900,24100,24000,24300,24500,24400,24600,24700,24891,
  ],
};
