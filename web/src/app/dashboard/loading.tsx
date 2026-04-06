// Skeleton streaming — pages render progressively as data arrives,
// no full-page blocking spinner. Matches the ios-skeleton classes
// defined in globals.css.

function SkelCard({ height = 120, style }: { height?: number; style?: React.CSSProperties }) {
  return (
    <div
      className="ios-skeleton"
      style={{ height, borderRadius: 12, ...style }}
    />
  );
}

function SkelRow({ style }: { style?: React.CSSProperties }) {
  return (
    <div
      className="ios-skeleton"
      style={{ height: 13, borderRadius: 6, ...style }}
    />
  );
}

export default function DashboardLoading() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* KPI strip skeleton */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>
        {[0, 1, 2, 3].map(i => (
          <div
            key={i}
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 10,
              padding: "18px 20px",
            }}
          >
            <div className="ios-skeleton" style={{ height: 11, width: "55%", borderRadius: 4, marginBottom: 10 }} />
            <div className="ios-skeleton" style={{ height: 26, width: "70%", borderRadius: 6, marginBottom: 8 }} />
            <div className="ios-skeleton" style={{ height: 12, width: "60%", borderRadius: 4 }} />
          </div>
        ))}
      </div>

      {/* Main content area skeleton */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 320px", minWidth: 0 }}>
          <div style={{ background: "var(--surface-1)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
            <div className="ios-skeleton" style={{ height: 11, width: "40%", borderRadius: 4, marginBottom: 14 }} />
            {[0,1,2,3,4,5,6,7,8].map(i => (
              <div key={i} className="skel-row" style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", marginBottom: 2 }}>
                <div className="ios-skeleton" style={{ width: 7, height: 7, borderRadius: "50%", flexShrink: 0 }} />
                <div className="ios-skeleton" style={{ width: 84, height: 13, borderRadius: 4, flexShrink: 0 }} />
                <div className="ios-skeleton" style={{ flex: 1, height: 12, borderRadius: 4 }} />
                <div className="ios-skeleton" style={{ width: 44, height: 11, borderRadius: 4, flexShrink: 0 }} />
              </div>
            ))}
          </div>
        </div>
        <div style={{ flex: "0 1 380px", minWidth: 280, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
            <div className="ios-skeleton" style={{ height: 11, width: "50%", borderRadius: 4, marginBottom: 12 }} />
            {[0,1,2,3].map(i => (
              <div key={i} className="skel-row" style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <div className="ios-skeleton" style={{ width: 60, height: 13, borderRadius: 4 }} />
                <div className="ios-skeleton" style={{ flex: 1, height: 12, borderRadius: 4 }} />
                <div className="ios-skeleton" style={{ width: 52, height: 12, borderRadius: 4 }} />
              </div>
            ))}
          </div>
          <div style={{ background: "var(--surface-1)", border: "1px solid var(--border)", borderRadius: 10, padding: 20 }}>
            <div className="ios-skeleton" style={{ height: 11, width: "40%", borderRadius: 4, marginBottom: 14 }} />
            <SkelRow style={{ marginBottom: 8 }} />
            <SkelRow style={{ marginBottom: 8 }} />
            <SkelRow style={{ width: "60%" }} />
          </div>
        </div>
      </div>
    </div>
  );
}
