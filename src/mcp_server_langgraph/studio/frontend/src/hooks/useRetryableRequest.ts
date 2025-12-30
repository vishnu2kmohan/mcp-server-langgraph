/**
 * useRetryableRequest Hook
 *
 * @deprecated This hook has no active runtime consumers and is scheduled for removal.
 * Consider using RTK Query's built-in retry mechanism instead:
 * - RTK Query provides automatic retry with `retry` option in baseQuery
 * - For custom retry logic, use the `retryCondition` in RTK Query
 *
 * If you need this functionality, please migrate to RTK Query patterns:
 * @see https://redux-toolkit.js.org/rtk-query/usage/customizing-queries#automatic-retries
 *
 * Original functionality:
 * - Exponential backoff with jitter
 * - Configurable max retries
 * - Cancel pending requests/retries
 * - Force immediate retry
 * - Status tracking (idle, loading, success, error, cancelled)
 *
 * Deprecation reason: No clear consumer in the codebase (Phase 5 hooks audit).
 * Removal timeline: Next major version
 */

import { useState, useCallback, useRef } from "react";
import {
  calculateBackoff,
  shouldRetry,
  getRetryConfig,
  type RetryConfig,
} from "../utils/retryStrategy";
import { classifyError } from "../errors/ErrorClassifier";
import type { ClassifiedError } from "../errors/ErrorTypes";

/**
 * Request status
 */
export type RequestStatus =
  | "idle"
  | "loading"
  | "success"
  | "error"
  | "cancelled";

/**
 * Hook result
 */
export interface RetryableRequestResult<T = unknown> {
  /** Current request status */
  status: RequestStatus;
  /** Response data (on success) */
  data: T | null;
  /** Classified error (on failure) */
  error: ClassifiedError | null;
  /** Number of retry attempts made */
  retryCount: number;
  /** Whether currently waiting to retry */
  isRetrying: boolean;
  /** Execute a request with retry */
  execute: (requestFn: () => Promise<T>) => Promise<T | null>;
  /** Cancel pending request and retries */
  cancel: () => void;
  /** Force immediate retry (skip backoff) */
  forceRetry: () => void;
  /** Get delay until next retry (ms) */
  getNextRetryDelay: () => number;
}

/**
 * Hook options
 */
export interface UseRetryableRequestOptions extends Partial<RetryConfig> {
  /** Callback on successful request */
  onSuccess?: (data: unknown) => void;
  /** Callback on final failure (after all retries) */
  onError?: (error: ClassifiedError) => void;
  /** Callback on each retry attempt */
  onRetry?: (attemptNumber: number, error: ClassifiedError) => void;
}

/**
 * Hook for making retryable HTTP requests.
 *
 * @deprecated Use RTK Query's built-in retry mechanism instead. See file header for migration guide.
 *
 * @example
 * ```tsx
 * const { execute, status, data, error, cancel, forceRetry } = useRetryableRequest({
 *   maxRetries: 3,
 *   onRetry: (attempt, error) => console.log(`Retry ${attempt}:`, error),
 * });
 *
 * const handleFetch = async () => {
 *   const result = await execute(() => fetch('/api/data').then(r => r.json()));
 *   if (result) {
 *     console.log('Success:', result);
 *   }
 * };
 *
 * // UI shows retry button when isRetrying
 * {isRetrying && <button onClick={forceRetry}>Retry Now</button>}
 * ```
 */
export function useRetryableRequest<T = unknown>(
  options: UseRetryableRequestOptions = {},
): RetryableRequestResult<T> {
  const config = getRetryConfig(options);

  // State
  const [status, setStatus] = useState<RequestStatus>("idle");
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ClassifiedError | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isRetrying, setIsRetrying] = useState(false);
  const [nextRetryDelay, setNextRetryDelay] = useState(0);

  // Refs for managing async state
  const cancelledRef = useRef(false);
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentRequestFnRef = useRef<(() => Promise<T>) | null>(null);
  const lastErrorRef = useRef<ClassifiedError | null>(null);

  /**
   * Clear retry timeout
   */
  const clearRetryTimeout = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
  }, []);

  /**
   * Reset state for new request
   */
  const resetState = useCallback(() => {
    clearRetryTimeout();
    setData(null);
    setError(null);
    setRetryCount(0);
    setIsRetrying(false);
    setNextRetryDelay(0);
    cancelledRef.current = false;
    lastErrorRef.current = null;
  }, [clearRetryTimeout]);

  /**
   * Execute a single attempt
   */
  const executeAttempt = useCallback(
    async (requestFn: () => Promise<T>, attempt: number): Promise<T | null> => {
      // Check if cancelled
      if (cancelledRef.current) {
        return null;
      }

      try {
        setStatus("loading");
        setIsRetrying(false);

        const result = await requestFn();

        // Check if cancelled during request
        if (cancelledRef.current) {
          return null;
        }

        // Success
        setStatus("success");
        setData(result);
        setError(null);
        setRetryCount(0);
        options.onSuccess?.(result);

        return result;
      } catch (err) {
        // Check if cancelled
        if (cancelledRef.current) {
          return null;
        }

        // Classify the error
        const classifiedError = classifyError(err);
        lastErrorRef.current = classifiedError;

        // Check if we should retry
        const context = { attemptNumber: attempt, config };

        if (shouldRetry(classifiedError, context)) {
          // Calculate backoff delay (use retryAfter if available)
          const delay =
            classifiedError.retryAfter ?? calculateBackoff(attempt, config);

          setRetryCount(attempt + 1);
          setIsRetrying(true);
          setNextRetryDelay(delay);
          options.onRetry?.(attempt + 1, classifiedError);

          // Schedule retry
          return new Promise((resolve) => {
            retryTimeoutRef.current = setTimeout(async () => {
              if (!cancelledRef.current) {
                const result = await executeAttempt(requestFn, attempt + 1);
                resolve(result);
              } else {
                resolve(null);
              }
            }, delay);
          });
        }

        // No more retries - final failure
        setStatus("error");
        setError(classifiedError);
        setIsRetrying(false);
        options.onError?.(classifiedError);

        return null;
      }
    },
    [config, options],
  );

  /**
   * Execute a request with retry logic
   */
  const execute = useCallback(
    async (requestFn: () => Promise<T>): Promise<T | null> => {
      resetState();
      currentRequestFnRef.current = requestFn;
      return executeAttempt(requestFn, 0);
    },
    [resetState, executeAttempt],
  );

  /**
   * Cancel pending request and retries
   */
  const cancel = useCallback(() => {
    cancelledRef.current = true;
    clearRetryTimeout();
    setStatus("cancelled");
    setIsRetrying(false);
  }, [clearRetryTimeout]);

  /**
   * Force immediate retry without waiting for backoff
   */
  const forceRetry = useCallback(() => {
    const requestFn = currentRequestFnRef.current;
    if (!requestFn || cancelledRef.current) return;

    clearRetryTimeout();
    setIsRetrying(false);

    // Execute with current retry count
    executeAttempt(requestFn, retryCount);
  }, [clearRetryTimeout, executeAttempt, retryCount]);

  /**
   * Get delay until next retry
   */
  const getNextRetryDelay = useCallback(() => {
    return nextRetryDelay;
  }, [nextRetryDelay]);

  return {
    status,
    data,
    error,
    retryCount,
    isRetrying,
    execute,
    cancel,
    forceRetry,
    getNextRetryDelay,
  };
}

export default useRetryableRequest;
