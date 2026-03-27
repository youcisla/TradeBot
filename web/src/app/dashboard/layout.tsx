import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import DashHeader from "@/components/DashHeader";
import DashBottomNav from "@/components/DashBottomNav";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <div className="min-h-dvh bg-surface-container-lowest text-on-surface">
      <DashHeader />
      <main className="pt-14 pb-20 px-4 md:px-8 max-w-7xl mx-auto">
        {children}
      </main>
      <DashBottomNav />
    </div>
  );
}
