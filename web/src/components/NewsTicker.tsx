"use client";

import { useCallback, useEffect, useState } from "react";

interface NewsItem {
  title: string;
  time: string;
  source?: string;
}

interface NewsTickerProps {
  symbol?: string;
}

export default function NewsTicker({ symbol }: NewsTickerProps) {
  const [expanded, setExpanded] = useState(false);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [collapsed, setCollapsed] = useState(true);

  const fetchNews = useCallback(async () => {
    // TODO: wire to actual news API (MT5 news or macro aggregator)
    // For now, populate from a placeholder or external source
    try {
      const r = await fetch("/api/candles/news", { signal: AbortSignal.timeout(3000) });
      if (r.ok) {
        const data = await r.json();
        if (Array.isArray(data)) setNews(data);
      }
    } catch {
      // silent — news is non-critical
    }
  }, []);

  useEffect(() => {
    fetchNews();
    const id = setInterval(fetchNews, 60_000);
    return () => clearInterval(id);
  }, [fetchNews]);

  if (collapsed) {
    return (
      <div style={styles.bar}>
        <button onClick={() => setCollapsed(false)} style={styles.expandBtn}>
          📰 News ▸
        </button>
      </div>
    );
  }

  return (
    <div style={styles.bar}>
      <div style={styles.header}>
        <span style={styles.label}>News</span>
        <div style={styles.headerRight}>
          {news.length > 0 && (
            <span style={styles.badge}>{news.length}</span>
          )}
          <button onClick={() => setCollapsed(true)} style={styles.collapseBtn}>
            ▾
          </button>
        </div>
      </div>

      {expanded && (
        <div style={styles.list}>
          {news.length === 0 ? (
            <span style={styles.empty}>No news available</span>
          ) : (
            news.slice(0, 10).map((item, i) => (
              <div key={i} style={styles.item}>
                <span style={styles.itemTime}>{item.time}</span>
                <span style={styles.itemTitle}>{item.title}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    background: "#F5F5F7",
    borderBottom: "1px solid #E5E7EB",
    padding: "0 14px",
  },
  expandBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#6B7280",
    padding: "6px 0",
    width: "100%",
    textAlign: "left",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "6px 0",
  },
  label: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  badge: {
    background: "#2563EB",
    color: "#FFFFFF",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    padding: "1px 5px",
    borderRadius: 8,
  },
  collapseBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: 10,
    color: "#9CA3AF",
  },
  list: {
    paddingBottom: 8,
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  item: {
    display: "flex",
    gap: 8,
    alignItems: "baseline",
  },
  itemTime: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    flexShrink: 0,
  },
  itemTitle: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#111111",
    lineHeight: 1.4,
  },
  empty: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
    fontStyle: "italic",
  },
};
