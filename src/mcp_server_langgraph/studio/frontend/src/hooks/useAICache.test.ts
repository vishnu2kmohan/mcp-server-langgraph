/**
 * AI Cache Hook Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Provides caching layer for AI Intelligence hooks to reduce API calls.
 *
 * Features:
 * - Configurable stale time (TTL)
 * - Cache invalidation
 * - Memory-efficient storage
 * - Cache key generation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useAICache, createCacheKey, type CacheEntry } from "./useAICache";

describe("useAICache", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("createCacheKey", () => {
    it("should generate consistent cache keys for same inputs", () => {
      const key1 = createCacheKey("nav_prediction", { userId: "user-1", page: "admin" });
      const key2 = createCacheKey("nav_prediction", { userId: "user-1", page: "admin" });
      expect(key1).toBe(key2);
    });

    it("should generate different keys for different inputs", () => {
      const key1 = createCacheKey("nav_prediction", { userId: "user-1", page: "admin" });
      const key2 = createCacheKey("nav_prediction", { userId: "user-1", page: "chat" });
      expect(key1).not.toBe(key2);
    });

    it("should include task type in cache key", () => {
      const key1 = createCacheKey("nav_prediction", { userId: "user-1" });
      const key2 = createCacheKey("contextual_help", { userId: "user-1" });
      expect(key1).not.toBe(key2);
    });
  });

  describe("basic caching", () => {
    it("should return cached value when available and not stale", async () => {
      const fetchFn = vi.fn().mockResolvedValue({ data: "test-result" });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-key",
          fetchFn,
          staleTime: 5 * 60 * 1000, // 5 minutes
        })
      );

      // First call - should fetch
      await waitFor(() => {
        expect(result.current.data).toEqual({ data: "test-result" });
      });
      expect(fetchFn).toHaveBeenCalledTimes(1);

      // Trigger refetch within stale time
      act(() => {
        result.current.refetch();
      });

      // Should use cached value, not call fetch again
      await waitFor(() => {
        expect(result.current.data).toEqual({ data: "test-result" });
      });
      // Still only 1 call because cache is valid
      expect(fetchFn).toHaveBeenCalledTimes(1);
    });

    it("should refetch when cache is stale", async () => {
      const fetchFn = vi.fn().mockResolvedValue({ data: "test-result" });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-key-stale",
          fetchFn,
          staleTime: 1000, // 1 second
        })
      );

      // First call
      await waitFor(() => {
        expect(result.current.data).toEqual({ data: "test-result" });
      });
      expect(fetchFn).toHaveBeenCalledTimes(1);

      // Advance time past stale time
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      // Trigger refetch - should call fetch again
      act(() => {
        result.current.refetch();
      });

      await waitFor(() => {
        expect(fetchFn).toHaveBeenCalledTimes(2);
      });
    });

    it("should force refetch when forceRefetch is called", async () => {
      const fetchFn = vi.fn().mockResolvedValue({ data: "test-result" });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-key-force",
          fetchFn,
          staleTime: 5 * 60 * 1000,
        })
      );

      await waitFor(() => {
        expect(result.current.data).toEqual({ data: "test-result" });
      });
      expect(fetchFn).toHaveBeenCalledTimes(1);

      // Force refetch should bypass cache
      act(() => {
        result.current.forceRefetch();
      });

      await waitFor(() => {
        expect(fetchFn).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("loading states", () => {
    it("should show loading state on initial fetch", async () => {
      const fetchFn = vi.fn().mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ data: "test" }), 100))
      );

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-loading",
          fetchFn,
          staleTime: 5000,
        })
      );

      expect(result.current.isLoading).toBe(true);

      act(() => {
        vi.advanceTimersByTime(150);
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it("should not show loading when returning cached value", async () => {
      const fetchFn = vi.fn().mockResolvedValue({ data: "cached" });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-no-loading",
          fetchFn,
          staleTime: 5 * 60 * 1000,
        })
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });

      // On subsequent access, should not show loading
      act(() => {
        result.current.refetch();
      });

      // Should immediately have data without loading
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toEqual({ data: "cached" });
    });
  });

  describe("error handling", () => {
    it("should capture and expose errors", async () => {
      const fetchFn = vi.fn().mockRejectedValue(new Error("Fetch failed"));

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-error",
          fetchFn,
          staleTime: 5000,
        })
      );

      await waitFor(() => {
        expect(result.current.error).toBeDefined();
        expect(result.current.error?.message).toBe("Fetch failed");
      });
    });

    it("should return stale data on error if available", async () => {
      let callCount = 0;
      const fetchFn = vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({ data: "original" });
        }
        return Promise.reject(new Error("Second call failed"));
      });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-stale-on-error",
          fetchFn,
          staleTime: 100,
          returnStaleOnError: true,
        })
      );

      // First call succeeds
      await waitFor(() => {
        expect(result.current.data).toEqual({ data: "original" });
      });

      // Advance past stale time
      act(() => {
        vi.advanceTimersByTime(200);
      });

      // Force refetch - will fail
      act(() => {
        result.current.forceRefetch();
      });

      // Should still have stale data
      await waitFor(() => {
        expect(result.current.data).toEqual({ data: "original" });
        expect(result.current.isStale).toBe(true);
      });
    });
  });

  describe("cache invalidation", () => {
    it("should clear cache when invalidate is called", async () => {
      const fetchFn = vi.fn().mockResolvedValue({ data: "test" });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-invalidate",
          fetchFn,
          staleTime: 5 * 60 * 1000,
        })
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });

      // Invalidate cache
      act(() => {
        result.current.invalidate();
      });

      expect(result.current.data).toBeNull();

      // Next refetch should call fetch
      act(() => {
        result.current.refetch();
      });

      await waitFor(() => {
        expect(fetchFn).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("disabled state", () => {
    it("should not fetch when disabled", async () => {
      const fetchFn = vi.fn().mockResolvedValue({ data: "test" });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-disabled",
          fetchFn,
          staleTime: 5000,
          enabled: false,
        })
      );

      // Should not call fetch
      expect(fetchFn).not.toHaveBeenCalled();
      expect(result.current.data).toBeNull();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("cache entry metadata", () => {
    it("should track cache entry timestamps", async () => {
      const fetchFn = vi.fn().mockResolvedValue({ data: "test" });

      const { result } = renderHook(() =>
        useAICache({
          cacheKey: "test-metadata",
          fetchFn,
          staleTime: 5000,
        })
      );

      await waitFor(() => {
        expect(result.current.data).toBeDefined();
      });

      expect(result.current.cachedAt).toBeDefined();
      expect(result.current.cachedAt).toBeInstanceOf(Date);
    });
  });
});

describe("CacheEntry type", () => {
  it("should have correct structure", () => {
    const entry: CacheEntry<{ value: string }> = {
      data: { value: "test" },
      timestamp: Date.now(),
      staleTime: 5000,
    };

    expect(entry.data).toBeDefined();
    expect(entry.timestamp).toBeDefined();
    expect(entry.staleTime).toBeDefined();
  });
});
