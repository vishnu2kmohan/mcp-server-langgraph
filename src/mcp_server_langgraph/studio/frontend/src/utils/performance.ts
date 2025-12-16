/**
 * Performance Utilities
 *
 * Helper functions for performance optimization including
 * debouncing, throttling, memoization, and lazy loading.
 */

/**
 * Debounce function - delays execution until after wait ms have elapsed
 * since the last invocation
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  wait: number,
): T & { cancel: () => void } {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  const debouncedFn = function (this: unknown, ...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      fn.apply(this, args);
      timeoutId = null;
    }, wait);
  } as T & { cancel: () => void };

  debouncedFn.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
  };

  return debouncedFn;
}

/**
 * Throttle function - limits execution to once per wait ms
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  wait: number,
): T {
  let lastCallTime = 0;

  return function (this: unknown, ...args: Parameters<T>) {
    const now = Date.now();

    if (now - lastCallTime >= wait) {
      lastCallTime = now;
      return fn.apply(this, args);
    }
  } as T;
}

/**
 * Memoize function - caches results based on arguments
 */
export function memoize<T extends (...args: unknown[]) => unknown>(
  fn: T,
): T & { clear: () => void } {
  const cache = new Map<string, ReturnType<T>>();

  const memoizedFn = function (
    this: unknown,
    ...args: Parameters<T>
  ): ReturnType<T> {
    const key = JSON.stringify(args);

    if (cache.has(key)) {
      return cache.get(key)!;
    }

    const result = fn.apply(this, args) as ReturnType<T>;
    cache.set(key, result);
    return result;
  } as T & { clear: () => void };

  memoizedFn.clear = () => {
    cache.clear();
  };

  return memoizedFn;
}

/**
 * Measure function execution time
 */
export interface PerformanceMeasurement<T> {
  result: T;
  duration: number;
  name: string;
}

export function measurePerformance<T>(
  fn: () => T,
  name: string,
): T extends Promise<infer U>
  ? Promise<PerformanceMeasurement<U>>
  : PerformanceMeasurement<T> {
  const start = performance.now();
  const result = fn();

  if (result instanceof Promise) {
    return result.then((resolvedResult) => ({
      result: resolvedResult,
      duration: performance.now() - start,
      name,
    })) as T extends Promise<infer U>
      ? Promise<PerformanceMeasurement<U>>
      : PerformanceMeasurement<T>;
  }

  return {
    result,
    duration: performance.now() - start,
    name,
  } as T extends Promise<infer U>
    ? Promise<PerformanceMeasurement<U>>
    : PerformanceMeasurement<T>;
}

/**
 * IntersectionObserver configuration for lazy loading
 */
export interface IntersectionObserverConfig {
  threshold?: number;
  rootMargin?: string;
  root?: Element | null;
}

export function createIntersectionObserverHook(
  options: IntersectionObserverConfig,
): Required<Omit<IntersectionObserverConfig, "root">> & {
  root?: Element | null;
} {
  return {
    threshold: options.threshold ?? 0,
    rootMargin: options.rootMargin ?? "0px",
    root: options.root,
  };
}

/**
 * Request Idle Callback polyfill for older browsers
 */
export function requestIdleCallbackPolyfill(
  callback: IdleRequestCallback,
  options?: IdleRequestOptions,
): number {
  if (typeof window !== "undefined" && "requestIdleCallback" in window) {
    return window.requestIdleCallback(callback, options);
  }

  // Fallback for browsers without requestIdleCallback
  const start = Date.now();
  return setTimeout(() => {
    callback({
      didTimeout: false,
      timeRemaining: () => Math.max(0, 50 - (Date.now() - start)),
    });
  }, 1) as unknown as number;
}

/**
 * Cancel idle callback polyfill
 */
export function cancelIdleCallbackPolyfill(id: number): void {
  if (typeof window !== "undefined" && "cancelIdleCallback" in window) {
    window.cancelIdleCallback(id);
  } else {
    clearTimeout(id);
  }
}

/**
 * Chunk array processing to avoid blocking the main thread
 */
export async function processInChunks<T, R>(
  items: T[],
  processor: (item: T) => R,
  chunkSize: number = 100,
): Promise<R[]> {
  const results: R[] = [];

  for (let i = 0; i < items.length; i += chunkSize) {
    const chunk = items.slice(i, i + chunkSize);

    // Process chunk
    for (const item of chunk) {
      results.push(processor(item));
    }

    // Yield to main thread between chunks
    if (i + chunkSize < items.length) {
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
  }

  return results;
}

/**
 * Preload critical resources
 */
export function preloadResource(
  href: string,
  as: "script" | "style" | "image" | "font" | "fetch",
): void {
  if (typeof document === "undefined") return;

  const link = document.createElement("link");
  link.rel = "preload";
  link.href = href;
  link.as = as;

  if (as === "font") {
    link.crossOrigin = "anonymous";
  }

  document.head.appendChild(link);
}

/**
 * Prefetch resource for future navigation
 */
export function prefetchResource(href: string): void {
  if (typeof document === "undefined") return;

  const link = document.createElement("link");
  link.rel = "prefetch";
  link.href = href;

  document.head.appendChild(link);
}
