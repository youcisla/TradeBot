import React from 'react';

export type ColumnDef<T> = {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  align?: 'left' | 'right' | 'center';
};

type DataTableProps<T> = {
  data: T[];
  columns: ColumnDef<T>[];
  loading?: boolean;
  onRowClick?: (row: T) => void;
};

export function DataTable<T>({ data, columns, loading, onRowClick }: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="w-full space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 bg-bg-3 animate-pulse rounded-sm" />
        ))}
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto border border-border rounded-sm">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="bg-bg-2 border-b border-border">
            {columns.map((col, i) => (
              <th key={i} className={`px-4 py-3 text-xs uppercase font-ui tracking-wider text-text-3 font-semibold text-${col.align || 'left'}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-text-3 font-ui italic">
                No data available
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr 
                key={i} 
                onClick={() => onRowClick?.(row)}
                className={`border-b border-border/50 hover:bg-bg-4 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
              >
                {columns.map((col, j) => (
                  <td key={j} className={`px-4 py-3 text-sm font-mono text-text-1 text-${col.align || 'left'}`}>
                    {col.cell ? col.cell(row) : String(row[col.accessorKey as keyof T] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
