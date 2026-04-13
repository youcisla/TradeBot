"use client";

import { useAppShell } from "@/components/AppShell";

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

  const session  = intelligence?.sessionLabel ?? "—";
  const regime   = intelligence?.marketRegime ?? "—";
  const vix      = intelligence?.vix;
  const spread   = intelligence?.spreadCondition ?? "—";
  const loopCount = status?.loop_count ?? 0;

  return (
    <div style={styles.wrapper}>
      <MacroPill label="Session" value={session} color={SESSION_COLORS[session.toLowerCase()] ?? "var(--text-3)"} />
      <Divider />
      <MacroPill label="Regime" value={regime} color={REGIME_COLORS[regime.toLowerCase()] ?? "var(--text-3)"} />
      <Divider />
      <MacroPill
        label="VIX"
        value={vix !== undefined ? vix.toFixed(1) : "—"}
        color={vix !== undefined ? (vix > 30 ? "var(--red)" : vix > 20 ? "var(--orange)" : "var(--green)") : "var(--text-3)"}
      />
      <Divider />
      <MacroPill label="Spread" value={spread} color="var(--text-2)" />
      <Divider />
      <MacroPill label="Loops" value={String(loopCount)} color="var(--text-3)" />
    </div>
  );
}

function MacroPill({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div style={styles.pill}>
      <span style={styles.pillLabel}>{label}</span>
      <span style={{ ...styles.pillValue, color }}>{value}</span>
    </div>
  );
}

function Divider() {
  return <div style={styles.divider} />;
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-2) var(--space-4)",
    display: "flex",
    alignItems: "center",
    gap: 0,
    overflowX: "auto",
  },
  pill: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 1,
    padding: "0 var(--space-3)",
    flexShrink: 0,
  },
  pillLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  pillValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 12,
    fontWeight: 700,
  },
  divider: {
    width: 1,
    height: 28,
    background: "var(--border)",
    flexShrink: 0,
    margin: "0 2px",
  },
};
