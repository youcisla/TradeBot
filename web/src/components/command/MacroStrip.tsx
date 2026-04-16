"use client";

import { useAppShell } from "@/components/AppShell";
import { cn } from "@/lib/utils";

const SESSION_COLORS: Record<string, string> = {
  london:  "var(--cyan)",
  newyork: "var(--orange)",
  overlap: "var(--green)",
  asian:   "var(--purple)",
  closed:  "var(--text-3)",
};

const REGIME_COLORS: Record<string, string> = {
  trending:  "var(--positive)",
  ranging:   "var(--warning)",
  volatile:  "var(--negative)",
  quiet:     "var(--text-3)",
};

export default function MacroStrip() {
  const { intelligence, status } = useAppShell();

  const session    = intelligence?.sessionLabel ?? "—";
  const regime    = intelligence?.marketRegime ?? "—";
  const vix       = intelligence?.vix;
  const spread     = intelligence?.spreadCondition ?? "—";
  const loopCount  = status?.loop_count ?? 0;

  const sessionColor  = SESSION_COLORS[session.toLowerCase()]  ?? "var(--text-3)";
  const regimeColor   = REGIME_COLORS[regime.toLowerCase()]     ?? "var(--text-3)";
  const vixColor      = vix !== undefined
    ? (vix > 30 ? "var(--negative)" : vix > 20 ? "var(--warning)" : "var(--positive)")
    : "var(--text-3)";

  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-2 flex items-center overflow-x-auto">
      <MacroPill label="Session" value={session} color={sessionColor} />
      <StripDivider />
      <MacroPill label="Regime"  value={regime}  color={regimeColor} />
      <StripDivider />
      <MacroPill label="VIX"     value={vix !== undefined ? vix.toFixed(1) : "—"} color={vixColor} />
      <StripDivider />
      <MacroPill label="Spread"  value={spread}  color="var(--text-2)" />
      <StripDivider />
      <MacroPill label="Loops"   value={String(loopCount)} color="var(--text-3)" />
    </div>
  );
}

function MacroPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 px-3 flex-shrink-0">
      <span
        className="font-mono text-[9px] font-bold uppercase"
        style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.08em" }}
      >
        {label}
      </span>
      <span className="font-mono text-sm font-bold" style={{ fontFamily: "var(--font-mono)", color }}>
        {value}
      </span>
    </div>
  );
}

function StripDivider() {
  return <span className="w-px h-7 flex-shrink-0 mx-0.5" style={{ background: "var(--border)" }} />;
}
