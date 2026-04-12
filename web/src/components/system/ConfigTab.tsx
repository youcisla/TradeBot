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
    return <div style={styles.loading}>Loading…</div>;
  }

  if (!data?.groups?.length) {
    return (
      <div style={styles.empty}>
        <span style={styles.emptyIcon}>⚙</span>
        <p>No config data available.</p>
      </div>
    );
  }

  return (
    <div style={styles.wrapper}>
      {data.groups.map((group) => (
        <div key={group.label} style={styles.group}>
          <div style={styles.groupHeader}>{group.label}</div>
          {group.items.map((item) => (
            <div key={item.key} style={styles.row}>
              <span style={styles.key}>{item.key}</span>
              <span style={styles.value}>{item.value}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(360, 1fr))",
    gap: "var(--space-4)",
  },
  group: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    overflow: "hidden",
  },
  groupHeader: {
    fontFamily: "var(--font-ui)",
    fontSize: 10,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    padding: "var(--space-2) var(--space-4)",
    background: "var(--bg-3)",
    borderBottom: "1px solid var(--border)",
  },
  row: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "7px var(--space-4)",
    borderBottom: "1px solid var(--border)",
    gap: "var(--space-4)",
  },
  key: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-2)",
    flexShrink: 0,
  },
  value: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-1)",
    textAlign: "right",
    wordBreak: "break-all",
  },
  loading: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    textAlign: "center",
    padding: "var(--space-5)",
  },
  empty: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-6)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "var(--space-2)",
    textAlign: "center",
  },
  emptyIcon: {
    fontSize: 28,
    opacity: 0.3,
  },
};
