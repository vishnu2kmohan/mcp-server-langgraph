/**
 * ErrorTypes
 *
 * A typed error taxonomy for consistent error handling across the application.
 * Provides error categories, classification, and type guards.
 *
 * Error Categories (based on recovery strategy):
 * - network: Connectivity issues (recoverable via retry)
 * - authentication: Session expired (recoverable via re-auth)
 * - authorization: Permission denied (not recoverable)
 * - validation: Input errors (not recoverable, fix input)
 * - server: 5xx errors (recoverable via retry)
 * - client: 4xx errors (depends on specific error)
 * - timeout: Request timeout (recoverable via retry)
 * - quota: Rate limiting (recoverable via wait)
 * - unknown: Catch-all (maybe recoverable)
 */

/**
 * Error categories based on recovery strategy
 */
export type ErrorCategory =
  | "network"
  | "authentication"
  | "authorization"
  | "validation"
  | "server"
  | "client"
  | "timeout"
  | "quota"
  | "unknown";

/**
 * All supported error categories
 */
export const ERROR_CATEGORIES: ErrorCategory[] = [
  "network",
  "authentication",
  "authorization",
  "validation",
  "server",
  "client",
  "timeout",
  "quota",
  "unknown",
];

/**
 * HTTP status code to error category mapping
 */
export const ERROR_CODES: Record<number, ErrorCategory> = {
  400: "validation",
  401: "authentication",
  403: "authorization",
  404: "client",
  405: "client",
  408: "timeout",
  409: "client",
  410: "client",
  422: "validation",
  429: "quota",
  500: "server",
  501: "server",
  502: "server",
  503: "server",
  504: "timeout",
};

/**
 * Error code string patterns to category mapping
 */
const ERROR_CODE_PATTERNS: Record<string, ErrorCategory> = {
  NETWORK: "network",
  AUTH_EXPIRED: "authentication",
  TOKEN_EXPIRED: "authentication",
  SESSION_EXPIRED: "authentication",
  PERMISSION_DENIED: "authorization",
  FORBIDDEN: "authorization",
  INVALID_INPUT: "validation",
  VALIDATION: "validation",
  RATE_LIMITED: "quota",
  RATE_LIMIT: "quota",
  TIMEOUT: "timeout",
  CONNECTION_TIMEOUT: "timeout",
};

/**
 * Recoverability by error category
 */
const RECOVERABILITY: Record<ErrorCategory, boolean | "maybe"> = {
  network: true,
  authentication: true,
  authorization: false,
  validation: false,
  server: true,
  client: "maybe",
  timeout: true,
  quota: true,
  unknown: "maybe",
};

/**
 * A classified error with category and metadata
 */
export interface ClassifiedError {
  /** Error category for routing */
  category: ErrorCategory;
  /** Human-readable message */
  message: string;
  /** Whether the error is recoverable */
  recoverable: boolean | "maybe";
  /** When the error occurred */
  timestamp: number;
  /** The original error object */
  originalError: Error | unknown;
  /** Optional error code */
  code?: string;
  /** Optional HTTP status code */
  statusCode?: number;
  /** Optional trace ID for debugging */
  traceId?: string;
  /** Optional context about the error */
  context?: Record<string, unknown>;
  /** Optional retry-after in milliseconds */
  retryAfter?: number;
  /** Optional user-friendly message override */
  userMessage?: string;
}

/**
 * Type alias for error codes
 */
export type ErrorCode = keyof typeof ERROR_CODES;

/**
 * Check if an error category is recoverable
 */
export function isRecoverable(category: ErrorCategory): boolean | "maybe" {
  return RECOVERABILITY[category];
}

/**
 * Get error category from status code or error code string
 */
export function getErrorCategory(codeOrStatus: number | string): ErrorCategory {
  if (typeof codeOrStatus === "number") {
    return ERROR_CODES[codeOrStatus] ?? "unknown";
  }

  // Check pattern matching for error code strings
  const upperCode = codeOrStatus.toUpperCase();
  for (const [pattern, category] of Object.entries(ERROR_CODE_PATTERNS)) {
    if (upperCode.includes(pattern)) {
      return category;
    }
  }

  return "unknown";
}

/**
 * Options for creating a classified error
 */
export interface CreateClassifiedErrorOptions {
  code?: string;
  statusCode?: number;
  traceId?: string;
  context?: Record<string, unknown>;
  retryAfter?: number;
  userMessage?: string;
  recoverable?: boolean;
}

/**
 * Create a classified error from an Error object
 */
export function createClassifiedError(
  error: Error | unknown,
  category: ErrorCategory,
  options: CreateClassifiedErrorOptions = {}
): ClassifiedError {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === "object" && error !== null && "message" in error
        ? String((error as Record<string, unknown>).message)
        : typeof error === "string"
          ? error
          : "Unknown error occurred";

  const defaultRecoverable = isRecoverable(category);

  return {
    category,
    message,
    recoverable: options.recoverable ?? defaultRecoverable,
    timestamp: Date.now(),
    originalError: error,
    code: options.code,
    statusCode: options.statusCode,
    traceId: options.traceId,
    context: options.context,
    retryAfter: options.retryAfter,
    userMessage: options.userMessage,
  };
}

/**
 * Type guard: Check if error is a network error
 */
export function isNetworkError(error: ClassifiedError): boolean {
  return error.category === "network";
}

/**
 * Type guard: Check if error is an auth error (authentication or authorization)
 */
export function isAuthError(error: ClassifiedError): boolean {
  return error.category === "authentication" || error.category === "authorization";
}

/**
 * Type guard: Check if error is a validation error
 */
export function isValidationError(error: ClassifiedError): boolean {
  return error.category === "validation";
}

/**
 * Type guard: Check if error is a server error
 */
export function isServerError(error: ClassifiedError): boolean {
  return error.category === "server";
}

/**
 * Type guard: Check if error is a rate limit error
 */
export function isRateLimitError(error: ClassifiedError): boolean {
  return error.category === "quota";
}

export default {
  ERROR_CATEGORIES,
  ERROR_CODES,
  isRecoverable,
  getErrorCategory,
  createClassifiedError,
  isNetworkError,
  isAuthError,
  isValidationError,
  isServerError,
  isRateLimitError,
};
