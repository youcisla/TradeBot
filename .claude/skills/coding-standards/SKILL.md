---
name: coding-standards
description: Master coding standards, UI/UX rules, design tokens, component patterns, and consistency rules for the TradingBot project. READ THIS before writing any frontend (Next.js/TSX) code. Also covers Python bot conventions.
user-invocable: false
---

# TradingBot — Coding Standards

## RULE 0: Read Before Write

Before modifying any file:
1. Read the file with the `Read` tool
2. Read any components it imports
3. Read the relevant skills
4. Only then make changes

---

## Frontend: UI/UX Design System

### Color Palette

```
Background layers:
  Page bg:      #080808
  Card bg:      #0a0a12
  Table bg:     #0e0e10
  Input bg:     #06060c

Borders:
  Primary:      #1c1c28
  Subtle:       rgba(28,28,40,0.5)

Text:
  Primary:      #c0ccd8   ← main readable text
  Secondary:    #9aa8b8   ← secondary readable text
  Subdued:      #7a8a9a   ← table cell secondary data, descriptions (was #4a5568)
  Dim:          #607888   ← section titles, table headers, KPI labels (was #2a3a4a)
  Ghost:        #3a5248   ← empty state messages (was #1e2e1e)

NOTE: #2a3a4a, #1e2e1e, #4a5568 are BANNED — too dark to read on #0a0a12 bg.

Accent / action colors:
  Green (profit, active, buy): #00ff88
  Cyan (primary data, symbol): #00d4ff
  Blue (info, learning):       #4da6ff
  Yellow (warning, analysis):  #f5c518
  Orange (ICT, council):       #ff9d00
  Red (loss, sell, danger):    #ff4455
  Purple (neural):             #d500f9
  Lime (model_manager):        #76ff03
  White/exec:                  #f0f0f0
  Trade manager:               #bf7fff
```

### Agent Colors (exact, consistent across all files)

```
market:        #00d4ff
analysis:      #f5c518
strategy:      #00ff88
neural:        #d500f9   ← New LSTM strategy agent
council:       #ff9d00
risk:          #ff4455
execution:     #f0f0f0
trade_manager: #bf7fff
learning:      #4da6ff
model_manager: #76ff03   ← New LSTM model trainer
logging:       #5c6a78
```

### Typography

```
Font:    'JetBrains Mono', monospace  ← ALL text, everywhere
Sizes:   8.5px (micro labels), 9px (caps label), 10px (data), 11px (body), 13px (medium value), 16px (metric), 20px+ (heading)
Weights: 700 (headings, values), 600 (labels), 400 (body)
Tracking: 0.2em (section labels), 0.14em (field labels), 0.08em (badges)
Case:    uppercase for all labels/headers/badges
```

---

## Frontend: Rules

### NEVER use Tailwind CSS classes (`className`)
All styling MUST be done with React inline styles (`style={{}}`).
This is non-negotiable. Reason: the existing codebase is being migrated away from Tailwind
to have pixel-perfect control and a consistent dark terminal aesthetic.

```tsx
// ❌ WRONG
<div className="flex items-center gap-4 border border-terminal-border rounded p-4">

// ✅ CORRECT
<div style={{ display: "flex", alignItems: "center", gap: 16,
  border: "1px solid #1c1c28", borderRadius: 8, padding: 16 }}>
```

### Card / Section pattern

```tsx
// Standard info card
<div style={{
  background: "#0a0a12",
  border: "1px solid #1c1c28",
  borderTop: "2px solid ACCENT_COLOR",   // colored top accent = card category
  borderRadius: 8,
  padding: "18px 20px",
}}>
  <div style={{
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 9, fontWeight: 700, letterSpacing: "0.16em",
    textTransform: "uppercase", color: "#2a3a4a",
    marginBottom: 14, paddingBottom: 10,
    borderBottom: "1px solid #1c1c28",
  }}>
    Section Title
  </div>
  {/* content */}
</div>
```

### Page header pattern

```tsx
<div>
  <div style={{
    fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
    color: "#2a3a4a", letterSpacing: "0.2em", textTransform: "uppercase",
  }}>
    Subsystem Name
  </div>
  <h1 style={{
    fontSize: 20, fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 700, color: "#ACCENT_COLOR",
    textShadow: "0 0 20px rgba(R,G,B,0.3)", marginTop: 2,
  }}>
    Page Title
  </h1>
</div>
```

### KPI card pattern

```tsx
<div style={{
  background: "#0a0a12", border: "1px solid #1c1c28",
  borderTop: `2px solid ${color}`, borderRadius: 8,
  padding: "16px 20px", textAlign: "center",
}}>
  <div style={{
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 22, fontWeight: 700, color,
    textShadow: `0 0 14px ${color}55`,
  }}>{value}</div>
  <div style={{
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 8.5, letterSpacing: "0.14em",
    textTransform: "uppercase", color: "#2a3a4a", marginTop: 4,
  }}>{label}</div>
</div>
```

### Table pattern

```tsx
<div style={{
  background: "#0e0e10", border: "1px solid #1c1c28",
  borderRadius: 8, overflow: "auto",
}}>
  <table style={{
    width: "100%", borderCollapse: "collapse",
    fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
  }}>
    <thead>
      <tr style={{ borderBottom: "1px solid #1c1c28" }}>
        {headers.map((h) => (
          <th key={h} style={{
            padding: "9px 10px",
            textAlign: isNumeric ? "right" : "left",
            fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
            color: "#2a3a4a", fontWeight: 600, whiteSpace: "nowrap",
          }}>{h}</th>
        ))}
      </tr>
    </thead>
    <tbody>
      <tr
        style={{ borderBottom: "1px solid rgba(28,28,40,0.5)", transition: "background 0.1s" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,212,255,0.03)"; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
      >
        {/* cells */}
      </tr>
    </tbody>
  </table>
</div>
```

