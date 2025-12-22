/**
 * AIErrorBoundary
 *
 * Error boundary specifically for AI-powered components.
 * Provides graceful degradation when AI features fail.
 *
 * Features:
 * - Catches errors from AI components
 * - Integrates with AIIntelligence context for error reporting
 * - Provides customizable fallback UI
 * - Supports retry functionality
 * - Silent mode for non-critical AI features
 * - Observability integration via callbacks
 */

import { Component, type ReactNode, type ErrorInfo } from "react";

// =============================================================================
// Types
// =============================================================================

export interface AIErrorFallbackProps {
  /** The error that occurred */
  error: Error;
  /** Function to reset the error state and retry */
  resetError: () => void;
  /** The feature name for display */
  featureName: string;
}

export type AIErrorFallback =
  | ReactNode
  | ((props: AIErrorFallbackProps) => ReactNode);

export interface AIErrorBoundaryProps {
  /** Child components to render */
  children: ReactNode;
  /** Name of the AI feature (for display and logging) */
  featureName: string;
  /** Custom fallback UI or function */
  fallback?: AIErrorFallback;
  /** Hide all UI on error (for non-critical features) */
  silent?: boolean;
  /** Disable the error boundary (errors will propagate) */
  disabled?: boolean;
  /** Callback when an error occurs */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  /** Callback when error is reset/retry */
  onReset?: () => void;
}

interface AIErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

// =============================================================================
// Default Fallback Component
// =============================================================================

function DefaultFallback({
  error,
  resetError,
  featureName,
}: AIErrorFallbackProps) {
  return (
    <div
      data-testid="ai-error-fallback"
      style={{
        padding: "16px",
        borderRadius: "8px",
        backgroundColor: "var(--color-error-surface, #fef2f2)",
        border: "1px solid var(--color-error-border, #fecaca)",
        color: "var(--color-error-text, #991b1b)",
        fontSize: "14px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginBottom: "8px",
        }}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
            fill="currentColor"
          />
        </svg>
        <strong>{featureName} unavailable</strong>
      </div>
      <p style={{ margin: "0 0 12px 0", fontSize: "13px", opacity: 0.9 }}>
        {error.message}
      </p>
      <button
        onClick={resetError}
        style={{
          padding: "6px 12px",
          borderRadius: "4px",
          border: "1px solid currentColor",
          backgroundColor: "transparent",
          color: "inherit",
          cursor: "pointer",
          fontSize: "13px",
        }}
      >
        Retry
      </button>
    </div>
  );
}

// =============================================================================
// Error Boundary Component
// =============================================================================

/**
 * Error boundary for AI-powered components.
 *
 * Provides graceful degradation when AI features fail, with options for:
 * - Custom fallback UI
 * - Silent mode (render nothing on error)
 * - Retry functionality
 * - Error reporting callbacks
 *
 * @example
 * ```tsx
 * // Basic usage
 * <AIErrorBoundary featureName="Navigation Predictions">
 *   <NavPredictionComponent />
 * </AIErrorBoundary>
 *
 * // With custom fallback
 * <AIErrorBoundary
 *   featureName="AI Suggestions"
 *   fallback={<div>Suggestions temporarily unavailable</div>}
 * >
 *   <AISuggestionsComponent />
 * </AIErrorBoundary>
 *
 * // Silent mode for non-critical features
 * <AIErrorBoundary featureName="AI Hints" silent>
 *   <AIHintsComponent />
 * </AIErrorBoundary>
 * ```
 */
export class AIErrorBoundary extends Component<
  AIErrorBoundaryProps,
  AIErrorBoundaryState
> {
  constructor(props: AIErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<AIErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Update state with error info
    this.setState({ errorInfo });

    // Call the onError callback if provided
    this.props.onError?.(error, errorInfo);

    // Log the error for observability
    console.error(
      `[AIErrorBoundary] ${this.props.featureName} error:`,
      error,
      errorInfo
    );
  }

  /**
   * Reset the error state to allow retry
   */
  resetError = (): void => {
    this.props.onReset?.();
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    const { children, featureName, fallback, silent, disabled } = this.props;
    const { hasError, error } = this.state;

    // If disabled, just render children (errors will propagate)
    if (disabled) {
      return children;
    }

    // If no error, render children normally
    if (!hasError || !error) {
      return children;
    }

    // Silent mode: render nothing on error
    if (silent) {
      return null;
    }

    // Custom fallback (function or element)
    if (fallback) {
      if (typeof fallback === "function") {
        return fallback({
          error,
          resetError: this.resetError,
          featureName,
        });
      }
      return fallback;
    }

    // Default fallback
    return (
      <DefaultFallback
        error={error}
        resetError={this.resetError}
        featureName={featureName}
      />
    );
  }
}

export default AIErrorBoundary;
