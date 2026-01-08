/**
 * CursorPagination
 *
 * Reusable cursor-based pagination component for list views.
 * Supports loading states, item counts, and accessibility.
 */

import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";

export interface CursorPaginationProps {
  hasNextPage: boolean;
  hasPreviousPage: boolean;
  onNextPage: () => void;
  onPreviousPage: () => void;
  isLoading?: boolean;
  itemCount?: number;
  totalCount?: number;
}

export function CursorPagination({
  hasNextPage,
  hasPreviousPage,
  onNextPage,
  onPreviousPage,
  isLoading = false,
  itemCount,
  totalCount,
}: CursorPaginationProps) {
  const isPreviousDisabled = !hasPreviousPage || isLoading;
  const isNextDisabled = !hasNextPage || isLoading;

  return (
    <div
      data-testid="cursor-pagination"
      className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700"
    >
      <div className="flex items-center gap-2">
        {isLoading && (
          <div data-testid="pagination-loading">
            <Loader2 className="w-4 h-4 animate-spin text-gray-400 dark:text-gray-400" />
          </div>
        )}
        {itemCount !== undefined && totalCount !== undefined && (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {itemCount} of {totalCount}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onPreviousPage}
          disabled={isPreviousDisabled}
          aria-label="Previous page"
          className={`
            flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg
            transition-colors
            ${
              isPreviousDisabled
                ? "text-gray-400 dark:text-gray-400 dark:text-gray-600 dark:text-gray-300 cursor-not-allowed"
                : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
            }
          `}
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>

        <button
          onClick={onNextPage}
          disabled={isNextDisabled}
          aria-label="Next page"
          className={`
            flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg
            transition-colors
            ${
              isNextDisabled
                ? "text-gray-400 dark:text-gray-400 dark:text-gray-600 dark:text-gray-300 cursor-not-allowed"
                : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
            }
          `}
        >
          Next
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export default CursorPagination;
