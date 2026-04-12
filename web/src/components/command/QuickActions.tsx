"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import Modal from "@/components/shared/Modal";
import { sendCommand } from "@/lib/ws";

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
      <div style={styles.wrapper}>
        <span style={styles.label}>Actions</span>
        <div style={styles.buttons}>
          {isRunning ? (
            <button
              style={styles.btn}
              onClick={() => setPending("pause")}
              disabled={loading !== null}
            >
              Pause
            </button>
          ) : (
            <button
              style={{ ...styles.btn, ...styles.btnResume }}
              onClick={() => setPending("resume")}
              disabled={loading !== null}
            >
              Resume
            </button>
          )}
          <button
            style={{ ...styles.btn, ...styles.btnWarn }}
            onClick={() => setPending("close_all")}
            disabled={loading !== null}
          >
            Close All
          </button>
          <button
            style={{ ...styles.btn, ...styles.btnDanger }}
            onClick={() => setPending("kill")}
            disabled={loading !== null}
          >
            Kill
          </button>
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

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3) var(--space-4)",
    display: "flex",
    alignItems: "center",
    gap: "var(--space-4)",
  },
  label: {
    fontFamily: "var(--font-ui)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--text-2)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    flexShrink: 0,
  },
  buttons: {
    display: "flex",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  },
  btn: {
    background: "var(--bg-3)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--text-1)",
    cursor: "pointer",
    fontFamily: "var(--font-ui)",
    fontSize: 12,
    fontWeight: 600,
    padding: "5px 14px",
  },
  btnResume: {
    border: "1px solid var(--accent)",
    color: "var(--accent)",
  },
  btnWarn: {
    border: "1px solid var(--orange)",
    color: "var(--orange)",
  },
  btnDanger: {
    background: "rgba(255,69,58,0.15)",
    border: "1px solid var(--red)",
    color: "var(--red)",
  },
};
