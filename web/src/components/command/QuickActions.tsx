"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import Modal from "@/components/shared/Modal";
import { sendCommand } from "@/lib/ws";
import { cn } from "@/lib/utils";

type ActionType = "pause" | "resume" | "close_all" | "kill";

interface ConfirmConfig {
  title: string;
  body: string;
  confirmLabel: string;
  variant: "danger" | "default";
}

const CONFIGS: Record<ActionType, ConfirmConfig> = {
  pause: {
    title: "Pause Bot",
    body: "The bot will stop scanning for new signals. Open trades remain active.",
    confirmLabel: "Pause",
    variant: "default",
  },
  resume: {
    title: "Resume Bot",
    body: "The bot will resume scanning and executing signals.",
    confirmLabel: "Resume",
    variant: "default",
  },
  close_all: {
    title: "Close All Positions",
    body: "This will immediately close ALL open positions at market price.",
    confirmLabel: "Close All",
    variant: "danger",
  },
  kill: {
    title: "KILL — Emergency Stop",
    body: "EMERGENCY: Closes all positions and shuts down the bot. This cannot be undone.",
    confirmLabel: "KILL",
    variant: "danger",
  },
};

export default function QuickActions() {
  const { isRunning } = useAppShell();
  const [pending, setPending] = useState<ActionType | null>(null);
  const [loading, setLoading] = useState<ActionType | null>(null);

  async function execute(action: ActionType) {
    setLoading(action);
    try {
      if (action === "pause") await sendCommand("pause");
      else if (action === "resume") await sendCommand("resume");
      else if (action === "close_all") await sendCommand("close_all");
      else if (action === "kill") await sendCommand("kill");
    } finally {
      setLoading(null);
      setPending(null);
    }
  }

  const config = pending ? CONFIGS[pending] : null;

  return (
    <>
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-3 flex items-center gap-4">
        <span
          className="text-[11px] font-bold uppercase flex-shrink-0"
          style={{ fontFamily: "var(--font-ui)", color: "var(--text-2)", letterSpacing: "0.08em" }}
        >
          Actions
        </span>
        <div className="flex gap-2 flex-wrap">
          {isRunning ? (
            <ActionBtn label="Pause"    onClick={() => setPending("pause")}    disabled={loading !== null} />
          ) : (
            <ActionBtn label="Resume"   onClick={() => setPending("resume")}   variant="accent" disabled={loading !== null} />
          )}
          <ActionBtn label="Close All" onClick={() => setPending("close_all")} variant="warn"   disabled={loading !== null} />
          <ActionBtn label="Kill"     onClick={() => setPending("kill")}      variant="danger" disabled={loading !== null} />
        </div>
      </div>

      {config && pending && (
        <Modal
          open={true}
          title={config.title}
          body={config.body}
          confirmLabel={loading === pending ? "…" : config.confirmLabel}
          cancelLabel="Cancel"
          variant={config.variant}
          onConfirm={() => execute(pending)}
          onCancel={() => setPending(null)}
        />
      )}
    </>
  );
}

function ActionBtn({ label, onClick, variant = "default", disabled }: {
  label: string;
  onClick: () => void;
  variant?: "default" | "accent" | "warn" | "danger";
  disabled?: boolean;
}) {
  return (
    <button
      className={cn(
        "rounded px-3 py-1.5 text-xs font-semibold cursor-pointer transition-all border",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        variant === "default" && "bg-[var(--bg-3)] border-[var(--border)] text-[var(--text-1)]",
        variant === "accent"  && "border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent)]/10",
        variant === "warn"    && "border-[var(--warning)] text-[var(--warning)] hover:bg-[var(--warning)]/10",
        variant === "danger"  && "bg-[var(--negative-dim)] border-[var(--negative)] text-[var(--negative)]",
      )}
      style={{ fontFamily: "var(--font-ui)" }}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
}
