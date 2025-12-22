/**
 * Retry Strategy
 *
 * Implements exponential backoff with jitter for retrying failed requests.
 * Based on AWS best practices for exponential backoff.
 *
 * Features:
 * - Exponential backoff with configurable base and max delays
 * - Jitter to prevent thundering herd
 * - Category-based retry decisions
 * - Integration with error classification
 */

import type { ClassifiedError, ErrorCategory } from "../errors/ErrorTypes";

/**
 * Retry configuration
 */
export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxRetries: number;
  /** Base delay in milliseconds */
  baseDelayMs: number;
  /** Maximum delay in milliseconds (cap) */
  maxDelayMs: number;
  /** Multiplier for exponential backoff */
  backoffMultiplier: number;
  /** Jitter factor (0-1) to add randomness */
  jitterFactor: number;
  /** Error categories that are retryable */
  retryableCategories?: ErrorCategory[];
}

/**
 * Retry context for decision making
 */
export interface RetryContext {
  /** Current attempt number (0-based) */
  attemptNumber: number;
  /** Retry configuration */
  config: RetryConfig;
}

/**
 * Default retry configuration
 */
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 16000,
  backoffMultiplier: 2,
  jitterFactor: 0.1,
  retryableCategories: ["network", "timeout", "server", "quota"],
};

/**
 * Calculate backoff delay for a given attempt.
 *
 * Formula: min(maxDelay, baseDelay * multiplier^attempt) * (1 ± jitter)
 *
 * @param attempt - Current attempt number (0-based)
 * @param config - Retry configuration
 * @returns Delay in milliseconds
 */
export function calculateBackoff(attempt: number, config: RetryConfig): number {
  const { baseDelayMs, maxDelayMs, backoffMultiplier, jitterFactor } = config;

  // Calculate base exponential delay
  const exponentialDelay = baseDelayMs * Math.pow(backoffMultiplier, attempt);

  // Cap at maximum delay
  const cappedDelay = Math.min(exponentialDelay, maxDelayMs);

  // Add jitter if configured
  if (jitterFactor > 0) {
    const jitterRange = cappedDelay * jitterFactor;
    const jitter = (Math.random() * 2 - 1) * jitterRange; // -jitterRange to +jitterRange
    return Math.max(0, Math.round(cappedDelay + jitter));
  }

  return cappedDelay;
}

/**
 * Determine if an error should be retried.
 *
 * @param error - Classified error
 * @param context - Retry context
 * @returns Whether to retry
 */
export function shouldRetry(
  error: ClassifiedError,
  context: RetryContext
): boolean {
  const { attemptNumber, config } = context;
  const { maxRetries, retryableCategories = DEFAULT_RETRY_CONFIG.retryableCategories } = config;

  // Check if we've exceeded max retries
  if (attemptNumber >= maxRetries) {
    return false;
  }

  // Non-recoverable errors should never be retried
  if (error.recoverable === false) {
    return false;
  }

  // Special handling for certain categories that should never be retried
  switch (error.category) {
    case "authentication":
      // Never retry auth errors - user needs to re-login
      return false;

    case "authorization":
      // Never retry authz errors - user lacks permission
      return false;

    case "validation":
      // Never retry validation errors - input is wrong
      return false;

    case "client":
      // Client errors (4xx) are generally not retryable
      return false;

    case "quota":
      // Quota errors should be retried with retryAfter if provided
      return true;

    default:
      break;
  }

  // "Maybe" recoverable errors only get one retry attempt
  if (error.recoverable === "maybe") {
    return attemptNumber < 1;
  }

  // Check if category is in retryable list
  const isRetryableCategory = retryableCategories?.includes(error.category) ?? false;

  return isRetryableCategory;
}

/**
 * Get retry configuration with optional overrides.
 *
 * @param overrides - Partial configuration to merge
 * @returns Complete retry configuration
 */
export function getRetryConfig(overrides?: Partial<RetryConfig>): RetryConfig {
  if (!overrides) {
    return { ...DEFAULT_RETRY_CONFIG };
  }

  return {
    ...DEFAULT_RETRY_CONFIG,
    ...overrides,
  };
}

export default {
  calculateBackoff,
  shouldRetry,
  getRetryConfig,
  DEFAULT_RETRY_CONFIG,
};
