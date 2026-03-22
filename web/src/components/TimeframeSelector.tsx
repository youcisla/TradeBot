"use client";

const TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];

interface Props {
  value: string;
  onChange: (tf: string) => void;
}

export default function TimeframeSelector({ value, onChange }: Props) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
      {TIMEFRAMES.map((tf) => {
        const active = tf === value;
        return (
          <button
            key={tf}
            onClick={() => onChange(tf)}
            style={{
              padding: "5px 10px",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10, fontWeight: 700, letterSpacing: "0.04em",
              background: active ? "rgba(0,255,136,0.15)" : "transparent",
              border: `1px solid ${active ? "rgba(0,255,136,0.4)" : "#1c1c28"}`,
              borderRadius: 4,
              color: active ? "#00ff88" : "#2a3a4a",
              cursor: "pointer",
              boxShadow: active ? "0 0 8px rgba(0,255,136,0.25)" : "none",
              transition: "background 0.12s, color 0.12s, border-color 0.12s, box-shadow 0.12s",
            }}
            onMouseEnter={(e) => {
              if (!active) {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.color = "#c0ccd8";
                btn.style.borderColor = "#2a3a4a";
              }
            }}
            onMouseLeave={(e) => {
              if (!active) {
                const btn = e.currentTarget as HTMLButtonElement;
                btn.style.color = "#2a3a4a";
                btn.style.borderColor = "#1c1c28";
              }
            }}
          >
            {tf}
          </button>
        );
      })}
    </div>
  );
}
