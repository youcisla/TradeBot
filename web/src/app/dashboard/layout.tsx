import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import Link from "next/link";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-terminal-border bg-terminal-surface px-6 py-3 flex items-center gap-6 text-xs">
        <span className="text-matrix font-bold text-sm cursor-blink">
          TRADING BOT
        </span>
        <Link href="/dashboard" className="text-matrix-dim hover:text-matrix transition-colors">
          Dashboard
        </Link>
        <Link href="/dashboard/trades" className="text-matrix-dim hover:text-matrix transition-colors">
          Trades
        </Link>
        <Link href="/dashboard/learning" className="text-matrix-dim hover:text-matrix transition-colors">
          Learning
        </Link>
      </nav>

      {/* Main content */}
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
