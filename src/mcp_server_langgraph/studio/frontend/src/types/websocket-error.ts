/**
 * WebSocket Error Types
 *
 * Unified error types and utilities for WebSocket hooks.
 * Extends the protocol-level WebSocketError from websocket-protocols.ts
 * with hook-level error codes and factory functions.
 *
 * @see websocket-protocols.ts for protocol-level types (wire format)
 * @see errors/ErrorTypes.ts for application-level error classification
 */

// Re-export protocol-level types for convenience
export type {
  WebSocketError,
  WebSocketErrorCode,
  WebSocketErrorPayload,
} from "./websocket-protocols";
export { isWebSocketError } from "./websocket-protocols";

// =============================================================================
// Hook-Level Error Codes
// =============================================================================

/**
 * Extended error codes for hook-level error handling.
 * Includes protocol codes plus additional hook-specific codes.
 */
export type HookErrorCode =
  // Protocol-level codes (from WebSocketErrorCode)
  | "token_expired"
  | "unauthorized"
  | "rate_limited"
  | "internal_error"
  | "invalid_request"
  | "not_found"
  // Hook-specific codes
  | "missing_session_id"
  | "network_error"
  | "connection_closed"
  | "server_error"
  | "validation_error"
  | "timeout";

/**
 * Error category for classification and handling decisions.
 */
export type ErrorCategory =
  | "authentication"
  | "network"
  | "server"
  | "client"
  | "quota"
  | "unknown";

/**
 * Hook-level WebSocket error with extended metadata.
 */
export interface HookWebSocketError {
  /** Error code for programmatic handling */
  code: HookErrorCode;
  /** Human-readable error message */
  message: string;
  /** Whether the error is recoverable via retry */
  retryable: boolean;
  /** Timestamp when error occurred */
  timestamp: number;
  /** Optional error category */
  category?: ErrorCategory;
  /** Optional additional details */
  details?: Record<string, unknown>;
  /** Optional context for debugging/telemetry */
  context?: {
    traceId?: string;
    retryAfter?: number;
    originalError?: Error;
    endpointId?: string;
  };
}

// =============================================================================
// WebSocket Close Codes
// =============================================================================

/**
 * Standard and custom WebSocket close codes.
 * Centralizes all close code constants.
 */
export const WEBSOCKET_CLOSE_CODES = {
  // Standard close codes (RFC 6455)
  NORMAL_CLOSURE: 1000,
  GOING_AWAY: 1001,
  PROTOCOL_ERROR: 1002,
  UNSUPPORTED_DATA: 1003,
  NO_STATUS_RECEIVED: 1005,
  ABNORMAL_CLOSURE: 1006,
  INVALID_FRAME_PAYLOAD: 1007,
  POLICY_VIOLATION: 1008,
  MESSAGE_TOO_BIG: 1009,
  MANDATORY_EXTENSION: 1010,
  INTERNAL_ERROR: 1011,
  TLS_HANDSHAKE: 1015,

  // Custom close codes (4000-4999)
  PROTOCOL_VERSION_MISMATCH: 4009,
  TOKEN_EXPIRED: 4010,
} as const;

export type WebSocketCloseCode =
  (typeof WEBSOCKET_CLOSE_CODES)[keyof typeof WEBSOCKET_CLOSE_CODES];

// =============================================================================
// Error Code Classification
// =============================================================================

/**
 * Map of error codes to their default retryable status.
 */
const RETRYABLE_CODES: Record<HookErrorCode, boolean> = {
  // Authentication - retryable with token refresh
  token_expired: true,
  unauthorized: false,

  // Network - retryable with backoff
  network_error: true,
  connection_closed: true,
  timeout: true,

  // Server - retryable with backoff
  internal_error: true,
  server_error: true,

  // Rate limiting - retryable after delay
  rate_limited: true,

  // Client errors - not retryable (fix required)
  invalid_request: false,
  validation_error: false,
  missing_session_id: false,
  not_found: false,
};

/**
 * Map of error codes to their category.
 */
