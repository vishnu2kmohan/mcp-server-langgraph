/**
 * Skeleton Loading Components
 *
 * Provides animated placeholder components for loading states.
 * Uses CVA (class-variance-authority) for type-safe variant management.
 */

import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "../../utils/cn";

/**
 * Skeleton variant styles using CVA
 * Exported for use in compound components or style composition
 */
export const skeletonVariants = cva(
  // Base styles
  "animate-pulse bg-neutral-200 dark:bg-neutral-700",
  {
    variants: {
      rounded: {
        true: "rounded-full",
        false: "rounded",
      },
    },
    defaultVariants: {
      rounded: false,
    },
  },
);

export interface SkeletonProps
  extends
    HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof skeletonVariants> {}

/**
 * Base skeleton component with pulse animation
 */
export function Skeleton({ rounded, className, ...props }: SkeletonProps) {
  return (
    <div className={cn(skeletonVariants({ rounded }), className)} {...props} />
  );
}

export type SkeletonCardProps = HTMLAttributes<HTMLDivElement>;

/**
 * Card skeleton with header and content sections
 */
export function SkeletonCard({ className, ...props }: SkeletonCardProps) {
  return (
    <div
      className={cn(
        "bg-white dark:bg-neutral-800",
        "border border-neutral-200 dark:border-neutral-700",
        "rounded-lg p-4",
        className,
      )}
      {...props}
    >
      <Skeleton className="h-4 w-1/3 mb-3" />
      <Skeleton className="h-8 w-1/2 mb-2" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}

export interface SkeletonTextProps extends HTMLAttributes<HTMLDivElement> {
  /** Number of text lines to render */
  lines?: number;
}

/**
 * Text skeleton with multiple lines of varying widths
 */
export function SkeletonText({
  lines = 3,
  className,
  ...props
}: SkeletonTextProps) {
  const lineWidths = ["w-full", "w-5/6", "w-3/4", "w-4/5", "w-2/3"];

  return (
    <div className={cn("space-y-2", className)} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={cn(
            "h-4",
            i === lines - 1 ? "w-3/4" : lineWidths[i % lineWidths.length],
          )}
        />
      ))}
    </div>
  );
}

export interface SkeletonListProps extends HTMLAttributes<HTMLDivElement> {
  /** Number of list items to render */
  items?: number;
}

/**
 * List skeleton with multiple item placeholders
 */
export function SkeletonList({
  items = 3,
  className,
  ...props
}: SkeletonListProps) {
  return (
    <div className={cn("space-y-3", className)} {...props}>
      {Array.from({ length: items }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "flex items-center gap-3 p-3",
            "bg-white dark:bg-neutral-800",
            "border border-neutral-200 dark:border-neutral-700",
            "rounded-lg",
          )}
        >
          <Skeleton className="h-10 w-10" rounded />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}
