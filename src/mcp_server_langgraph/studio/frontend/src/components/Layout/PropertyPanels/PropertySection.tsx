/**
 * PropertySection Component
 *
 * Collapsible section for property panels.
 */

import { ChevronRight, ChevronDown } from "lucide-react";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface PropertySectionProps {
  id: string;
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  /** Optional badge to show in header */
  badge?: React.ReactNode;
}

// =============================================================================
// Component
// =============================================================================

export function PropertySection({
  title,
  isExpanded,
  onToggle,
  children,
  badge,
}: PropertySectionProps) {
  return (
    <div
      data-testid={`property-section-${title.toLowerCase().replace(/\s+/g, "-")}`}
      className="border-b border-gray-200 dark:border-gray-700 last:border-b-0"
    >
      <button
        type="button"
        onClick={onToggle}
        className={cn(
          "w-full flex items-center gap-2 px-3 py-2",
          "text-xs font-semibold tracking-wider",
          "text-gray-600 dark:text-gray-300",
          "hover:bg-gray-100 dark:hover:bg-gray-700/50",
          "transition-colors",
        )}
      >
        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span className="flex-1 text-left">{title}</span>
        {badge && <span>{badge}</span>}
      </button>
      {isExpanded && <div className="px-3 pb-3 space-y-2">{children}</div>}
    </div>
  );
}

export default PropertySection;
