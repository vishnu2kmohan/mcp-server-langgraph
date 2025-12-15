/**
 * TableArtifact Component
 *
 * Renders a data table with sorting and filtering capabilities.
 * Features:
 * - Column sorting (ascending/descending)
 * - Row click handling
 * - Export functionality
 * - Expandable/collapsible view
 * - Responsive design
 */

import { useState, useMemo } from "react";
import {
  ChevronUp,
  ChevronDown,
  Download,
  Maximize2,
  Minimize2,
  Table,
} from "lucide-react";

export interface TableColumn {
  key: string;
  label: string;
  sortable?: boolean;
  type?: "string" | "number" | "date";
}

export interface TableArtifactProps {
  title: string;
  columns: TableColumn[];
  data: Record<string, unknown>[];
  onRowClick?: (row: Record<string, unknown>) => void;
  onExport?: () => void;
  expandable?: boolean;
  className?: string;
}

type SortDirection = "asc" | "desc" | null;

interface SortConfig {
  key: string;
  direction: SortDirection;
}

/**
 * Compare two values for sorting
 */
function compareValues(
  a: unknown,
  b: unknown,
  type: "string" | "number" | "date" = "string",
): number {
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;

  if (type === "number") {
    return (a as number) - (b as number);
  }

  if (type === "date") {
    return new Date(a as string).getTime() - new Date(b as string).getTime();
  }

  return String(a).localeCompare(String(b));
}

export function TableArtifact({
  title,
  columns,
  data,
  onRowClick,
  onExport,
  expandable = false,
  className = "",
}: TableArtifactProps) {
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: "",
    direction: null,
  });
  const [isExpanded, setIsExpanded] = useState(false);

  // Sort data based on current config
  const sortedData = useMemo(() => {
    if (!sortConfig.key || !sortConfig.direction) {
      return data;
    }

    const column = columns.find((c) => c.key === sortConfig.key);
    const type = column?.type || "string";

    return [...data].sort((a, b) => {
      const aValue = a[sortConfig.key];
      const bValue = b[sortConfig.key];
      const comparison = compareValues(aValue, bValue, type);
      return sortConfig.direction === "desc" ? -comparison : comparison;
    });
  }, [data, sortConfig, columns]);

  const handleSort = (key: string) => {
    const column = columns.find((c) => c.key === key);
    if (!column?.sortable) return;

    setSortConfig((prev) => {
      if (prev.key !== key) {
        return { key, direction: "asc" };
      }
      if (prev.direction === "asc") {
        return { key, direction: "desc" };
      }
      return { key: "", direction: null };
    });
  };

  const handleExport = () => {
    if (onExport) {
      onExport();
    } else {
      // Default CSV export
      const headers = columns.map((c) => c.label).join(",");
      const rows = sortedData.map((row) =>
        columns.map((c) => String(row[c.key] ?? "")).join(","),
      );
      const csv = [headers, ...rows].join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_")}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const renderSortIndicator = (key: string) => {
    if (sortConfig.key !== key) {
      return <span className="w-4" />;
    }
    return sortConfig.direction === "asc" ? (
      <ChevronUp size={14} />
    ) : (
      <ChevronDown size={14} />
    );
  };

  return (
    <div
      className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden ${className}`}
      data-testid="table-artifact"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Table size={16} className="text-gray-500 dark:text-gray-400" />
          <h3 className="font-medium text-gray-900 dark:text-gray-100">
            {title}
          </h3>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            ({sortedData.length} rows)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExport}
            className="flex items-center gap-1 px-2 py-1 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            aria-label="Export CSV"
          >
            <Download size={14} />
            Export
          </button>
          {expandable && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              aria-label={isExpanded ? "Collapse table" : "Expand table"}
            >
              {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      {data.length === 0 ? (
        <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
          No data available
        </div>
      ) : (
        <div
          className={`overflow-x-auto ${isExpanded ? "max-h-none" : "max-h-96"}`}
        >
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.key}
                    className={`px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider ${
                      column.sortable
                        ? "cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
                        : ""
                    }`}
                    onClick={() => handleSort(column.key)}
                  >
                    <div className="flex items-center gap-1">
                      <span>{column.label}</span>
                      {column.sortable && renderSortIndicator(column.key)}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {sortedData.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className={`${
                    onRowClick
                      ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50"
                      : ""
                  }`}
                  onClick={() => onRowClick?.(row)}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100 whitespace-nowrap"
                    >
                      {String(row[column.key] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
