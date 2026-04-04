import DashHeader from "@/components/DashHeader";
import DashSidebar from "@/components/DashSidebar";
import DashBottomNav from "@/components/DashBottomNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: "100vh", background: "#000000", fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif' }}>
      <DashHeader />

      <div style={{ display: "flex", paddingTop: 52 }}>
        {/* Sidebar — hidden on mobile via media handled by DashSidebar itself */}
        <DashSidebar />

        <main
          style={{
            flex: 1,
            marginLeft: 256,
            minHeight: "calc(100vh - 52px)",
            padding: 20,
            paddingBottom: 80,
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
            padding-bottom: 80px !important;
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
