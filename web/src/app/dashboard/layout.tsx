import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import DashNav from "@/components/DashNav";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession(authOptions);
  if (!session) redirect("/login");

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#080808" }}>
      <DashNav />
      <main style={{ flex: 1, padding: "24px" }}>
        {children}
      </main>
    </div>
  );
}
