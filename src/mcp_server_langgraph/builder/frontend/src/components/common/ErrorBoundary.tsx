/**
 * ErrorBoundary Component
 *
 * Enhanced error boundary with recovery suggestions and error tracking.
 * Implements UX Honeycomb "Credible" facet with graceful error handling.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';

// ==============================================================================
// Types
// ==============================================================================

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode | ((props: { error: Error; resetError: () => void }) => ReactNode);
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

// ==============================================================================
// Helpers
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==============================================================================
// Default Fallback Component
// ==============================================================================

function DefaultErrorFallback({
  error,
  resetError,
}: {
  error: Error;
  resetError: () => void;
}) {
  const handleRefresh = () => {
    window.location.reload();
  };

  return (
    <div
      role="alert"
      className={clsx(
        'min-h-[400px] flex items-center justify-center',
        'bg-gray-50 dark:bg-gray-900'
      )}
    >
      <div className="max-w-md p-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg text-center">
        {/* Error Icon */}
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
          <svg
            className="w-8 h-8 text-red-600 dark:text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        {/* Error Title */}
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
          Something went wrong
        </h2>

        {/* Error Message */}
        <p className="text-gray-600 dark:text-gray-300 mb-4">
          {error.message || 'An unexpected error occurred'}
        </p>

        {/* Recovery Suggestions */}
        <div className="text-left mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
            Try these steps:
          </h3>
          <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1">
            <li className="flex items-start gap-2">
              <span className="text-gray-400">1.</span>
              <span>Click "Try Again" to retry the operation</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-gray-400">2.</span>
              <span>Refresh the page to start fresh</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-gray-400">3.</span>
              <span>Check your network connection</span>
            </li>
          </ul>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 justify-center">
          <button
            onClick={resetError}
            className={clsx(
              'px-4 py-2 rounded-lg font-medium',
              'bg-blue-600 text-white',
              'hover:bg-blue-700',
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
            )}
          >
            Try Again
          </button>
          <button
            onClick={handleRefresh}
            className={clsx(
              'px-4 py-2 rounded-lg font-medium',
              'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200',
              'hover:bg-gray-200 dark:hover:bg-gray-600',
              'focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2'
            )}
          >
            Refresh Page
          </button>
        </div>
      </div>
    </div>
  );
}

// ==============================================================================
// ErrorBoundary Class Component
// ==============================================================================

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  resetError = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      const { fallback } = this.props;
      const { error } = this.state;

      // Custom fallback function
      if (typeof fallback === 'function') {
        return fallback({ error, resetError: this.resetError });
      }

      // Custom fallback element
      if (fallback) {
        return fallback;
      }

      // Default fallback
      return <DefaultErrorFallback error={error} resetError={this.resetError} />;
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
