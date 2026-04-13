import AppShell from "@/components/AppShell";
import AppShellLayout from "@/components/shell/app-shell";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppShell>
      <AppShellLayout>{children}</AppShellLayout>
    </AppShell>
  );
}
