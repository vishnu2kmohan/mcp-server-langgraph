/**
 * Skeleton Components for Visual Workflow Builder
 *
 * Provides loading placeholder animations for:
 * - Generic content (Skeleton, SkeletonCard, SkeletonList, SkeletonText)
 * - Workflow-specific content (SkeletonWorkflowNode)
 * - Code panel content (SkeletonCodeBlock)
 *
 * WCAG 2.1 AA Compliant:
 * - Uses aria-hidden for decorative loading states
 * - Provides aria-label for meaningful context
 */

import React from 'react';

// ==============================================================================
// Types
// ==============================================================================

export type SkeletonVariant = 'text' | 'rounded' | 'circular';

export interface SkeletonProps {
  variant?: SkeletonVariant;
  width?: string | number;
  height?: string | number;
  className?: string;
  'data-testid'?: string;
}

// ==============================================================================
// Helper to combine class names
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==============================================================================
// Variant Styles
// ==============================================================================

const variantStyles: Record<SkeletonVariant, string> = {
  text: 'rounded',
  rounded: 'rounded-lg',
  circular: 'rounded-full',
};

// ==============================================================================
// Base Skeleton Component
// ==============================================================================

export function Skeleton({
  variant = 'text',
  width,
  height,
  className,
  'data-testid': testId,
}: SkeletonProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'animate-pulse bg-gray-200 dark:bg-gray-700',
        variantStyles[variant],
        className
      )}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
      data-testid={testId}
      aria-hidden="true"
    />
  );
}

// ==============================================================================
// SkeletonCard Component
// ==============================================================================

export interface SkeletonCardProps {
  className?: string;
}

export function SkeletonCard({ className }: SkeletonCardProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'p-4 rounded-lg border border-gray-200 dark:border-gray-700',
        'bg-white dark:bg-gray-800',
        className
      )}
      role="presentation"
      aria-label="Loading..."
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <Skeleton variant="circular" width={40} height={40} />

        <div className="flex-1 space-y-2">
          {/* Title */}
          <Skeleton height={16} width="60%" data-testid="skeleton-line" />

          {/* Description lines */}
          <Skeleton height={12} width="100%" data-testid="skeleton-line" />
          <Skeleton height={12} width="80%" data-testid="skeleton-line" />
        </div>
      </div>
    </div>
  );
}

// ==============================================================================
// SkeletonList Component
// ==============================================================================

export interface SkeletonListProps {
  count?: number;
  className?: string;
}

export function SkeletonList({ count = 3, className }: SkeletonListProps): React.ReactElement {
  return (
    <div className={clsx('space-y-3', className)}>
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonCard key={index} />
      ))}
    </div>
  );
}

// ==============================================================================
// SkeletonText Component
// ==============================================================================

export interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

export function SkeletonText({ lines = 3, className }: SkeletonTextProps): React.ReactElement {
  return (
    <div className={clsx('space-y-2', className)} data-testid="skeleton-text">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height={12}
          width={index === lines - 1 ? '60%' : '100%'}
          data-testid="skeleton-line"
        />
      ))}
    </div>
  );
}

// ==============================================================================
// SkeletonWorkflowNode Component (Builder-specific)
// ==============================================================================

export interface SkeletonWorkflowNodeProps {
  className?: string;
}

export function SkeletonWorkflowNode({ className }: SkeletonWorkflowNodeProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'w-40 p-3 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-600',
        'bg-gray-100 dark:bg-gray-800',
        className
      )}
      role="presentation"
      aria-label="Loading node..."
      data-testid="skeleton-workflow-node"
    >
      <div className="space-y-2">
        {/* Node icon */}
        <Skeleton variant="circular" width={24} height={24} />
        {/* Node title */}
        <Skeleton height={14} width="80%" />
        {/* Node description */}
        <Skeleton height={10} width="60%" />
      </div>
    </div>
  );
}

// ==============================================================================
// SkeletonCodeBlock Component (Builder-specific)
// ==============================================================================

export interface SkeletonCodeBlockProps {
  lines?: number;
  className?: string;
}

export function SkeletonCodeBlock({ lines = 8, className }: SkeletonCodeBlockProps): React.ReactElement {
  // Simulate varying line widths like real code
  const getLineWidth = (index: number): string => {
    const widths = ['70%', '85%', '40%', '60%', '90%', '50%', '75%', '45%'];
    return widths[index % widths.length];
  };

  return (
    <div
      className={clsx(
        'p-4 rounded-lg bg-gray-900 dark:bg-gray-950',
        className
      )}
      data-testid="skeleton-code-block"
      role="presentation"
      aria-label="Loading code..."
    >
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, index) => (
          <Skeleton
            key={index}
            height={14}
            width={getLineWidth(index)}
            className="bg-gray-700 dark:bg-gray-800"
            data-testid="skeleton-code-line"
          />
        ))}
      </div>
    </div>
  );
}
