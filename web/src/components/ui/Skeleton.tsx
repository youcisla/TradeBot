import { cn } from "@/lib/utils"

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("animate-pulse rounded-md", className)}
      style={{ background: "var(--bg-3)" }}
      {...props}
    />
  )
}

function SkeletonLine({ width = "100%", height = 14 }: { width?: string; height?: number }) {
  return (
    <div
      className="rounded animate-pulse"
      style={{ width, height, background: "var(--bg-3)" }}
    />
  );
}

export { Skeleton, SkeletonLine }

/** Full TanStack Table skeleton with header + N rows */
export function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="flex flex-col">
      <div
        className="grid gap-2 px-4 py-2 border-b"
        style={{ background: "var(--bg-3)", borderColor: "var(--border)", gridTemplateColumns: "48px 1fr 80px 1fr 80px 80px 52px" }}
      >
        {["", "", "", "", "", "", ""].map((_, i) => (
          <SkeletonLine key={i} height={9} width="60%" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="grid gap-2 px-4 py-3 border-b"
          style={{ borderColor: "var(--border-subtle)", gridTemplateColumns: "48px 1fr 80px 1fr 80px 80px 52px" }}
        >
          <SkeletonLine height={14} />
          <div className="flex flex-col gap-1.5">
            <SkeletonLine width="60%" height={12} />
            <SkeletonLine width="40%" height={9} />
          </div>
          <SkeletonLine height={14} />
          <SkeletonLine height={10} />
          <SkeletonLine height={14} />
          <SkeletonLine height={14} />
          <SkeletonLine height={14} />
        </div>
      ))}
    </div>
  );
}

/** StatCard-shaped skeleton */
export function StatCardSkeleton() {
  return (
    <div
      className="rounded flex flex-col gap-2 p-3"
      style={{ background: "var(--bg-2)", border: "1px solid var(--border)" }}
    >
      <SkeletonLine width="50%" height={9} />
      <SkeletonLine width="70%" height={20} />
    </div>
  );
}

/** KPI row skeleton (6 StatCard skeletons) */
export function KpiRowSkeleton() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
  );
}

/** Positions card skeleton */
export function PositionsSkeleton() {
  return (
    <div className="flex flex-col">
      <div
        className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2 border-b"
        style={{ background: "var(--bg-3)", borderColor: "var(--border)" }}
      >
        {["Symbol", "Dir", "Entry", "PnL", "SL", "Age", ""].map((h) => (
          <span
            key={h}
            className="font-mono"
            style={{ color: "var(--text-3)", fontSize: 9, letterSpacing: "0.06em" }}
          >
            {h}
          </span>
        ))}
      </div>
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="grid grid-cols-[2fr_56px_1fr_1fr_1fr_60px_28px] gap-2 px-4 py-2.5 border-b"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <div className="flex flex-col gap-1">
            <SkeletonLine width="60%" height={12} />
            <SkeletonLine width="40%" height={9} />
          </div>
          <SkeletonLine height={14} />
          <SkeletonLine height={14} />
          <SkeletonLine height={14} />
          <SkeletonLine height={14} />
          <SkeletonLine height={14} />
          <SkeletonLine height={14} />
        </div>
      ))}
    </div>
  );
}

/** Event feed skeleton */
export function EventFeedSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="flex flex-col px-3 py-1.5 gap-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-start gap-3">
          <SkeletonLine width="48px" height={10} />
          <SkeletonLine width="72px" height={14} />
          <SkeletonLine width="48px" height={14} />
          <div className="flex-1">
            <SkeletonLine height={12} />
          </div>
        </div>
      ))}
    </div>
  );
}