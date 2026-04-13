import { AppShellProvider } from "@/components/app/AppShellProvider";
import { AppShellLayout } from "@/components/app/AppShellLayout";
import { ErrorBoundary } from "@/components/ui/error-boundary";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ErrorBoundary>
      <AppShellProvider>
        <AppShellLayout>{children}</AppShellLayout>
      </AppShellProvider>
    </ErrorBoundary>
  );
}
