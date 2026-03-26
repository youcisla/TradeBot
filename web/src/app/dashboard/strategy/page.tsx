"use client";

const S = {
  card: {
    background: "#0e0e10" as const,
    border: "1px solid #1c1c28",
    borderRadius: 8,
    padding: "20px 22px",
    position: "relative" as const,
    overflow: "hidden" as const,
  },
  heading: {
    fontSize: 9,
    fontFamily: "'JetBrains Mono', monospace",
    color: "#607888",
    letterSpacing: "0.18em",
    textTransform: "uppercase" as const,
    fontWeight: 600,
    marginBottom: 14,
    borderBottom: "1px solid #1c1c28",
    paddingBottom: 10,
  },
  label: {
    fontSize: 9.5,
    color: "#607888",
    fontFamily: "'JetBrains Mono', monospace",
  },
  value: {
    fontSize: 11,
    color: "#9aa8b8",
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 600,
  },
  mono: {
    fontFamily: "'JetBrains Mono', monospace",
  },
};

function Card({ title, accent, children }: { title: string; accent?: string; children: React.ReactNode }) {
  const accentColor = accent ?? "#00ff88";
  return (
    <div style={S.card}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent, ${accentColor}44, transparent)`,
      }} />
      <div style={S.heading}>{title}</div>
      {children}
    </div>
  );
}

function Row({ label, value, hint, color }: { label: string; value: string; hint?: string; color?: string }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "flex-start",
      padding: "5px 0", borderBottom: "1px solid rgba(28,28,40,0.4)",
    }}>
      <span style={S.label}>{label}</span>
      <span style={{ textAlign: "right" }}>
        <span style={{ ...S.value, color: color ?? "#9aa8b8" }}>{value}</span>
        {hint && <span style={{ display: "block", fontSize: 8.5, color: "#607888", ...S.mono }}>{hint}</span>}
      </span>
    </div>
  );
}

function Tag({ children, color }: { children: React.ReactNode; color: "green" | "red" | "yellow" | "blue" | "purple" }) {
  const colors = {
    green:  { bg: "rgba(0,255,136,0.12)",  text: "#00ff88", border: "rgba(0,255,136,0.25)" },
    red:    { bg: "rgba(255,68,85,0.12)",   text: "#ff4455", border: "rgba(255,68,85,0.25)" },
    yellow: { bg: "rgba(245,197,24,0.12)",  text: "#f5c518", border: "rgba(245,197,24,0.25)" },
    blue:   { bg: "rgba(77,166,255,0.12)",  text: "#4da6ff", border: "rgba(77,166,255,0.25)" },
    purple: { bg: "rgba(213,0,249,0.12)",   text: "#d500f9", border: "rgba(213,0,249,0.25)" },
  }[color];
  return (
    <span style={{
      display: "inline-block",
      padding: "2px 9px", borderRadius: 3, marginRight: 8,
      fontSize: 9, fontWeight: 700, letterSpacing: "0.08em",
      fontFamily: "'JetBrains Mono', monospace",
      background: colors.bg, color: colors.text,
      border: `1px solid ${colors.border}`,
      textTransform: "uppercase" as const,
    }}>
      {children}
    </span>
  );
}

export default function StrategyPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Header */}
      <div>
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#607888", letterSpacing: "0.2em", textTransform: "uppercase",
        }}>
          Architecture
        </div>
        <h1 style={{
          fontSize: 20, fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 700, marginTop: 2,
          background: "linear-gradient(90deg, #d500f9, #00ff88)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        }}>
          DeepSeek LLM Strategy
        </h1>
        <p style={{
          fontSize: 11, ...S.mono, color: "#607888", marginTop: 8, lineHeight: 1.6,
        }}>
          The primary signal generator queries the DeepSeek chat API with the last 20 H1 candles
          plus all computed indicators. The LLM reasons over price action and returns a structured
          JSON signal. The Council (ICT + DanialFX + Traditional experts) confirms every signal
          before it reaches execution.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

        {/* API Setup */}
        <Card title="DeepSeek API" accent="#d500f9">
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            <Row label="Model"           value="deepseek-chat"    hint="configurable via DEEPSEEK_MODEL" />
            <Row label="Min confidence"  value="65%"              hint="to generate a signal" color="#00ff88" />
            <Row label="Cache TTL"       value="30 min"           hint="per symbol — avoids API spam" />
            <Row label="Temperature"     value="0.2"              hint="low for consistent, structured output" />
            <Row label="Max tokens"      value="300"              hint="JSON response only" />
            <Row label="Timeout"         value="15 s"             hint="per call — never blocks the loop" />
            <Row label="Response format" value="json_object"      hint="enforced by API parameter" color="#d500f9" />
          </div>
          <div style={{
            marginTop: 14, fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5,
            background: "#0a0a12", border: "1px solid #1c1c28",
            borderRadius: 5, padding: "10px 14px",
            color: "#7a8a9a", lineHeight: 2,
          }}>
            <div style={{ color: "#d500f9" }}>Response schema:</div>
            <div style={{ paddingLeft: 10 }}>{`{ "direction": "BUY" | "SELL" | "HOLD",`}</div>
            <div style={{ paddingLeft: 10 }}>{`  "confidence": 0.0–1.0,`}</div>
            <div style={{ paddingLeft: 10 }}>{`  "stop_loss": float,`}</div>
            <div style={{ paddingLeft: 10 }}>{`  "take_profit_1": float,   // 1R`}</div>
            <div style={{ paddingLeft: 10 }}>{`  "take_profit_2": float,   // 2R`}</div>
            <div style={{ paddingLeft: 10 }}>{`  "take_profit_3": float,   // 3R`}</div>
            <div style={{ paddingLeft: 10 }}>{`  "reasoning": "max 80 words" }`}</div>
          </div>
        </Card>

        {/* Prompt Context */}
        <Card title="Prompt Context (per call)" accent="#f5c518">
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            <Row label="Candle history"  value="Last 20 H1 bars"   hint="OHLCV table, oldest → newest" />
            <Row label="RSI"             value="14-period"          hint="normalised momentum" />
            <Row label="ATR"             value="14-period"          hint="volatility baseline for SL" />
            <Row label="SMA fast/slow"   value="10 / 50"            hint="crossover state + values" />
            <Row label="Regime"          value="trending / ranging / volatile" />
            <Row label="Trend"           value="bullish / bearish / neutral" />
            <Row label="Session"         value="London / NY / Asian / overlap" />
            <Row label="Macro (Crucix)"  value="tier, VIX, sentiment, lot_scale" hint="when Crucix is running" color="#00ffcc" />
          </div>
          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 9, color: "#607888", ...S.mono, lineHeight: 1.7 }}>
              SL rules injected into prompt: must be beyond nearest swing high/low,
              minimum 2×ATR distance. TP1=1R, TP2=2R, TP3=3R from entry.
            </div>
          </div>
        </Card>

        {/* Sanity checks */}
        <Card title="Signal Sanity Checks" accent="#00ff88">
          <div style={{ ...S.mono, fontSize: 10.5, color: "#7a8a9a", lineHeight: 1.7 }}>
            <p style={{ marginBottom: 10, color: "#7a8a9a" }}>
              Even with <span style={{ color: "#d500f9" }}>json_object</span> mode, every field is validated
              before a signal is emitted:
            </p>
            <div style={{ paddingLeft: 12 }}>
              <div><Tag color="green">pass</Tag><span>confidence ≥ DEEPSEEK_MIN_CONFIDENCE</span></div>
              <div style={{ marginTop: 6 }}><Tag color="green">pass</Tag><span>direction ∈ {"{ BUY, SELL }"}</span></div>
              <div style={{ marginTop: 6 }}><Tag color="red">reject</Tag><span>BUY with SL ≥ entry</span></div>
              <div style={{ marginTop: 6 }}><Tag color="red">reject</Tag><span>SELL with SL ≤ entry</span></div>
              <div style={{ marginTop: 6 }}><Tag color="red">reject</Tag><span>stop_loss or take_profit_1 = 0</span></div>
              <div style={{ marginTop: 6 }}><Tag color="yellow">cache</Tag><span>re-use last result within 30 min TTL</span></div>
              <div style={{ marginTop: 6 }}><Tag color="yellow">null</Tag><span>API error / timeout → return None (ICT/SMA fallback)</span></div>
            </div>
          </div>
        </Card>

        {/* Signal Flow */}
        <Card title="Signal Pipeline (Main Loop)" accent="#ff9d00">
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5,
            color: "#7a8a9a", lineHeight: 2,
            background: "#0a0a12", border: "1px solid #1c1c28",
            borderRadius: 5, padding: "10px 14px",
          }}>
            <div><span style={{ color: "#00d4ff" }}>Market</span> → get H1 candles + live tick</div>
            <div><span style={{ color: "#f5c518" }}>Analysis</span> → RSI, ATR, SMA, regime, session</div>
            <div><span style={{ color: "#00ff88" }}>Strategy</span> → run all 3 strategies in parallel</div>
            <div style={{ paddingLeft: 14, color: "#d500f9" }}>DeepSeek → LLM call (cached 30 min)</div>
            <div style={{ paddingLeft: 14, color: "#7a8a9a" }}>ICT/SMC → order blocks, FVG, BOS</div>
            <div style={{ paddingLeft: 14, color: "#7a8a9a" }}>SMA crossover → fast/slow MA signal</div>
            <div><span style={{ color: "#00ff88" }}>Rank</span> → sort all signals by confidence</div>
            <div><span style={{ color: "#ff9d00" }}>Council</span> → ICT + DanialFX + Traditional confirm</div>
            <div style={{ paddingLeft: 14, color: "#607888" }}>majority vote required to proceed</div>
            <div><span style={{ color: "#ff4455" }}>Risk</span> → position size, daily limits, spread, correlation</div>
            <div><span style={{ color: "#f0f0f0" }}>Exec</span> → open MT5 order (SL=2×ATR, TP×3)</div>
            <div><span style={{ color: "#bf7fff" }}>TradeMgr</span> → partial close, breakeven, trailing</div>
          </div>
        </Card>

        {/* Risk Management */}
        <Card title="Risk Management">
          <Row label="Max Risk per Trade"    value="2%"         hint="of account equity" />
          <Row label="Max Open Trades"       value="3" />
          <Row label="Max Daily Loss"        value="5%"         hint="of account equity" />
          <Row label="Max Spread"            value="3.0 pips"   hint="rejects trades above this" />
          <Row label="Stop Loss"             value="2 × ATR"    hint="from entry (LLM may tighten)" color="#ff4455" />
          <Row label="TP1"                   value="1R"         hint="close 40%" color="#00ff88" />
          <Row label="TP2"                   value="2R"         hint="close 30%, trailing starts" color="#00ff88" />
          <Row label="TP3"                   value="3R"         hint="close remainder" color="#00ff88" />
          <Row label="Commission"            value="$7 / lot"   hint="factored into breakeven" />
          <Row label="Macro blackout"        value="FLASH tier" hint="Crucix FLASH alert → no new trades" color="#00ffcc" />
          <Row label="Correlation guard"     value="cross-pair" hint="blocks correlated pair in same direction" />
        </Card>

        {/* Score System */}
        <Card title="Learning Score System">
          <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1c1c28" }}>
                <th style={{ padding: "4px 6px", textAlign: "left", fontSize: 8.5, color: "#607888", letterSpacing: "0.1em", textTransform: "uppercase" }}>Outcome</th>
                <th style={{ padding: "4px 6px", textAlign: "right", fontSize: 8.5, color: "#607888", letterSpacing: "0.1em", textTransform: "uppercase" }}>Score</th>
                <th style={{ padding: "4px 6px", textAlign: "left", fontSize: 8.5, color: "#607888", letterSpacing: "0.1em", textTransform: "uppercase" }}>Rule</th>
              </tr>
            </thead>
            <tbody>
              {[
                { label: "Clean Win",    score: "+3", color: "#00ff88", rule: "Profit ≥ 2R" },
                { label: "Messy Win",    score: "+1", color: "#76ff03", rule: "Profit > 0 but < 2R" },
                { label: "Normal Loss",  score: "−2", color: "#f5c518", rule: "SL hit, entry valid" },
                { label: "Bad Loss",     score: "−5", color: "#ff4455", rule: "SL hit + loss > 1.5R" },
              ].map((r) => (
                <tr key={r.label} style={{ borderBottom: "1px solid rgba(28,28,40,0.4)" }}>
                  <td style={{ padding: "5px 6px", color: r.color }}>{r.label}</td>
                  <td style={{ padding: "5px 6px", textAlign: "right", fontWeight: 700, color: r.color }}>{r.score}</td>
                  <td style={{ padding: "5px 6px", color: "#7a8a9a" }}>{r.rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 12, fontSize: 9.5, color: "#607888", fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.6 }}>
            Bonus: +0.5 each for RSI aligned, trend aligned, volume sufficient, no news event.
            Confidence step: 0.02 per score point · min 10% · max 100%.
          </div>
        </Card>

      </div>
    </div>
  );
}
