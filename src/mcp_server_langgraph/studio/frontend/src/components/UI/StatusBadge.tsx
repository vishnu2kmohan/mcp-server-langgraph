/**
 * StatusBadge Component
 *
 * A semantic status badge component with CVA-based type-safe variants.
 * Provides consistent styling for status indicators across the application.
 *
 * Uses class-variance-authority (CVA) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { type HTMLAttributes, type ReactNode } from "react";
import { CheckCircle, AlertCircle, XCircle, Info, Circle } from "lucide-react";
import { cn } from "../../utils/cn";

/**
 * StatusBadge variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const statusBadgeVariants = cva(
  // Base styles
  "inline-flex items-center font-medium",
  {
    variants: {
      status: {
        success: [
          "bg-success-3 text-success-11",
          "dark:bg-success-a6 dark:text-success-5",
        ],
        warning: [
          "bg-warning-3 text-warning-10",
          "dark:bg-warning-a6 dark:text-warning-6",
        ],
        error: [
          "bg-error-3 text-error-11",
          "dark:bg-error-a6 dark:text-error-9",
        ],
        info: [
          "bg-primary-3 text-primary-11",
          "dark:bg-primary-a6 dark:text-primary-5",
        ],
        neutral: [
          "bg-neutral-2 text-neutral-11",
        ],
      },
      size: {
        sm: "px-2 py-0.5 text-xs gap-1",
        md: "px-2.5 py-1 text-sm gap-1.5",
        lg: "px-3 py-1.5 text-base gap-2",
      },
      pill: {
        true: "rounded-full",
        false: "rounded-md",
      },
    },
    defaultVariants: {
      status: "neutral",
      size: "md",
      pill: false,
    },
  },
);

export type StatusBadgeStatus = NonNullable<
  VariantProps<typeof statusBadgeVariants>["status"]
>;
export type StatusBadgeSize = NonNullable<
  VariantProps<typeof statusBadgeVariants>["size"]
>;

export interface StatusBadgeProps
  extends
    Omit<HTMLAttributes<HTMLSpanElement>, "children">,
    VariantProps<typeof statusBadgeVariants> {
  /** Custom icon to display */
  icon?: ReactNode;
  /** Show default icon for status type */
  showIcon?: boolean;
  /** Children content */
  children: ReactNode;
}

/**
 * Get default icon for status type
 */
function getDefaultIcon(status: StatusBadgeStatus): ReactNode {
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
  size,
  pill,
  icon,
  showIcon = false,
  className,
  children,
  ...props
}: StatusBadgeProps) {
  const displayIcon =
    icon ?? (showIcon ? getDefaultIcon(status ?? "neutral") : null);

  return (
    <span
      role="status"
      data-testid="status-badge"
      className={cn(statusBadgeVariants({ status, size, pill }), className)}
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
