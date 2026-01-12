/**
 * Badge Component
 *
 * A consistent, accessible badge component with multiple variants.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 * Aligned with the shared design system tokens.
 */

import { cva, type VariantProps } from "class-variance-authority";
import { type HTMLAttributes, type ReactNode } from "react";
import { cn } from "../../utils/cn";

/**
 * Badge variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const badgeVariants = cva(
  // Base styles
  "inline-flex items-center font-medium",
  {
    variants: {
      variant: {
        default: [
          "bg-neutral-100 dark:bg-neutral-800 text-neutral-800",
          "dark:text-neutral-200",
        ],
        primary: [
          "bg-brand-primary text-white",
          "dark:bg-primary-600 dark:text-white",
        ],
        success: [
          "bg-success-500 text-white",
          "dark:bg-success-600 dark:text-white",
        ],
        warning: [
          "bg-warning-500 text-white",
          "dark:bg-warning-600 dark:text-white",
        ],
        error: ["bg-error-500 text-white", "dark:bg-error-600 dark:text-white"],
        outline: [
          "bg-transparent border border-neutral-300 dark:border-neutral-600",
          "text-neutral-700 dark:text-neutral-300",
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
      variant: "default",
      size: "md",
      pill: false,
    },
  },
);

export type BadgeVariant = NonNullable<
  VariantProps<typeof badgeVariants>["variant"]
>;
export type BadgeSize = NonNullable<VariantProps<typeof badgeVariants>["size"]>;

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  /** Icon to display before the text */
  icon?: ReactNode;
}

/**
 * Badge component with consistent styling
 */
export function Badge({
  variant,
  size,
  pill,
  icon,
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant, size, pill }), className)}
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
