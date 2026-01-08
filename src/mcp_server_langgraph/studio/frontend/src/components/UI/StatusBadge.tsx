/**
 * StatusBadge Component
 *
 * A semantic status badge component that uses the design system colors.
 * Provides consistent styling for status indicators across the application.
 *
 * Uses STATUS_BADGE_STYLES from utils/colors for centralized color management.
 */

import { type HTMLAttributes, type ReactNode } from "react";
import { CheckCircle, AlertCircle, XCircle, Info, Circle } from "lucide-react";
import { STATUS_BADGE_STYLES, type StatusBadgeType } from "../../utils/colors";

export type StatusBadgeSize = "sm" | "md" | "lg";

export interface StatusBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /** Status type determines the color scheme */
  status: StatusBadgeType;
  /** Size of the badge */
  size?: StatusBadgeSize;
  /** Custom icon to display */
  icon?: ReactNode;
  /** Show default icon for status type */
  showIcon?: boolean;
  /** Render as pill (fully rounded) */
  pill?: boolean;
  /** Children content */
  children: ReactNode;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Get size-specific classes
 */
function getSizeClasses(size: StatusBadgeSize): string {
  const sizes: Record<StatusBadgeSize, string> = {
    sm: "px-2 py-0.5 text-xs gap-1",
    md: "px-2.5 py-1 text-sm gap-1.5",
    lg: "px-3 py-1.5 text-base gap-2",
  };
  return sizes[size];
}

/**
 * Get default icon for status type
 */
function getDefaultIcon(status: StatusBadgeType): ReactNode {
  const iconClass = "w-3.5 h-3.5";
  switch (status) {
    case "success":
      return <CheckCircle className={iconClass} />;
    case "warning":
      return <AlertCircle className={iconClass} />;
    case "error":
      return <XCircle className={iconClass} />;
    case "info":
      return <Info className={iconClass} />;
    case "neutral":
    default:
      return <Circle className={iconClass} />;
  }
}

/**
 * StatusBadge component with semantic status-based styling
 */
export function StatusBadge({
  status,
  size = "md",
  icon,
  showIcon = false,
  pill = false,
  className,
  children,
  ...props
}: StatusBadgeProps) {
  const displayIcon = icon ?? (showIcon ? getDefaultIcon(status) : null);

  return (
    <span
      role="status"
      data-testid="status-badge"
      className={cn(
        // Base styles
        "inline-flex items-center font-medium",
        // Rounding
        pill ? "rounded-full" : "rounded-md",
        // Status colors from design system
        STATUS_BADGE_STYLES[status],
        // Size styles
        getSizeClasses(size),
        className,
      )}
      {...props}
    >
      {/* Icon */}
      {displayIcon && (
        <span className="shrink-0" aria-hidden="true">
          {displayIcon}
        </span>
      )}
      {/* Badge text */}
      {children}
    </span>
  );
}
