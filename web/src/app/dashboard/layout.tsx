import AppShell from "@/components/AppShell";
import StatusBar from "@/components/shell/StatusBar";
import Nav from "@/components/shell/Nav";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppShell>
      <StatusBar />
      <Nav />
      {/* Main content — offset by header height; sidebar pushes from left on desktop */}
      <main
        style={{
          paddingTop: "var(--header-h)",
          paddingLeft: "var(--sidebar-w)",
          minHeight: "100vh",
        }}
        className="hidden lg:block"
      >
        <div style={{ padding: "var(--space-5)" }}>{children}</div>
      </main>
      {/* Mobile: no sidebar offset, bottom nav is fixed */}
      <main
        style={{ paddingTop: "var(--header-h)", paddingBottom: "var(--nav-bottom-h)" }}
        className="lg:hidden"
      >
        <div style={{ padding: "var(--space-4)" }}>{children}</div>
      </main>
    </AppShell>
  );
}
