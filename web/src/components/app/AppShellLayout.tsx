"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/app/Header";
import { MobileNav } from "@/components/app/MobileNav";
import { TopStrip } from "@/components/app/top-strip";
import { PipelineRibbon } from "@/components/app/pipeline-ribbon";
import { RailSidebar } from "@/components/app/rail-sidebar";
import { CommandPalette } from "@/components/app/command-palette";

interface AppShellLayoutProps {
  children: React.ReactNode;
}

export function AppShellLayout({ children }: AppShellLayoutProps) {
  const [page, setPage] = useState("mission");
  const [paletteOpen, setPaletteOpen] = useState(false);
  const router = useRouter();

  return (
    <div
      className="min-h-screen"
      style={{ background: "var(--bg)", color: "var(--text-1)" }}
    >
      {/* Fixed top header */}
      <Header />

      {/* TopStrip + PipelineRibbon below header */}
      <div
        className="fixed left-0 right-0 z-40 flex flex-col"
        style={{
          top: "var(--header-h)",
          background: "var(--bg-2)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <TopStrip onCmd={(cmd) => cmd === "palette" && setPaletteOpen(true)} />
        <PipelineRibbon />
      </div>

      {/* Fixed left sidebar — desktop only */}
      <div className="hidden lg:block">
        <RailSidebar page={page} onNav={setPage} />
      </div>

      {/* Main content — desktop */}
      <main
        className="hidden lg:block"
        style={{
          paddingTop: "148px",
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
          paddingTop: "148px",
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
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onNav={(p) => {
          setPage(p);
          router.push(`/dashboard/${p === "mission" ? "" : p}`);
          setPaletteOpen(false);
        }}
      />
    </div>
  );
}
