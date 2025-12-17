/**
 * PropertyRow Component
 *
 * A single row displaying a label-value pair in property panels.
 */

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface PropertyRowProps {
  label: string;
  value: string | number | React.ReactNode;
  /** Optional mono-space styling for IDs/codes */
  mono?: boolean;
  /** Optional action button */
  action?: React.ReactNode;
}

// =============================================================================
// Component
// =============================================================================

export function PropertyRow({ label, value, mono, action }: PropertyRowProps) {
  return (
    <div className="flex justify-between items-center text-xs gap-2">
      <span className="text-gray-500 dark:text-gray-400 flex-shrink-0">
        {label}
      </span>
      <div className="flex items-center gap-1">
        <span
          className={cn(
            "text-gray-700 dark:text-gray-200 font-medium truncate",
            mono && "font-mono text-[10px]",
          )}
        >
          {value}
        </span>
        {action}
      </div>
    </div>
  );
}

export default PropertyRow;
