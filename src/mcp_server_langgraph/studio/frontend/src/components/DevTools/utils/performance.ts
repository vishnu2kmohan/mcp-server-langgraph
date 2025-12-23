/**
 * Performance Utilities for DevTools
 *
 * Provides optimizations for rendering long lists, batching updates,
 * and debouncing expensive operations.
 */

import { useCallback, useMemo, useRef, useState, useEffect } from "react";

// =============================================================================
// Batched Updates
// =============================================================================

/**
 * Batches multiple updates into a single render cycle
 * Uses requestAnimationFrame for smooth updates
 */
export function useBatchedUpdates<T>(
  items: T[],
  batchSize: number = 50,
): { displayedItems: T[]; hasMore: boolean; loadMore: () => void } {
  const [displayedCount, setDisplayedCount] = useState(batchSize);

  const displayedItems = useMemo(
    () => items.slice(0, displayedCount),
    [items, displayedCount],
  );

  const hasMore = displayedCount < items.length;

  const loadMore = useCallback(() => {
    if (hasMore) {
      requestAnimationFrame(() => {
        setDisplayedCount((prev) => Math.min(prev + batchSize, items.length));
      });
    }
  }, [hasMore, batchSize, items.length]);

  // Reset when items change significantly
  useEffect(() => {
    if (items.length <= batchSize) {
      setDisplayedCount(batchSize);
    }
  }, [items.length, batchSize]);

  return { displayedItems, hasMore, loadMore };
}

// =============================================================================
// Debounced Value
// =============================================================================

/**
 * Debounces a value to prevent excessive re-renders
 */
export function useDebouncedValue<T>(value: T, delay: number = 150): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// =============================================================================
// Throttled Callback
// =============================================================================

/**
 * Throttles a callback to prevent excessive calls
 */
export function useThrottledCallback<T extends (...args: unknown[]) => void>(
  callback: T,
  delay: number = 100,
): T {
  const lastCall = useRef<number>(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  return useCallback(
    ((...args: unknown[]) => {
      const now = Date.now();
      const remaining = delay - (now - lastCall.current);

      if (remaining <= 0) {
        lastCall.current = now;
        callback(...args);
      } else if (!timeoutRef.current) {
        timeoutRef.current = setTimeout(() => {
          lastCall.current = Date.now();
          timeoutRef.current = undefined;
          callback(...args);
        }, remaining);
      }
    }) as T,
    [callback, delay],
  );
}

// =============================================================================
// Virtual List (Simple Implementation)
// =============================================================================

interface VirtualListOptions {
  itemHeight: number;
  overscan?: number;
  containerHeight: number;
}

interface VirtualListResult<T> {
  virtualItems: Array<{ item: T; index: number; style: React.CSSProperties }>;
  totalHeight: number;
  containerStyle: React.CSSProperties;
}

/**
 * Simple virtual list implementation for fixed-height items
 * For production, consider using @tanstack/react-virtual
 */
export function useVirtualList<T>(
  items: T[],
  scrollTop: number,
  options: VirtualListOptions,
): VirtualListResult<T> {
  const { itemHeight, overscan = 3, containerHeight } = options;

  return useMemo(() => {
    const totalHeight = items.length * itemHeight;

    // Calculate visible range
    const startIndex = Math.max(
      0,
      Math.floor(scrollTop / itemHeight) - overscan,
    );
    const endIndex = Math.min(
      items.length,
      Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan,
    );

    // Create virtual items
    const virtualItems = items.slice(startIndex, endIndex).map((item, i) => ({
      item,
      index: startIndex + i,
      style: {
        position: "absolute" as const,
        top: (startIndex + i) * itemHeight,
        height: itemHeight,
        left: 0,
        right: 0,
      },
    }));

    return {
      virtualItems,
      totalHeight,
      containerStyle: {
        position: "relative" as const,
        height: totalHeight,
      },
    };
  }, [items, scrollTop, itemHeight, overscan, containerHeight]);
}

// =============================================================================
// Memoized Filter
// =============================================================================

/**
 * Memoizes expensive filter operations
 */
export function useMemoizedFilter<T>(
  items: T[],
  filter: (item: T) => boolean,
  deps: unknown[] = [],
): T[] {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => items.filter(filter), [items, ...deps]);
}

// =============================================================================
// Stable Callback
// =============================================================================

/**
 * Creates a stable callback reference that doesn't change identity
 * Useful for preventing child re-renders
 */
export function useStableCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
): T {
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  return useCallback(((...args: unknown[]) => callbackRef.current(...args)) as T, []);
}

// =============================================================================
// Performance Measurement
// =============================================================================

/**
 * Measures render performance in development mode
 */
export function useRenderCount(componentName: string): void {
  const renderCount = useRef(0);

  useEffect(() => {
    renderCount.current += 1;
    if (process.env.NODE_ENV === "development") {
      console.debug(`[DevTools] ${componentName} rendered: ${renderCount.current}`);
    }
  });
}

/**
 * Measures time taken for an operation
 */
export function measureTime<T>(operation: () => T, label: string): T {
  if (process.env.NODE_ENV !== "development") {
    return operation();
  }

  const start = performance.now();
  const result = operation();
  const end = performance.now();
  console.debug(`[DevTools] ${label}: ${(end - start).toFixed(2)}ms`);
  return result;
}

// =============================================================================
// Lazy Initialization
// =============================================================================

/**
 * Lazily initializes a value only when first accessed
 */
export function useLazyInit<T>(factory: () => T): T {
  const initialized = useRef(false);
  const value = useRef<T>();

  if (!initialized.current) {
    value.current = factory();
    initialized.current = true;
  }

  return value.current as T;
}

// =============================================================================
// Intersection Observer Hook (for lazy loading)
// =============================================================================

/**
 * Hook for detecting when an element is visible
 * Useful for lazy loading content in tabs
 */
export function useIntersectionObserver(
  ref: React.RefObject<Element>,
  options?: IntersectionObserverInit,
): boolean {
  const [isIntersecting, setIsIntersecting] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(([entry]) => {
      setIsIntersecting(entry.isIntersecting);
    }, options);

    observer.observe(element);

    return () => observer.disconnect();
  }, [ref, options]);

  return isIntersecting;
}
