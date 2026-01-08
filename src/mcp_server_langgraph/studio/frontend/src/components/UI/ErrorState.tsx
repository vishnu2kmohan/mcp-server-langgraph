/**
 * ErrorState
 *
 * Standardized error state component for consistent error display across pages.
 * Provides customizable styling, retry functionality, and accessible design.
 */

import { AlertCircle, RefreshCw } from "lucide-react";

export type ErrorStateVariant = "default" | "compact" | "fullscreen";

export interface ErrorStateProps {
  /** Error title */
  title?: string;
  /** Error message to display */
  message?: string;
  /** Callback when retry button is clicked. If not provided, retry button is hidden */
  onRetry?: () => void;
  /** Custom retry button text */
  retryText?: string;
  /** Variant for different size contexts */
  variant?: ErrorStateVariant;
  /** Optional className for additional styling */
  className?: string;
}

const variantClasses: Record<ErrorStateVariant, string> = {
  default: "h-64",
  compact: "py-8",
  fullscreen: "h-full",
};

export function ErrorState({
  title = "Error",
  message = "Something went wrong",
  onRetry,
  retryText = "Retry",
  variant = "default",
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center text-center ${variantClasses[variant]} ${className}`}
    >
      <AlertCircle size={48} className="text-error-500 mb-4" />
      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
        {title}
      </h3>
      <p className="text-gray-500 dark:text-gray-400 mb-4 max-w-md">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <RefreshCw size={16} />
          {retryText}
        </button>
      )}
    </div>
  );
}

export default ErrorState;
