"use client";

export default function PageHeader({
  subsystem,
  title,
  accent = "#00ff88",
}: {
  subsystem: string;
  title: string;
  accent?: string;
}) {
  const [r, g, b] = hexToRgb(accent);
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
        color: "#607888", letterSpacing: "0.2em", textTransform: "uppercase",
      }}>
        {subsystem}
      </div>
      <h1 style={{
        fontSize: 20, fontFamily: "'JetBrains Mono', monospace",
        fontWeight: 700, color: accent,
        textShadow: `0 0 20px rgba(${r},${g},${b},0.3)`,
        marginTop: 2, marginBottom: 0,
      }}>
        {title}
      </h1>
    </div>
  );
}

function hexToRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return [r, g, b];
}
