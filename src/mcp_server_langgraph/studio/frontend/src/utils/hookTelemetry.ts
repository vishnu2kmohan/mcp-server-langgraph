/**
 * Hook Telemetry Utilities
 *
 * Standardized telemetry helpers for React hooks to consistently log
 * degradation, retry, backoff, and fallback events.
 *
 * @example
 * ```ts
 * const telemetry = useHookTelemetry("MyHook");
 *
 * // Log graceful degradation
 * telemetry.logDegradation("missing_session_id", { inputLength: 10 });
 *
 * // Log retry attempt
 * telemetry.logRetry(2, 3, new Error("Network error"));
 *
 * // Log exponential backoff
 * telemetry.logBackoff(2, 2000);
 * ```
 */

import { useMemo } from "react";
import { devLogger } from "./devLogger";

// =============================================================================
// Types
// =============================================================================

/**
 * Common degradation reasons used across hooks.
 */
export type DegradationReason =
  | "missing_session_id"
  | "api_error"
  | "network_error"
  | "timeout"
  | "rate_limited"
  | "validation_error"
  | "auth_failure"
  | "cache_stale"
  | "api_unavailable"
  | string; // Allow custom reasons

/**
 * Telemetry event types.
 */
export type TelemetryEventType =
  | "degradation"
  | "retry"
  | "backoff"
  | "fallback"
  | "error";

/**
 * Telemetry event metrics for retry tracking.
 */
export interface TelemetryMetrics {
  /** Current attempt number (1-based) */
  attempt?: number;
  /** Maximum retry attempts */
  maxAttempts?: number;
  /** Backoff delay in milliseconds */
  delayMs?: number;
  /** HTTP status code if applicable */
  statusCode?: number;
}

/**
 * A tracked telemetry event.
 */
export interface HookTelemetryEvent {
  /** Event type */
  type: TelemetryEventType;
  /** Reason for the event (degradation/fallback reason) */
  reason?: string;
  /** Additional context */
  context: Record<string, unknown>;
  /** Event metrics (for retry/backoff) */
  metrics?: TelemetryMetrics;
  /** Error message if applicable */
  error?: string;
  /** Event timestamp */
  timestamp: number;
}

/**
 * Options for creating hook telemetry.
 */
export interface HookTelemetryOptions {
  /** Maximum number of events to track (default: 100) */
  maxEvents?: number;
}

/**
 * Hook telemetry instance interface.
 */
export interface HookTelemetry {
  /**
   * Log a graceful degradation event.
   * Use when the hook falls back to a safe default due to missing data or errors.
   */
  logDegradation: (
    reason: DegradationReason,
    context: Record<string, unknown>,
  ) => void;

  /**
   * Log a retry attempt.
   * Use before each retry attempt in a retry loop.
   */
  logRetry: (attempt: number, maxAttempts: number, error: Error) => void;

  /**
   * Log exponential backoff delay.
   * Use when pausing between retry attempts.
   */
  logBackoff: (attempt: number, delayMs: number) => void;

  /**
   * Log fallback usage.
   * Use when returning a fallback value instead of the expected result.
   */
  logFallback: (reason: string, fallbackValue: unknown) => void;

  /**
   * Log an error occurrence.
   * Use for unexpected errors that should be tracked.
   */
  logError: (error: Error | unknown, context: Record<string, unknown>) => void;

  /**
   * Get all tracked events.
   * Useful for debugging and testing.
   */
  getEvents: () => HookTelemetryEvent[];

  /**
   * Clear all tracked events.
   */
  clearEvents: () => void;
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a telemetry instance for a hook.
 *
 * @param hookName - The name of the hook (used as log prefix)
 * @param options - Configuration options
 * @returns A HookTelemetry instance
 *
 * @example
 * ```ts
 * const telemetry = createHookTelemetry("useAISuggestions");
 * telemetry.logDegradation("missing_session_id", { inputLength: 10 });
 * ```
 */
export function createHookTelemetry(
  hookName: string,
  options: HookTelemetryOptions = {},
): HookTelemetry {
  const { maxEvents = 100 } = options;
  const logger = devLogger.withPrefix(`[${hookName}]`);
  const events: HookTelemetryEvent[] = [];

  const addEvent = (event: HookTelemetryEvent) => {
    events.push(event);
    // Keep only most recent events
    while (events.length > maxEvents) {
      events.shift();
    }
  };

  const getErrorMessage = (error: Error | unknown): string => {
    if (error instanceof Error) {
      return error.message;
    }
    return String(error);
  };

  return {
    logDegradation(
      reason: DegradationReason,
      context: Record<string, unknown>,
    ) {
      logger.debug("Graceful degradation", {
        reason,
        ...context,
      });

      addEvent({
        type: "degradation",
        reason,
        context,
        timestamp: Date.now(),
      });
    },

    logRetry(attempt: number, maxAttempts: number, error: Error) {
      logger.warn(`Retry attempt ${attempt}/${maxAttempts}`, {
        attempt,
        maxAttempts,
        error: error.message,
      });

      addEvent({
        type: "retry",
        context: {},
        metrics: {
          attempt,
          maxAttempts,
        },
        error: error.message,
        timestamp: Date.now(),
      });
    },

    logBackoff(attempt: number, delayMs: number) {
      logger.debug("Exponential backoff", {
        attempt,
        delayMs,
      });

      addEvent({
        type: "backoff",
        context: {},
        metrics: {
          attempt,
          delayMs,
        },
        timestamp: Date.now(),
      });
    },

    logFallback(reason: string, fallbackValue: unknown) {
      logger.debug("Using fallback", {
        reason,
        fallback: fallbackValue,
      });

      addEvent({
        type: "fallback",
        reason,
        context: { fallback: fallbackValue },
        timestamp: Date.now(),
      });
    },

    logError(error: Error | unknown, context: Record<string, unknown>) {
      const errorMessage = getErrorMessage(error);

      logger.error("Error occurred", {
        error: errorMessage,
        ...context,
      });

      addEvent({
        type: "error",
        context,
        error: errorMessage,
        timestamp: Date.now(),
      });
    },

    getEvents() {
      return [...events];
    },

    clearEvents() {
      events.length = 0;
    },
  };
}

// =============================================================================
// React Hook
// =============================================================================

/**
 * React hook for hook telemetry.
 * Creates a stable telemetry instance that persists across renders.
 *
 * @param hookName - The name of the hook (used as log prefix)
 * @param options - Configuration options
 * @returns A HookTelemetry instance
 *
 * @example
 * ```ts
 * function useMyHook() {
 *   const telemetry = useHookTelemetry("useMyHook");
 *
 *   useEffect(() => {
 *     if (!sessionId) {
 *       telemetry.logDegradation("missing_session_id", {});
 *       return;
 *     }
 *   }, [sessionId, telemetry]);
 * }
 * ```
 */
export function useHookTelemetry(
  hookName: string,
  options: HookTelemetryOptions = {},
): HookTelemetry {
  // Create stable telemetry instance
  return useMemo(
    () => createHookTelemetry(hookName, options),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [hookName], // Only recreate if hookName changes
  );
}