const ERROR_CATEGORIES: Record<HookErrorCode, ErrorCategory> = {
  token_expired: "authentication",
  unauthorized: "authentication",

  network_error: "network",
  connection_closed: "network",
  timeout: "network",

  internal_error: "server",
  server_error: "server",

  rate_limited: "quota",

  invalid_request: "client",
  validation_error: "client",
  missing_session_id: "client",
  not_found: "client",
};

// =============================================================================
// Factory Functions
// =============================================================================

export interface CreateWebSocketErrorOptions {
  /** Override default retryable status */
  retryable?: boolean;
  /** Additional details for debugging */
  details?: Record<string, unknown>;
  /** Context for debugging/telemetry */
  context?: HookWebSocketError["context"];
}

/**
 * Create a standardized WebSocket error for hooks.
 *
 * @param code - The error code
 * @param message - Human-readable error message
 * @param options - Optional configuration
 * @returns A HookWebSocketError object
 *
 * @example
 * ```ts
 * const error = createWebSocketError("missing_session_id", "Session ID required");
 * setLastError(error);
 * ```
 */
export function createWebSocketError(
  code: HookErrorCode,
  message: string,
  options: CreateWebSocketErrorOptions = {},
): HookWebSocketError {
  const retryable = options.retryable ?? RETRYABLE_CODES[code] ?? false;
  const category = ERROR_CATEGORIES[code] ?? "unknown";

  return {
    code,
    message,
    retryable,
    timestamp: Date.now(),
    category,
    ...(options.details && { details: options.details }),
    ...(options.context && { context: options.context }),
  };
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Check if an error is retryable.
 *
 * @param error - The error to check
 * @returns true if the error can be retried
 */
export function isRetryableError(error: HookWebSocketError): boolean {
  return error.retryable;
}

/**
 * Get the category for an error code.
 *
 * @param code - The error code
 * @returns The error category
 */
export function getErrorCategory(code: HookErrorCode): ErrorCategory {
  return ERROR_CATEGORIES[code] ?? "unknown";
}

/**
 * Convert a WebSocket close code to an error code.
 *
 * @param closeCode - The WebSocket close code
 * @returns The corresponding HookErrorCode
 */
export function closeCodeToErrorCode(closeCode: number): HookErrorCode {
  switch (closeCode) {
    case WEBSOCKET_CLOSE_CODES.NORMAL_CLOSURE:
    case WEBSOCKET_CLOSE_CODES.GOING_AWAY:
      return "connection_closed";

    case WEBSOCKET_CLOSE_CODES.TOKEN_EXPIRED:
      return "token_expired";

    case WEBSOCKET_CLOSE_CODES.PROTOCOL_VERSION_MISMATCH:
      return "invalid_request";

    case WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE:
    case WEBSOCKET_CLOSE_CODES.TLS_HANDSHAKE:
      return "network_error";

    case WEBSOCKET_CLOSE_CODES.INTERNAL_ERROR:
      return "internal_error";

    case WEBSOCKET_CLOSE_CODES.PROTOCOL_ERROR:
    case WEBSOCKET_CLOSE_CODES.UNSUPPORTED_DATA:
    case WEBSOCKET_CLOSE_CODES.INVALID_FRAME_PAYLOAD:
    case WEBSOCKET_CLOSE_CODES.POLICY_VIOLATION:
    case WEBSOCKET_CLOSE_CODES.MESSAGE_TOO_BIG:
    case WEBSOCKET_CLOSE_CODES.MANDATORY_EXTENSION:
      return "server_error";

    default:
      // Custom codes in 4000-4999 range
      if (closeCode >= 4000 && closeCode < 5000) {
        return "server_error";
      }
      return "network_error";
  }
}

/**
 * Create an error from a WebSocket close event.
 *
 * @param closeCode - The close code from the event
 * @param reason - The close reason from the event
 * @returns A HookWebSocketError
 */
export function createErrorFromCloseEvent(
  closeCode: number,
  reason?: string,
): HookWebSocketError {
  const code = closeCodeToErrorCode(closeCode);
  const message = reason || `WebSocket closed with code ${closeCode}`;

  return createWebSocketError(code, message, {
    details: { closeCode },
  });
}
