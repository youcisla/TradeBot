"use client";

import { useEffect, useMemo, useState } from "react";

type ToolEvent = {
  id: number;
  agent: string;
  level: string;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
};

type ToolCycle = {
  id: number;
  level: string;
  message: string;
  data: {
    loop?: number;
    failed_tools?: string[];
    executed_tools?: string[];
    emergency_mode?: boolean;
    doctor_warning_count?: number;
  } | null;
  created_at: string;
};

function cardStyle(accent: string): React.CSSProperties {
  return {
    borderRadius: 14,
    border: `1px solid ${accent}`,
    background: "#111214",
    padding: 14,
  };
}

function buttonStyle(bg: string): React.CSSProperties {
  return {
    border: "none",
    borderRadius: 10,
    padding: "10px 14px",
    background: bg,
    color: "#fff",
    fontWeight: 700,
    cursor: "pointer",
    fontSize: 13,
  };
}

export default function ToolsPage() {
  const [cycles, setCycles] = useState<ToolCycle[]>([]);
  const [events, setEvents] = useState<ToolEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const fetchData = async () => {
      try {
        const res = await fetch("/api/tools?cycleLimit=80&eventLimit=250");
        const data = await res.json();
        if (!active) return;
        setCycles(Array.isArray(data.cycles) ? data.cycles : []);
        setEvents(Array.isArray(data.events) ? data.events : []);
        setError(null);
      } catch (e) {
        if (!active) return;
        setError((e as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchData();
    const id = setInterval(fetchData, 5000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const summary = useMemo(() => {
    const latest = cycles[0];
    const warningCount = Number(latest?.data?.doctor_warning_count ?? 0);
    const emergency = Boolean(latest?.data?.emergency_mode ?? false);
    const failedCount = Array.isArray(latest?.data?.failed_tools)
      ? latest!.data!.failed_tools!.length
      : 0;
    return { warningCount, emergency, failedCount };
  }, [cycles]);

  const sendToolCommand = async (action: "list" | "run", tool?: string, payload?: Record<string, unknown>) => {
    setBusy(tool ?? action);
    try {
      const body = {
        command: "tool",
        payload: {
          action,
          ...(tool ? { tool } : {}),
          ...(payload ? payload : {}),
        },
      };
      const res = await fetch("/api/commands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(String(err.error ?? `Request failed (${res.status})`));
      }
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div style={{ color: "#fff", fontFamily: "-apple-system, system-ui, sans-serif" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 28, letterSpacing: "-0.02em" }}>Tool System</h1>
        <div style={{ fontSize: 12, color: "#9aa0a6" }}>Live: refresh every 5s</div>
      </div>

      <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
        <div style={cardStyle("#2a4f90")}>Warnings: <strong>{summary.warningCount}</strong></div>
        <div style={cardStyle(summary.emergency ? "#7a2f2f" : "#2f6b41")}>Emergency: <strong>{summary.emergency ? "ON" : "OFF"}</strong></div>
        <div style={cardStyle(summary.failedCount > 0 ? "#7a532f" : "#2f6b41")}>Failed tools (latest): <strong>{summary.failedCount}</strong></div>
      </div>

      <div style={{ marginTop: 14, display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button style={buttonStyle("#2f6b41")} disabled={Boolean(busy)} onClick={() => sendToolCommand("run", "strategy_reweight_recent_regime")}>
          {busy === "strategy_reweight_recent_regime" ? "Running..." : "Run Reweight"}
        </button>
        <button style={buttonStyle("#7a532f")} disabled={Boolean(busy)} onClick={() => sendToolCommand("run", "emergency_mode_activate", { reason: "dashboard_manual" })}>
          {busy === "emergency_mode_activate" ? "Running..." : "Force Emergency"}
        </button>
        <button style={buttonStyle("#345a9c")} disabled={Boolean(busy)} onClick={() => sendToolCommand("run", "emergency_mode_deactivate", { reason: "dashboard_manual" })}>
          {busy === "emergency_mode_deactivate" ? "Running..." : "Clear Emergency"}
        </button>
        <button style={buttonStyle("#3b3f45")} disabled={Boolean(busy)} onClick={() => sendToolCommand("list")}>
          {busy === "list" ? "Running..." : "List Tools"}
        </button>
      </div>

      {error && (
        <div style={{ marginTop: 12, borderRadius: 10, border: "1px solid #7a2f2f", background: "#261415", padding: 10, color: "#ffb4b4" }}>
          {error}
        </div>
      )}

      <div style={{ marginTop: 16, display: "grid", gap: 14, gridTemplateColumns: "minmax(320px, 1.2fr) minmax(320px, 1fr)" }}>
        <section style={cardStyle("#25303d")}>
          <h2 style={{ margin: "0 0 10px", fontSize: 18 }}>Cycle History</h2>
          {loading ? (
            <div style={{ color: "#9aa0a6" }}>Loading...</div>
          ) : cycles.length === 0 ? (
            <div style={{ color: "#9aa0a6" }}>No tool cycles yet.</div>
          ) : (
            <div style={{ maxHeight: 520, overflowY: "auto", display: "grid", gap: 8 }}>
              {cycles.map((c) => (
                <div key={c.id} style={{ border: "1px solid #2c2f34", borderRadius: 10, padding: 10, background: "#0f1012" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, fontSize: 12, color: "#9aa0a6" }}>
                    <span>#{c.data?.loop ?? "-"}</span>
                    <span>{new Date(c.created_at).toLocaleString()}</span>
                  </div>
                  <div style={{ marginTop: 6, fontSize: 13 }}>
                    executed: {(c.data?.executed_tools ?? []).join(", ") || "-"}
                  </div>
                  <div style={{ marginTop: 4, fontSize: 13, color: (c.data?.failed_tools?.length ?? 0) > 0 ? "#ffb4b4" : "#9be7b5" }}>
                    failed: {(c.data?.failed_tools ?? []).join(", ") || "none"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section style={cardStyle("#25303d")}>
          <h2 style={{ margin: "0 0 10px", fontSize: 18 }}>Tool Outcomes</h2>
          {loading ? (
            <div style={{ color: "#9aa0a6" }}>Loading...</div>
          ) : events.length === 0 ? (
            <div style={{ color: "#9aa0a6" }}>No tool events yet.</div>
          ) : (
            <div style={{ maxHeight: 520, overflowY: "auto", display: "grid", gap: 8 }}>
              {events.map((e) => (
                <div key={e.id} style={{ border: "1px solid #2c2f34", borderRadius: 10, padding: 10, background: "#0f1012" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, fontSize: 12, color: "#9aa0a6" }}>
                    <span>{String(e.level).toUpperCase()}</span>
                    <span>{new Date(e.created_at).toLocaleTimeString()}</span>
                  </div>
                  <div style={{ marginTop: 6, fontSize: 13 }}>{e.message}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
