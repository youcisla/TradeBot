"use client";

import { useEffect, useState } from "react";

interface ConfigItem {
  key: string;
  value: string;
  description?: string;
}

interface ConfigGroup {
  label: string;
  items: ConfigItem[];
}

interface ConfigData {
  groups: ConfigGroup[];
}

export default function ConfigTab() {
  const [data, setData] = useState<ConfigData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/config")
      .then((r) => r.json())
      .then((d: ConfigData) => { setData(d); setLoading(false); })
      .catch(() => { setLoading(false); });
  }, []);

  if (loading) {
    return (
      <p className="font-mono text-sm text-center py-5" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
        Loading…
      </p>
    );
  }

  if (!data?.groups?.length) {
    return (
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-6 py-6 flex flex-col items-center gap-2 text-center">
        <span className="text-2xl opacity-30">⚙</span>
        <p className="font-mono text-sm" style={{ color: "var(--text-3)" }}>
          No config data available.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))" }}>
      {data.groups.map((group) => (
        <div key={group.label} className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md overflow-hidden">
          <div className="px-4 py-2 bg-[var(--bg-3)] border-b border-[var(--border)]">
            <span className="text-[10px] font-bold uppercase" style={{ fontFamily: "var(--font-ui)", color: "var(--text-3)", letterSpacing: "0.08em" }}>
              {group.label}
            </span>
          </div>
          {group.items.map((item) => (
            <div key={item.key} className="flex justify-between items-center px-4 py-[7px] border-b border-[var(--border)] gap-4">
              <span className="font-mono text-sm font-semibold text-[var(--text-2)] flex-shrink-0" style={{ fontFamily: "var(--font-mono)" }}>
                {item.key}
              </span>
              <span className="font-mono text-sm text-[var(--text-1)] text-right break-all" style={{ fontFamily: "var(--font-mono)" }}>
                {item.value}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
