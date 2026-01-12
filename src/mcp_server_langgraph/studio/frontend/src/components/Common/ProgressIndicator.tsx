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

import { Button } from "@/components/UI";

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
    fill: "bg-primary-600 dark:bg-primary-500",
    track: "bg-primary-100 dark:bg-primary-900/30",
  },
  success: {
    fill: "bg-success-600 dark:bg-success-500",
    track: "bg-success-100 dark:bg-success-900/30",
  },
  warning: {
    fill: "bg-warning-600 dark:bg-warning-500",
    track: "bg-warning-100 dark:bg-warning-900/30",
  },
  error: {
    fill: "bg-error-600 dark:bg-error-500",
    track: "bg-error-100 dark:bg-error-900/30",
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
          className={`flex items-center justify-between ${sizeClasses.text} text-neutral-600 dark:text-neutral-400`}
        >
          {status && <span>{status}</span>}
          {eta && (
            <span className="text-neutral-500 dark:text-neutral-400">
              {eta}
            </span>
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
              className="h-5 w-5 animate-spin text-primary-600 dark:text-primary-400"
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
                className={`min-w-[3rem] text-right font-medium ${sizeClasses.text} text-neutral-700 dark:text-neutral-300`}
              >
                {percentage}%
              </span>
            )}
          </div>
        )}

        {/* Cancel button */}
        {onCancel && (
          <Button
            variant="secondary"
            className="p-1 rounded-md text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-800 focus:ring-primary-500"
            type="button"
            onClick={onCancel}
            disabled={cancelling}
            aria-label="Cancel"
          >
            <X size={size === "sm" ? 14 : size === "lg" ? 20 : 16} />
          </Button>
        )}
      </div>
    </div>
  );
}

export default ProgressIndicator;
