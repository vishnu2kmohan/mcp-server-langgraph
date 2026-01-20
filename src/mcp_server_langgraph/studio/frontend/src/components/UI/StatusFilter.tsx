/**
 * StatusFilter Component
 *
 * Reusable component for filtering by status with a design system dropdown.
 * Features:
 * - Single select via dropdown (uses design system Select)
 * - "All" option to clear filter
 * - Accessibility support
 * - Consistent styling with design system
 *
 * @example
 * ```tsx
 * <StatusFilter
 *   options={[
 *     { value: "active", label: "Active" },
 *     { value: "archived", label: "Archived" },
 *   ]}
 *   value={statusFilter}
 *   onChange={setStatusFilter}
 *   ariaLabel="Filter by status"
 * />
 * ```
 */

import { Select, type SelectSize } from "./Select";
import { cn } from "@/utils/cn";

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
  /** Size variant */
  size?: SelectSize;
  /** Whether the filter is disabled */
  disabled?: boolean;
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
  size = "sm",
  disabled = false,
  className = "",
}: StatusFilterProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newValue = e.target.value;
    onChange(newValue === "" ? null : newValue);
  };

  // Convert StatusOptions to SelectOptions
  const selectOptions = [
    { value: "", label: allLabel },
    ...options,
  ];

  return (
    <div data-testid="status-filter" className={cn("inline-block", className)}>
      <Select
        value={value ?? ""}
        onChange={handleChange}
        aria-label={ariaLabel}
        size={size}
        disabled={disabled}
        fullWidth={false}
      >
        {selectOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </div>
  );
}
