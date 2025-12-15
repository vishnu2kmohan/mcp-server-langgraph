/**
 * useDebounce Hook
 *
 * Custom hooks for debouncing values and callbacks to optimize
 * API calls by delaying execution until user stops typing.
 */

import { useState, useEffect, useRef, useCallback, useMemo } from "react";

/**
 * Debounce a value - returns the debounced value that updates
 * after the specified delay.
 *
 * @param value - The value to debounce
 * @param delay - Delay in milliseconds (default: 300ms)
 * @returns The debounced value
 *
 * @example
 * const [searchQuery, setSearchQuery] = useState('');
 * const debouncedQuery = useDebounce(searchQuery, 300);
 *
 * useEffect(() => {
 *   // This will only run 300ms after the user stops typing
 *   searchApi(debouncedQuery);
 * }, [debouncedQuery]);
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Debounced callback with cancel and flush capabilities.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface DebouncedFunction<T extends (...args: any[]) => any> {
  (...args: Parameters<T>): void;
  cancel: () => void;
  flush: () => void;
}

/**
 * Create a debounced version of a callback function.
 *
 * @param callback - The callback to debounce
 * @param delay - Delay in milliseconds (default: 300ms)
 * @returns Debounced function with cancel and flush methods
 *
 * @example
 * const handleSearch = useDebouncedCallback((query: string) => {
 *   searchApi(query);
 * }, 300);
 *
 * <input onChange={(e) => handleSearch(e.target.value)} />
 *
 * // Cancel pending call
 * handleSearch.cancel();
 *
 * // Execute immediately
 * handleSearch.flush();
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number = 300,
): DebouncedFunction<T> {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(callback);
  const argsRef = useRef<Parameters<T> | null>(null);

  // Update callback ref on every render to get the latest callback
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      // Guard for test environments where clearTimeout may be undefined during cleanup
      if (typeof clearTimeout === "function") {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = null;
    }
    argsRef.current = null;
  }, []);

  const flush = useCallback(() => {
    if (timeoutRef.current && argsRef.current !== null) {
      if (typeof clearTimeout === "function") {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = null;
      callbackRef.current(...argsRef.current);
      argsRef.current = null;
    }
  }, []);

  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      argsRef.current = args;

      if (timeoutRef.current && typeof clearTimeout === "function") {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        timeoutRef.current = null;
        callbackRef.current(...args);
        argsRef.current = null;
      }, delay);
    },
    [delay],
  );

  // Cleanup on unmount
  useEffect(() => {
    return cancel;
  }, [cancel]);

  // Return the debounced function with cancel and flush methods
  return useMemo(() => {
    const fn = debouncedCallback as DebouncedFunction<T>;
    fn.cancel = cancel;
    fn.flush = flush;
    return fn;
  }, [debouncedCallback, cancel, flush]);
}

export default useDebounce;
