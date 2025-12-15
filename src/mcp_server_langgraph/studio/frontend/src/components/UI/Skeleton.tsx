/**
 * Skeleton Loading Components
 *
 * Provides animated placeholder components for loading states.
 * Uses Tailwind CSS for styling and animation.
 */

import React from "react";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Apply rounded-full style for circular/avatar skeletons */
  rounded?: boolean;
}

/**
 * Base skeleton component with pulse animation
 */
export function Skeleton({
  className = "",
  rounded = false,
  ...props
}: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-gray-200 dark:bg-gray-700 ${rounded ? "rounded-full" : "rounded"} ${className}`}
      {...props}
    />
  );
}

type SkeletonCardProps = React.HTMLAttributes<HTMLDivElement>;

/**
 * Card skeleton with header and content sections
 */
export function SkeletonCard({ className = "", ...props }: SkeletonCardProps) {
  return (
    <div
      className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 ${className}`}
      {...props}
    >
      <Skeleton className="h-4 w-1/3 mb-3" />
      <Skeleton className="h-8 w-1/2 mb-2" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}

interface SkeletonTextProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Number of text lines to render */
  lines?: number;
}

/**
 * Text skeleton with multiple lines of varying widths
 */
export function SkeletonText({
  lines = 3,
  className = "",
  ...props
}: SkeletonTextProps) {
  const lineWidths = ["w-full", "w-5/6", "w-3/4", "w-4/5", "w-2/3"];

  return (
    <div className={`space-y-2 ${className}`} {...props}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={`h-4 ${i === lines - 1 ? "w-3/4" : lineWidths[i % lineWidths.length]}`}
        />
      ))}
    </div>
  );
}

interface SkeletonListProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Number of list items to render */
  items?: number;
}

/**
 * List skeleton with multiple item placeholders
 */
export function SkeletonList({
  items = 3,
  className = "",
  ...props
}: SkeletonListProps) {
  return (
    <div className={`space-y-3 ${className}`} {...props}>
      {Array.from({ length: items }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
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