### Direction badge pattern (BUY/SELL)

```tsx
<span style={{
  display: "inline-block", padding: "1px 7px", borderRadius: 3,
  fontSize: 9, fontWeight: 700, letterSpacing: "0.06em",
  background: dir === "BUY" ? "rgba(0,255,136,0.12)" : "rgba(255,68,85,0.12)",
  color: dir === "BUY" ? "#00ff88" : "#ff4455",
  border: `1px solid ${dir === "BUY" ? "rgba(0,255,136,0.3)" : "rgba(255,68,85,0.3)"}`,
}}>
  {dir}
</span>
```

### Button pattern

```tsx
// Primary button (green)
<button
  style={{
    padding: "9px 20px",
    background: "rgba(0,255,136,0.08)",
    border: "1px solid rgba(0,255,136,0.3)",
    borderRadius: 5,
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11, fontWeight: 700, letterSpacing: "0.08em",
    color: "#00ff88", cursor: "pointer",
  }}
  onMouseEnter={(e) => {
    (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,255,136,0.15)";
  }}
  onMouseLeave={(e) => {
    (e.currentTarget as HTMLButtonElement).style.background = "rgba(0,255,136,0.08)";
  }}
>
  ACTION
</button>

// Danger button (red)
// Same pattern but use #ff4455 / rgba(255,68,85,...)
```

### Input field pattern (with focus state)

```tsx
function TerminalInput({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [focused, setFocused] = useState(false);
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={{
        width: "100%", background: "#06060c",
        border: `1px solid ${focused ? "#00ff88" : "#1c1c28"}`,
        borderRadius: 4, padding: "8px 12px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11.5, color: "#c0ccd8", outline: "none",
        boxShadow: focused ? "0 0 0 2px rgba(0,255,136,0.18)" : "none",
        transition: "border-color 0.15s, box-shadow 0.15s",
        boxSizing: "border-box",
      }}
    />
  );
}
```

### Empty state pattern

```tsx
<div style={{
  padding: "40px 20px", textAlign: "center",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 11, color: "#3a5248",
}}>
  no data recorded yet
</div>
```

---

## Frontend: File Locations

```
web/src/
  app/
    dashboard/
      page.tsx          ← Main dashboard
      analytics/page.tsx
      trades/page.tsx
      learning/page.tsx
      strategy/page.tsx
      ict/page.tsx
      settings/page.tsx
      chart/page.tsx
      layout.tsx         ← Server component wrapping DashNav
  components/
    AgentFeed.tsx        ← Agent pipeline + terminal log (KEY FILE)
    BotStatusBar.tsx     ← HUD bar at top of dashboard
    CommandPanel.tsx
    OpenTradesTable.tsx
    EquityCurve.tsx
    SymbolFilter.tsx
    DashNav.tsx          ← Client nav using usePathname()
    TradingChart.tsx     ← Lightweight Charts (dynamic import)
  lib/
    time.ts             ← formatShort(), formatChartDate()
    formatPrice.ts
```

### DashNav — active link detection

`layout.tsx` is a server component. Active link detection needs `usePathname()`, so it lives in `DashNav.tsx` (a `"use client"` component).

```tsx
// layout.tsx — server component, imports DashNav
import DashNav from "@/components/DashNav";

// DashNav.tsx — client component
"use client";
import { usePathname } from "next/navigation";
```

### AgentFeed — agent keys

The `AgentFeed.tsx` component shows the pipeline and support agents. The `key` must exactly match the `agent` field value stored in the `agent_events` DB table.

```
PIPELINE: market, analysis, strategy, neural, council, risk, execution, trade_manager
SUPPORT:  learning, model_manager, logging
```

---

## Python Bot: Conventions

```python
# Always use type hints
def analyze(self, market_data: MarketData) -> MarketContext: ...

# Config from environment via config/settings.py — never hardcode values
from config.settings import settings
max_trades = settings.MAX_OPEN_TRADES

# Logging via logging_agent, not print()
self.logger.record("event_name", {"key": "value"})

# Error handling: catch specific exceptions, log them, don't re-raise silently
try:
    result = broker.place_order(signal)
except BrokerConnectionError as e:
    self.logger.record("execution_error", {"error": str(e), "signal": signal})
    return None

# Agents communicate through data models in models/
# No agent calls another agent directly — main loop orchestrates
```

### Database tables

```sql
trades             -- open and closed trades
trade_scores       -- learning system scores per trade
strategy_confidence -- per-strategy confidence (0.0 to 1.0)
agent_events       -- pipeline events (agent, symbol, message, timestamp)
bot_commands       -- remote commands (pause/resume/kill)
bot_status         -- current bot state (running/paused)
ict_setups         -- ICT pattern detections
```

---

## Skill Maintenance Rules

1. **Update `trading-bot-overview` when:** architecture changes, new agent added, new strategy, new infra component
2. **Update `coding-standards` when:** new UI pattern established, new color token, new component pattern, user requests a style change
3. **Update `implement-agent` when:** an agent's interface, responsibilities, or rules change
4. **Update `add-strategy` when:** the strategy base class, Signal model, or registration process changes
5. **Always update skills in the same session where the change was made** — don't defer to "later"
