/**
 * ErrorBoundary
 *
 * Global error boundary component with telemetry integration.
 * Catches React render errors and provides recovery options.
 *
 * Features:
 * - Catches errors from child component tree
 * - Telemetry integration via onError callback
 * - Customizable fallback UI
 * - Recovery/retry functionality
 * - WCAG 2.1 AA accessible
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary
 *   onError={(error, info) => telemetry.trackError(error, info)}
 *   onReset={() => window.location.reload()}
 * >
 *   <App />
 * </ErrorBoundary>
 * ```
 */
import { Component, createRef, type ReactNode, type RefObject } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface ErrorInfo {
  /** React component stack trace */
  componentStack: string;
  /** Name of the error boundary that caught this error */
  boundaryName?: string;
}

export interface FallbackRenderProps {
  /** The error that was caught */
  error: Error;
  /** Function to reset the error boundary state */
  resetErrorBoundary: () => void;
}

export interface ErrorBoundaryProps {
  /** Child components to render */
  children: ReactNode;
  /** Callback when an error is caught (for telemetry) */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Callback when reset/retry is triggered */
  onReset?: () => void;
  /** Static fallback element to display on error */
  fallback?: ReactNode;
  /** Render prop for custom fallback with error details */
  fallbackRender?: (props: FallbackRenderProps) => ReactNode;
  /** Whether to show error details (stack trace) */
  showDetails?: boolean;
  /** Name to identify this boundary (for telemetry) */
  name?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

// =============================================================================
// Component
// =============================================================================

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  private retryButtonRef: RefObject<HTMLButtonElement>;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
    this.retryButtonRef = createRef<HTMLButtonElement>();
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    const { onError, name } = this.props;

    // Convert React's ErrorInfo to our ErrorInfo type
    const info: ErrorInfo = {
      componentStack: errorInfo.componentStack || "",
      boundaryName: name,
    };

    // Call onError callback for telemetry - wrap in try/catch to be safe
    if (onError) {
      try {
        onError(error, info);
      } catch {
        // Silently ignore errors in the error handler
      }
    }
  }

  componentDidUpdate(
    _prevProps: ErrorBoundaryProps,
    prevState: ErrorBoundaryState,
  ): void {
    // Focus the retry button when error state changes to true
    if (
      !prevState.hasError &&
      this.state.hasError &&
      this.retryButtonRef.current
    ) {
      this.retryButtonRef.current.focus();
    }
  }

  resetErrorBoundary = (): void => {
    const { onReset } = this.props;
    this.setState({ hasError: false, error: null });
    onReset?.();
  };

  render(): ReactNode {
    const { hasError, error } = this.state;
    const { children, fallback, fallbackRender, showDetails } = this.props;

    if (!hasError) {
      return children;
    }

    // Custom fallback render prop
    if (fallbackRender && error) {
      return fallbackRender({
        error,
        resetErrorBoundary: this.resetErrorBoundary,
      });
    }

    // Static fallback element
    if (fallback) {
      return fallback;
    }

    // Default fallback UI
    return (
      <div
        role="alert"
        aria-live="assertive"
        className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border border-error-200 bg-error-50 p-6 text-center dark:border-error-800 dark:bg-error-950"
      >
        <AlertTriangle
          className="mb-4 h-12 w-12 text-error-500 dark:text-error-400"
          aria-hidden="true"
        />
        <h2 className="mb-2 text-lg font-semibold text-error-800 dark:text-error-200">
          Something went wrong
        </h2>
        <p className="mb-4 max-w-md text-sm text-error-600 dark:text-error-300">
          {error?.message || "An unexpected error occurred"}
        </p>
        {showDetails && error && (
          <details className="mb-4 w-full max-w-lg text-left">
            <summary className="cursor-pointer text-sm font-medium text-error-700 dark:text-error-300">
              Error Details
            </summary>
            <pre className="mt-2 overflow-auto rounded bg-error-100 p-3 text-xs text-error-800 dark:bg-error-900 dark:text-error-200">
              Error: {error.name}: {error.message}
              {error.stack && `\n\n${error.stack}`}
            </pre>
          </details>
        )}
        <Button
          variant="danger"
          className="rounded-md bg-error-600 px-4 py-2 text-sm text-white hover:bg-error-700 focus:ring-error-500 focus:ring-offset-2 dark:bg-error-700 dark:hover:bg-error-600"
          ref={this.retryButtonRef}
          type="button"
          onClick={this.resetErrorBoundary}
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Try Again
        </Button>
      </div>
    );
  }
}
