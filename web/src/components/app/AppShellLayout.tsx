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
    <div className="min-h-screen" style={{ background: "var(--bg)", color: "var(--text-1)" }}>
      {/* Fixed top header */}
      <Header />

      {/* Fixed left sidebar — desktop only */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Main content — desktop */}
      <main
        className="hidden lg:block"
        style={{
          paddingTop: "var(--header-h)",
          paddingLeft: "var(--sidebar-w)",
          minHeight: "100vh",
        }}
      >
        <div className="p-6">{children}</div>
      </main>

      {/* Main content — mobile */}
      <main
        className="lg:hidden"
        style={{
          paddingTop: "var(--header-h)",
          paddingBottom: "var(--nav-bottom-h)",
          minHeight: "100vh",
        }}
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
