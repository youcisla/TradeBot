import DashHeader from "@/components/DashHeader";
import DashSidebar from "@/components/DashSidebar";
import DashBottomNav from "@/components/DashBottomNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "radial-gradient(circle at 12% -10%, #1a2a3f 0%, #06070a 45%, #030303 100%)",
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "fixed",
          inset: 0,
          pointerEvents: "none",
          zIndex: 0,
          background:
            "radial-gradient(circle at 82% 8%, rgba(20,182,255,0.20), transparent 34%)," +
            "radial-gradient(circle at 12% 72%, rgba(255,160,65,0.12), transparent 38%)," +
            "linear-gradient(120deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 55%)",
        }}
      />

      <DashHeader />

      <div style={{ display: "flex", paddingTop: 64, position: "relative", zIndex: 1 }}>
        {/* Sidebar — hidden on mobile via media handled by DashSidebar itself */}
        <DashSidebar />

        <main
          style={{
            flex: 1,
            marginLeft: 256,
            minHeight: "calc(100vh - 64px)",
            padding: "24px 24px 96px",
            overflowX: "hidden",
          }}
        >
          <div style={{ margin: "0 auto", width: "100%", maxWidth: 1400 }}>
            {children}
          </div>
        </main>
      </div>

      {/* Bottom nav — only on mobile, handled by DashBottomNav itself */}
      <DashBottomNav />

      <style>{`
        @media (max-width: 1023px) {
          main {
            margin-left: 0 !important;
            padding: 16px 14px 92px !important;
          }
        }
        @media (min-width: 1024px) {
          .dash-bottom-nav {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}
