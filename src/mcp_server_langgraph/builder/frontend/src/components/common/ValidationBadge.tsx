/**
 * ValidationBadge Component
 *
 * Displays workflow validation status with visual indicators.
 * Implements UX Honeycomb "Credible" facet.
 */

import React from 'react';

// ==============================================================================
// Types
// ==============================================================================

export type ValidationStatus = 'valid' | 'warning' | 'error' | 'validating';

export interface ValidationBadgeProps {
  status: ValidationStatus;
  errorCount?: number;
  warningCount?: number;
  size?: 'sm' | 'md' | 'lg';
}

// ==============================================================================
// Helpers
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==============================================================================
// Icons
// ==============================================================================

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 13l4 4L19 7"
      />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

function ErrorIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function SpinnerIcon({ className }: { className?: string }) {
  return (
    <svg className={clsx(className, 'animate-spin')} fill="none" viewBox="0 0 24 24">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

// ==============================================================================
// Component
// ==============================================================================

export function ValidationBadge({
  status,
  errorCount = 0,
  warningCount = 0,
  size = 'md',
}: ValidationBadgeProps): React.ReactElement {
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  };

  const iconSizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  };

  const statusConfig = {
    valid: {
      bgClass: 'bg-green-100 dark:bg-green-900/30',
      textClass: 'text-green-700 dark:text-green-300',
      icon: <CheckIcon className={iconSizeClasses[size]} />,
      label: 'Valid',
      ariaLabel: 'Workflow is valid',
    },
    warning: {
      bgClass: 'bg-yellow-100 dark:bg-yellow-900/30',
      textClass: 'text-yellow-700 dark:text-yellow-300',
      icon: <WarningIcon className={iconSizeClasses[size]} />,
      label: `${warningCount} warning${warningCount === 1 ? '' : 's'}`,
      ariaLabel: `Workflow has ${warningCount} warning${warningCount === 1 ? '' : 's'}`,
    },
    error: {
      bgClass: 'bg-red-100 dark:bg-red-900/30',
      textClass: 'text-red-700 dark:text-red-300',
      icon: <ErrorIcon className={iconSizeClasses[size]} />,
      label: `${errorCount} error${errorCount === 1 ? '' : 's'}`,
      ariaLabel: `Workflow has ${errorCount} error${errorCount === 1 ? '' : 's'}`,
    },
    validating: {
      bgClass: 'bg-blue-100 dark:bg-blue-900/30',
      textClass: 'text-blue-700 dark:text-blue-300',
      icon: <SpinnerIcon className={iconSizeClasses[size]} />,
      label: 'Validating',
      ariaLabel: 'Validating workflow',
    },
  };

  const config = statusConfig[status];

  return (
    <div
      role="status"
      data-testid="validation-badge"
      aria-label={config.ariaLabel}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        sizeClasses[size],
        config.bgClass,
        config.textClass
      )}
    >
      {config.icon}
      <span>{config.label}</span>
    </div>
  );
}

export default ValidationBadge;
