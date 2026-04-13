"use client";

interface EmptyStateProps {
  /** Material Symbols icon name */
  icon?: string;
  title: string;
  description?: string;
  /** Optional action button */
  action?: React.ReactNode;
  className?: string;
}

/**
 * Shown when a list/table has no data.
 * Provides context and a path forward.
 *
 * @example
 * <EmptyState
 *   icon="inbox"
 *   title="No signals yet"
 *   description="Signals will appear here when the bot finds opportunities."
 * />
 */
export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-12 px-6 text-center ${className ?? ""}`}
    >
      {icon && (
        <span
          className="material-symbols-outlined"
          style={{
            fontSize: 32,
            color: "var(--text-3)",
            fontVariationSettings: "'FILL' 0, 'wght' 200, 'GRAD' 0, 'opsz' 32",
          }}
        >
          {icon}
        </span>
      )}

      <div className="flex flex-col gap-1.5">
        <span
          style={{
            color: "var(--text-2)",
            fontFamily: "var(--font-ui)",
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          {title}
        </span>

        {description && (
          <span
            style={{
              color: "var(--text-3)",
              fontFamily: "var(--font-ui)",
              fontSize: 12,
              maxWidth: 280,
              lineHeight: 1.5,
            }}
          >
            {description}
          </span>
        )}
      </div>

      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}
