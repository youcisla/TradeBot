"use client";

import { useEffect, useRef } from "react";
import { useKeyboard } from "@/hooks/useKeyboard";

type WidthVariant = "sm" | "md" | "lg";

const WIDTH_MAP: Record<WidthVariant, string> = {
  sm: "360px",
  md: "480px",
  lg: "640px",
};

interface DrawerPanelProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  /** Fixed action buttons at the bottom */
  footer?: React.ReactNode;
  width?: WidthVariant;
}

/**
 * Right-side drawer panel for deep-dive views.
 * Opens with a slide-in animation from the right.
 * Closes on: X button, backdrop click, or Escape key.
 *
 * @example
 * <DrawerPanel
 *   open={!!selectedTrade}
 *   onClose={() => setSelectedTrade(null)}
 *   title="EUR/USD Trade Detail"
 *   footer={<Button onClick={closeDrawer}>Close</Button>}
 * >
 *   {selectedTrade && <TradeDetail trade={selectedTrade} />}
 * </DrawerPanel>
 */
export function DrawerPanel({
  open,
  onClose,
  title,
  subtitle,
  children,
  footer,
  width = "md",
}: DrawerPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // ESC to close
  useKeyboard([{ key: "Escape", action: onClose }]);

  // Trap focus inside drawer when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 150,
          background: "rgba(0,0,0,0.6)",
          backdropFilter: "blur(2px)",
          animation: "fadeIn 0.15s ease-out",
        }}
      />

      {/* Drawer panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
        style={{
          position: "fixed",
          top: 0,
          right: 0,
          bottom: 0,
          zIndex: 160,
          width: WIDTH_MAP[width],
          maxWidth: "100vw",
          background: "var(--bg-2)",
          borderLeft: "1px solid var(--border-active)",
          boxShadow: "var(--shadow-lg)",
          display: "flex",
          flexDirection: "column",
          animation: "slideInRight 0.2s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between gap-4 px-5 py-4"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="flex flex-col gap-0.5 min-w-0">
            <h2
              id="drawer-title"
              className="font-bold truncate"
              style={{
                color: "var(--text-1)",
                fontFamily: "var(--font-ui)",
                fontSize: 15,
                fontWeight: 600,
              }}
            >
              {title}
            </h2>
            {subtitle && (
              <span
                style={{
                  color: "var(--text-3)",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                }}
              >
                {subtitle}
              </span>
            )}
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            aria-label="Close drawer"
            className="flex-shrink-0 rounded p-1 transition-colors"
            style={{
              color: "var(--text-3)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLElement).style.background = "var(--bg-3)")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLElement).style.background = "transparent")
            }
          >
            <span
              className="material-symbols-outlined"
              style={{ fontVariationSettings: "'FILL' 0, 'wght' 300, 'opsz' 20" }}
            >
              close
            </span>
          </button>
        </div>

        {/* Scrollable content */}
        <div
          className="flex-1 overflow-y-auto px-5 py-4"
          style={{ minHeight: 0 }}
        >
          {children}
        </div>

        {/* Fixed footer */}
        {footer && (
          <div
            className="px-5 py-4 flex items-center justify-end gap-3"
            style={{ borderTop: "1px solid var(--border)" }}
          >
            {footer}
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to   { transform: translateX(0); }
        }
      `}</style>
    </>
  );
}
