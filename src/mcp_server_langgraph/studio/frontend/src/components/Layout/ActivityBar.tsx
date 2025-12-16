/**
 * ActivityBar Component
 *
 * JupyterLab/VS Code-style activity bar for quick navigation between sidebar views.
 *
 * Features:
 * - Vertical or horizontal orientation
 * - Icon buttons with tooltips
 * - Badge support for notifications
 * - Keyboard navigation
 * - Active state highlighting
 */

import { type ReactNode, type HTMLAttributes, useCallback } from "react";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface ActivityItem {
  /** Unique identifier for this item */
  id: string;
  /** Icon to display (React node, typically from lucide-react) */
  icon: ReactNode;
  /** Accessible label for the item */
  label: string;
  /** Optional badge count */
  badge?: number;
  /** Whether the item is disabled */
  disabled?: boolean;
}

export interface ActivityBarProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  "onSelect"
> {
  /** Activity items to display */
  items: ActivityItem[];
  /** Currently active item ID */
  activeId: string;
  /** Callback when an item is selected */
  onSelect: (id: string) => void;
  /** Bar orientation */
  orientation?: "vertical" | "horizontal";
  /** Additional class names */
  className?: string;
}

// =============================================================================
// ActivityBar - Main container
// =============================================================================

export function ActivityBar({
  items,
  activeId,
  onSelect,
  orientation = "vertical",
  className,
  ...props
}: ActivityBarProps) {
  const handleSelect = useCallback(
    (id: string) => {
      if (id !== activeId) {
        onSelect(id);
      }
    },
    [activeId, onSelect],
  );

  return (
    <div
      role="tablist"
      aria-orientation={orientation}
      className={cn(
        "flex gap-1 p-2",
        "bg-gray-100 dark:bg-gray-800",
        orientation === "vertical" ? "flex-col" : "flex-row",
        className,
      )}
      {...props}
    >
      {items.map((item) => (
        <ActivityBarItem
          key={item.id}
          id={item.id}
          icon={item.icon}
          label={item.label}
          badge={item.badge}
          disabled={item.disabled}
          isActive={activeId === item.id}
          onClick={() => handleSelect(item.id)}
        />
      ))}
    </div>
  );
}

// =============================================================================
// ActivityBarItem - Individual item button
// =============================================================================

export interface ActivityBarItemProps {
  /** Item ID */
  id: string;
  /** Icon to display */
  icon: ReactNode;
  /** Accessible label */
  label: string;
  /** Optional badge count */
  badge?: number;
  /** Whether the item is disabled */
  disabled?: boolean;
  /** Whether this item is currently active */
  isActive: boolean;
  /** Click handler */
  onClick: () => void;
}

export function ActivityBarItem({
  icon,
  label,
  badge,
  disabled = false,
  isActive,
  onClick,
}: ActivityBarItemProps) {
  const handleClick = useCallback(() => {
    if (!disabled && !isActive) {
      onClick();
    }
  }, [disabled, isActive, onClick]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (
        (event.key === "Enter" || event.key === " ") &&
        !disabled &&
        !isActive
      ) {
        event.preventDefault();
        onClick();
      }
    },
    [disabled, isActive, onClick],
  );

  // Format badge display
  const displayBadge =
    badge !== undefined ? (badge > 99 ? "99+" : String(badge)) : null;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        "relative p-2.5 rounded-lg transition-all",
        "focus:outline-none focus:ring-2 focus:ring-primary-500",
        // Active state
        isActive && "bg-primary-100 dark:bg-primary-900/30",
        isActive && "text-primary-700 dark:text-primary-300",
        // Inactive state
        !isActive && "text-gray-500 dark:text-gray-400",
        !isActive && "hover:bg-gray-200 dark:hover:bg-gray-700",
        !isActive && "hover:text-gray-700 dark:hover:text-gray-200",
        // Disabled state
        disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      {/* Icon */}
      <span className="block">{icon}</span>

      {/* Badge */}
      {displayBadge && (
        <span
          className={cn(
            "absolute -top-0.5 -right-0.5",
            "min-w-[18px] h-[18px] px-1",
            "flex items-center justify-center",
            "text-[10px] font-bold",
            "bg-red-500 text-white",
            "rounded-full",
          )}
        >
          {displayBadge}
        </span>
      )}
    </button>
  );
}

export default ActivityBar;
