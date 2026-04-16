"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

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
      className="fixed inset-0 flex items-center justify-center z-[200]"
      style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}
      onClick={(e) => { if (e.target === overlayRef.current) onCancel(); }}
    >
      <div
        className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md w-full max-w-[400px]"
        style={{ boxShadow: "0 24px 48px rgba(0,0,0,0.5)" }}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <span className="text-sm font-bold" style={{ fontFamily: "var(--font-ui)", color: "var(--text-1)" }}>
            {title}
          </span>
          <button
            className="bg-none border-none text-[var(--text-3)] cursor-pointer text-sm p-0 px-1"
            style={{ background: "none", border: "none", cursor: "pointer" }}
            onClick={onCancel}
          >
            ✕
          </button>
        </div>

        {(body || children) && (
          <div className="px-4 py-4">
            {body && (
              <p className="text-sm m-0" style={{ fontFamily: "var(--font-ui)", color: "var(--text-2)", lineHeight: 1.6 }}>
                {body}
              </p>
            )}
            {children}
          </div>
        )}

        <div className="flex justify-end gap-3 px-4 py-3 border-t border-[var(--border)]">
          <button
            className="rounded px-4 py-1.5 text-sm cursor-pointer transition-all bg-[var(--bg-3)] border border-[var(--border)] text-[var(--text-2)] hover:border-[var(--text-3)]"
            style={{ fontFamily: "var(--font-ui)" }}
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            className="rounded px-4 py-1.5 text-sm font-bold text-[#0e0e0e] cursor-pointer transition-all"
            style={{ fontFamily: "var(--font-ui)", background: confirmColor, border: "none" }}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
