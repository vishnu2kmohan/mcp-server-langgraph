/**
 * WebSocket Reconnection Metrics Types
 *
 * Types for tracking WebSocket reconnection behavior, timing, and failure reasons.
 * Used by useRealtimeSync and other WebSocket hooks for observability.
 */

/**
 * Categorized reasons for WebSocket reconnection failures.
 */
export type ReconnectionFailureReason =
  | "max_attempts_exceeded" // Exceeded maxReconnectAttempts
  | "token_expired" // Authentication token expired (4010)
  | "token_refresh_failed" // Token refresh after 4010 failed
  | "network_error" // Network-level failures
  | "server_error" // Server-side close (5xx equivalent)
  | "invalid_url" // Invalid WebSocket URL
  | "manual_disconnect" // User-initiated disconnect
  | "unknown"; // Unclassified failures

/**
 * WebSocket close code categories for failure reason classification.
 */
export const WS_CLOSE_CODE_CATEGORIES: Record<
  string,
  ReconnectionFailureReason
> = {
  // Normal closure - not a failure
  "1000": "manual_disconnect",
  // Going away (e.g., page navigation)
  "1001": "manual_disconnect",
  // Protocol error
  "1002": "server_error",
  // Unsupported data
  "1003": "server_error",
  // Reserved
  "1004": "unknown",
  // No status received
  "1005": "unknown",
  // Abnormal closure (network issue)
  "1006": "network_error",
  // Invalid frame payload
  "1007": "server_error",
  // Policy violation
  "1008": "server_error",
  // Message too big
  "1009": "server_error",
  // Mandatory extension missing
  "1010": "server_error",
  // Internal server error
  "1011": "server_error",
  // TLS handshake failure
  "1015": "network_error",
  // Token expired (custom code)
  "4010": "token_expired",
};

/**
 * Individual reconnection attempt record.
 */
export interface ReconnectionAttempt {
  /** Timestamp when the attempt started */
  timestamp: number;
  /** Attempt number (1-based) */
  attemptNumber: number;
  /** Whether this attempt succeeded */
  succeeded: boolean;
  /** Duration of the attempt in milliseconds (null if still in progress) */
  durationMs: number | null;
  /** Reason for failure (null if succeeded) */
  failureReason: ReconnectionFailureReason | null;
  /** WebSocket close code that triggered this attempt (null for initial connection) */
  triggerCloseCode: number | null;
}

/**
 * Aggregated reconnection metrics for observability.
 */
export interface ReconnectionMetrics {
  // === Counts ===

  /** Total number of successful reconnections */
  totalReconnections: number;

  /** Total number of reconnection attempts (including failures) */
  totalAttempts: number;

  /** Current streak of consecutive failures (resets on success) */
  consecutiveFailures: number;

  // === Timing ===

  /** Timestamp of last successful reconnection (null if never reconnected) */
  lastReconnectionTime: number | null;

  /** Timestamp of last disconnection (null if never disconnected) */
  lastDisconnectionTime: number | null;

  /** Average duration of successful reconnections in milliseconds */
  avgReconnectionDurationMs: number | null;

  /** Total time spent reconnecting in milliseconds */
  totalReconnectionTimeMs: number;

  // === Failure Tracking ===

  /** Count of failures by reason */
  failuresByReason: Record<ReconnectionFailureReason, number>;

  // === Derived Metrics ===

  /** Success rate as percentage (0-100), null if no attempts */
  successRate: number | null;

  /** Recent reconnection attempts (limited to last N) */
  recentAttempts: ReconnectionAttempt[];
}

/**
 * Options for reconnection metrics tracking.
 */
export interface ReconnectionMetricsOptions {
  /** Maximum number of recent attempts to keep in history (default: 10) */
  maxRecentAttempts?: number;
  /** Whether to track detailed attempt history (default: true) */
  trackHistory?: boolean;
}

/**
 * Create initial empty metrics state.
 */
export function createInitialReconnectionMetrics(): ReconnectionMetrics {
  return {
    totalReconnections: 0,
    totalAttempts: 0,
    consecutiveFailures: 0,
    lastReconnectionTime: null,
    lastDisconnectionTime: null,
    avgReconnectionDurationMs: null,
    totalReconnectionTimeMs: 0,
    failuresByReason: {
      max_attempts_exceeded: 0,
      token_expired: 0,
      token_refresh_failed: 0,
      network_error: 0,
      server_error: 0,
      invalid_url: 0,
      manual_disconnect: 0,
      unknown: 0,
    },
    successRate: null,
    recentAttempts: [],
  };
}

/**
 * Classify a WebSocket close code into a failure reason.
 */
export function classifyCloseCode(code: number): ReconnectionFailureReason {
  const category = WS_CLOSE_CODE_CATEGORIES[String(code)];
  return category ?? "unknown";
}

/**
 * Calculate success rate from metrics.
 */
export function calculateSuccessRate(
  totalReconnections: number,
  totalAttempts: number,
): number | null {
  if (totalAttempts === 0) return null;
  return Math.round((totalReconnections / totalAttempts) * 100);
}

/**
 * Calculate average reconnection duration.
 */
export function calculateAvgDuration(
  totalTimeMs: number,
  totalReconnections: number,
): number | null {
  if (totalReconnections === 0) return null;
  return Math.round(totalTimeMs / totalReconnections);
}
