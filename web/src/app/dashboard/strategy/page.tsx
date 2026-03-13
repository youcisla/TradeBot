"use client";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-terminal-border rounded bg-terminal-surface p-5">
      <div className="text-matrix text-xs font-bold uppercase tracking-widest mb-3 border-b border-terminal-border pb-2">
        {title}
      </div>
      {children}
    </div>
  );
}

function Row({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex justify-between items-start py-1 border-b border-terminal-border/20 last:border-0">
      <span className="text-matrix-dim text-[11px]">{label}</span>
      <span className="text-right">
        <span className="text-matrix text-[11px] font-bold">{value}</span>
        {hint && <span className="text-matrix-dim text-[9px] block">{hint}</span>}
      </span>
    </div>
  );
}

const TAG = "px-2 py-0.5 rounded text-[9px] font-bold uppercase";

export default function StrategyPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-matrix text-lg font-bold">Strategy & Risk Model</h1>
      <p className="text-matrix-dim text-xs leading-relaxed">
        This page documents the trading logic, risk rules, and learning feedback loop that the bot uses in production.
        All parameters are configurable via environment variables.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current Strategy */}
        <Card title="Active Strategy — SMA Crossover">
          <div className="space-y-2 text-[11px] text-matrix-dim leading-relaxed">
            <p>
              <span className={`${TAG} bg-green-900/40 text-green-400 mr-2`}>BUY</span>
              When the <span className="text-matrix font-bold">SMA(10)</span> crosses <strong>above</strong> the{" "}
              <span className="text-matrix font-bold">SMA(50)</span>.
            </p>
            <p>
              <span className={`${TAG} bg-red-900/40 text-red-400 mr-2`}>SELL</span>
              When the <span className="text-matrix font-bold">SMA(10)</span> crosses <strong>below</strong> the{" "}
              <span className="text-matrix font-bold">SMA(50)</span>.
            </p>
            <p className="pt-2 border-t border-terminal-border/30">
              <strong className="text-matrix">Stop Loss</strong>: 1× ATR(14) from entry price
            </p>
            <p>
              <strong className="text-matrix">Take Profits</strong>: R:R ratio 1:1, 1:2, 1:3 (TP1 = 1× risk, TP2 = 2× risk, TP3 = 3× risk)
            </p>
          </div>
        </Card>

        {/* Indicators */}
        <Card title="Technical Indicators">
          <table className="w-full text-[11px]">
            <thead className="text-matrix-dim uppercase border-b border-terminal-border text-[9px]">
              <tr>
                <th className="text-left py-1">Indicator</th>
                <th className="text-right py-1">Period</th>
                <th className="text-left py-1 pl-3">Usage</th>
              </tr>
            </thead>
            <tbody className="text-matrix-dim">
              <tr className="border-b border-terminal-border/20">
                <td className="py-1 text-matrix font-bold">SMA Fast</td>
                <td className="py-1 text-right">10</td>
                <td className="py-1 pl-3">Crossover signals</td>
              </tr>
              <tr className="border-b border-terminal-border/20">
                <td className="py-1 text-matrix font-bold">SMA Slow</td>
                <td className="py-1 text-right">50</td>
                <td className="py-1 pl-3">Crossover signals + trend</td>
              </tr>
              <tr className="border-b border-terminal-border/20">
                <td className="py-1 text-matrix font-bold">RSI</td>
                <td className="py-1 text-right">14</td>
                <td className="py-1 pl-3">Filter — direction alignment</td>
              </tr>
              <tr>
                <td className="py-1 text-matrix font-bold">ATR</td>
                <td className="py-1 text-right">14</td>
                <td className="py-1 pl-3">SL distance + regime detection</td>
              </tr>
            </tbody>
          </table>
        </Card>

        {/* Risk Management */}
        <Card title="Risk Management">
          <div className="space-y-1">
            <Row label="Max Risk per Trade" value="2%" hint="of account equity" />
            <Row label="Max Open Trades" value="3" />
            <Row label="Max Daily Loss" value="5%" hint="of account equity" />
            <Row label="Max Spread" value="3.0 pips" hint="rejects trades above this" />
            <Row label="Drawdown Cooldown" value="24 hours" hint="pauses after max daily loss" />
            <Row label="Min Lot Size" value="0.01" />
            <Row label="Commission" value="$7 / lot" hint="factored into breakeven" />
            <Row label="News Blackout" value="15 min" hint="before & after high-impact events" />
          </div>
        </Card>

        {/* Trade Execution */}
        <Card title="Trade Execution Model">
          <div className="space-y-1">
            <Row label="TP1 Close" value="40%" hint="of position" />
            <Row label="TP2 Close" value="30%" hint="of position" />
            <Row label="TP3 Close" value="30%" hint="remainder" />
            <Row label="Trailing Stop" value="20 pips" hint="activates after TP2" />
            <Row label="Breakeven SL" value="After TP1" hint="entry + spread + commission" />
          </div>
          <div className="mt-3 p-3 bg-terminal rounded border border-terminal-border/40 text-[10px] text-matrix-dim font-mono leading-relaxed">
            <div>Signal approved → Execution Agent opens</div>
            <div className="pl-4">→ TP1 hit → close 40%, SL → breakeven</div>
            <div className="pl-4">→ TP2 hit → close 30%, trailing SL starts</div>
            <div className="pl-4">→ TP3 hit → close 30%, trade closed</div>
            <div className="pl-4">→ SL hit → close all remaining</div>
          </div>
        </Card>

        {/* Market Regime */}
        <Card title="Market Regime Detection">
          <div className="space-y-2 text-[11px] text-matrix-dim">
            <p>
              <span className={`${TAG} bg-yellow-900/40 text-yellow-400 mr-2`}>VOLATILE</span>
              14-bar price range &gt; 3× ATR
            </p>
            <p>
              <span className={`${TAG} bg-blue-900/40 text-blue-400 mr-2`}>TRENDING</span>
              |SMA(10) − SMA(50)| &gt; ATR
            </p>
            <p>
              <span className={`${TAG} bg-purple-900/40 text-purple-400 mr-2`}>RANGING</span>
              Neither volatile nor trending
            </p>
            <p className="pt-2 text-[10px] border-t border-terminal-border/30">
              Regime is stored in the entry snapshot and used by the learning system for post-trade scoring.
            </p>
          </div>
        </Card>

        {/* Learning System */}
        <Card title="Learning & Feedback Loop">
          <div className="space-y-2 text-[11px]">
            <p className="text-matrix-dim">
              After each closed trade, the bot assigns an objective score based on the entry snapshot:
            </p>
            <table className="w-full text-[10px]">
              <thead className="text-matrix-dim uppercase border-b border-terminal-border text-[9px]">
                <tr>
                  <th className="text-left py-1">Outcome</th>
                  <th className="text-right py-1">Score</th>
                  <th className="text-left py-1 pl-3">Rule</th>
                </tr>
              </thead>
              <tbody className="text-matrix-dim">
                <tr className="border-b border-terminal-border/20">
                  <td className="py-1 text-green-400">Clean Win</td>
                  <td className="py-1 text-right text-green-400 font-bold">+3</td>
                  <td className="py-1 pl-3">Profit + all filters aligned</td>
                </tr>
                <tr className="border-b border-terminal-border/20">
                  <td className="py-1 text-yellow-400">Messy Win</td>
                  <td className="py-1 text-right text-yellow-400 font-bold">+1</td>
                  <td className="py-1 pl-3">Profit but filter marginal</td>
                </tr>
                <tr className="border-b border-terminal-border/20">
                  <td className="py-1 text-orange-400">Normal Loss</td>
                  <td className="py-1 text-right text-orange-400 font-bold">−2</td>
                  <td className="py-1 pl-3">SL hit, entry was valid</td>
                </tr>
                <tr className="border-b border-terminal-border/20">
                  <td className="py-1 text-red-400">Bad Loss</td>
                  <td className="py-1 text-right text-red-400 font-bold">−5</td>
                  <td className="py-1 pl-3">SL hit + filter violation</td>
                </tr>
                <tr>
                  <td className="py-1 text-red-600">Rule Violation</td>
                  <td className="py-1 text-right text-red-600 font-bold">−10</td>
                  <td className="py-1 pl-3">Forced past a filter</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Card>

        {/* Confidence */}
        <Card title="Confidence Levels">
          <div className="space-y-1">
            <Row label="Default (new strategy)" value="0.50" />
            <Row label="Full confidence (no throttling)" value="≥ 0.70" />
            <Row label="Reduced (smaller lots)" value="0.30 – 0.50" />
            <Row label="Disabled (no trading)" value="&lt; 0.20" />
          </div>
          <p className="text-matrix-dim text-[10px] mt-3">
            Confidence adjusts automatically per strategy based on cumulative trade scores.
            Strategies below the disable threshold stop receiving signals until manually re-enabled.
          </p>
        </Card>

        {/* Data Sources */}
        <Card title="Data Sources & Filters">
          <div className="space-y-2 text-[11px] text-matrix-dim">
            <p><strong className="text-matrix">Market Data:</strong> MetaTrader 5 (real-time ticks + candles)</p>
            <p><strong className="text-matrix">News Calendar:</strong> ForexFactory / economic API (high-impact events)</p>
            <p><strong className="text-matrix">Session Detection:</strong> London, New York, Asian, Overlap — auto-tagged</p>
            <p className="pt-2 border-t border-terminal-border/30">
              <strong className="text-matrix">Pre-trade filters:</strong> spread check, news blackout, spike detection,
              stale-quote guard, max open trades, daily loss limit, drawdown cooldown.
            </p>
          </div>
        </Card>

        {/* Known Limitations */}
        <Card title="Known Limitations">
          <ul className="list-disc list-inside space-y-1 text-[11px] text-matrix-dim">
            <li>Single strategy active (SMA Crossover). More planned.</li>
            <li>MT5 partial close uses counter-order, not native partial close API.</li>
            <li>News data depends on external API availability.</li>
            <li>No multi-timeframe confirmation yet (uses single M15 by default).</li>
            <li>Learning system rule-based only — no ML/AI model retraining.</li>
            <li>Demo mode enabled during Phase 1 — no real money at risk.</li>
          </ul>
        </Card>
      </div>
    </div>
  );
}
