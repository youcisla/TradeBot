import { AppShellProvider } from "@/components/app/AppShellProvider";
import { AppShell } from "@/components/AppShell";
import { ErrorBoundary } from "@/components/ui/error-boundary";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ErrorBoundary>
      <AppShellProvider>
        <AppShell>{children}</AppShell>
      </AppShellProvider>
    </ErrorBoundary>
  );
}
