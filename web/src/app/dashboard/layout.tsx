import DashHeader from "@/components/DashHeader";
import DashSidebar from "@/components/DashSidebar";
import DashBottomNav from "@/components/DashBottomNav";

// Auth is handled by middleware.ts (Edge runtime) — no session check needed here.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-surface-container-lowest text-on-surface">
      {/* Fixed top header — full width */}
      <DashHeader />

      {/* Below header: sidebar + content */}
      <div className="flex pt-11">
        {/* Desktop sidebar — hidden on mobile */}
        <div className="hidden md:block">
          <DashSidebar />
        </div>

        {/* Main content */}
        <main className="flex-1 md:ml-[200px] min-h-[calc(100vh-44px)] p-6 overflow-x-hidden">
          {children}
        </main>
      </div>

      {/* Mobile bottom nav — hidden on desktop */}
      <div className="md:hidden">
        <DashBottomNav />
      </div>
    </div>
  );
}
