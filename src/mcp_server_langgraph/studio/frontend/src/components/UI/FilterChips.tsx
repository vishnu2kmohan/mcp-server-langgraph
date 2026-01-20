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
    "px-3 py-1.5 text-sm font-medium rounded-full transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-neutral-12";

  if (isSelected) {
    switch (color) {
      case "green":
        return `${baseClasses} bg-success-3 text-success-11 ring-2 ring-success-7 dark:bg-success-a5 dark:text-success-5 focus:ring-success-7`;
      case "red":
        return `${baseClasses} bg-error-3 text-error-11 ring-2 ring-error-7 dark:bg-error-a5 dark:text-error-9 focus:ring-error-7`;
      case "yellow":
        return `${baseClasses} bg-warning-3 text-warning-11 ring-2 ring-warning-7 dark:bg-warning-a5 dark:text-warning-6 focus:ring-warning-7`;
      case "blue":
        return `${baseClasses} bg-primary-3 text-primary-11 ring-2 ring-primary-7 dark:bg-primary-a5 dark:text-primary-5 focus:ring-primary-7`;
      case "gray":
      default:
        return `${baseClasses} bg-neutral-3 text-neutral-12 ring-2 ring-neutral-8 focus:ring-neutral-8`;
    }
  } else {
    // Unselected state - subtle coloring based on the color
    switch (color) {
      case "green":
        return `${baseClasses} bg-neutral-2 text-neutral-11 hover:bg-success-1 hover:text-success-11 dark:hover:bg-success-a3 dark:hover:text-success-7 focus:ring-success-7`;
      case "red":
        return `${baseClasses} bg-neutral-2 text-neutral-11 hover:bg-error-1 hover:text-error-11 dark:hover:bg-error-a3 dark:hover:text-error-7 focus:ring-error-7`;
      case "yellow":
        return `${baseClasses} bg-neutral-2 text-neutral-11 hover:bg-warning-3 hover:text-warning-10 dark:hover:bg-warning-a3 dark:hover:text-warning-9 focus:ring-warning-7`;
      case "blue":
        return `${baseClasses} bg-neutral-2 text-neutral-11 hover:bg-primary-1 hover:text-primary-11 dark:hover:bg-primary-a3 dark:hover:text-primary-7 focus:ring-primary-7`;
      case "gray":
      default:
        return `${baseClasses} bg-neutral-2 text-neutral-11 hover:bg-neutral-3 focus:ring-neutral-8`;
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
