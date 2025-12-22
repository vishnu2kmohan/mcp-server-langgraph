/**
 * ErrorClassifier
 *
 * Classification logic for analyzing errors and categorizing them
 * for appropriate handling. Supports:
 * - Standard Error objects
 * - Fetch Response objects
 * - Axios error objects
 * - WebSocket close events
 */

import {
  type ErrorCategory,
  type ClassifiedError,
  createClassifiedError,
  getErrorCategory,
  ERROR_CODES,
} from "./ErrorTypes";

/**
 * Options for error classification
 */
export interface ErrorClassificationOptions {
  /** HTTP status code */
  statusCode?: number;
  /** Error code string */
  code?: string;
  /** Trace ID for debugging */
  traceId?: string;
  /** Additional context */
  context?: Record<string, unknown>;
  /** Retry-after time in milliseconds */
  retryAfter?: number;
}

/**
 * Message patterns to error category mapping
 */
const MESSAGE_PATTERNS: Array<{ pattern: RegExp; category: ErrorCategory }> = [
  { pattern: /network\s*error/i, category: "network" },
  { pattern: /failed\s*to\s*fetch/i, category: "network" },
  { pattern: /cors/i, category: "network" },
  { pattern: /offline/i, category: "network" },
  { pattern: /no\s*internet/i, category: "network" },
  { pattern: /time\s*out/i, category: "timeout" },
  { pattern: /timed\s*out/i, category: "timeout" },
  { pattern: /timeout/i, category: "timeout" },
  { pattern: /aborted/i, category: "timeout" },
  { pattern: /rate\s*limit/i, category: "quota" },
  { pattern: /too\s*many\s*requests/i, category: "quota" },
  { pattern: /unauthorized/i, category: "authentication" },
  { pattern: /unauthenticated/i, category: "authentication" },
  { pattern: /token\s*expired/i, category: "authentication" },
  { pattern: /session\s*expired/i, category: "authentication" },
  { pattern: /forbidden/i, category: "authorization" },
  { pattern: /permission\s*denied/i, category: "authorization" },
  { pattern: /not\s*allowed/i, category: "authorization" },
  { pattern: /invalid\s*input/i, category: "validation" },
  { pattern: /validation\s*error/i, category: "validation" },
  { pattern: /bad\s*request/i, category: "validation" },
];

/**
 * Detect category from error message
 */
function detectCategoryFromMessage(message: string): ErrorCategory | null {
  for (const { pattern, category } of MESSAGE_PATTERNS) {
    if (pattern.test(message)) {
      return category;
    }
  }
  return null;
}

/**
 * Detect category from error type
 */
function detectCategoryFromErrorType(error: Error): ErrorCategory | null {
  if (error instanceof TypeError) {
    return "client";
  }
  if (error.name === "AbortError" || error instanceof DOMException) {
    return "timeout";
  }
  return null;
}

/**
 * Classify a generic error
 */
export function classifyError(
  error: Error | unknown,
  options: ErrorClassificationOptions = {}
): ClassifiedError {
  // Handle null/undefined
  if (error === null || error === undefined) {
    return createClassifiedError(
      new Error("Unknown error occurred"),
      "unknown",
      options
    );
  }

  // Handle string errors
  if (typeof error === "string") {
    return createClassifiedError(new Error(error), "unknown", options);
  }

  // Get message
  const message =
    error instanceof Error
      ? error.message
      : typeof error === "object" && "message" in error
        ? String((error as Record<string, unknown>).message)
        : "Unknown error occurred";

  // Priority 1: Status code
  const statusCategory = options.statusCode ? ERROR_CODES[options.statusCode] : undefined;
  if (statusCategory) {
    return createClassifiedError(error, statusCategory, {
      ...options,
    });
  }

  // Priority 2: Error type detection
  if (error instanceof Error) {
    const typeCategory = detectCategoryFromErrorType(error);
    if (typeCategory) {
      // For TypeError, also check message for more specific category
      const messageCategory = detectCategoryFromMessage(message);
      return createClassifiedError(
        error,
        messageCategory ?? typeCategory,
        options
      );
    }
  }

  // Priority 3: Message pattern matching
  const messageCategory = detectCategoryFromMessage(message);
  if (messageCategory) {
    return createClassifiedError(error, messageCategory, options);
  }

  // Priority 4: Error code string
  if (options.code) {
    const codeCategory = getErrorCategory(options.code);
    if (codeCategory !== "unknown") {
      return createClassifiedError(error, codeCategory, options);
    }
  }

  // Default: unknown
  return createClassifiedError(error, "unknown", options);
}

/**
 * Classify a fetch Response or fetch error
 */
