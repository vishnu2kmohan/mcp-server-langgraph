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
  });
});
