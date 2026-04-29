"use client";

interface ChipProps {
  tone?: "pos" | "neg" | "warn" | "info" | "accent" | "violet" | "";
  solid?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * Handoff-style chip — tone colors match CSS class tokens:
 * .chip.pos | .chip.neg | .chip.warn | .chip.info | .chip.accent | .chip.violet
 */
export function Chip({ tone = "", solid = false, children, className = "" }: ChipProps) {
  return (
    <span className={["chip", tone, solid ? "solid" : "", className].filter(Boolean).join(" ")}>
      {children}
    </span>
  );
}

interface SdotProps {
  tone?: "pos" | "neg" | "warn" | "info" | "accent" | "violet" | "";
  live?: boolean;
  className?: string;
}

/**
 * Status dot — animated pulse when live=true.
 */
export function Sdot({ tone = "", live = false, className = "" }: SdotProps) {
  return <span className={["sdot", tone, live ? "live" : "", className].filter(Boolean).join(" ")} />;
}
