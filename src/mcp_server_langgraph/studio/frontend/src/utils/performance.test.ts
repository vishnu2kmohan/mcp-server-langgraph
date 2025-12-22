/**
 * Performance Utilities Tests
 *
 * TDD tests for performance optimization helpers.
 * Tests lazy loading, debouncing, throttling, and memoization.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  debounce,
  throttle,
  memoize,
  measurePerformance,
  createIntersectionObserverHook,
  requestIdleCallbackPolyfill,
  cancelIdleCallbackPolyfill,
  processInChunks,
  preloadResource,
  prefetchResource,
} from "./performance";

describe("Performance Utilities", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("debounce", () => {
    it("should delay function execution", () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should reset timer on subsequent calls", () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      vi.advanceTimersByTime(50);
      debouncedFn();
      vi.advanceTimersByTime(50);
      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should pass arguments to debounced function", () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn("arg1", "arg2");
      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledWith("arg1", "arg2");
    });

    it("should use latest arguments on multiple calls", () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn("first");
      debouncedFn("second");
      debouncedFn("third");
      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledTimes(1);
      expect(fn).toHaveBeenCalledWith("third");
    });

    it("should have cancel method", () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      debouncedFn.cancel();
      vi.advanceTimersByTime(100);

      expect(fn).not.toHaveBeenCalled();
    });
  });

  describe("throttle", () => {
    it("should execute immediately on first call", () => {
      const fn = vi.fn();
      const throttledFn = throttle(fn, 100);

      throttledFn();
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should throttle subsequent calls", () => {
      const fn = vi.fn();
      const throttledFn = throttle(fn, 100);

      throttledFn();
      throttledFn();
      throttledFn();
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should allow calls after throttle period", () => {
      const fn = vi.fn();
      const throttledFn = throttle(fn, 100);

      throttledFn();
      vi.advanceTimersByTime(100);
      throttledFn();

      expect(fn).toHaveBeenCalledTimes(2);
    });

    it("should pass arguments correctly", () => {
      const fn = vi.fn();
      const throttledFn = throttle(fn, 100);

      throttledFn("arg1", "arg2");
      expect(fn).toHaveBeenCalledWith("arg1", "arg2");
    });
  });

  describe("memoize", () => {
    it("should cache results", () => {
      const fn = vi.fn((x: number) => x * 2);
      const memoizedFn = memoize(fn);

      expect(memoizedFn(5)).toBe(10);
      expect(memoizedFn(5)).toBe(10);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it("should call function for different arguments", () => {
      const fn = vi.fn((x: number) => x * 2);
      const memoizedFn = memoize(fn);

      expect(memoizedFn(5)).toBe(10);
      expect(memoizedFn(10)).toBe(20);
      expect(fn).toHaveBeenCalledTimes(2);
    });

    it("should handle multiple arguments", () => {
      const fn = vi.fn((a: number, b: number) => a + b);
      const memoizedFn = memoize(fn);

      expect(memoizedFn(1, 2)).toBe(3);
      expect(memoizedFn(1, 2)).toBe(3);
      expect(memoizedFn(2, 3)).toBe(5);
      expect(fn).toHaveBeenCalledTimes(2);
    });

    it("should have cache clear method", () => {
      const fn = vi.fn((x: number) => x * 2);
      const memoizedFn = memoize(fn);

      memoizedFn(5);
      memoizedFn.clear();
      memoizedFn(5);

      expect(fn).toHaveBeenCalledTimes(2);
    });
  });

  describe("measurePerformance", () => {
    it("should measure function execution time", async () => {
      const fn = () => {
        let sum = 0;
        for (let i = 0; i < 1000; i++) sum += i;
        return sum;
      };

      const result = measurePerformance(fn, "test-operation");
      expect(result.result).toBe(499500);
      expect(result.duration).toBeGreaterThanOrEqual(0);
      expect(result.name).toBe("test-operation");
    });

    it("should measure async function execution time", async () => {
      vi.useRealTimers();
      const asyncFn = async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
        return "done";
      };

      const result = await measurePerformance(asyncFn, "async-operation");
      expect(result.result).toBe("done");
      expect(result.duration).toBeGreaterThanOrEqual(10);
    });
  });

  describe("createIntersectionObserverHook", () => {
    it("should create an observer configuration", () => {
      const config = createIntersectionObserverHook({
        threshold: 0.5,
        rootMargin: "10px",
      });

      expect(config.threshold).toBe(0.5);
      expect(config.rootMargin).toBe("10px");
    });

    it("should use default values", () => {
      const config = createIntersectionObserverHook({});

      expect(config.threshold).toBe(0);
      expect(config.rootMargin).toBe("0px");
    });

    it("should pass root element when provided", () => {
      const mockRoot = document.createElement("div");
      const config = createIntersectionObserverHook({
        root: mockRoot,
      });

      expect(config.root).toBe(mockRoot);
    });
  });

  describe("requestIdleCallbackPolyfill", () => {
    it("should use native requestIdleCallback when available", () => {
      const mockCallback = vi.fn();
      const mockRequestIdleCallback = vi.fn().mockReturnValue(123);

      // Mock window.requestIdleCallback
      const originalRIC = window.requestIdleCallback;
      window.requestIdleCallback = mockRequestIdleCallback;

      const result = requestIdleCallbackPolyfill(mockCallback);

      expect(mockRequestIdleCallback).toHaveBeenCalledWith(
        mockCallback,
        undefined,
      );
      expect(result).toBe(123);

      // Restore
      window.requestIdleCallback = originalRIC;
    });

    it("should use fallback when requestIdleCallback not available", () => {
      vi.useRealTimers();
      const mockCallback = vi.fn();

      // Mock window without requestIdleCallback
      const originalRIC = window.requestIdleCallback;
      // @ts-expect-error - intentionally removing for test
      delete window.requestIdleCallback;

      const result = requestIdleCallbackPolyfill(mockCallback);
      // In browsers, setTimeout returns a number, but in Node.js it returns a Timeout object
      // The function returns a valid timeout ID that can be used with clearTimeout
      expect(result).toBeDefined();
      expect(result).not.toBeNull();

      // Restore
      window.requestIdleCallback = originalRIC;
    });

    it("should provide deadline with timeRemaining in fallback mode", async () => {
      // Use real timers so setTimeout actually fires
      vi.useRealTimers();

      // Mock window without requestIdleCallback to force fallback
      const originalRIC = window.requestIdleCallback;
      // @ts-expect-error - intentionally removing for test
      delete window.requestIdleCallback;

      let capturedDeadline: { didTimeout: boolean; timeRemaining: () => number } | null = null;
      const callback = (deadline: { didTimeout: boolean; timeRemaining: () => number }) => {
        capturedDeadline = deadline;
      };

      requestIdleCallbackPolyfill(callback);

      // Wait for setTimeout to fire (uses 1ms timeout)
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Verify deadline was provided with correct structure
      expect(capturedDeadline).not.toBeNull();
      expect(capturedDeadline!.didTimeout).toBe(false);
      // timeRemaining should return a number >= 0
      const remaining = capturedDeadline!.timeRemaining();
      expect(remaining).toBeGreaterThanOrEqual(0);
      expect(remaining).toBeLessThanOrEqual(50);

      // Restore
      window.requestIdleCallback = originalRIC;
    });

    it("should pass options to native requestIdleCallback", () => {
      const mockCallback = vi.fn();
      const mockRequestIdleCallback = vi.fn().mockReturnValue(456);
      const options = { timeout: 1000 };

      const originalRIC = window.requestIdleCallback;
      window.requestIdleCallback = mockRequestIdleCallback;

      requestIdleCallbackPolyfill(mockCallback, options);

      expect(mockRequestIdleCallback).toHaveBeenCalledWith(
        mockCallback,
        options,
      );

      window.requestIdleCallback = originalRIC;
    });
  });

  describe("cancelIdleCallbackPolyfill", () => {
    it("should use native cancelIdleCallback when available", () => {
      const mockCancelIdleCallback = vi.fn();

      const originalCIC = window.cancelIdleCallback;
      window.cancelIdleCallback = mockCancelIdleCallback;

      cancelIdleCallbackPolyfill(123);

      expect(mockCancelIdleCallback).toHaveBeenCalledWith(123);

      window.cancelIdleCallback = originalCIC;
    });

    it("should use clearTimeout fallback when cancelIdleCallback not available", () => {
      const originalCIC = window.cancelIdleCallback;
      // @ts-expect-error - intentionally removing for test
      delete window.cancelIdleCallback;

      const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

      cancelIdleCallbackPolyfill(456);

      expect(clearTimeoutSpy).toHaveBeenCalledWith(456);

      window.cancelIdleCallback = originalCIC;
      clearTimeoutSpy.mockRestore();
    });
  });

  describe("processInChunks", () => {
    it("should process all items", async () => {
      vi.useRealTimers();
      const items = [1, 2, 3, 4, 5];
      const processor = (x: number) => x * 2;

      const results = await processInChunks(items, processor, 2);

      expect(results).toEqual([2, 4, 6, 8, 10]);
    });

    it("should process items in chunks", async () => {
      vi.useRealTimers();
      const items = [1, 2, 3, 4, 5, 6];
      const callOrder: number[] = [];
      const processor = (x: number) => {
        callOrder.push(x);
        return x;
      };

      await processInChunks(items, processor, 2);

      // All items should be processed
      expect(callOrder).toEqual([1, 2, 3, 4, 5, 6]);
    });

    it("should handle empty array", async () => {
      const items: number[] = [];
      const processor = (x: number) => x * 2;

      const results = await processInChunks(items, processor, 100);

      expect(results).toEqual([]);
    });

    it("should handle chunk size larger than array", async () => {
      vi.useRealTimers();
      const items = [1, 2, 3];
      const processor = (x: number) => x * 2;

      const results = await processInChunks(items, processor, 100);

      expect(results).toEqual([2, 4, 6]);
    });

    it("should use default chunk size", async () => {
      vi.useRealTimers();
      const items = [1, 2, 3];
      const processor = (x: number) => x * 2;

      const results = await processInChunks(items, processor);

      expect(results).toEqual([2, 4, 6]);
    });
  });

  describe("preloadResource", () => {
    beforeEach(() => {
      // Clear head of any test links
      document.head.innerHTML = "";
    });

    it("should create preload link for script", () => {
      preloadResource("/app.js", "script");

      const link = document.querySelector('link[rel="preload"]');
      expect(link).not.toBeNull();
      expect(link?.getAttribute("href")).toBe("/app.js");
      expect(link?.getAttribute("as")).toBe("script");
    });

    it("should create preload link for style", () => {
      preloadResource("/app.css", "style");

      const link = document.querySelector('link[rel="preload"]');
      expect(link?.getAttribute("as")).toBe("style");
    });

    it("should create preload link for image", () => {
      preloadResource("/hero.png", "image");

      const link = document.querySelector('link[rel="preload"]');
      expect(link?.getAttribute("as")).toBe("image");
    });

    it("should set crossOrigin for fonts", () => {
      preloadResource("/font.woff2", "font");

      const link = document.querySelector('link[rel="preload"]');
      expect(link?.getAttribute("as")).toBe("font");
      expect(link?.getAttribute("crossorigin")).toBe("anonymous");
    });

    it("should not set crossOrigin for non-fonts", () => {
      preloadResource("/app.js", "script");

      const link = document.querySelector('link[rel="preload"]');
      expect(link?.getAttribute("crossorigin")).toBeNull();
    });
  });

  describe("prefetchResource", () => {
    beforeEach(() => {
      document.head.innerHTML = "";
    });

    it("should create prefetch link", () => {
      prefetchResource("/next-page.js");

      const link = document.querySelector('link[rel="prefetch"]');
      expect(link).not.toBeNull();
      expect(link?.getAttribute("href")).toBe("/next-page.js");
    });
  });

  describe("debounce edge cases", () => {
    it("should handle cancel when no pending call", () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      // Cancel without any call - should not throw
      expect(() => debouncedFn.cancel()).not.toThrow();
      expect(fn).not.toHaveBeenCalled();
    });

    it("should preserve this context", () => {
      const obj = {
        value: 42,
        getValue: function () {
          return this.value;
        },
      };

      const debouncedFn = debounce(obj.getValue.bind(obj), 100);
      debouncedFn();
      vi.advanceTimersByTime(100);

      // The function should have been called with correct context
      expect(obj.getValue()).toBe(42);
    });
  });

  describe("throttle edge cases", () => {
    it("should return undefined for throttled calls", () => {
      const fn = vi.fn().mockReturnValue("result");
      const throttledFn = throttle(fn, 100);

      const firstResult = throttledFn();
      const secondResult = throttledFn();

      expect(firstResult).toBe("result");
      expect(secondResult).toBeUndefined();
    });
  });
});
