/**
 * SortDropdown Component
 *
 * Reusable component for selecting sort field and order.
 * Features:
 * - Sort field selection via dropdown
 * - Sort order toggle (asc/desc)
 * - Optional clear option
 * - Loading and disabled states
 * - Accessibility support
 */

import { ArrowUpAZ, ArrowDownAZ } from "lucide-react";

import { Button } from "@/components/UI";

/**
 * Sort option definition
 */
export interface SortOption {
  /** Value to use in API call */
  value: string;
  /** Display label */
  label: string;
}

/**
 * Sort order type
 */
export type SortOrder = "asc" | "desc";

/**
 * Props for SortDropdown component
 */
export interface SortDropdownProps {
  /** Available sort options */
  options: SortOption[];
  /** Current sort field value */
  sortBy: string;
  /** Current sort order */
  sortOrder: SortOrder;
  /** Callback when sort changes */
  onChange: (sortBy: string, sortOrder: SortOrder) => void;
  /** Label text */
  label?: string;
  /** Whether to show clear option */
  allowClear?: boolean;
  /** Whether dropdown is disabled */
  disabled?: boolean;
  /** Whether loading */
  isLoading?: boolean;
  /** Aria label for dropdown */
  ariaLabel?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * SortDropdown component
 */
export function SortDropdown({
  options,
  sortBy,
  sortOrder,
  onChange,
  label,
  allowClear = false,
  disabled = false,
  isLoading = false,
  ariaLabel,
  className = "",
}: SortDropdownProps) {
  const isDisabled = disabled || isLoading;

  /**
   * Handle field change
   */
  const handleFieldChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange(e.target.value, sortOrder);
  };

  /**
   * Handle order toggle
   */
  const handleOrderToggle = () => {
    const newOrder: SortOrder = sortOrder === "asc" ? "desc" : "asc";
    onChange(sortBy, newOrder);
  };

  return (
    <div
      data-testid="sort-dropdown"
      className={`flex items-center gap-2 ${className}`}
    >
      {label && (
        <label className="text-sm text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
          {label}
        </label>
      )}
      <select
        value={sortBy}
        onChange={handleFieldChange}
        disabled={isDisabled}
        aria-label={ariaLabel ?? "Sort by"}
        className="px-3 py-1.5 text-sm border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {allowClear && <option value="">None</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <Button
        variant="secondary"
        className="p-1.5 border border-neutral-300 dark:border-neutral-600 rounded-md bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-50 dark:hover:bg-neutral-700 focus:ring-primary-500"
        type="button"
        onClick={handleOrderToggle}
        disabled={isDisabled}
        aria-label="Sort order"
      >
        {sortOrder === "asc" ? (
          <ArrowUpAZ size={16} data-testid="sort-asc-icon" />
        ) : (
          <ArrowDownAZ size={16} data-testid="sort-desc-icon" />
        )}
      </Button>
    </div>
  );
}
