import { Button } from "@/components/UI";
/**
 * FilterChips Component
 *
 * Reusable component for filtering with clickable chips.
 * Follows best practices for filter UI:
 * - No "All" dropdown - clicking a selected chip toggles it off
 * - Visual indication of selected state
 * - Accessible with proper ARIA attributes
 * - Optional color coding for semantic meaning
 */

/**
 * Filter option definition
 */
export interface FilterOption {
  /** Value to use in API call */
  value: string;
  /** Display label */
  label: string;
  /** Optional color for semantic indication (green, red, yellow, gray, blue) */
  color?: string;
}

/**
 * Props for FilterChips component
 */
export interface FilterChipsProps {
  /** Available filter options */
  options: FilterOption[];
  /** Current selected value (null means none selected) */
  value: string | null;
  /** Callback when value changes */
  onChange: (value: string | null) => void;
  /** Aria label for the filter group */
  ariaLabel?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Get chip color classes based on color name and selected state
 */
function getChipClasses(
  color: string | undefined,
  isSelected: boolean,
): string {
  const baseClasses =
    "px-3 py-1.5 text-sm font-medium rounded-full transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-neutral-900";

  if (isSelected) {
    switch (color) {
      case "green":
        return `${baseClasses} bg-success-100 text-success-800 ring-2 ring-success-500 dark:bg-success-900/40 dark:text-success-300 focus:ring-success-500`;
      case "red":
        return `${baseClasses} bg-error-100 text-error-800 ring-2 ring-error-500 dark:bg-error-900/40 dark:text-error-300 focus:ring-error-500`;
      case "yellow":
        return `${baseClasses} bg-warning-100 text-warning-800 ring-2 ring-warning-500 dark:bg-warning-900/40 dark:text-warning-300 focus:ring-warning-500`;
      case "blue":
        return `${baseClasses} bg-primary-100 text-primary-800 ring-2 ring-primary-500 dark:bg-primary-900/40 dark:text-primary-300 focus:ring-primary-500`;
      case "gray":
      default:
        return `${baseClasses} bg-neutral-200 text-neutral-900 ring-2 ring-neutral-500 dark:bg-neutral-700 dark:text-neutral-100 focus:ring-neutral-500`;
    }
  } else {
    // Unselected state - subtle coloring based on the color
    switch (color) {
      case "green":
        return `${baseClasses} bg-neutral-100 text-neutral-700 hover:bg-success-50 hover:text-success-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-success-900/20 dark:hover:text-success-400 focus:ring-success-500`;
      case "red":
        return `${baseClasses} bg-neutral-100 text-neutral-700 hover:bg-error-50 hover:text-error-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-error-900/20 dark:hover:text-error-400 focus:ring-error-500`;
      case "yellow":
        return `${baseClasses} bg-neutral-100 text-neutral-700 hover:bg-warning-50 hover:text-warning-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-warning-900/20 dark:hover:text-warning-400 focus:ring-warning-500`;
      case "blue":
        return `${baseClasses} bg-neutral-100 text-neutral-700 hover:bg-primary-50 hover:text-primary-700 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-primary-900/20 dark:hover:text-primary-400 focus:ring-primary-500`;
      case "gray":
      default:
        return `${baseClasses} bg-neutral-100 text-neutral-700 hover:bg-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:hover:bg-neutral-700 focus:ring-neutral-500`;
    }
  }
}

/**
 * FilterChips component - clickable filter chips
 */
export function FilterChips({
  options,
  value,
  onChange,
  ariaLabel = "Filter options",
  className = "",
}: FilterChipsProps) {
  const handleClick = (optionValue: string) => {
    // Toggle off if clicking the already selected option
    if (value === optionValue) {
      onChange(null);
    } else {
      onChange(optionValue);
    }
  };

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`flex flex-wrap gap-2 ${className}`}
    >
      {options.map((option) => {
        const isSelected = value === option.value;
        return (
          <Button
            key={option.value}
            type="button"
            onClick={() => handleClick(option.value)}
            className={getChipClasses(option.color, isSelected)}
            aria-pressed={isSelected}
          >
            {option.label}
          </Button>
        );
      })}
    </div>
  );
}
