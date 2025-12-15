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
    "px-3 py-1.5 text-sm font-medium rounded-full transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-900";

  if (isSelected) {
    switch (color) {
      case "green":
        return `${baseClasses} bg-green-100 text-green-800 ring-2 ring-green-500 dark:bg-green-900/40 dark:text-green-300 focus:ring-green-500`;
      case "red":
        return `${baseClasses} bg-red-100 text-red-800 ring-2 ring-red-500 dark:bg-red-900/40 dark:text-red-300 focus:ring-red-500`;
      case "yellow":
        return `${baseClasses} bg-yellow-100 text-yellow-800 ring-2 ring-yellow-500 dark:bg-yellow-900/40 dark:text-yellow-300 focus:ring-yellow-500`;
      case "blue":
        return `${baseClasses} bg-blue-100 text-blue-800 ring-2 ring-blue-500 dark:bg-blue-900/40 dark:text-blue-300 focus:ring-blue-500`;
      case "gray":
      default:
        return `${baseClasses} bg-gray-200 text-gray-900 ring-2 ring-gray-500 dark:bg-gray-700 dark:text-gray-100 focus:ring-gray-500`;
    }
  } else {
    // Unselected state - subtle coloring based on the color
    switch (color) {
      case "green":
        return `${baseClasses} bg-gray-100 text-gray-700 hover:bg-green-50 hover:text-green-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-green-900/20 dark:hover:text-green-400 focus:ring-green-500`;
      case "red":
        return `${baseClasses} bg-gray-100 text-gray-700 hover:bg-red-50 hover:text-red-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-red-900/20 dark:hover:text-red-400 focus:ring-red-500`;
      case "yellow":
        return `${baseClasses} bg-gray-100 text-gray-700 hover:bg-yellow-50 hover:text-yellow-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-yellow-900/20 dark:hover:text-yellow-400 focus:ring-yellow-500`;
      case "blue":
        return `${baseClasses} bg-gray-100 text-gray-700 hover:bg-blue-50 hover:text-blue-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-blue-900/20 dark:hover:text-blue-400 focus:ring-blue-500`;
      case "gray":
      default:
        return `${baseClasses} bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 focus:ring-gray-500`;
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
          <button
            key={option.value}
            type="button"
            onClick={() => handleClick(option.value)}
            className={getChipClasses(option.color, isSelected)}
            aria-pressed={isSelected}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
