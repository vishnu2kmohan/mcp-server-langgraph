/**
 * CursorPagination
 *
 * Reusable cursor-based pagination component for list views.
 * Supports loading states, item counts, and accessibility.
 */

import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";

import { Button } from "@/components/UI";

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
      className="flex items-center justify-between px-4 py-3 bg-neutral-1 border-t border-neutral-5"
    >
      <div className="flex items-center gap-2">
        {isLoading && (
          <div data-testid="pagination-loading">
            <Loader2 className="w-4 h-4 animate-spin text-neutral-9" />
          </div>
        )}
        {itemCount !== undefined && totalCount !== undefined && (
          <span className="text-sm text-neutral-10">
            {itemCount} of {totalCount}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Button
          className="flex px-3 py-1.5 text-sm rounded-lg"
          onClick={onPreviousPage}
          disabled={isPreviousDisabled}
          aria-label="Previous page"
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </Button>

        <Button
          className="flex px-3 py-1.5 text-sm rounded-lg"
          onClick={onNextPage}
          disabled={isNextDisabled}
          aria-label="Next page"
        >
          Next
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}

export default CursorPagination;
