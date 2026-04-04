"use client";

const TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"];

const SF: React.CSSProperties = {
  fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
};

interface Props {
  value: string;
  onChange: (tf: string) => void;
}

export default function TimeframeSelector({ value, onChange }: Props) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      background: "rgba(116,116,128,0.18)",
      borderRadius: 9,
      padding: 2,
      gap: 1,
    }}>
      {TIMEFRAMES.map((tf) => {
        const active = tf === value;
        return (
          <button
            key={tf}
            onClick={() => onChange(tf)}
            style={{
              ...SF,
              height: 32,
              padding: "0 10px",
              fontSize: 13,
              fontWeight: active ? 600 : 400,
              background: active ? "#2C2C2E" : "transparent",
              border: "none",
              borderRadius: 7,
              color: active ? "#FFFFFF" : "rgba(235,235,245,0.4)",
              cursor: "pointer",
              boxShadow: active ? "0 1px 4px rgba(0,0,0,0.3)" : "none",
              transition: "background 0.15s, color 0.15s, box-shadow 0.15s",
              whiteSpace: "nowrap",
            }}
            onMouseEnter={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(235,235,245,0.7)";
              }
            }}
            onMouseLeave={(e) => {
              if (!active) {
                (e.currentTarget as HTMLButtonElement).style.color = "rgba(235,235,245,0.4)";
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
