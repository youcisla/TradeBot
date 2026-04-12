"use client";

const TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"] as const;
type TF = typeof TIMEFRAMES[number];

interface Props {
  selected: TF;
  onChange: (tf: TF) => void;
}

export default function TimeframeBar({ selected, onChange }: Props) {
  return (
    <div style={styles.wrapper}>
      {TIMEFRAMES.map((tf) => (
        <button
          key={tf}
          style={{
            ...styles.btn,
            ...(tf === selected ? styles.btnActive : {}),
          }}
          onClick={() => onChange(tf)}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display:  "flex",
    alignItems: "center",
    gap:       2,
  },
  btn: {
    background: "none",
    border:     "1px solid transparent",
    borderRadius: "var(--radius-sm)",
    color:      "var(--text-3)",
    cursor:     "pointer",
    fontFamily: "var(--font-mono)",
    fontSize:   11,
    fontWeight: 600,
    padding:    "3px 8px",
  },
  btnActive: {
    background: "var(--bg-3)",
    border:     "1px solid var(--border-active)",
    color:      "var(--text-1)",
  },
};
