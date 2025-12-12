/**
 * Skeleton Component
 *
 * Provides loading placeholder animations for content.
 * Part of P3.3 UX Excellence - Loading States & Micro-interactions.
 */

import React from 'react';
import clsx from 'clsx';

export type SkeletonVariant = 'text' | 'rounded' | 'circular';

export interface SkeletonProps {
  variant?: SkeletonVariant;
  width?: string | number;
  height?: string | number;
  className?: string;
  'data-testid'?: string;
}

const variantStyles: Record<SkeletonVariant, string> = {
  text: 'rounded',
  rounded: 'rounded-lg',
  circular: 'rounded-full',
};

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
        'animate-pulse bg-gray-200 dark:bg-dark-hover',
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

export interface SkeletonCardProps {
  className?: string;
}

export function SkeletonCard({ className }: SkeletonCardProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'p-4 rounded-lg border border-gray-200 dark:border-dark-border',
        'bg-white dark:bg-dark-surface',
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

/**
 * Skeleton for message bubbles in chat
 */
export interface SkeletonMessageProps {
  isUser?: boolean;
  className?: string;
}

export function SkeletonMessage({ isUser = false, className }: SkeletonMessageProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'flex w-full',
        isUser ? 'justify-end' : 'justify-start',
        className
      )}
      role="presentation"
      aria-label="Loading message..."
    >
      <div
        className={clsx(
          'max-w-[80%] rounded-2xl px-4 py-3 space-y-2',
          isUser
            ? 'bg-primary-500/50 rounded-br-md'
            : 'bg-gray-100 dark:bg-dark-surface rounded-bl-md'
        )}
      >
        <Skeleton height={12} width="200px" data-testid="skeleton-line" />
        <Skeleton height={12} width="150px" data-testid="skeleton-line" />
      </div>
    </div>
  );
}

/**
 * Skeleton for sidebar items
 */
export function SkeletonSidebarItem({ className }: { className?: string }): React.ReactElement {
  return (
    <div
      className={clsx('flex items-center gap-3 p-2', className)}
      role="presentation"
      aria-label="Loading..."
    >
      <Skeleton variant="rounded" width={32} height={32} />
      <div className="flex-1 space-y-1">
        <Skeleton height={14} width="70%" data-testid="skeleton-line" />
        <Skeleton height={10} width="50%" data-testid="skeleton-line" />
      </div>
    </div>
  );
}
