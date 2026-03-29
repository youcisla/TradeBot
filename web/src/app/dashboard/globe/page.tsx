"use client";

import dynamic from "next/dynamic";

function GlobeFallback() {
  return (
    <div
      style={{
        width: "100%",
        minHeight: 600,
        borderRadius: 16,
        border: "1px solid #494847",
        background:
          "radial-gradient(circle at 20% 20%, rgba(0, 210, 253, 0.14), transparent 40%), radial-gradient(circle at 80% 75%, rgba(233, 102, 255, 0.12), transparent 42%), rgba(14, 14, 14, 0.7)",
        color: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        textAlign: "center",
        fontFamily: "'Fira Code', monospace",
      }}
    >
      <div style={{ maxWidth: 560 }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 18, letterSpacing: "0.02em" }}>
          Globe Renderer Unavailable
        </h2>
        <p style={{ margin: 0, color: "#adaaaa", fontSize: 13, lineHeight: 1.6 }}>
          The 3D globe could not be initialized due to a React/renderer runtime
          mismatch. The rest of the dashboard remains available.
        </p>
      </div>
    </div>
  );
}

// R3F canvas must be loaded client-side only — SSR not supported
const ForexGlobe = dynamic(
  () =>
    import("./ForexGlobe").catch(() => {
      // Runtime-safe fallback when react-three stack is not compatible.
      return { default: GlobeFallback };
    }),
  {
  ssr: false,
  loading: () => (
    <div style={{
      width: "100%",
      height: "600px",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "rgba(14,14,14,0.6)",
      borderRadius: 16,
      border: "1px solid #494847",
      color: "#adaaaa",
      fontSize: 13,
      letterSpacing: "0.1em",
      fontFamily: "'Fira Code', monospace",
    }}>
      LOADING GLOBE...
    </div>
  ),
  },
);

export default function GlobePage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, padding: "8px 0" }}>
      {/* Page header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{
            margin: 0,
            fontSize: 22,
            fontWeight: 700,
            color: "#fff",
            fontFamily: "'Fira Code', monospace",
            letterSpacing: "-0.01em",
          }}>
            Forex Session Globe
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "#adaaaa", letterSpacing: "0.05em" }}>
            Live market session activity across global financial centers
          </p>
        </div>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "6px 14px",
          background: "rgba(0,253,135,0.08)",
          border: "1px solid rgba(0,253,135,0.25)",
          borderRadius: 20,
          fontSize: 11,
          fontWeight: 700,
          color: "#00fd87",
          letterSpacing: "0.12em",
          fontFamily: "'Fira Code', monospace",
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#00fd87",
            boxShadow: "0 0 6px #00fd87",
            animation: "pulse 2s infinite",
          }} />
          LIVE
        </div>
      </div>

      {/* 3D Globe */}
      <ForexGlobe />
    </div>
  );
}
