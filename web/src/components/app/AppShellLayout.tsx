"use client";

import { Header } from "@/components/app/Header";
import { Sidebar } from "@/components/app/Sidebar";
import { MobileNav } from "@/components/app/MobileNav";
import { CommandPalette } from "@/components/app/CommandPalette";

interface AppShellLayoutProps {
  children: React.ReactNode;
}

export function AppShellLayout({ children }: AppShellLayoutProps) {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text-1)]">
      {/* Fixed top header */}
      <Header />

      {/* Fixed left sidebar — desktop only */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Main content — desktop */}
      <main
        className="hidden lg:block pt-[var(--header-h)] pl-[var(--sidebar-w)]"
        style={{ minHeight: "100vh" }}
      >
        <div className="p-6">{children}</div>
      </main>

      {/* Main content — mobile */}
      <main
        className="lg:hidden pt-[var(--header-h)]"
        style={{ paddingBottom: "var(--nav-bottom-h)", minHeight: "100vh" }}
      >
        <div className="p-4">{children}</div>
      </main>

      {/* Mobile bottom nav */}
      <div className="lg:hidden">
        <MobileNav />
      </div>

      {/* Global command palette */}
      <CommandPalette />
    </div>
  );
}
