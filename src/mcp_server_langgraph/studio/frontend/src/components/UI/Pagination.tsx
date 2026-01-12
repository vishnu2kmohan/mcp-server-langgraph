/**
 * Pagination Components
 *
 * Reusable pagination components for cursor-based and page-based navigation.
 * Features:
 * - CursorPagination: For cursor-based APIs (prev/next only)
 * - PagePagination: For page-based APIs (numbered pages)
 * - Items per page selection
 * - Loading states
 * - Accessibility support
 */

import { ChevronLeft, ChevronRight, MoreHorizontal } from "lucide-react";

import { Button } from "@/components/UI";

/**
 * Props for CursorPagination component
 */
export interface CursorPaginationProps {
  /** Whether there are more items after current page */
  hasNext: boolean;
  /** Whether there are items before current page */
  hasPrev: boolean;
  /** Callback when next is clicked */
  onNext: () => void;
  /** Callback when prev is clicked */
  onPrev: () => void;
  /** Whether pagination is loading */
  isLoading?: boolean;
  /** Total item count (optional) */
  itemCount?: number;
  /** Show limit selector */
  showLimitSelector?: boolean;
  /** Current limit value */
  limit?: number;
  /** Callback when limit changes */
  onLimitChange?: (limit: number) => void;
  /** Available limit options */
  limitOptions?: number[];
  /** Additional CSS classes */
  className?: string;
}

/**
 * Cursor-based pagination component
 * Used for APIs that use cursor/token-based pagination
 */
