/**
 * useTieredCache Hook Tests
 *
 * TDD - Tests for tiered caching hook that provides:
 * - L1 (in-memory) + L2 (sessionStorage) caching
 * - Stale-while-revalidate pattern
 * - Cache metrics tracking
 *
 * Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor, act , cleanup} from "@testing-library/react";
import { useTieredCache } from "./useTieredCache";

// =============================================================================
// Test Constants
// =============================================================================

const TEST_CACHE_KEY = "test:cache:key";
const TEST_DATA = { id: "1", name: "Test Data" };
const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes

// =============================================================================
// Mock Data & Helpers
// =============================================================================

const createMockFetcher = (data: unknown) => {
  return vi.fn().mockResolvedValue(data);
};

// Note: L1 cache is cleared via invalidate() in tests - no direct access needed

// =============================================================================
// useTieredCache Tests
// =============================================================================

describe("useTieredCache", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    sessionStorage.clear();
      cleanup();
      vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should return undefined data initially and isLoading=true", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const { result } = renderHook(() =>
        useTieredCache(TEST_CACHE_KEY, fetcher)
      );

      // Initial state before fetch completes
      expect(result.current.isLoading).toBe(true);
      expect(result.current.isStale).toBe(false);
    });

    it("should fetch and cache data on mount", async () => {
      const fetcher = createMockFetcher(TEST_DATA);

      const { result } = renderHook(() =>
        useTieredCache(TEST_CACHE_KEY + "-fetch", fetcher)
      );

      // Wait for fetch to complete
      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });

      expect(result.current.isLoading).toBe(false);
      expect(fetcher).toHaveBeenCalledTimes(1);
    });
  });

  describe("L2 cache (sessionStorage)", () => {
    it("should persist data to sessionStorage", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-persist";

      const { result } = renderHook(() => useTieredCache(key, fetcher));

      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });

      // Verify data is in sessionStorage
      const stored = sessionStorage.getItem(`tiered_cache:${key}`);
      expect(stored).not.toBeNull();

      const parsed = JSON.parse(stored!);
      expect(parsed.data).toEqual(TEST_DATA);
      expect(parsed._cachedAt).toBeGreaterThan(0);
    });

    it("should load from L2 cache on fresh mount", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-l2load";

      // Pre-populate L2 cache
      const cachedEntry = {
        data: TEST_DATA,
        _cachedAt: Date.now(),
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      const { result } = renderHook(() => useTieredCache(key, fetcher));

      // Should return cached data immediately
      expect(result.current.data).toEqual(TEST_DATA);
      expect(result.current.isLoading).toBe(false);
    });

    it("should track L2 hits in cacheStats", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-l2stats";

      // Pre-populate L2 cache
      const cachedEntry = {
        data: TEST_DATA,
        _cachedAt: Date.now(),
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      const { result } = renderHook(() => useTieredCache(key, fetcher));

      expect(result.current.cacheStats.l2Hits).toBeGreaterThan(0);
    });
  });

  describe("stale-while-revalidate (SWR)", () => {
    it("should detect stale data when near expiry", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-stale";

      // Pre-populate with stale cache (old timestamp)
      const staleTimestamp = Date.now() - DEFAULT_TTL_MS + 30 * 1000; // 30s before expiry
      const cachedEntry = {
        data: TEST_DATA,
        _cachedAt: staleTimestamp,
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      const { result } = renderHook(() =>
        useTieredCache(key, fetcher, {
          staleThresholdMs: 60 * 1000, // 60s threshold
        })
      );

      // Should return stale data with isStale=true
      expect(result.current.data).toEqual(TEST_DATA);
      expect(result.current.isStale).toBe(true);
    });

    it("should return fresh data with isStale=false", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-fresh";

      // Pre-populate with fresh cache
      const cachedEntry = {
        data: TEST_DATA,
        _cachedAt: Date.now() - 10 * 1000, // 10 seconds ago
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      const { result } = renderHook(() =>
        useTieredCache(key, fetcher, {
          staleThresholdMs: 60 * 1000, // 60s threshold
        })
      );

      // Fresh data (10s old, threshold is 60s from end of 5min TTL)
      expect(result.current.data).toEqual(TEST_DATA);
      expect(result.current.isStale).toBe(false);
    });
  });

  describe("cache invalidation", () => {
    it("should clear L2 on invalidation", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-invalidate";

      const { result } = renderHook(() => useTieredCache(key, fetcher));

      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });

      // Invalidate
      act(() => {
        result.current.invalidate();
      });

      // L2 should be cleared
      const stored = sessionStorage.getItem(`tiered_cache:${key}`);
      expect(stored).toBeNull();
    });
  });

  describe("TTL handling", () => {
    it("should expire data after TTL", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-expired";

      // Pre-populate cache with expired data
      const expiredTimestamp = Date.now() - DEFAULT_TTL_MS - 1000;
      const cachedEntry = {
        data: TEST_DATA,
        _cachedAt: expiredTimestamp,
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      renderHook(() => useTieredCache(key, fetcher, { ttlMs: DEFAULT_TTL_MS }));

      // Expired cache should trigger refetch
      await waitFor(() => {
        expect(fetcher).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("error handling", () => {
    it("should return error on fetch failure", async () => {
      const error = new Error("Fetch failed");
      const fetcher = vi.fn().mockRejectedValue(error);
      const key = TEST_CACHE_KEY + "-error";

      const { result } = renderHook(() => useTieredCache(key, fetcher));

      await waitFor(() => {
        expect(result.current.error).toBeDefined();
      });

      expect(result.current.error?.message).toBe("Fetch failed");
    });
  });

  describe("cache stats", () => {
    it("should track misses on initial fetch", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-misses";

      const { result } = renderHook(() => useTieredCache(key, fetcher));

      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });

      expect(result.current.cacheStats.misses).toBeGreaterThan(0);
    });
  });

  describe("options", () => {
    it("should skip fetching when enabled is false", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-disabled";

      const { result } = renderHook(() =>
        useTieredCache(key, fetcher, { enabled: false })
      );

      // Should not fetch
      expect(fetcher).not.toHaveBeenCalled();
      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("metrics callback integration", () => {
    it("should call onCacheEvent with 'l2Hit' when L2 cache is hit", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-l2-callback";
      const onCacheEvent = vi.fn();

      // Pre-populate L2 cache
      const cachedEntry = {
        data: TEST_DATA,
        _cachedAt: Date.now(),
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      renderHook(() =>
        useTieredCache(key, fetcher, { onCacheEvent })
      );

      expect(onCacheEvent).toHaveBeenCalledWith("l2Hit", key);
    });

    it("should call onCacheEvent with 'miss' on cache miss", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-miss-callback";
      const onCacheEvent = vi.fn();

      const { result } = renderHook(() =>
        useTieredCache(key, fetcher, { onCacheEvent })
      );

      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });

      expect(onCacheEvent).toHaveBeenCalledWith("miss", key);
    });

    it("should not call onCacheEvent when not provided", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-no-callback";

      // This should not throw
      const { result } = renderHook(() => useTieredCache(key, fetcher));

      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });
    });

    it("should integrate with useAICacheMetrics tracking functions", () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-metrics-integration";

      // Pre-populate L2 cache
      const cachedEntry = {
        data: TEST_DATA,
        _cachedAt: Date.now(),
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      // Simulating integration - callback receives event and can dispatch to metrics
      let capturedEvent: string | null = null;
      const onCacheEvent = (event: string, _cacheKey: string) => {
        capturedEvent = event;
      };

      renderHook(() => useTieredCache(key, fetcher, { onCacheEvent }));

      expect(capturedEvent).toBe("l2Hit");
    });
  });

  describe("Redis L2 option", () => {
    // Mock fetch for Redis L2 API calls
    const originalFetch = global.fetch;

    beforeEach(() => {
      global.fetch = vi.fn();
    });

    afterEach(() => {
      global.fetch = originalFetch;
        cleanup();
        vi.clearAllMocks();
        vi.restoreAllMocks();
    });

    it("should use Redis L2 when useRedisL2 is true", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-redis-l2";

      // Mock Redis L2 cache miss then successful fetch
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ key, hit: false, value: null }),
      });

      const { result } = renderHook(() =>
        useTieredCache(key, fetcher, { useRedisL2: true })
      );

      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });

      // Verify Redis L2 API was called
      expect(global.fetch).toHaveBeenCalled();
    });

    it("should fall back to sessionStorage when Redis L2 fails", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-redis-fallback";

      // Mock Redis L2 API failure
      (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error("Network error")
      );

      // Pre-populate sessionStorage as fallback
      const cachedEntry = {
        data: { ...TEST_DATA, source: "session" },
        _cachedAt: Date.now(),
      };
      sessionStorage.setItem(
        `tiered_cache:${key}`,
        JSON.stringify(cachedEntry)
      );

      const { result } = renderHook(() =>
        useTieredCache(key, fetcher, { useRedisL2: true })
      );

      // Should fall back to sessionStorage data
      await waitFor(() => {
        expect(result.current.data).toEqual({ ...TEST_DATA, source: "session" });
      });
    });

    it("should not call Redis L2 API when useRedisL2 is false (default)", async () => {
      const fetcher = createMockFetcher(TEST_DATA);
      const key = TEST_CACHE_KEY + "-no-redis";

      const { result } = renderHook(() =>
        useTieredCache(key, fetcher, { useRedisL2: false })
      );

      await waitFor(() => {
        expect(result.current.data).toEqual(TEST_DATA);
      });

      // Redis L2 API should not be called
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });
});
