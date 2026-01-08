/**
 * DataExplorer - Phase 2
 *
 * Dynamic data exploration dashboard with sorting,
 * filtering, search, and pagination.
 */
import { useState, useCallback, useMemo } from "react";
import {
  Search,
  Download,
  ChevronUp,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface ColumnConfig {
  id: string;
  label: string;
  type: "string" | "number" | "date" | "boolean";
  sortable?: boolean;
  filterable?: boolean;
}

export interface DataExplorerConfig {
  id: string;
  title: string;
  dataSource?: string;
  columns: ColumnConfig[];
  data: Record<string, unknown>[];
  pageSize?: number;
}

export interface DataExplorerProps {
  config: DataExplorerConfig;
  isLoading?: boolean;
  onSort?: (columnId: string, direction: "asc" | "desc") => void;
  onFilter?: (columnId: string, value: string) => void;
  onSearch?: (query: string) => void;
  onPageChange?: (page: number) => void;
  onExport?: () => void;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function DataExplorer({
  config,
  isLoading = false,
  onSort,
  onFilter,
  onSearch,
  onPageChange,
  onExport,
  className,
}: DataExplorerProps) {
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const pageSize = config.pageSize || config.data.length;
  const totalPages = Math.ceil(config.data.length / pageSize);

  const handleSort = useCallback(
    (columnId: string) => {
      const column = config.columns.find((c) => c.id === columnId);
      if (!column?.sortable) return;

      const newDirection =
        sortColumn === columnId && sortDirection === "asc" ? "desc" : "asc";
      setSortColumn(columnId);
      setSortDirection(newDirection);
      onSort?.(columnId, newDirection);
    },
    [config.columns, sortColumn, sortDirection, onSort],
  );

  const handleFilter = useCallback(
    (columnId: string, value: string) => {
      setFilters((prev) => ({ ...prev, [columnId]: value }));
      onFilter?.(columnId, value);
    },
    [onFilter],
  );

  const handleSearch = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setSearchQuery(value);
      onSearch?.(value);
    },
    [onSearch],
  );

  const handlePageChange = useCallback(
    (page: number) => {
      setCurrentPage(page);
      onPageChange?.(page);
    },
    [onPageChange],
  );

  // Paginated data
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return config.data.slice(start, end);
  }, [config.data, currentPage, pageSize]);

  const filterableColumns = config.columns.filter((c) => c.filterable);

  return (
    <div
      data-testid="data-explorer"
      className={cn(
        "bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="font-semibold text-gray-900 dark:text-gray-100">
          {config.title}
        </h2>

        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-400"
            />
            <input
              data-testid="search-input"
              type="text"
              value={searchQuery}
              onChange={handleSearch}
              placeholder="Search..."
              className="pl-9 pr-3 py-1.5 text-sm rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>

          {/* Export */}
          <button
            data-testid="export-button"
            type="button"
            onClick={onExport}
            className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:hover:text-gray-300 transition-colors"
            aria-label="Export data"
          >
            <Download size={18} />
          </button>
        </div>
      </div>

      {/* Filters */}
      {filterableColumns.length > 0 && (
        <div className="flex gap-3 p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          {filterableColumns.map((column) => (
            <input
              key={column.id}
              data-testid={`filter-${column.id}`}
              type="text"
              value={filters[column.id] || ""}
              onChange={(e) => handleFilter(column.id, e.target.value)}
              placeholder={`Filter ${column.label}...`}
              className="px-2 py-1 text-sm rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          ))}
        </div>
      )}

      {/* Table */}
      <div className="relative overflow-x-auto">
        {isLoading && (
          <div
            data-testid="loading-overlay"
            className="absolute inset-0 bg-white/50 dark:bg-gray-900/50 flex items-center justify-center z-10"
          >
            <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
          </div>
        )}

        {config.data.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            No data available
          </div>
        ) : (
          <table role="table" className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                {config.columns.map((column) => (
                  <th
                    key={column.id}
                    role="columnheader"
                    scope="col"
                    data-sortable={column.sortable ? "true" : "false"}
                    onClick={() => handleSort(column.id)}
                    className={cn(
                      "px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-400",
                      column.sortable &&
                        "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/50",
                    )}
                  >
                    <div className="flex items-center gap-1">
                      {column.label}
                      {column.sortable &&
                        sortColumn === column.id &&
                        (sortDirection === "asc" ? (
                          <ChevronUp size={14} />
                        ) : (
                          <ChevronDown size={14} />
                        ))}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900/30"
                >
                  {config.columns.map((column) => (
                    <td
                      key={column.id}
                      className="px-4 py-3 text-gray-900 dark:text-gray-100"
                    >
                      {String(row[column.id] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {config.pageSize && totalPages > 1 && (
        <div
          data-testid="pagination"
          className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700"
        >
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Page {currentPage} of {totalPages}
          </span>

          <div className="flex items-center gap-2">
            <button
              data-testid="prev-page"
              type="button"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              data-testid="next-page"
              type="button"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