export function CursorPagination({
  hasNext,
  hasPrev,
  onNext,
  onPrev,
  isLoading = false,
  itemCount,
  showLimitSelector = false,
  limit = 20,
  onLimitChange,
  limitOptions = [10, 20, 50, 100],
  className = "",
}: CursorPaginationProps) {
  const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLimit = parseInt(e.target.value, 10);
    onLimitChange?.(newLimit);
  };

  return (
    <nav
      aria-label="Pagination"
      className={`flex items-center justify-between gap-4 ${className}`}
    >
      <div className="flex items-center gap-2">
        {itemCount !== undefined && (
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {itemCount} items
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {showLimitSelector && (
          <div className="flex items-center gap-2">
            <label
              htmlFor="limit-select"
              className="text-sm text-neutral-500 dark:text-neutral-400"
            >
              Show:
            </label>
            <select
              id="limit-select"
              value={limit}
              onChange={handleLimitChange}
              className="px-2 py-1 text-sm border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100"
              disabled={isLoading}
            >
              {limitOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            className="flex px-3 py-1.5 text-sm text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:hover:bg-white dark:disabled:hover:bg-neutral-800"
            onClick={onPrev}
            disabled={!hasPrev || isLoading}
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
            Previous
          </Button>

          <Button
            variant="secondary"
            className="flex px-3 py-1.5 text-sm text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:hover:bg-white dark:disabled:hover:bg-neutral-800"
            onClick={onNext}
            disabled={!hasNext || isLoading}
            aria-label="Next page"
          >
            Next
            <ChevronRight size={16} />
          </Button>
        </div>
      </div>
    </nav>
  );
}

/**
 * Props for PagePagination component
 */
export interface PagePaginationProps {
  /** Current page number (1-indexed) */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Callback when page changes */
  onPageChange: (page: number) => void;
  /** Whether pagination is loading */
  isLoading?: boolean;
  /** Total item count (optional) */
  totalItems?: number;
  /** Items per page (optional) */
  perPage?: number;
  /** Callback when per page changes */
  onPerPageChange?: (perPage: number) => void;
  /** Available per page options */
  perPageOptions?: number[];
  /** Maximum number of page buttons to show */
  maxPageButtons?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Generate array of page numbers to display
 */
function getPageNumbers(
  currentPage: number,
  totalPages: number,
  maxButtons: number,
): (number | "ellipsis")[] {
  if (totalPages <= maxButtons) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | "ellipsis")[] = [];
  const halfButtons = Math.floor(maxButtons / 2);

  // Always show first page
  pages.push(1);

  // Calculate start and end of middle section
  let start = Math.max(2, currentPage - halfButtons + 1);
  let end = Math.min(totalPages - 1, currentPage + halfButtons - 1);

  // Adjust if we're near the beginning
  if (currentPage <= halfButtons) {
    end = Math.min(totalPages - 1, maxButtons - 2);
  }

  // Adjust if we're near the end
  if (currentPage > totalPages - halfButtons) {
    start = Math.max(2, totalPages - maxButtons + 3);
  }

  // Add ellipsis before middle section if needed
  if (start > 2) {
    pages.push("ellipsis");
  }

  // Add middle pages
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  // Add ellipsis after middle section if needed
  if (end < totalPages - 1) {
    pages.push("ellipsis");
  }

  // Always show last page
  if (totalPages > 1) {
    pages.push(totalPages);
  }

  return pages;
}

/**
 * Page-based pagination component
 * Used for APIs that use page/per_page pagination
 */
export function PagePagination({
  currentPage,
  totalPages,
  onPageChange,
  isLoading = false,
  totalItems,
  perPage,
  onPerPageChange,
  perPageOptions = [10, 20, 50, 100],
  maxPageButtons = 7,
  className = "",
}: PagePaginationProps) {
  const pageNumbers = getPageNumbers(currentPage, totalPages, maxPageButtons);

  const handlePerPageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newPerPage = parseInt(e.target.value, 10);
    onPerPageChange?.(newPerPage);
  };

  return (
    <nav
      aria-label="Pagination"
      className={`flex items-center justify-between gap-4 ${className}`}
    >
      <div className="flex items-center gap-4">
        {totalItems !== undefined && (
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {totalItems} items
          </span>
        )}

        {perPage !== undefined && onPerPageChange && (
          <div className="flex items-center gap-2">
            <label
              htmlFor="perpage-select"
              className="text-sm text-neutral-500 dark:text-neutral-400"
            >
              Show:
            </label>
            <select
              id="perpage-select"
              value={perPage}
              onChange={handlePerPageChange}
              className="px-2 py-1 text-sm border border-neutral-300 dark:border-neutral-600 rounded bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100"
              disabled={isLoading}
            >
              {perPageOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      <div className="flex items-center gap-1">
        {/* Previous button */}
        <Button
          variant="secondary"
          size="sm"
          className="flex px-2 py-1.5 text-sm text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:hover:bg-white dark:disabled:hover:bg-neutral-800"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1 || isLoading}
          aria-label="Previous page"
        >
          <ChevronLeft size={16} />
          <span className="sr-only sm:not-sr-only">Previous</span>
        </Button>

        {/* Page numbers */}
        <div className="hidden sm:flex items-center gap-1">
          {pageNumbers.map((page, index) =>
            page === "ellipsis" ? (
              <span
                key={`ellipsis-${index}`}
                className="px-2 py-1 text-neutral-500 dark:text-neutral-400"
              >
                <MoreHorizontal size={16} aria-label="..." />
                <span className="sr-only">...</span>
              </span>
            ) : (
              <Button
                className="px-3 py-1.5 text-sm rounded-md"
                key={page}
                onClick={() => onPageChange(page)}
                disabled={isLoading}
                aria-label={`Page ${page}`}
                aria-current={page === currentPage ? "page" : undefined}
              >
                {page}
              </Button>
            ),
          )}
        </div>

        {/* Mobile: just show current page */}
        <span className="sm:hidden px-3 py-1.5 text-sm text-neutral-700 dark:text-neutral-300">
          {currentPage} / {totalPages}
        </span>

        {/* Next button */}
        <Button
          variant="secondary"
          size="sm"
          className="flex px-2 py-1.5 text-sm text-neutral-700 dark:text-neutral-300 bg-white dark:bg-neutral-800 border border-neutral-300 dark:border-neutral-600 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-700 disabled:hover:bg-white dark:disabled:hover:bg-neutral-800"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages || isLoading}
          aria-label="Next page"
        >
          <span className="sr-only sm:not-sr-only">Next</span>
          <ChevronRight size={16} />
        </Button>
      </div>
    </nav>
  );
}
