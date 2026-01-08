/**
 * StatusFilter Component
 *
 * Reusable component for filtering by status with a simple dropdown.
 * Features:
 * - Single select via dropdown
 * - "All" option to clear filter
 * - Accessibility support
 */

/**
 * Status option definition
 */
export interface StatusOption {
  /** Value to use in API call */
  value: string;
  /** Display label */
  label: string;
}

/**
 * Props for StatusFilter component
 */
export interface StatusFilterProps {
  /** Available status options */
  options: StatusOption[];
  /** Current selected status value (null means "all") */
  value: string | null;
  /** Callback when status changes */
  onChange: (value: string | null) => void;
  /** Label for the "All" option (default: "All") */
  allLabel?: string;
  /** Aria label for the select */
  ariaLabel?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * StatusFilter component
 */
export function StatusFilter({
  options,
  value,
  onChange,
  allLabel = "All",
  ariaLabel = "Status",
  className = "",
}: StatusFilterProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newValue = e.target.value;
    onChange(newValue === "" ? null : newValue);
  };

  return (
    <div data-testid="status-filter" className={`inline-block ${className}`}>
      <select
        value={value ?? ""}
        onChange={handleChange}
        aria-label={ariaLabel}
        className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
