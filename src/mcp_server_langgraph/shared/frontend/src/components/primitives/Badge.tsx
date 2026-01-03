/**
 * Badge Component (Shared Primitive)
 *
 * Accessible badge/tag with CVA variants for consistent styling.
 *
 * @module @mcp-server-langgraph/shared-frontend/primitives
 */

import { type HTMLAttributes, type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../utils/cn';

/**
 * Badge variants using CVA for type-safe, consistent styling
 */
export const badgeVariants = cva(
  // Base styles
  ['inline-flex items-center font-medium'],
  {
    variants: {
      variant: {
        default: [
          'bg-gray-100 text-gray-800',
          'dark:bg-gray-800 dark:text-gray-200',
        ],
        primary: [
          'bg-primary-100 text-primary-800',
          'dark:bg-primary-900 dark:text-primary-200',
        ],
        success: [
          'bg-success-100 text-success-800',
          'dark:bg-success-900 dark:text-success-200',
        ],
        warning: [
          'bg-warning-100 text-warning-800',
          'dark:bg-warning-900 dark:text-warning-200',
        ],
        error: [
          'bg-error-100 text-error-800',
          'dark:bg-error-900 dark:text-error-200',
        ],
        outline: [
          'bg-transparent border border-gray-300 text-gray-700',
          'dark:border-gray-600 dark:text-gray-300',
        ],
      },
      size: {
        sm: 'px-2 py-0.5 text-xs gap-1',
        md: 'px-2.5 py-1 text-sm gap-1.5',
        lg: 'px-3 py-1.5 text-base gap-2',
      },
      pill: {
        true: 'rounded-full',
        false: 'rounded-md',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
      pill: false,
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  /** Icon to display before the text */
  icon?: ReactNode;
}

/**
 * Badge component with consistent styling
 *
 * @example
 * ```tsx
 * <Badge variant="success">Active</Badge>
 * <Badge variant="error" pill>Failed</Badge>
 * <Badge icon={<StarIcon />} size="sm">Featured</Badge>
 * ```
 */
export function Badge({
  className,
  variant,
  size,
  pill,
  icon,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(badgeVariants({ variant, size, pill, className }))}
      {...props}
    >
      {icon && (
        <span className="shrink-0" aria-hidden="true">
          {icon}
        </span>
      )}
      {children}
    </span>
  );
}
