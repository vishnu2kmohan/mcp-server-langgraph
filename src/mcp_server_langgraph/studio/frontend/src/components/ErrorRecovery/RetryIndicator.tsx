/**
 * RetryIndicator Component
 *
 * Sprint 3 - Phase 2.2: Automatic Retry System
 *
 * Visual component showing retry progress with countdown timer,
 * progress bar, and user controls for canceling or forcing retry.
 *
 * @example
 * ```tsx
 * <RetryIndicator
 *   retryCount={2}
 *   maxRetries={3}
 *   delayMs={5000}
 *   onCancel={() => cancelRequest()}
 *   onForceRetry={() => retryNow()}
 *   errorMessage="Connection timed out"
 *   errorCategory="network"
 * />
 * ```
 */

import React, { useEffect, useState, useCallback, useRef } from "react";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface RetryIndicatorProps {
  /** Current retry attempt number */
  retryCount: number;
  /** Maximum retry attempts */
  maxRetries: number;
  /** Delay in milliseconds until next retry */
  delayMs: number;
  /** Called when user cancels retry */
  onCancel: () => void;
  /** Called when user forces immediate retry */
  onForceRetry: () => void;
  /** Called when countdown completes */
  onComplete?: () => void;
  /** Error message to display */
  errorMessage?: string;
  /** Error category for icon display */
  errorCategory?: string;
  /** Whether countdown is paused */
  paused?: boolean;
  /** Compact display mode */
  compact?: boolean;
  /** Custom className for styling */
  className?: string;
  /** Test ID for testing */
  testId?: string;
}

// =============================================================================
// Constants
// =============================================================================

const CATEGORY_ICONS: Record<string, string> = {
  network: "📡",
  authentication: "🔐",
  authorization: "🚫",
  validation: "📝",
  server: "🖥️",
  timeout: "⏱️",
  quota: "📊",
  client: "💻",
  unknown: "❓",
};

// =============================================================================
// Component
// =============================================================================

export function RetryIndicator({
  retryCount,
  maxRetries,
  delayMs,
  onCancel,
  onForceRetry,
  onComplete,
  errorMessage,
  errorCategory,
  paused = false,
  compact = false,
  className = "",
  testId = "retry-indicator",
}: RetryIndicatorProps): React.ReactElement {
  // Countdown state (in seconds)
  const [secondsRemaining, setSecondsRemaining] = useState(
    Math.ceil(delayMs / 1000),
  );
  const [progressPercent, setProgressPercent] = useState(100);
  const [isStopped, setIsStopped] = useState(false);

  // Refs for cleanup
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef(Date.now());
  const pausedTimeRef = useRef<number | null>(null);

  // Calculate remaining time on each tick
  const updateProgress = useCallback(() => {
    if (isStopped) return;

    const elapsed = Date.now() - startTimeRef.current;
    const remaining = Math.max(0, delayMs - elapsed);
    const seconds = Math.ceil(remaining / 1000);
    const percent = Math.round((remaining / delayMs) * 100);

    setSecondsRemaining(seconds);
    setProgressPercent(percent);

    if (remaining <= 0) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      onComplete?.();
    }
  }, [delayMs, onComplete, isStopped]);

  // Handle pause/resume
  useEffect(() => {
    if (paused) {
      // Save current state when pausing
      pausedTimeRef.current = Date.now();
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } else if (pausedTimeRef.current !== null) {
      // Resume: adjust start time to account for pause duration
      const pauseDuration = Date.now() - pausedTimeRef.current;
      startTimeRef.current += pauseDuration;
      pausedTimeRef.current = null;

      // Restart interval
      intervalRef.current = setInterval(updateProgress, 100);
    }
  }, [paused, updateProgress]);

  // Start/stop interval
  useEffect(() => {
    if (isStopped || paused) return;

    startTimeRef.current = Date.now();
    intervalRef.current = setInterval(updateProgress, 100);
    updateProgress(); // Initial update

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [delayMs, updateProgress, isStopped, paused]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    setIsStopped(true);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    onCancel();
  }, [onCancel]);

  // Handle force retry
  const handleForceRetry = useCallback(() => {
    setIsStopped(true);
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    onForceRetry();
  }, [onForceRetry]);

  const categoryIcon = errorCategory
    ? CATEGORY_ICONS[errorCategory] || CATEGORY_ICONS.unknown
    : null;

  return (
    <div
      className={`retry-indicator ${compact ? "retry-indicator-compact" : ""} ${className}`}
      data-testid={testId}
      role="alert"
      aria-live="polite"
    >
      {/* Header with retry count */}
      <div className="retry-indicator-header">
        {categoryIcon && (
          <span
            className="error-category-icon"
            data-testid="error-category-icon"
            aria-hidden="true"
          >
            {categoryIcon}
          </span>
        )}
        <span className="retry-count">
          Retry {retryCount} of {maxRetries}
        </span>
        {paused && <span className="retry-paused-badge">Paused</span>}
      </div>
      {/* Error message */}
      {errorMessage && <p className="retry-error-message">{errorMessage}</p>}
      {/* Countdown timer */}
      <div className="retry-countdown-container">
        <span className="retry-countdown-label">Retrying in</span>
        <span className="retry-countdown" data-testid="retry-countdown">
          {secondsRemaining}
        </span>
        <span className="retry-countdown-unit">s</span>
      </div>
      {/* Progress bar (hidden in compact mode) */}
      {!compact && (
        <div
          role="progressbar"
          aria-valuenow={progressPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Retry countdown: ${progressPercent}% remaining`}
          className="retry-progress-bar"
        >
          <div
            className="retry-progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      )}
      {/* Action buttons */}
      <div className="retry-actions">
        <Button
          className="retry-button retry-button-cancel"
          type="button"
          onClick={handleCancel}
          aria-label="Cancel retry"
        >
          Cancel
        </Button>
        <Button
          className="retry-button retry-button-force"
          type="button"
          onClick={handleForceRetry}
          aria-label="Retry now"
        >
          Retry Now
        </Button>
      </div>
    </div>
  );
}

export default RetryIndicator;
