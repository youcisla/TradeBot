"use client";

interface SectionHeaderProps {
  title: string;
  /** Optional element on the right (filter chips, action button, count badge) */
  action?: React.ReactNode;
  className?: string;
}

/**
 * Labelled section divider with an optional right-side action slot.
 * Used inside pages to group related components.
 *
 * @example
 * <SectionHeader
 *   title="Open Positions"
 *   action={<Button size="sm">View All</Button>}
 * />
 */
export function SectionHeader({ title, action, className }: SectionHeaderProps) {
  return (
    <div
      className={`flex items-center justify-between ${className ?? ""}`}
    >
      <span
        className="text-xs font-bold uppercase tracking-widest"
        style={{
          color: "var(--text-3)",
          fontFamily: "var(--font-mono)",
          fontSize: 9,
          letterSpacing: "0.08em",
        }}
      >
        {title}
      </span>
      {action && <div>{action}</div>}
    </div>
  );
}
