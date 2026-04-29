"use client";

import { useBotStatus } from "@/lib/swr";
import { stateHue } from "@/lib/handoff";
import { Sdot } from "@/components/ui/chip";

const PIPELINE_AGENTS = [
  { id: "crucix",       label: "Crucix",      state: "IDLE" },
  { id: "market",       label: "Market",       state: "RUNNING" },
  { id: "analysis",     label: "Analysis",     state: "RUNNING" },
  { id: "strategy",     label: "Strategy",     state: "RUNNING" },
  { id: "neural",       label: "Neural",       state: "IDLE" },
  { id: "council",      label: "Council",      state: "RUNNING" },
  { id: "risk",         label: "Risk",         state: "RUNNING" },
  { id: "execution",    label: "Execution",    state: "RUNNING" },
  { id: "trade_manager",label: "Trade Mgr",   state: "RUNNING" },
];

interface PipelineRibbonProps {
  compact?: boolean;
}

export function PipelineRibbon({ compact = false }: PipelineRibbonProps) {
  const { data: status } = useBotStatus();
  const loopMs = (status as unknown as Record<string, unknown>)?.last_scan_latency_ms as number | undefined;

  return (
    <div className="ribbon">
      <span className="label" style={{ marginRight: 12 }}>
        Pipeline
      </span>
      {PIPELINE_AGENTS.map((a, i) => {
        const tone = stateHue(a.state);
        return (
          <span key={a.id} style={{ display: "contents" }}>
            <div
              className={`ribbon-node ${a.state.toLowerCase()}`}
              title={a.state}
            >
              <Sdot tone={tone} live={a.state === "RUNNING"} />
              <span className="rl">{a.label}</span>
              {!compact && (
                <span className="rs mono">
                  —
                </span>
              )}
            </div>
            {i < PIPELINE_AGENTS.length - 1 && (
              <span className="ribbon-sep">›</span>
            )}
          </span>
        );
      })}
      <div style={{ flex: 1 }} />
      <span className="label">Iter</span>
      <span
        className="mono tnum dim"
        style={{ marginLeft: 6 }}
      >
        #{status?.loop_count?.toLocaleString() ?? "—"}
      </span>
      <span
        className="mono tnum dim"
        style={{ marginLeft: 14 }}
      >
        {loopMs != null ? `${Math.round(loopMs)}ms` : "—"}
      </span>
    </div>
  );
}
