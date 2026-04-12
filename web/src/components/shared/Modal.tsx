"use client";

import { useEffect, useRef } from "react";

interface ModalProps {
  open: boolean;
  title: string;
  body?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "default";
  onConfirm: () => void;
  onCancel: () => void;
  children?: React.ReactNode;
}

export default function Modal({
  open, title, body, confirmLabel = "Confirm", cancelLabel = "Cancel",
  variant = "default", onConfirm, onCancel, children,
}: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, onCancel]);

  if (!open) return null;

  const confirmColor = variant === "danger" ? "var(--red)" : "var(--accent)";

  return (
    <div
      ref={overlayRef}
      style={styles.overlay}
      onClick={(e) => { if (e.target === overlayRef.current) onCancel(); }}
    >
      <div style={styles.dialog}>
        <div style={styles.header}>
          <span style={styles.title}>{title}</span>
          <button style={styles.closeBtn} onClick={onCancel}>✕</button>
        </div>

        {(body || children) && (
          <div style={styles.body}>
            {body && <p style={styles.bodyText}>{body}</p>}
            {children}
          </div>
        )}

        <div style={styles.actions}>
          <button style={styles.cancelBtn} onClick={onCancel}>{cancelLabel}</button>
          <button
            style={{ ...styles.confirmBtn, background: confirmColor }}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed", inset: 0,
    background: "rgba(0,0,0,0.75)",
    display: "flex", alignItems: "center", justifyContent: "center",
    zIndex: 200,
    backdropFilter: "blur(4px)",
  },
  dialog: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    width: "100%",
    maxWidth: 400,
    boxShadow: "0 24px 48px rgba(0,0,0,0.5)",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "var(--space-4)",
    borderBottom: "1px solid var(--border)",
  },
  title: {
    fontFamily: "var(--font-ui)",
    fontSize: 14,
    fontWeight: 700,
    color: "var(--text-1)",
  },
  closeBtn: {
    background: "none", border: "none",
    color: "var(--text-3)", cursor: "pointer",
    fontSize: 14, padding: "0 4px",
  },
  body: {
    padding: "var(--space-4)",
  },
  bodyText: {
    fontFamily: "var(--font-ui)",
    fontSize: 13,
    color: "var(--text-2)",
    lineHeight: 1.6,
    margin: 0,
  },
  actions: {
    display: "flex", justifyContent: "flex-end", gap: "var(--space-3)",
    padding: "var(--space-4)",
    borderTop: "1px solid var(--border)",
  },
  cancelBtn: {
    background: "var(--bg-3)", border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--text-2)", cursor: "pointer",
    fontFamily: "var(--font-ui)", fontSize: 13,
    padding: "6px 16px",
  },
  confirmBtn: {
    border: "none", borderRadius: "var(--radius-sm)",
    color: "#0e0e0e", cursor: "pointer",
    fontFamily: "var(--font-ui)", fontSize: 13, fontWeight: 700,
    padding: "6px 16px",
  },
};
