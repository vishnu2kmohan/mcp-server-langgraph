/**
 * ErrorRecovery Component
 *
 * Provides enhanced error messages with recovery guidance.
 * Classifies errors and suggests appropriate recovery actions.
 */

import { ReactElement, useMemo } from 'react';

// =============================================================================
// Types
// =============================================================================

export type ErrorType = 'network' | 'timeout' | 'auth' | 'validation' | 'server' | 'unknown';

export interface ErrorRecoveryProps {
  /** The error to display */
  error: Error;
  /** Error type for classification (auto-detected if not provided) */
  errorType?: ErrorType;
  /** Callback when retry button is clicked */
  onRetry: () => void;
  /** Callback when dismiss button is clicked */
  onDismiss?: () => void;
  /** Display variant */
  variant?: 'inline' | 'modal' | 'toast';
  /** Additional CSS classes */
  className?: string;
  /** Custom title override */
  title?: string;
  /** Custom recovery suggestions override */
  suggestions?: string[];
  /** Link to documentation */
  docsLink?: string;
}

// =============================================================================
// Error Classification
// =============================================================================

const NETWORK_PATTERNS = [
  /network/i,
  /fetch/i,
  /connection/i,
  /net::/i,
  /offline/i,
  /dns/i,
];

const TIMEOUT_PATTERNS = [
  /timeout/i,
  /timed out/i,
  /etimedout/i,
  /deadline/i,
];

const AUTH_PATTERNS = [
  /401/,
  /403/,
  /unauthorized/i,
  /forbidden/i,
  /token/i,
  /auth/i,
  /login/i,
  /session/i,
];

const VALIDATION_PATTERNS = [
  /validation/i,
  /invalid/i,
  /required/i,
  /missing/i,
  /format/i,
];

const SERVER_PATTERNS = [
  /500/,
  /502/,
  /503/,
  /504/,
  /internal server/i,
  /service unavailable/i,
  /bad gateway/i,
];

export function classifyError(error: Error): ErrorType {
  const message = error.message || '';

  if (NETWORK_PATTERNS.some(pattern => pattern.test(message))) {
    return 'network';
  }
  if (TIMEOUT_PATTERNS.some(pattern => pattern.test(message))) {
    return 'timeout';
  }
  if (AUTH_PATTERNS.some(pattern => pattern.test(message))) {
    return 'auth';
  }
  if (VALIDATION_PATTERNS.some(pattern => pattern.test(message))) {
    return 'validation';
  }
  if (SERVER_PATTERNS.some(pattern => pattern.test(message))) {
    return 'server';
  }

  return 'unknown';
}

// =============================================================================
// Recovery Suggestions
// =============================================================================

const RECOVERY_SUGGESTIONS: Record<ErrorType, string[]> = {
  network: [
    'Check your internet connection',
    'Verify the server URL is correct',
    'Try disabling VPN or proxy if using one',
    'Check if the server is running',
  ],
  timeout: [
    'Wait a moment and try again',
    'The server may be experiencing high load',
    'Check your network speed',
    'Try a simpler request',
  ],
  auth: [
    'Try logging in again',
    'Your session may have expired',
    'Check your credentials',
    'Contact an administrator if the issue persists',
  ],
  validation: [
    'Check your input for errors',
    'Ensure all required fields are filled',
    'Verify the data format is correct',
    'Review the field requirements',
  ],
  server: [
    'The server encountered an error - try again later',
    'This is not your fault - the server is having issues',
    'Wait a few minutes before retrying',
    'Contact support if the issue persists',
  ],
  unknown: [
    'Try the operation again',
    'Refresh the page',
    'Clear your browser cache',
    'Contact support if the issue persists',
  ],
};

const ERROR_TITLES: Record<ErrorType, string> = {
  network: 'Connection Problem',
  timeout: 'Request Timed Out',
  auth: 'Authentication Required',
  validation: 'Invalid Input',
  server: 'Server Error',
  unknown: 'Something Went Wrong',
};

export function getRecoverySuggestions(errorType: ErrorType): string[] {
  return RECOVERY_SUGGESTIONS[errorType] || RECOVERY_SUGGESTIONS.unknown;
}

// =============================================================================
// Helper Functions
// =============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// =============================================================================
// ErrorRecovery Component
// =============================================================================

export function ErrorRecovery({
  error,
  errorType,
  onRetry,
  onDismiss,
  variant = 'inline',
  className,
  title,
  suggestions,
  docsLink,
}: ErrorRecoveryProps): ReactElement {
  const detectedType = useMemo(
    () => errorType || classifyError(error),
    [error, errorType]
  );

  const displayTitle = title || ERROR_TITLES[detectedType];
  const displaySuggestions = suggestions || getRecoverySuggestions(detectedType);

  const baseStyles = clsx(
    'rounded-lg border p-4',
    'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
    className
  );

  const content = (
    <>
      {/* Title */}
      <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
        {displayTitle}
      </h3>

      {/* Error Message */}
      <p className="text-red-700 dark:text-red-300 mb-4">
        {error.message}
      </p>

      {/* Recovery Suggestions */}
      <div className="mb-4">
        <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
          Try these steps:
        </p>
        <ul className="list-disc list-inside text-sm text-red-700 dark:text-red-300 space-y-1">
          {displaySuggestions.map((suggestion, index) => (
            <li key={index}>{suggestion}</li>
          ))}
        </ul>
      </div>

      {/* Documentation Link */}
      {docsLink && (
        <a
          href={docsLink}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-red-600 dark:text-red-400 hover:underline mb-4 block"
        >
          Learn more in the documentation
        </a>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onRetry}
          className={clsx(
            'px-4 py-2 rounded-md text-sm font-medium',
            'bg-red-600 text-white hover:bg-red-700',
            'focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2'
          )}
        >
          Retry
        </button>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className={clsx(
              'px-4 py-2 rounded-md text-sm font-medium',
              'bg-white text-red-700 border border-red-300 hover:bg-red-50',
              'dark:bg-gray-800 dark:text-red-300 dark:border-red-700 dark:hover:bg-gray-700',
              'focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2'
            )}
          >
            Dismiss
          </button>
        )}
      </div>
    </>
  );

  // Render based on variant
  if (variant === 'modal') {
    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-live="assertive"
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      >
        <div className={clsx(baseStyles, 'max-w-md w-full shadow-xl')}>
          {content}
        </div>
      </div>
    );
  }

  if (variant === 'toast') {
    return (
      <div
        role="alert"
        aria-live="assertive"
        className={clsx(
          baseStyles,
          'fixed bottom-4 right-4 max-w-sm shadow-lg z-50'
        )}
      >
        {content}
      </div>
    );
  }

  // Default: inline variant
  return (
    <div role="alert" aria-live="assertive" className={baseStyles}>
      {content}
    </div>
  );
}

// =============================================================================
// Exports
// =============================================================================

export default ErrorRecovery;
