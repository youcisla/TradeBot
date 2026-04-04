export default function DashboardLoading() {
  return (
    <>
      <div
        style={{
          position: "fixed",
          inset: 0,
          background: "#000000",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 16,
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
          zIndex: 9999,
        }}
      >
        {/* Spinning circle */}
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            border: "2.5px solid rgba(235,235,245,0.12)",
            borderTopColor: "#0A84FF",
            animation: "iosSpinner 0.75s linear infinite",
          }}
        />

        {/* Label */}
        <span
          style={{
            fontSize: 15,
            color: "rgba(235,235,245,0.4)",
            letterSpacing: "0.01em",
          }}
        >
          NeuralFX
        </span>
      </div>

      <style>{`
        @keyframes iosSpinner {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </>
  );
}
