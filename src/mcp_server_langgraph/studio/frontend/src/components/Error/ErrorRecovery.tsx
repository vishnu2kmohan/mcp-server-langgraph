/**
 * ErrorRecovery Component
 *
 * Enhanced error display with recovery actions.
 * Features:
 * - Structured error display with code and message
 * - Recovery actions (retry, report, dismiss)
 * - Expandable details with trace ID
 * - Copy error info to clipboard
 * - Severity levels (error, warning, info)
 * - Troubleshooting suggestions
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import { useState, useCallback } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Info,
  RefreshCw,
  X,
  Bug,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
} from "lucide-react";

// ==============================================================================
// Types
// ==============================================================================

export type ErrorSeverity = "error" | "warning" | "info";

export interface ErrorInfo {
  /** Error code */
  code: string;
  /** Human-readable message */
  message: string;
  /** Trace ID for support */
  traceId?: string;
  /** When the error occurred */
  timestamp?: number;
  /** Additional details */
  details?: Record<string, unknown>;
}

export interface ErrorRecoveryProps {
  /** Error information */
  error: ErrorInfo;
  /** Error severity */
  severity?: ErrorSeverity;
  /** Suggestions for recovery */
  suggestions?: string[];
  /** Additional CSS classes */
  className?: string;
  /** Callback when user clicks retry */
  onRetry?: () => void;
  /** Callback when user dismisses error */
  onDismiss?: () => void;
  /** Callback when user reports error */
  onReport?: () => void;
}

// ==============================================================================
// Constants
// ==============================================================================

const SEVERITY_CONFIG: Record<
  ErrorSeverity,
  {
    icon: typeof AlertCircle;
    bgColor: string;
    borderColor: string;
    textColor: string;
  }
> = {
  error: {
    icon: AlertCircle,
    bgColor: "bg-red-50 dark:bg-red-900/20",
    borderColor: "border-red-200 dark:border-red-800",
    textColor: "text-red-700 dark:text-red-400",
  },
  warning: {
    icon: AlertTriangle,
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    borderColor: "border-yellow-200 dark:border-yellow-800",
    textColor: "text-yellow-700 dark:text-yellow-400",
  },
  info: {
    icon: Info,
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    borderColor: "border-blue-200 dark:border-blue-800",
    textColor: "text-blue-700 dark:text-blue-400",
  },
};

// ==============================================================================
// Component
// ==============================================================================

export function ErrorRecovery({
  error,
  severity = "error",
  suggestions,
  className = "",
  onRetry,
  onDismiss,
  onReport,
}: ErrorRecoveryProps) {
  const [showDetails, setShowDetails] = useState(false);
  const [copied, setCopied] = useState(false);

  const config = SEVERITY_CONFIG[severity];
  const Icon = config.icon;

  // Copy error info to clipboard
  const handleCopy = useCallback(async () => {
    const errorText = [
      `Error Code: ${error.code}`,
      `Message: ${error.message}`,
      error.traceId ? `Trace ID: ${error.traceId}` : null,
      error.timestamp
        ? `Time: ${new Date(error.timestamp).toISOString()}`
        : null,
      error.details
        ? `Details: ${JSON.stringify(error.details, null, 2)}`
        : null,
    ]
      .filter(Boolean)
      .join("\n");

    await navigator.clipboard.writeText(errorText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [error]);

  return (
    <div
      data-testid="error-recovery"
      data-severity={severity}
      role="alert"
      aria-live="assertive"
      className={`rounded-lg border p-4 ${config.bgColor} ${config.borderColor} ${className}`}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <Icon
          data-testid="error-icon"
          className={`h-5 w-5 flex-shrink-0 mt-0.5 ${config.textColor}`}
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <h3
            role="heading"
            aria-level={3}
            className={`text-sm font-medium ${config.textColor}`}
          >
            <code className="font-mono bg-white/50 dark:bg-black/20 px-1.5 py-0.5 rounded">
              {error.code}
            </code>
          </h3>
          <p className="mt-1 text-sm text-gray-700 dark:text-gray-300">
            {error.message}
          </p>
        </div>
      </div>

      {/* Suggestions */}
      {suggestions && suggestions.length > 0 && (
        <div className="mt-3 ml-8">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            Try:
          </p>
          <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400 space-y-0.5">
            {suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 ml-8 flex flex-wrap items-center gap-2">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        )}
        {onReport && (
          <button
            type="button"
            onClick={onReport}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <Bug size={14} />
            Report
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <X size={14} />
            Dismiss
          </button>
        )}
        <button
          type="button"
          onClick={() => setShowDetails(!showDetails)}
          aria-label={showDetails ? "Hide details" : "Show details"}
          className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          Details
        </button>
      </div>

      {/* Details */}
      {showDetails && (
        <div className="mt-3 ml-8 p-3 bg-white/50 dark:bg-black/20 rounded-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Error Details
            </span>
            <button
              type="button"
              onClick={handleCopy}
              aria-label="Copy error details"
              className="inline-flex items-center gap-1 px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 bg-gray-100 dark:bg-gray-800 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {copied ? (
                <>
                  <Check size={12} />
                  Copied
                </>
              ) : (
                <>
                  <Copy size={12} />
                  Copy
                </>
              )}
            </button>
          </div>
          <dl className="text-xs space-y-1">
            <div className="flex">
              <dt className="font-medium text-gray-500 dark:text-gray-400 w-20">
                Code:
              </dt>
              <dd className="font-mono text-gray-700 dark:text-gray-300">
                {error.code}
              </dd>
            </div>
            {error.traceId && (
              <div className="flex">
                <dt className="font-medium text-gray-500 dark:text-gray-400 w-20">
                  Trace ID:
                </dt>
                <dd className="font-mono text-gray-700 dark:text-gray-300">
                  {error.traceId}
                </dd>
              </div>
            )}
            {error.timestamp && (
              <div className="flex">
                <dt className="font-medium text-gray-500 dark:text-gray-400 w-20">
                  Time:
                </dt>
                <dd className="font-mono text-gray-700 dark:text-gray-300">
                  {new Date(error.timestamp).toLocaleString()}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

export default ErrorRecovery;
