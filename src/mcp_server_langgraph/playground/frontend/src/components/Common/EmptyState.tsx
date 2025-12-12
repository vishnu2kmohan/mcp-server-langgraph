/**
 * EmptyState Component
 *
 * A reusable empty state component with icon, title, description,
 * CTA button, and suggestions. Part of P3.2 UX Excellence.
 */

import React from 'react';
import clsx from 'clsx';

export type EmptyStateVariant = 'default' | 'compact' | 'large';

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  suggestions?: string[];
  variant?: EmptyStateVariant;
  className?: string;
}

function DefaultIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.5}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"
      />
    </svg>
  );
}

const variantStyles: Record<EmptyStateVariant, string> = {
  default: 'py-8 bg-gray-50 dark:bg-dark-bg',
  compact: 'py-4',
  large: 'py-16 bg-gray-50 dark:bg-dark-bg',
};

export function EmptyState({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  suggestions,
  variant = 'default',
  className,
}: EmptyStateProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center text-center px-4 rounded-lg',
        variantStyles[variant],
        className
      )}
      data-testid="empty-state"
      role="region"
      aria-label={title}
    >
      {/* Icon */}
      <div className="mb-4 text-gray-400 dark:text-dark-textMuted">
        {icon || <DefaultIcon className="w-12 h-12" />}
      </div>

      {/* Title */}
      <h3 className="text-lg font-medium text-gray-700 dark:text-dark-textSecondary mb-2">
        {title}
      </h3>

      {/* Description */}
      {description && (
        <p className="text-sm text-gray-500 dark:text-dark-textMuted max-w-sm mb-4">
          {description}
        </p>
      )}

      {/* CTA Button */}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className={clsx(
            'px-4 py-2 rounded-lg font-medium text-sm',
            'bg-primary-600 text-white hover:bg-primary-700',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
            'transition-colors'
          )}
        >
          {actionLabel}
        </button>
      )}

      {/* Suggestions */}
      {suggestions && suggestions.length > 0 && (
        <div className="mt-4 text-sm text-gray-500 dark:text-dark-textMuted">
          <span className="font-medium">Try:</span>
          <ul className="mt-2 space-y-1">
            {suggestions.map((suggestion, index) => (
              <li key={index} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-primary-400" />
                {suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
