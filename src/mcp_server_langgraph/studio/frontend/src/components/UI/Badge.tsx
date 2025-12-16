/**
 * Badge Component
 *
 * A consistent, accessible badge component with multiple variants.
 * Aligned with the shared design system tokens.
 */

import { type HTMLAttributes, type ReactNode } from "react";

export type BadgeVariant =
  | "default"
  | "primary"
  | "success"
  | "warning"
  | "error"
  | "outline";
export type BadgeSize = "sm" | "md" | "lg";

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /** Visual variant of the badge */
  variant?: BadgeVariant;
  /** Size of the badge */
  size?: BadgeSize;
  /** Icon to display before the text */
  icon?: ReactNode;
  /** Render as pill (fully rounded) */
  pill?: boolean;
}

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Get variant-specific classes
 */
function getVariantClasses(variant: BadgeVariant): string {
  const variants: Record<BadgeVariant, string> = {
    default: cn(
      "bg-gray-100 text-gray-800",
      "dark:bg-gray-800 dark:text-gray-200",
    ),
    primary: cn(
      "bg-brand-primary text-white",
      "dark:bg-blue-600 dark:text-white",
    ),
    success: cn(
      "bg-success-500 text-white",
      "dark:bg-success-600 dark:text-white",
    ),
    warning: cn(
      "bg-warning-500 text-white",
      "dark:bg-warning-600 dark:text-white",
    ),
    error: cn("bg-error-500 text-white", "dark:bg-error-600 dark:text-white"),
    outline: cn(
      "bg-transparent border border-gray-300 text-gray-700",
      "dark:border-gray-600 dark:text-gray-300",
    ),
  };
  return variants[variant];
}

/**
 * Get size-specific classes
 */
function getSizeClasses(size: BadgeSize): string {
  const sizes: Record<BadgeSize, string> = {
    sm: "px-2 py-0.5 text-xs gap-1",
    md: "px-2.5 py-1 text-sm gap-1.5",
    lg: "px-3 py-1.5 text-base gap-2",
  };
  return sizes[size];
}

/**
 * Badge component with consistent styling
 */
export function Badge({
  variant = "default",
  size = "md",
  icon,
  pill = false,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        // Base styles
        "inline-flex items-center font-medium",
        // Rounding
        pill ? "rounded-full" : "rounded-md",
        // Variant styles
        getVariantClasses(variant),
        // Size styles
        getSizeClasses(size),
        className,
      )}
      {...props}
    >
      {/* Icon */}
      {icon && (
        <span className="shrink-0" aria-hidden="true">
          {icon}
        </span>
      )}
      {/* Badge text */}
      {children}
    </span>
  );
}
