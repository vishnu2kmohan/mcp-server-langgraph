/**
 * RiskBadge Component
 *
 * Displays risk levels with semantic color coding and optional icons.
 * Uses CVA for type-safe size variants and dynamic color from utils/colors.
 *
 * Risk levels:
 * - Low: Success (green)
 * - Medium: Warning (amber)
 * - High: Error (red)
 * - Critical: Strong error (dark red)
 */

import { cva, type VariantProps } from "class-variance-authority";
import { type HTMLAttributes, type ReactNode } from "react";
import { Shield, ShieldAlert, ShieldX, AlertOctagon } from "lucide-react";
import { getRiskLevelColor, type RiskLevel } from "../../utils/colors";
import { cn } from "../../utils/cn";

/**
 * RiskBadge variant styles using CVA
 */
export const riskBadgeVariants = cva(
  // Base styles
  "inline-flex items-center font-medium",
  {
    variants: {
      size: {
        sm: "text-xs gap-1",
        md: "text-sm gap-1.5",
        lg: "text-base gap-2",
      },
    },
    defaultVariants: {
      size: "md",
    },
  },
);

/**
 * Icon size variants using CVA
 */
export const riskBadgeIconVariants = cva("", {
  variants: {
    size: {
      sm: "w-3 h-3",
      md: "w-3.5 h-3.5",
      lg: "w-4 h-4",
    },
  },
  defaultVariants: {
    size: "md",
  },
});

export type RiskBadgeSize = NonNullable<
  VariantProps<typeof riskBadgeVariants>["size"]
>;

export interface RiskBadgeProps
  extends
    Omit<HTMLAttributes<HTMLSpanElement>, "children">,
    VariantProps<typeof riskBadgeVariants> {
  /** Risk level */
  level: RiskLevel;
  /** Show icon for risk level */
  showIcon?: boolean;
  /** Optional label prefix */
  label?: string;
}

/**
 * Get icon for risk level
 */
function getRiskIcon(level: RiskLevel, size: RiskBadgeSize): ReactNode {
  const iconClass = riskBadgeIconVariants({ size });
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
  size,
  showIcon = false,
  label,
  className,
  ...props
}: RiskBadgeProps) {
  const resolvedSize = size ?? "md";
  const levelText = capitalize(level);
  const displayText = label ? `${label}: ${levelText}` : levelText;
  const ariaLabel = `Risk level: ${levelText}`;

  return (
    <span
      role="status"
      data-testid="risk-badge"
      aria-label={ariaLabel}
      className={cn(
        riskBadgeVariants({ size }),
        // Dynamic risk color from design system
        getRiskLevelColor(level),
        className,
      )}
      {...props}
    >
      {showIcon && (
        <span className="shrink-0" aria-hidden="true">
          {getRiskIcon(level, resolvedSize)}
        </span>
      )}
      {displayText}
    </span>
  );
}
