"use client";

import { useLearning, useRisk } from "@/lib/swr";
import { fmtPct } from "@/lib/format";

export default function LearningTab() {
  const { data: ld } = useLearning();
  const { data: risk } = useRisk();

  return (
    <div className="flex flex-col gap-3">
      {/* WFO scores */}
      <div className="grid grid-cols-2 gap-3">
        <WFOCard
          label="Overfitting Score"
          value={risk?.wfo_overfitting != null ? fmtPct(risk.wfo_overfitting * 100) : "—"}
          color={risk?.wfo_overfitting != null && risk.wfo_overfitting > 0.7 ? "var(--negative)" : "var(--positive)"}
        />
        <WFOCard
          label="Stability Score"
          value={risk?.wfo_stability != null ? fmtPct(risk.wfo_stability * 100) : "—"}
          color={risk?.wfo_stability != null && risk.wfo_stability < 0.5 ? "var(--warning)" : "var(--positive)"}
        />
      </div>

      {/* Strategy confidences */}
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-3 flex flex-col gap-2">
        <span className="font-mono text-[9px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
          Strategy Confidence
        </span>
        {(ld?.confidences ?? []).length === 0 ? (
          <p className="font-mono text-sm" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", margin: 0 }}>
            No strategy data
          </p>
        ) : (
          ld?.confidences.map((s) => (
            <div key={s.strategy} className="grid gap-2 py-1 border-b border-[var(--border)] last:border-b-0" style={{ gridTemplateColumns: "100px 1fr 48px 32px", alignItems: "center" }}>
              <span className="font-mono text-sm font-bold text-[var(--text-1)]" style={{ fontFamily: "var(--font-mono)" }}>
                {s.strategy}
              </span>
              <div className="h-1 bg-[var(--bg-3)] rounded overflow-hidden">
                <div
                  className="h-full rounded transition-all"
                  style={{
                    width: `${Math.min(s.confidence * 100, 100)}%`,
                    background: s.confidence >= 0.6 ? "var(--positive)" : s.confidence >= 0.4 ? "var(--warning)" : "var(--negative)",
                  }}
                />
              </div>
              <span className="font-mono text-sm font-semibold text-[var(--text-2)] text-right" style={{ fontFamily: "var(--font-mono)" }}>
                {fmtPct(s.confidence * 100)}
              </span>
              <span className="font-mono text-[10px] text-[var(--text-3)] text-right">
                {s.total_trades}t
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function WFOCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-4 flex flex-col gap-1 items-center">
      <span className="font-mono text-[9px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
        {label}
      </span>
      <span className="font-mono text-2xl font-bold" style={{ fontFamily: "var(--font-mono)", color }}>
        {value}
      </span>
    </div>
  );
}
