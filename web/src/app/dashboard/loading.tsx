// Shown instantly when navigating between dashboard pages,
// while the next page's server components stream in.
export default function DashboardLoading() {
  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      gap: 16,
      marginTop: 24,
      animation: "fadeIn 80ms ease-out",
    }}>
      {/* Page header skeleton */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ width: 80, height: 10, background: "#1a1a1a", borderRadius: 2 }} />
        <div style={{ width: 260, height: 28, background: "#1a1a1a", borderRadius: 2 }} />
      </div>

      {/* Card row skeleton */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        {[0, 1, 2].map((i) => (
          <div key={i} style={{
            height: 180,
            background: "#0e0e0e",
            borderLeft: "2px solid #1a1a1a",
            padding: 20,
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}>
            <div style={{ width: 100, height: 8, background: "#1a1a1a", borderRadius: 2 }} />
            <div style={{ width: "60%", height: 28, background: "#1a1a1a", borderRadius: 2, marginTop: 16 }} />
            <div style={{ width: "40%", height: 12, background: "#1a1a1a", borderRadius: 2 }} />
          </div>
        ))}
      </div>

      {/* Wide card skeleton */}
      <div style={{
        height: 120,
        background: "#0e0e0e",
        border: "1px solid #1a1a1a",
        padding: 20,
        display: "flex",
        gap: 12,
      }}>
        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} style={{ flex: 1, height: "100%", background: "#1a1a1a", borderRadius: 2 }} />
        ))}
      </div>
    </div>
  );
}
