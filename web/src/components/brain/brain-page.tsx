"use client";

import Link from "next/link";
import { Panel } from "@/components/ui/panel";

export default function BrainPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-64 rounded gap-4"
      style={{ background: "var(--bg-2)", border: "1px solid var(--border)" }}
    >
      <span
        className="material-symbols-outlined text-5xl opacity-30"
        style={{ color: "var(--accent)", fontVariationSettings: "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 48" }}
      >
        account_tree
      </span>
      <p className="font-bold text-base" style={{ color: "var(--text-1)", margin: 0 }}>
        Agent Theater
      </p>
      <p className="font-mono text-xs" style={{ color: "var(--text-3)", margin: 0, textAlign: "center" }}>
        Full agent inspection moved to{" "}
        <Link
          href="/dashboard/system"
          className="underline"
          style={{ color: "var(--accent)" }}
        >
          System → Agents tab
        </Link>
      </p>
    </div>
  );
}
