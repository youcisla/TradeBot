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
    color: "#2a3a4a",
    letterSpacing: "0.18em",
    textTransform: "uppercase" as const,
    fontWeight: 600,
    marginBottom: 14,
    borderBottom: "1px solid #1c1c28",
    paddingBottom: 10,
  },
  label: {
    fontSize: 9.5,
    color: "#3a4a5a",
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
  const accentColor = accent ?? "#00ff41";
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
        {hint && <span style={{ display: "block", fontSize: 8.5, color: "#2a3a4a", ...S.mono }}>{hint}</span>}
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

const FEATURES = [
  { name: "close_ret",    desc: "log(close / prev_close)",           note: "price momentum" },
  { name: "high_body",    desc: "(high − close) / ATR",               note: "upper wick ratio" },
  { name: "low_body",     desc: "(close − low) / ATR",                note: "lower wick ratio" },
  { name: "candle_body",  desc: "(close − open) / ATR",               note: "body direction & size" },
  { name: "volume_z",     desc: "(vol − vol_mean) / vol_std",         note: "z-score over 50 bars" },
  { name: "rsi_centered", desc: "(RSI(14) − 50) / 50",               note: "normalized momentum" },
  { name: "sma_ratio",    desc: "(sma_fast − sma_slow) / ATR",        note: "trend alignment" },
  { name: "atr_pct",     desc: "ATR / close",                        note: "relative volatility" },
  { name: "spread_atr",  desc: "spread / ATR",                       note: "0 when unavailable" },
];

export default function StrategyPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Header */}
      <div>
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#2a3a4a", letterSpacing: "0.2em", textTransform: "uppercase",
        }}>
          Architecture
        </div>
        <h1 style={{
          fontSize: 20, fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 700, marginTop: 2,
          background: "linear-gradient(90deg, #d500f9, #00ff88)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        }}>
          Neural LSTM Strategy
        </h1>
        <p style={{
          fontSize: 11, ...S.mono, color: "#3a4a5a", marginTop: 8, lineHeight: 1.6,
        }}>
          A 2-layer LSTM trained on 2 years of H1 OHLCV data per symbol. The Council (ICT + DanialFX + Traditional experts)
          acts as a confirmation gate for every neural signal. Models train automatically at startup and fine-tune continuously as real trades close.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

        {/* Model Architecture */}
        <Card title="LSTM Model Architecture" accent="#d500f9">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
              color: "#9aa8b8", lineHeight: 1.7,
              background: "#0a0a12", border: "1px solid #1c1c28",
              borderRadius: 5, padding: "12px 14px",
            }}>
              <div style={{ color: "#d500f9" }}>LSTMTradingModel</div>
              <div style={{ paddingLeft: 14, color: "#4a5568" }}>Input  : (batch, <span style={{ color: "#f5c518" }}>50</span>, <span style={{ color: "#f5c518" }}>9</span>)   — 50 H1 bars × 9 features</div>
              <div style={{ paddingLeft: 14, color: "#4a5568" }}>LSTM   : hidden=<span style={{ color: "#00ff88" }}>64</span>, layers=<span style={{ color: "#00ff88" }}>2</span>, dropout=0.2</div>
              <div style={{ paddingLeft: 14, color: "#4a5568" }}>Output : (batch, <span style={{ color: "#f5c518" }}>3</span>)       — [BUY, SELL, HOLD]</div>
            </div>
            <Row label="Sequence length" value="50 bars" hint="last 50 H1 candles" />
            <Row label="Input features" value="9" hint="per timestep" />
            <Row label="Hidden size" value="64" />
            <Row label="LSTM layers" value="2" />
            <Row label="Output classes" value="BUY / SELL / HOLD" color="#d500f9" />
            <Row label="Min confidence" value="60%" hint="to generate a signal" color="#00ff88" />
          </div>
        </Card>

        {/* Input Features */}
        <Card title="Input Features (9 per bar)" accent="#f5c518">
          <table style={{
            width: "100%", borderCollapse: "collapse",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
          }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1c1c28" }}>
                <th style={{ padding: "4px 6px", textAlign: "left", fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.12em", textTransform: "uppercase" }}>#</th>
                <th style={{ padding: "4px 6px", textAlign: "left", fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.12em", textTransform: "uppercase" }}>Name</th>
                <th style={{ padding: "4px 6px", textAlign: "left", fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.12em", textTransform: "uppercase" }}>Formula / Notes</th>
              </tr>
            </thead>
            <tbody>
              {FEATURES.map((f, i) => (
                <tr key={f.name} style={{ borderBottom: "1px solid rgba(28,28,40,0.4)" }}>
                  <td style={{ padding: "5px 6px", color: "#2a3a4a" }}>{i}</td>
                  <td style={{ padding: "5px 6px", color: "#f5c518", fontWeight: 700 }}>{f.name}</td>
                  <td style={{ padding: "5px 6px", color: "#4a5568" }}>
                    <div>{f.desc}</div>
                    <div style={{ fontSize: 8.5, color: "#2a3a4a" }}>{f.note}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Auto-Labeling */}
        <Card title="Auto-Labeling (Training Data)" accent="#00ff88">
          <div style={{ ...S.mono, fontSize: 10.5, color: "#7a8a9a", lineHeight: 1.7 }}>
            <p style={{ marginBottom: 10, color: "#4a5568" }}>
              For each bar <span style={{ color: "#00ff88" }}>i</span>, look forward <span style={{ color: "#f5c518" }}>20</span> bars.
              The first direction to move ≥ <span style={{ color: "#f5c518" }}>1.5 × ATR</span> from entry wins:
            </p>
            <div style={{ paddingLeft: 12 }}>
              <div><Tag color="green">BUY</Tag><span style={{ color: "#4a5568" }}>Up first → label = 0</span></div>
              <div style={{ marginTop: 6 }}><Tag color="red">SELL</Tag><span style={{ color: "#4a5568" }}>Down first → label = 1</span></div>
              <div style={{ marginTop: 6 }}><Tag color="yellow">HOLD</Tag><span style={{ color: "#4a5568" }}>Neither in 20 bars → label = 2</span></div>
            </div>
          </div>
          <div style={{ marginTop: 14 }}>
            <Row label="Horizon"        value="20 bars" hint="forward look-ahead" />
            <Row label="ATR multiplier" value="1.5×"    hint="of 14-bar ATR" />
            <Row label="Label ratio"    value="~33% / 33% / 33%" hint="balanced with class weights" />
          </div>
        </Card>

        {/* Training */}
        <Card title="Training Pipeline" accent="#00d4ff">
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            <Row label="History"       value="2 years H1" hint="per symbol" />
            <Row label="Split"         value="80% train / 20% val" hint="temporal (no shuffle)" />
            <Row label="Optimizer"     value="Adam, lr=0.001" />
            <Row label="Loss"          value="Weighted CrossEntropy" hint="compensates class imbalance" />
            <Row label="Batch size"    value="32" />
            <Row label="Epochs"        value="20 max" hint="early stop: patience=3" />
            <Row label="Thread pool"   value="4 workers" hint="parallel per-symbol training" />
            <Row label="Model file"    value="{SYMBOL}_H1.pt" hint="models/neural/" />
          </div>

          {/* Flow */}
          <div style={{
            marginTop: 14, fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5,
            background: "#0a0a12", border: "1px solid #1c1c28",
            borderRadius: 5, padding: "10px 14px",
            color: "#4a5568", lineHeight: 2,
          }}>
            <div style={{ color: "#00d4ff" }}>Startup:</div>
            <div style={{ paddingLeft: 10 }}>→ check models/neural/ (skip if &lt; 7 days old)</div>
            <div style={{ paddingLeft: 10 }}>→ download H1 history via data_downloader</div>
            <div style={{ paddingLeft: 10 }}>→ auto_label() → build_features() → train LSTM</div>
            <div style={{ paddingLeft: 10 }}>→ save .pt + .json (normalizer params)</div>
            <div style={{ paddingLeft: 10, color: "#00ff88" }}>→ model READY — bot starts trading</div>
          </div>
        </Card>

        {/* Fine-Tuning */}
        <Card title="Continuous Fine-Tuning" accent="#76ff03">
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            <Row label="Replay buffer"   value="200 trades" hint="ring buffer per symbol" />
            <Row label="Trigger"         value="every 20 closures" hint="per symbol" />
            <Row label="Fine-tune epochs" value="5" />
            <Row label="Learning rate"   value="0.0001" hint="10× lower to prevent forgetting" />
            <Row label="Label source"    value="trade PnL" hint="profit → reinforce, loss → HOLD" color="#76ff03" />
          </div>
          <div style={{
            marginTop: 14, fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5,
            background: "#0a0a12", border: "1px solid #1c1c28",
            borderRadius: 5, padding: "10px 14px",
            color: "#4a5568", lineHeight: 2,
          }}>
            <div style={{ color: "#76ff03" }}>Trade closes:</div>
            <div style={{ paddingLeft: 10 }}>learning_agent.review_trade()</div>
            <div style={{ paddingLeft: 10 }}>→ model_manager.record_outcome(label)</div>
            <div style={{ paddingLeft: 10 }}>→ replay_buffer.append((features, label))</div>
            <div style={{ paddingLeft: 10 }}>→ [every 20] background fine-tune thread</div>
          </div>
        </Card>

        {/* Signal Flow */}
        <Card title="Signal Pipeline (Main Loop)" accent="#ff9d00">
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 9.5,
            color: "#4a5568", lineHeight: 2,
            background: "#0a0a12", border: "1px solid #1c1c28",
            borderRadius: 5, padding: "10px 14px",
          }}>
            <div><span style={{ color: "#00d4ff" }}>Market</span> → get H1 candles + context</div>
            <div><span style={{ color: "#f5c518" }}>Analysis</span> → RSI, ATR, trend, regime</div>
            <div><span style={{ color: "#d500f9" }}>Neural</span> → LSTM.predict() → (direction, p%)</div>
            <div style={{ paddingLeft: 14, color: "#2a3a4a" }}>if p &lt; 60% → skip</div>
            <div><span style={{ color: "#ff9d00" }}>Council</span> → ICT + DanialFX + Traditional confirm</div>
            <div style={{ paddingLeft: 14, color: "#2a3a4a" }}>majority vote required to proceed</div>
            <div><span style={{ color: "#ff4455" }}>Risk</span> → position size, daily limits, spread</div>
            <div><span style={{ color: "#f0f0f0" }}>Exec</span> → open MT5 order (SL=2×ATR, TP×3)</div>
            <div><span style={{ color: "#bf7fff" }}>TradeMgr</span> → partial close, breakeven, trailing</div>
          </div>
        </Card>

        {/* Risk Management */}
        <Card title="Risk Management">
          <Row label="Max Risk per Trade" value="2%"         hint="of account equity" />
          <Row label="Max Open Trades"    value="3" />
          <Row label="Max Daily Loss"     value="5%"         hint="of account equity" />
          <Row label="Max Spread"         value="3.0 pips"   hint="rejects trades above this" />
          <Row label="Stop Loss"          value="2 × ATR"    hint="from entry" color="#ff4455" />
          <Row label="TP1"                value="1R"         hint="close 40%" color="#00ff88" />
          <Row label="TP2"                value="2R"         hint="close 30%, trailing starts" color="#00ff88" />
          <Row label="TP3"                value="3R"         hint="close remainder" color="#00ff88" />
          <Row label="Commission"         value="$7 / lot"   hint="factored into breakeven" />
          <Row label="News blackout"      value="15 min"     hint="before & after high-impact" />
        </Card>

        {/* Score System */}
        <Card title="Learning Score System">
          <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1c1c28" }}>
                <th style={{ padding: "4px 6px", textAlign: "left", fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.1em", textTransform: "uppercase" }}>Outcome</th>
                <th style={{ padding: "4px 6px", textAlign: "right", fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.1em", textTransform: "uppercase" }}>Score</th>
                <th style={{ padding: "4px 6px", textAlign: "left", fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.1em", textTransform: "uppercase" }}>Rule</th>
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
                  <td style={{ padding: "5px 6px", color: "#4a5568" }}>{r.rule}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 12, fontSize: 9.5, color: "#2a3a4a", fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.6 }}>
            Bonus: +0.5 each for RSI aligned, trend aligned, volume sufficient, no news event.
            Confidence step: 0.02 per score point · min 10% · max 100%.
          </div>
        </Card>

      </div>
    </div>
  );
}
