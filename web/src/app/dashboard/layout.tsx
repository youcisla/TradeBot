import DashHeader from "@/components/DashHeader";
import DashSidebar from "@/components/DashSidebar";
import DashBottomNav from "@/components/DashBottomNav";

// Auth is handled by middleware.ts (Edge runtime) — no session check needed here.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen text-on-surface bg-[radial-gradient(circle_at_10%_0%,rgba(28,213,255,0.08),transparent_38%),radial-gradient(circle_at_90%_100%,rgba(0,253,135,0.07),transparent_40%),linear-gradient(180deg,#090909_0%,#050505_100%)]">
      <DashHeader />

      <div className="flex pt-14">
        <div className="hidden lg:block">
          <DashSidebar />
        </div>

        <main className="flex-1 lg:ml-[248px] min-h-[calc(100vh-56px)] px-3 sm:px-5 lg:px-7 pb-20 lg:pb-8 overflow-x-hidden">
          <div className="mx-auto w-full max-w-[1520px] pt-2 lg:pt-3">
            {children}
          </div>
        </main>
      </div>

      <div className="lg:hidden">
        <DashBottomNav />
      </div>
    </div>
  );
}
