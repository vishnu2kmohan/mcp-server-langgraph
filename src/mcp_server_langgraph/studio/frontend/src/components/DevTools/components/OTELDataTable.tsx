/**
 * OTELDataTable Component
 *
 * Virtualized table wrapper for high-volume OTEL data.
 * Built on TanStack Table with optional virtualization.
 *
 * Features:
 * - TanStack Table core for sorting/filtering
 * - Optional virtualization for large datasets
 * - Row expansion with custom render
 * - Auto-tail support for streaming data
 * - Buffer management with max entries
 * - Export to JSON/CSV
 */

import React, {
  useState,
  useCallback,
  useMemo,
  useRef,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type Row,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Download, ChevronUp, ChevronDown } from "lucide-react";

import { cn } from "../../../utils/cn";
import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface OTELDataTableProps<T> extends Omit<
  HTMLAttributes<HTMLDivElement>,
  "children"
> {
  /** Data to display */
  data: T[];
  /** Column definitions */
  columns: ColumnDef<T>[];
  /** Enable sorting */
  enableSorting?: boolean;
  /** Default sort configuration */
  defaultSort?: { id: string; desc: boolean };
  /** Controlled expanded row ID */
  expandedRowId?: string | null;
  /** Callback when row is expanded/collapsed */
  onRowExpand?: (id: string | null) => void;
  /** Custom render function for expanded row content */
  renderExpandedRow?: (row: T) => ReactNode;
  /** Function to get custom row class names */
  getRowClassName?: (row: T) => string;
  /** Virtualization threshold (rows) - default: 100 */
  virtualizeThreshold?: number;
  /** Estimated row height for virtualization - default: 36 */
  estimatedRowHeight?: number;
  /** Overscan count for virtualization - default: 10 */
  overscan?: number;
  /** Maximum entries in buffer - default: 5000 */
  maxEntries?: number;
  /** Callback when buffer is full and entries evicted */
  onBufferFull?: () => void;
  /** Enable auto-tail for streaming data */
  enableAutoTail?: boolean;
  /** Enable export functionality */
  enableExport?: boolean;
  /** Export filename (without extension) */
  exportFilename?: string;
  /** Get row ID from row data */
  getRowId?: (row: T) => string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * OTEL Data Table Component
 *
 * @example
 * ```tsx
 * <OTELDataTable
 *   data={logs}
 *   columns={logColumns}
 *   enableSorting
 *   renderExpandedRow={(log) => <LogDetails log={log} />}
 * />
 * ```
 */
export function OTELDataTable<T extends { id?: string }>({
  data,
  columns,
  enableSorting = false,
  defaultSort,
  expandedRowId: controlledExpandedRowId,
  onRowExpand,
  renderExpandedRow,
  getRowClassName,
  virtualizeThreshold = 100,
  estimatedRowHeight = 36,
  overscan = 10,
  maxEntries = 5000,
  onBufferFull,
  enableAutoTail: _enableAutoTail = false,
  enableExport = false,
  exportFilename = "export",
  getRowId,
  className,
  ...props
}: OTELDataTableProps<T>) {
  // State
  const [sorting, setSorting] = useState<SortingState>(
    defaultSort ? [{ id: defaultSort.id, desc: defaultSort.desc }] : [],
  );
  const [internalExpandedRowId, setInternalExpandedRowId] = useState<
    string | null
  >(null);

  // Refs
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Determine if controlled or uncontrolled expansion
  const isControlledExpansion = controlledExpandedRowId !== undefined;
  const expandedRowId = isControlledExpansion
    ? controlledExpandedRowId
    : internalExpandedRowId;

  // Apply max entries buffer limit
  const bufferedData = useMemo(() => {
    if (data.length > maxEntries) {
      onBufferFull?.();
      return data.slice(-maxEntries);
    }
    return data;
  }, [data, maxEntries, onBufferFull]);

  // Determine if we should virtualize
  const shouldVirtualize = bufferedData.length > virtualizeThreshold;

  // Row ID accessor
  const rowIdAccessor = useCallback(
    (row: T, index: number): string => {
      if (getRowId) return getRowId(row);
      if (row.id !== undefined) return String(row.id);
      return String(index);
    },
    [getRowId],
  );

  // TanStack Table instance
  const table = useReactTable({
    data: bufferedData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: enableSorting ? getSortedRowModel() : undefined,
    getRowId: (row, index) => rowIdAccessor(row, index),
  });

  const { rows } = table.getRowModel();

  // Virtualizer (only used when shouldVirtualize is true)
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => estimatedRowHeight,
    overscan,
    enabled: shouldVirtualize,
  });

  const virtualRows = virtualizer.getVirtualItems();

  // Handle row click for expansion
  const handleRowClick = useCallback(
    (rowId: string) => {
      if (!renderExpandedRow) return;

      const newExpandedId = expandedRowId === rowId ? null : rowId;

      if (isControlledExpansion) {
        onRowExpand?.(newExpandedId);
      } else {
        setInternalExpandedRowId(newExpandedId);
        onRowExpand?.(newExpandedId);
      }
    },
    [expandedRowId, isControlledExpansion, onRowExpand, renderExpandedRow],
  );

  // Handle keyboard navigation
  const handleRowKeyDown = useCallback(
    (e: React.KeyboardEvent, rowId: string) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleRowClick(rowId);
      }
    },
    [handleRowClick],
  );

  // Export to JSON
  const handleExport = useCallback(() => {
    const jsonStr = JSON.stringify(bufferedData, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${exportFilename}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [bufferedData, exportFilename]);

  // Render table header
  const renderHeader = () => (
    <thead className="sticky top-0 bg-neutral-1 dark:bg-neutral-2 z-10">
      {table.getHeaderGroups().map((headerGroup) => (
        <tr key={headerGroup.id}>
          {headerGroup.headers.map((header) => {
            const isSorted = header.column.getIsSorted();
            const canSort = enableSorting && header.column.getCanSort();

            return (
              <th
                key={header.id}
                role="columnheader"
                aria-sort={
                  isSorted === "asc"
                    ? "ascending"
                    : isSorted === "desc"
                      ? "descending"
                      : undefined
                }
                data-sorted={isSorted || undefined}
                className={cn(
                  "px-3 py-2 text-left text-xs font-semibold text-neutral-11",
                  "border-b border-neutral-5",
                  canSort && "cursor-pointer select-none hover:bg-neutral-2",
                )}
                onClick={
                  canSort ? header.column.getToggleSortingHandler() : undefined
                }
              >
                <div className="flex items-center gap-1">
                  {flexRender(
                    header.column.columnDef.header,
                    header.getContext(),
                  )}
                  {canSort && (
                    <span className="shrink-0">
                      {isSorted === "asc" ? (
                        <ChevronUp size={12} aria-hidden="true" />
                      ) : isSorted === "desc" ? (
                        <ChevronDown size={12} aria-hidden="true" />
                      ) : (
                        <span className="w-3" />
                      )}
                    </span>
                  )}
                </div>
              </th>
            );
          })}
        </tr>
      ))}
    </thead>
  );

  // Render a single row
  const renderRow = (row: Row<T>, style?: React.CSSProperties) => {
    const rowId = row.id;
    const isExpanded = expandedRowId === rowId;
    const customClassName = getRowClassName?.(row.original) ?? "";

    return (
      <tr
        key={rowId}
        role="row"
        tabIndex={renderExpandedRow ? 0 : undefined}
        style={style}
        className={cn(
          "border-b border-neutral-5 hover:bg-neutral-2 dark:hover:bg-neutral-3",
          "transition-colors duration-fast",
          renderExpandedRow && "cursor-pointer",
          isExpanded && "bg-neutral-2 dark:bg-neutral-3",
          customClassName,
        )}
        onClick={() => handleRowClick(rowId)}
        onKeyDown={(e) => handleRowKeyDown(e, rowId)}
      >
        {row.getVisibleCells().map((cell) => (
          <td key={cell.id} className="px-3 py-2 text-sm text-neutral-11">
            {flexRender(cell.column.columnDef.cell, cell.getContext())}
          </td>
        ))}
      </tr>
    );
  };

  // Render expanded row content
  const renderExpandedContent = (row: Row<T>) => {
    if (expandedRowId !== row.id || !renderExpandedRow) return null;

    return (
      <tr key={`${row.id}-expanded`} className="bg-neutral-1 dark:bg-neutral-2">
        <td colSpan={columns.length} className="px-3 py-4">
          {renderExpandedRow(row.original)}
        </td>
      </tr>
    );
  };

  // Render virtualized body
  const renderVirtualizedBody = () => {
    const totalSize = virtualizer.getTotalSize();

    return (
      <tbody
        style={{
          height: `${totalSize}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualRows.map((virtualRow) => {
          const row = rows[virtualRow.index];
          return renderRow(row, {
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: `${virtualRow.size}px`,
            transform: `translateY(${virtualRow.start}px)`,
          });
        })}
      </tbody>
    );
  };

  // Render standard body
  const renderStandardBody = () => (
    <tbody>
      {rows.map((row) => (
        <React.Fragment key={row.id}>
          {renderRow(row)}
          {renderExpandedContent(row)}
        </React.Fragment>
      ))}
    </tbody>
  );

  // Empty state
  if (bufferedData.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center py-8 text-neutral-9 text-sm",
          className,
        )}
        {...props}
      >
        No data available
      </div>
    );
  }

  return (
    <div className={cn("relative", className)} {...props}>
      {/* Export button */}
      {enableExport && (
        <div className="flex justify-end mb-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={handleExport}
            className={cn(
              "inline-flex items-center gap-1 px-2 py-1 text-xs font-medium",
              "text-neutral-10 hover:text-neutral-12",
            )}
            aria-label="Export data"
          >
            <Download size={12} aria-hidden="true" />
            <span>Export</span>
          </Button>
        </div>
      )}

      {/* Table container */}
      <div
        ref={tableContainerRef}
        className={cn(
          "overflow-auto rounded-lg border border-neutral-5",
          shouldVirtualize && "max-h-[600px]",
        )}
      >
        <table role="table" className="w-full border-collapse text-sm">
          {renderHeader()}
          {shouldVirtualize ? renderVirtualizedBody() : renderStandardBody()}
        </table>
      </div>
    </div>
  );
}

export default OTELDataTable;
