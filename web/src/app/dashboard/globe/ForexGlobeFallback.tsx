"use client";

export default function ForexGlobeFallback() {
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
          mismatch. The dashboard remains available while dependencies are
          synchronized.
        </p>
      </div>
    </div>
  );
}