export function classifyFetchError(
  responseOrError: Response | Error
): ClassifiedError | Promise<ClassifiedError> {
  // Check for AbortError first (by name - works in all environments)
  // DOMException may not be caught by instanceof Error in some test environments
  if (
    "name" in responseOrError &&
    (responseOrError as Error).name === "AbortError"
  ) {
    return createClassifiedError(responseOrError as Error, "timeout");
  }

  // Handle Error (e.g., TypeError from failed fetch)
  if (responseOrError instanceof Error) {
    if (responseOrError instanceof TypeError) {
      return classifyError(responseOrError, { code: "NETWORK_ERROR" });
    }
    return classifyError(responseOrError);
  }

  // Handle Response
  const response = responseOrError;
  return (async () => {
    const options: ErrorClassificationOptions = {
      statusCode: response.status,
    };

    // Extract trace ID
    const traceId =
      response.headers.get("X-Trace-ID") ??
      response.headers.get("x-trace-id") ??
      undefined;
    if (traceId) {
      options.traceId = traceId;
    }

    // Extract retry-after for rate limits
    const retryAfter = response.headers.get("Retry-After");
    if (retryAfter) {
      // Convert seconds to milliseconds
      const seconds = parseInt(retryAfter, 10);
      if (!isNaN(seconds)) {
        options.retryAfter = seconds * 1000;
      }
    }

    // Try to parse error body
    let message = response.statusText || `HTTP ${response.status}`;
    const contentType = response.headers.get("Content-Type");
    if (contentType?.includes("application/json")) {
      try {
        const body = await response.json();
        if (body.error) {
          if (typeof body.error === "string") {
            message = body.error;
          } else if (body.error.message) {
            message = body.error.message;
            if (body.error.code) {
              options.code = body.error.code;
            }
          }
        } else if (body.message) {
          message = body.message;
        }
      } catch {
        // Ignore JSON parsing errors
      }
    }

    const error = new Error(message);
    return classifyError(error, options);
  })();
}

/**
 * Axios error structure (simplified)
 */
interface AxiosError {
  isAxiosError: boolean;
  response?: {
    status: number;
    data?: {
      error?: string | { code?: string; message?: string };
      message?: string;
    };
    headers?: Record<string, string>;
  };
  message: string;
  code?: string;
}

/**
 * Classify an Axios error
 */
export function classifyAxiosError(error: AxiosError): ClassifiedError {
  const options: ErrorClassificationOptions = {};
  const message = error.message ?? "";

  // Check for timeout
  if (error.code === "ECONNABORTED" || message.includes("timeout")) {
    return createClassifiedError(error, "timeout", options);
  }

  // Check for network error (no response)
  if (!error.response) {
    if (error.code === "ERR_NETWORK" || message.includes("Network")) {
      return createClassifiedError(error, "network", options);
    }
    return createClassifiedError(error, "unknown", options);
  }

  // Has response - classify by status
  const { response } = error;
  options.statusCode = response.status;

  // Extract trace ID
  if (response.headers) {
    const traceId =
      response.headers["x-trace-id"] ?? response.headers["X-Trace-ID"];
    if (traceId) {
      options.traceId = traceId;
    }
  }

  // Extract error code from response data
  if (response.data?.error) {
    if (typeof response.data.error === "object" && response.data.error.code) {
      options.code = response.data.error.code;
    }
  }

  return classifyError(new Error(error.message), options);
}

/**
 * WebSocket close event structure
 */
interface WebSocketCloseEvent {
  code: number;
  reason?: string;
}

/**
 * WebSocket close codes to error category mapping
 */
const WS_CLOSE_CODES: Record<number, ErrorCategory> = {
  1000: "client", // Normal closure
  1001: "client", // Going away
  1002: "client", // Protocol error
  1003: "client", // Unsupported data
  1006: "network", // Abnormal closure (connection lost)
  1007: "validation", // Invalid data
  1008: "authorization", // Policy violation
  1009: "validation", // Message too big
  1010: "client", // Mandatory extension
  1011: "server", // Internal server error
  1015: "network", // TLS handshake failure
  // Custom codes (4xxx range)
  4001: "authentication", // Unauthorized
  4003: "authorization", // Forbidden
  4029: "quota", // Rate limited
};

/**
 * Classify a WebSocket close event
 */
export function classifyWebSocketError(
  event: WebSocketCloseEvent
): ClassifiedError {
  const category = WS_CLOSE_CODES[event.code] ?? "unknown";
  const message = event.reason || `WebSocket closed with code ${event.code}`;

  // Normal closure (1000) is not recoverable - it's intentional
  const recoverable = event.code === 1000 ? false : undefined;

  return createClassifiedError(new Error(message), category, {
    code: `WS_${event.code}`,
    context: { wsCode: event.code, reason: event.reason },
    recoverable,
  });
}

export default {
  classifyError,
  classifyFetchError,
  classifyAxiosError,
  classifyWebSocketError,
};
