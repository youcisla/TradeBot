"use client";

import { useEffect, useState, useCallback } from "react";
import useSWR from "swr";
import { Panel } from "@/components/ui/panel";
import { SETTINGS_REGISTRY, FIELD_MAP, type SettingsField } from "@/lib/settings-registry";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

function relTime(iso?: string): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.floor(ms / 60000);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function StatusTab() {
  const { data } = useSWR("/api/status-detail", fetcher, { refreshInterval: 5000 });
  const status = data?.status;
  const perf = data?.performance;
  const faults: { symbol: string; fail_count: number; disabled_until: string }[] = data?.symbolFaults ?? [];
  const sessions: { id: number; started_at: string; ended_at?: string; version: string; exit_reason: string }[] = data?.sessions ?? [];

  const uptimeMs = status?.last_heartbeat
    ? Date.now() - new Date(status.last_heartbeat).getTime() + (status.uptime_seconds ?? 0) * 1000
    : 0;
  const uptime = uptimeMs > 0
    ? uptimeMs < 3600000
      ? `${Math.floor(uptimeMs / 60000)}m`
      : `${Math.floor(uptimeMs / 3600000)}h`
    : "—";

  return (
    <div className="flex flex-col gap-6">
      {/* Bot uptime + broker */}
      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Status</span>
          <span className={`text-lg font-semibold ${status?.broker_connected ? "text-green-400" : "text-red-400"}`}>
            {status?.broker_connected ? "Connected" : "Disconnected"}
          </span>
          <span className="text-xs text-neutral-400">via PU Prime MT5</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Uptime</span>
          <span className="text-lg font-semibold text-white">{uptime}</span>
          <span className="text-xs text-neutral-400">since {status?.started_at ? relTime(status.started_at) : "—"}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Version</span>
          <span className="text-sm font-mono text-white">{status?.version ?? "—"}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Python PID</span>
          <span className="text-sm font-mono text-white">{status?.pid ?? "—"}</span>
        </div>
      </div>

      {/* Risk limits */}
      <div>
        <span className="text-xs text-neutral-500 uppercase tracking-wider">Risk Limits</span>
        <div className="mt-2 flex flex-col gap-2">
          {[
            ["Max Risk / Trade", status?.max_risk_per_trade],
            ["Max Daily Loss", status?.max_daily_loss_pct ? `${(Number(status.max_daily_loss_pct) * 100).toFixed(1)}%` : "—"],
            ["Max Open Trades", status?.max_open_trades],
          ].map(([label, val]) => (
            <div key={String(label)} className="flex justify-between text-sm">
              <span style={{ color: "var(--text-2)" }}>{label}</span>
              <span className="font-mono text-white">{String(val ?? "—")}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Performance snapshot */}
      {perf && (
        <div>
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Live Performance</span>
          <div className="mt-2 grid grid-cols-3 gap-4">
            {[
              ["Win Rate", perf.win_rate != null ? `${(Number(perf.win_rate) * 100).toFixed(1)}%` : "—"],
              ["Expectancy", perf.expectancy != null ? `${(Number(perf.expectancy) * 100).toFixed(2)}%` : "—"],
              ["Sharpe (proxy)", perf.sharpe_proxy ?? "—"],
            ].map(([label, val]) => (
              <div key={String(label)} className="flex flex-col gap-0.5">
                <span className="text-xs text-neutral-500">{label}</span>
                <span className="text-sm font-semibold text-white">{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategy info */}
      {status?.current_strategy && (
        <div>
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Active Strategy</span>
          <div className="mt-2 flex flex-col gap-1.5">
            <div className="flex justify-between text-sm">
              <span style={{ color: "var(--text-2)" }}>Strategy</span>
              <span className="font-mono text-white">{status.current_strategy}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span style={{ color: "var(--text-2)" }}>LLM Gate</span>
              <span className={status.debate_enabled ? "text-green-400" : "text-neutral-500"}>
                {status.debate_enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span style={{ color: "var(--text-2)" }}>Trading Mode</span>
              <span className="font-mono text-white">{status.trading_mode ?? "LIVE"}</span>
            </div>
          </div>
        </div>
      )}

      {/* Crucix status */}
      {status?.crucix_enabled !== undefined && (
        <div>
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Macro Intelligence</span>
          <div className="mt-2 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${status.crucix_enabled ? "bg-green-400" : "bg-neutral-600"}`} />
            <span className="text-sm" style={{ color: "var(--text-1)" }}>
              Crucix {status.crucix_enabled ? "Active" : "Disabled"}
            </span>
            {status.crucix_connected !== undefined && (
              <span className="text-xs text-neutral-500">
                · {status.crucix_connected ? "connected" : "no connection"}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Faulted symbols */}
      {faults.length > 0 && (
        <div>
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Faulted Symbols ({faults.length})</span>
          <div className="mt-2 flex flex-col gap-1">
            {faults.slice(0, 5).map((f) => (
              <div key={f.symbol} className="flex justify-between text-sm">
                <span className="font-mono text-red-400">{f.symbol}</span>
                <span className="text-neutral-500">{f.fail_count} fails · re-enable {relTime(f.disabled_until)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent sessions */}
      {sessions.length > 0 && (
        <div>
          <span className="text-xs text-neutral-500 uppercase tracking-wider">Recent Sessions</span>
          <div className="mt-2 flex flex-col gap-2">
            {sessions.map((s) => (
              <div key={s.id} className="flex justify-between text-sm">
                <div className="flex flex-col">
                  <span className="font-mono text-white">v{s.version ?? "?"}</span>
                  <span className="text-xs text-neutral-500">{s.started_at ? relTime(s.started_at) : "—"}</span>
                </div>
                <div className="flex flex-col items-end">
                  <span className={`text-xs ${s.exit_reason === "normal" ? "text-green-400" : "text-yellow-400"}`}>
                    {s.exit_reason ?? "—"}
                  </span>
                  {s.ended_at && <span className="text-xs text-neutral-500">ended {relTime(s.ended_at)}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Single field row ──────────────────────────────────────────────────────────

function FieldRow({
  field,
  value,
  hasOverride,
  onSave,
  onClear,
}: {
  field: SettingsField;
  value: unknown;
  hasOverride: boolean;
  onSave: (key: string, value: string) => void;
  onClear: (key: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value ?? ""));

  useEffect(() => { setDraft(String(value ?? "")); }, [value]);

  if (!editing) {
    return (
      <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-2">
          <span className="text-sm" style={{ color: "var(--text-2)" }}>{field.label}</span>
          {hasOverride && (
            <span className="w-2 h-2 rounded-full bg-green-400 shrink-0" title="DB override active" />
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono" style={{ color: "var(--text-1)" }}>
            {field.type === "bool" ? (value ? "true" : "false") : String(value ?? "—")}
          </span>
          <button
            onClick={() => setEditing(true)}
            className="text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-neutral-400 hover:text-white transition-colors"
          >
            Edit
          </button>
          {hasOverride && (
            <button
              onClick={() => onClear(field.key)}
              className="text-xs px-2 py-1 rounded bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors"
              title="Remove override"
            >
              Clear
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between py-2 border-b" style={{ borderColor: "var(--border)" }}>
      <span className="text-sm" style={{ color: "var(--text-2)" }}>{field.label}</span>
      <div className="flex items-center gap-2">
        {field.type === "bool" ? (
          <button
            onClick={() => setDraft(draft === "true" ? "false" : "true")}
            className={`text-sm px-3 py-1 rounded font-mono transition-colors ${
              draft === "true" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
            }`}
          >
            {draft}
          </button>
        ) : field.type === "str" && field.options ? (
          <select
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="px-2 py-1 bg-white/5 border border-white/10 rounded text-sm text-white"
          >
            {field.options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        ) : (
          <input
            type="number"
            value={draft}
            min={field.min}
            max={field.max}
            step={field.step ?? 1}
            onChange={(e) => setDraft(e.target.value)}
            className="px-2 py-1 w-28 bg-white/5 border border-white/10 rounded text-sm text-white font-mono"
          />
        )}
        <button
          onClick={() => { onSave(field.key, draft); setEditing(false); }}
          className="text-xs px-2 py-1 rounded bg-green-500/20 hover:bg-green-500/30 text-green-400 transition-colors"
        >
          Save
        </button>
        <button
          onClick={() => { setDraft(String(value ?? "")); setEditing(false); }}
          className="text-xs px-2 py-1 rounded bg-white/5 hover:bg-white/10 text-neutral-400 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Tab content ──────────────────────────────────────────────────────────────

function SettingsTab({
  group,
  overrides,
  defaultValues,
  onSave,
  onClear,
}: {
  group: (typeof SETTINGS_REGISTRY)[number];
  overrides: Set<string>;
  defaultValues: Record<string, string>;
  onSave: (key: string, value: string) => void;
  onClear: (key: string) => void;
}) {
  const [saving, setSaving] = useState<Record<string, boolean>>({});

  const handleSave = useCallback(
    async (key: string, value: string) => {
      setSaving((p) => ({ ...p, [key]: true }));
      await onSave(key, value);
      setSaving((p) => ({ ...p, [key]: false }));
    },
    [onSave]
  );

  return (
    <div className="flex flex-col gap-1">
      {group.fields.map((field) => (
        <FieldRow
          key={field.key}
          field={field}
          value={defaultValues[field.key] ?? ""}
          hasOverride={overrides.has(field.key)}
          onSave={handleSave}
          onClear={onClear}
        />
      ))}
    </div>
  );
}

// ── Main settings page ───────────────────────────────────────────────────────

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("status");

  const { data: overridesData, mutate: mutateOverrides } = useSWR(
    "/api/settings/overrides", fetcher, { refreshInterval: 30000 }
  );
  const overrideKeys = new Set<string>((overridesData?.overrides ?? []).map((r: { key: string }) => r.key));
  const overridesMap: Record<string, string> = Object.fromEntries(
    (overridesData?.overrides ?? []).map((r: { key: string; value: string }) => [r.key, r.value])
  );

  const { data: configData } = useSWR("/api/config", fetcher);
  const configValues: Record<string, string> = Object.fromEntries(
    (configData?.groups ?? []).flatMap((g: { items: { key: string; value: string }[] }) =>
      g.items.map((i: { key: string; value: string }) => [i.key, i.value])
    )
  );

  const snakeToDot = (s: string) =>
    s.replace(/([A-Z])/g, (c) => c.toLowerCase()).replace(/_/g, ".");

  const effectiveValues: Record<string, string> = { ...configValues };
  for (const [key, val] of Object.entries(overridesMap)) {
    effectiveValues[snakeToDot(key)] = val;
  }

  const handleSave = useCallback(
    async (key: string, value: string) => {
      await fetch("/api/settings/overrides", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
      });
      mutateOverrides();
    },
    [mutateOverrides]
  );

  const handleClear = useCallback(
    async (key: string) => {
      await fetch("/api/settings/overrides", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      mutateOverrides();
    },
    [mutateOverrides]
  );

  const activeGroup = SETTINGS_REGISTRY.find((g) => g.id === activeTab) ?? SETTINGS_REGISTRY[0];

  return (
    <div className="flex flex-col gap-4">

      {/* Tab bar */}
      <div className="flex gap-1 flex-wrap border-b" style={{ borderColor: "var(--border)" }}>
        {SETTINGS_REGISTRY.map((g) => (
          <button
            key={g.id}
            onClick={() => setActiveTab(g.id)}
            className="px-4 py-2 text-sm transition-colors"
            style={{
              borderBottom: "2px solid",
              borderColor: activeTab === g.id ? "var(--accent)" : "transparent",
              color: activeTab === g.id ? "var(--text-1)" : "var(--text-3)",
            }}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* Active tab panel */}
      <Panel title={activeGroup.label}>
        {activeTab === "status" ? (
          <StatusTab />
        ) : (
          <SettingsTab
            group={activeGroup}
            overrides={overrideKeys}
            defaultValues={effectiveValues}
            onSave={handleSave}
            onClear={handleClear}
          />
        )}
      </Panel>

      {/* Override info */}
      <div
        className="rounded-lg p-4 text-sm"
        style={{
          background: "rgba(48,209,88,0.06)",
          border: "1px solid rgba(48,209,88,0.20)",
          color: "var(--text-2)",
        }}
      >
        <span className="text-green-400 font-semibold">Runtime overrides</span>
        {" "}— Changes are saved to the <code className="font-mono text-xs">bot_settings_overrides</code>{" "}
        table and applied to the live Python bot on the next command poll. Overrides persist across restarts.
        A <span className="inline-block w-2 h-2 rounded-full bg-green-400 align-middle mr-1" />green dot
        indicates an active override.
      </div>
    </div>
  );
}
