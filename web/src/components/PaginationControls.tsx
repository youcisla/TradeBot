"use client";

const FONT =
  "-apple-system, BlinkMacSystemFont, \"SF Pro Display\", system-ui, sans-serif";

interface PaginationControlsProps {
  page: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (nextPage: number) => void;
  onPageSizeChange?: (nextPageSize: number) => void;
  pageSizeOptions?: number[];
  label?: string;
}

export default function PaginationControls({
  page,
  totalItems,
  pageSize,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  label = "items",
}: PaginationControlsProps) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const clampedPage = Math.min(Math.max(page, 1), totalPages);
  const start = totalItems === 0 ? 0 : (clampedPage - 1) * pageSize + 1;
  const end = Math.min(clampedPage * pageSize, totalItems);

  const canPrev = clampedPage > 1;
  const canNext = clampedPage < totalPages;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
        flexWrap: "wrap",
        marginTop: 12,
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontSize: 12,
          color: "rgba(235,235,245,0.5)",
        }}
      >
        {totalItems === 0 ? `0 ${label}` : `${start}-${end} of ${totalItems} ${label}`}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            style={{
              height: 30,
              borderRadius: 8,
              border: "1px solid rgba(84,84,88,0.65)",
              background: "rgba(118,118,128,0.2)",
              color: "#FFFFFF",
              padding: "0 8px",
              fontFamily: FONT,
              fontSize: 12,
            }}
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option}/page
              </option>
            ))}
          </select>
        )}

        <button
          disabled={!canPrev}
          onClick={() => onPageChange(clampedPage - 1)}
          style={{
            height: 30,
            minWidth: 64,
            borderRadius: 8,
            border: "1px solid rgba(84,84,88,0.65)",
            background: canPrev ? "rgba(118,118,128,0.2)" : "rgba(118,118,128,0.08)",
            color: canPrev ? "#FFFFFF" : "rgba(235,235,245,0.35)",
            cursor: canPrev ? "pointer" : "not-allowed",
            fontFamily: FONT,
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          Prev
        </button>

        <div
          style={{
            minWidth: 64,
            textAlign: "center",
            fontFamily: FONT,
            fontSize: 12,
            color: "rgba(235,235,245,0.7)",
          }}
        >
          {clampedPage}/{totalPages}
        </div>

        <button
          disabled={!canNext}
          onClick={() => onPageChange(clampedPage + 1)}
          style={{
            height: 30,
            minWidth: 64,
            borderRadius: 8,
            border: "1px solid rgba(84,84,88,0.65)",
            background: canNext ? "rgba(118,118,128,0.2)" : "rgba(118,118,128,0.08)",
            color: canNext ? "#FFFFFF" : "rgba(235,235,245,0.35)",
            cursor: canNext ? "pointer" : "not-allowed",
            fontFamily: FONT,
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          Next
        </button>
      </div>
    </div>
  );
}
