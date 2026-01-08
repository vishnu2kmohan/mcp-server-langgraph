/**
 * RiskBadge Component
 *
 * Displays risk levels with semantic color coding and optional icons.
 * Uses getRiskLevelColor from utils/colors for centralized color management.
 *
 * Risk levels:
 * - Low: Success (green)
 * - Medium: Warning (amber)
 * - High: Error (red)
 * - Critical: Strong error (dark red)
 */

import { type HTMLAttributes, type ReactNode } from "react";
import { Shield, ShieldAlert, ShieldX, AlertOctagon } from "lucide-react";
import { getRiskLevelColor, type RiskLevel } from "../../utils/colors";

export type RiskBadgeSize = "sm" | "md" | "lg";

export interface RiskBadgeProps extends Omit<
  HTMLAttributes<HTMLSpanElement>,
  "children"
> {
  /** Risk level */
  level: RiskLevel;
  /** Size of the badge */
  size?: RiskBadgeSize;
  /** Show icon for risk level */
  showIcon?: boolean;
  /** Optional label prefix */
  label?: string;
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
function getSizeClasses(size: RiskBadgeSize): string {
  const sizes: Record<RiskBadgeSize, string> = {
    sm: "text-xs gap-1",
    md: "text-sm gap-1.5",
    lg: "text-base gap-2",
  };
  return sizes[size];
}

/**
 * Get icon size based on badge size
 */
function getIconSize(size: RiskBadgeSize): string {
  const sizes: Record<RiskBadgeSize, string> = {
    sm: "w-3 h-3",
    md: "w-3.5 h-3.5",
    lg: "w-4 h-4",
  };
  return sizes[size];
}

/**
 * Get icon for risk level
 */
function getRiskIcon(level: RiskLevel, size: RiskBadgeSize): ReactNode {
  const iconClass = getIconSize(size);
  switch (level) {
    case "low":
      return <Shield className={iconClass} />;
    case "medium":
      return <ShieldAlert className={iconClass} />;
    case "high":
      return <ShieldX className={iconClass} />;
    case "critical":
      return <AlertOctagon className={iconClass} />;
    default:
      return <Shield className={iconClass} />;
  }
}

/**
 * Capitalize first letter
 */
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * RiskBadge component with semantic risk-based styling
 */
export function RiskBadge({
  level,
  size = "md",
  showIcon = false,
  label,
  className,
  ...props
}: RiskBadgeProps) {
  const levelText = capitalize(level);
  const displayText = label ? `${label}: ${levelText}` : levelText;
  const ariaLabel = `Risk level: ${levelText}`;

  return (
    <span
      role="status"
      data-testid="risk-badge"
      aria-label={ariaLabel}
      className={cn(
        // Base styles
        "inline-flex items-center font-medium",
        // Risk color from design system
        getRiskLevelColor(level),
        // Size styles
        getSizeClasses(size),
        className,
      )}
      {...props}
    >
      {showIcon && (
        <span className="shrink-0" aria-hidden="true">
          {getRiskIcon(level, size)}
        </span>
      )}
      {displayText}
    </span>
  );
}
