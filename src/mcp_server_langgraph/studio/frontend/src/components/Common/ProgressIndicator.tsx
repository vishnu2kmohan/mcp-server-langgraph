/**
 * ProgressIndicator Component
 *
 * Progress indicator with determinate and indeterminate modes.
 * Features:
 * - Determinate progress bar with percentage
 * - Indeterminate spinner for unknown duration
 * - Status text display
 * - Cancel button for interruptible operations
 * - ETA display when calculable
 * - Size and color variants
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import { Loader2, X } from "lucide-react";

// ==============================================================================
// Types
// ==============================================================================

export type ProgressSize = "sm" | "md" | "lg";
export type ProgressColor = "primary" | "success" | "warning" | "error";

export interface ProgressIndicatorProps {
  /** Current progress value (0-max) */
  value?: number;
  /** Maximum progress value */
  max?: number;
  /** Show as indeterminate (spinner) */
  indeterminate?: boolean;
  /** Show percentage text */
  showPercentage?: boolean;
  /** Status message to display */
  status?: string;
  /** Estimated time remaining */
  eta?: string;
  /** Size variant */
  size?: ProgressSize;
  /** Color variant */
  color?: ProgressColor;
  /** Accessible label */
  label?: string;
  /** Called when user clicks cancel */
  onCancel?: () => void;
  /** Whether cancel is in progress */
  cancelling?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Constants
// ==============================================================================

const SIZE_CLASSES: Record<ProgressSize, { bar: string; text: string }> = {
  sm: { bar: "h-1", text: "text-xs" },
  md: { bar: "h-2", text: "text-sm" },
  lg: { bar: "h-3", text: "text-base" },
};

const COLOR_CLASSES: Record<ProgressColor, { fill: string; track: string }> = {
  primary: {
    fill: "bg-blue-600 dark:bg-blue-500",
    track: "bg-blue-100 dark:bg-blue-900/30",
  },
  success: {
    fill: "bg-green-600 dark:bg-green-500",
    track: "bg-green-100 dark:bg-green-900/30",
  },
  warning: {
    fill: "bg-yellow-600 dark:bg-yellow-500",
    track: "bg-yellow-100 dark:bg-yellow-900/30",
  },
  error: {
    fill: "bg-red-600 dark:bg-red-500",
    track: "bg-red-100 dark:bg-red-900/30",
  },
};

// ==============================================================================
// Component
// ==============================================================================

export function ProgressIndicator({
  value = 0,
  max = 100,
  indeterminate = false,
  showPercentage = false,
  status,
  eta,
  size = "md",
  color = "primary",
  label,
  onCancel,
  cancelling = false,
  className = "",
}: ProgressIndicatorProps) {
  // Calculate percentage (clamped to 0-100)
  const percentage = Math.min(
    100,
    Math.max(0, Math.round((value / max) * 100)),
  );

  const sizeClasses = SIZE_CLASSES[size];
  const colorClasses = COLOR_CLASSES[color];

  return (
    <div
      data-testid="progress-indicator"
      data-size={size}
      data-color={color}
      className={`space-y-2 ${className}`}
    >
      {/* Status and ETA row */}
      {(status || eta) && (
        <div
          role="status"
          aria-live="polite"
          className={`flex items-center justify-between ${sizeClasses.text} text-gray-600 dark:text-gray-400`}
        >
          {status && <span>{status}</span>}
          {eta && (
            <span className="text-gray-500 dark:text-gray-500">{eta}</span>
          )}
        </div>
      )}

      {/* Progress bar / Spinner container */}
      <div className="flex items-center gap-3">
        {indeterminate ? (
          // Indeterminate spinner
          <div
            role="progressbar"
            aria-busy="true"
            aria-label={label || "Loading"}
            className="flex items-center gap-2"
          >
            <Loader2
              data-testid="progress-spinner"
              className="h-5 w-5 animate-spin text-blue-600 dark:text-blue-400"
              aria-hidden="true"
            />
          </div>
        ) : (
          // Determinate progress bar
          <div className="flex-1 flex items-center gap-3">
            <div
              role="progressbar"
              aria-valuenow={percentage}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={label || "Progress"}
              className={`flex-1 rounded-full overflow-hidden ${sizeClasses.bar} ${colorClasses.track}`}
            >
              <div
                data-testid="progress-fill"
                className={`h-full rounded-full transition-all duration-300 ease-out ${colorClasses.fill}`}
                style={{ width: `${percentage}%` }}
              />
            </div>

            {/* Percentage text */}
            {showPercentage && (
              <span
                className={`min-w-[3rem] text-right font-medium ${sizeClasses.text} text-gray-700 dark:text-gray-300`}
              >
                {percentage}%
              </span>
            )}
          </div>
        )}

        {/* Cancel button */}
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={cancelling}
            aria-label="Cancel"
            className={`p-1 rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${
              cancelling ? "opacity-50 cursor-not-allowed" : ""
            }`}
          >
            <X size={size === "sm" ? 14 : size === "lg" ? 20 : 16} />
          </button>
        )}
      </div>
    </div>
  );
}

export default ProgressIndicator;
