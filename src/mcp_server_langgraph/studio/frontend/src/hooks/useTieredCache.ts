/**
 * useTieredCache Hook
 *
 * Provides tiered caching for frontend data with:
 * - L1 (in-memory) for sub-millisecond access
 * - L2 (sessionStorage) for persistence across re-renders
 * - Stale-while-revalidate (SWR) pattern for optimal UX
 * - Cache metrics tracking for observability
 *
 * Mirrors backend TieredCacheMixin/StaleWhileRevalidateMixin patterns.
 *
 * @example
 * ```tsx
 * const { data, isLoading, isStale, invalidate, cacheStats } = useTieredCache(
 *   "user:profile",
 *   () => fetchUserProfile(),
 *   { ttlMs: 10 * 60 * 1000 } // 10 minutes
 * );
 *
 * // Use data with loading/stale states
 * if (isLoading) return <Spinner />;
 * if (isStale) showRefreshIndicator();
 * return <Profile data={data} />;
 * ```
 *
 * Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { authenticatedFetch } from "../utils/authenticatedFetch";

// =============================================================================
// Types
// =============================================================================

/** Cache event types for metrics integration */
export type CacheEventType = "l1Hit" | "l2Hit" | "miss";

export interface UseTieredCacheOptions {
  /** Cache TTL in milliseconds (default: 5 minutes) */
  ttlMs?: number;
  /** Stale threshold in milliseconds - data older than this is considered stale (default: 60s) */
  staleThresholdMs?: number;
  /** Whether to enable fetching (default: true) */
  enabled?: boolean;
  /** Whether to deduplicate concurrent requests (default: true) */
  deduplicate?: boolean;
  /** Callback for cache events - enables integration with useAICacheMetrics */
  onCacheEvent?: (event: CacheEventType, cacheKey: string) => void;
  /** Whether to use Redis L2 instead of sessionStorage (default: false) */
  useRedisL2?: boolean;
}

export interface CacheStats {
  /** Number of L1 (in-memory) cache hits */
  l1Hits: number;
  /** Number of L2 (sessionStorage) cache hits */
  l2Hits: number;
  /** Number of cache misses */
  misses: number;
  /** Cache age in milliseconds */
  age: number;
}

export interface UseTieredCacheResult<T> {
  /** Cached or fetched data */
  data: T | undefined;
  /** Whether data is currently being fetched */
  isLoading: boolean;
  /** Whether cached data is stale (near expiry, background refresh triggered) */
  isStale: boolean;
  /** Fetch error if any */
  error: Error | undefined;
  /** Invalidate cache and refetch */
  invalidate: () => void;
  /** Manual refetch */
  refetch: () => Promise<void>;
  /** Cache statistics */
  cacheStats: CacheStats;
}

interface CacheEntry<T> {
  data: T;
  _cachedAt: number;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes
const DEFAULT_STALE_THRESHOLD_MS = 60 * 1000; // 60 seconds
const CACHE_PREFIX = "tiered_cache:";

// =============================================================================
// L1 Cache (In-Memory)
// =============================================================================

// Global L1 cache shared across all hook instances
const l1Cache = new Map<string, CacheEntry<unknown>>();

// Inflight requests for deduplication
const inflightRequests = new Map<string, Promise<unknown>>();

// =============================================================================
// L2 Cache (SessionStorage)
// =============================================================================
// Note: We intentionally use sessionStorage (not the localStorage-based storage utility)
// because L2 cache entries should be session-scoped and cleared on tab close.
/* eslint-disable no-restricted-globals */

function getL2CacheKey(key: string): string {
  return `${CACHE_PREFIX}${key}`;
}

function getFromL2<T>(key: string): CacheEntry<T> | null {
  try {
    const stored = sessionStorage.getItem(getL2CacheKey(key));
    if (!stored) return null;
    return JSON.parse(stored) as CacheEntry<T>;
  } catch {
    return null;
  }
}

function setToL2<T>(key: string, entry: CacheEntry<T>): void {
  try {
    sessionStorage.setItem(getL2CacheKey(key), JSON.stringify(entry));
  } catch {
    // Ignore storage errors (quota exceeded, etc.)
  }
}

function deleteFromL2(key: string): void {
  try {
    sessionStorage.removeItem(getL2CacheKey(key));
  } catch {
    // Ignore errors
  }
}

/* eslint-enable no-restricted-globals */

// =============================================================================
// Redis L2 Cache (API-backed)
// =============================================================================

/**
 * Get cached value from Redis L2 via API.
 * Falls back gracefully on any error.
 */
async function getFromRedisL2<T>(key: string): Promise<CacheEntry<T> | null> {
  try {
    const response = await authenticatedFetch(
      `/api/v1/cache/${encodeURIComponent(key)}`,
    );
    if (!response.ok) return null;
    const data = await response.json();
    if (data.hit && data.value) {
      return data.value as CacheEntry<T>;
    }
    return null;
  } catch {
    return null; // Fallback to sessionStorage on error
  }
}

/**
 * Set cached value to Redis L2 via API.
 * Fails silently on error.
 */
async function setToRedisL2<T>(
  key: string,
  entry: CacheEntry<T>,
  ttlMs: number,
): Promise<void> {
  try {
    await authenticatedFetch(`/api/v1/cache/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify({
        value: entry,
        ttl_seconds: Math.floor(ttlMs / 1000),
      }),
    });
  } catch {
    // Ignore errors - Redis L2 is best-effort
  }
}

/**
 * Delete cached value from Redis L2 via API.
 * Fails silently on error.
 */
async function deleteFromRedisL2(key: string): Promise<void> {
  try {
    await authenticatedFetch(`/api/v1/cache/${encodeURIComponent(key)}`, {
      method: "DELETE",
    });
  } catch {
    // Ignore errors
  }
}

// =============================================================================
// useTieredCache Hook
// =============================================================================

export function useTieredCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseTieredCacheOptions = {},
): UseTieredCacheResult<T> {
  const {
    ttlMs = DEFAULT_TTL_MS,
    staleThresholdMs = DEFAULT_STALE_THRESHOLD_MS,
    enabled = true,
    deduplicate = true,
    onCacheEvent,
    useRedisL2 = false,
  } = options;

  const [data, setData] = useState<T | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [isStale, setIsStale] = useState(false);
  const [error, setError] = useState<Error | undefined>(undefined);
  const [cacheStats, setCacheStats] = useState<CacheStats>({
    l1Hits: 0,
    l2Hits: 0,
    misses: 0,
    age: 0,
  });

  const mountedRef = useRef(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  // Ref to avoid stale closures in callbacks
  const onCacheEventRef = useRef(onCacheEvent);
  onCacheEventRef.current = onCacheEvent;

  /**
   * Check if cache entry is expired.
   */
  const isExpired = useCallback(
    (entry: CacheEntry<unknown>): boolean => {
      const age = Date.now() - entry._cachedAt;
      return age > ttlMs;
    },
    [ttlMs],
  );

  /**
   * Check if cache entry is stale (near expiry but not expired).
   */
  const isDataStale = useCallback(
    (entry: CacheEntry<unknown>): boolean => {
      const age = Date.now() - entry._cachedAt;
      const timeUntilExpiry = ttlMs - age;
      return timeUntilExpiry > 0 && timeUntilExpiry < staleThresholdMs;
    },
    [ttlMs, staleThresholdMs],
  );

  /**
   * Fetch data from source and update caches.
   */
  const fetchData = useCallback(async (): Promise<T | undefined> => {
    try {
      let fetchPromise: Promise<unknown>;

      // Deduplication: reuse inflight request
      if (deduplicate && inflightRequests.has(key)) {
        fetchPromise = inflightRequests.get(key)!;
      } else {
        fetchPromise = fetcherRef.current();
        if (deduplicate) {
          inflightRequests.set(key, fetchPromise);
        }
      }

      const result = (await fetchPromise) as T;

      // Update L1 and L2 caches
      const entry: CacheEntry<T> = {
        data: result,
        _cachedAt: Date.now(),
      };

      l1Cache.set(key, entry as CacheEntry<unknown>);

      // Save to L2 (Redis or sessionStorage)
      if (useRedisL2) {
        await setToRedisL2(key, entry, ttlMs);
      }
      setToL2(key, entry); // Always save to sessionStorage as fallback

      return result;
    } finally {
      if (deduplicate) {
        inflightRequests.delete(key);
      }
    }
  }, [key, deduplicate, useRedisL2, ttlMs]);

  /**
   * Invalidate cache and refetch.
   */
  const invalidate = useCallback(() => {
    // Clear L1
    l1Cache.delete(key);
    // Clear L2 (both Redis and sessionStorage)
    if (useRedisL2) {
      deleteFromRedisL2(key); // Fire and forget
    }
    deleteFromL2(key);
    // Trigger refetch
    setData(undefined);
    setIsStale(false);
    setError(undefined);
  }, [key, useRedisL2]);

  /**
   * Manual refetch.
   */
  const refetch = useCallback(async () => {
    if (!mountedRef.current) return;

    setIsLoading(true);
    setError(undefined);

    try {
      const result = await fetchData();
      if (mountedRef.current && result !== undefined) {
        setData(result);
        setIsStale(false);
        setCacheStats((prev) => ({
          ...prev,
          age: 0,
        }));
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err : new Error(String(err)));
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [fetchData]);

  /**
   * Handle L2 cache hit (shared logic for Redis and sessionStorage).
   */
  const handleL2Hit = useCallback(
    (l2Entry: CacheEntry<T>) => {
      // Populate L1 from L2
      l1Cache.set(key, l2Entry as CacheEntry<unknown>);

      setData(l2Entry.data);
      setIsLoading(false);
      setIsStale(isDataStale(l2Entry));
      setCacheStats((prev) => ({
        ...prev,
        l2Hits: prev.l2Hits + 1,
        age: Date.now() - l2Entry._cachedAt,
      }));
      onCacheEventRef.current?.("l2Hit", key);

      // If stale, trigger background refresh
      if (isDataStale(l2Entry)) {
        fetchData()
          .then((result) => {
            if (mountedRef.current && result !== undefined) {
              setData(result);
              setIsStale(false);
            }
          })
          .catch((err) => {
            if (mountedRef.current) {
              setError(err instanceof Error ? err : new Error(String(err)));
            }
          });
      }
    },
    [key, isDataStale, fetchData],
  );

  /**
   * Handle cache miss (shared logic).
   */
  const handleCacheMiss = useCallback(() => {
    setCacheStats((prev) => ({
      ...prev,
      misses: prev.misses + 1,
    }));
    onCacheEventRef.current?.("miss", key);

    setIsLoading(true);
    fetchData()
      .then((result) => {
        if (mountedRef.current && result !== undefined) {
          setData(result);
          setCacheStats((prev) => ({
            ...prev,
            age: 0,
          }));
        }
      })
      .catch((err) => {
        if (mountedRef.current) {
          setError(err instanceof Error ? err : new Error(String(err)));
        }
      })
      .finally(() => {
        if (mountedRef.current) {
          setIsLoading(false);
        }
      });
  }, [key, fetchData]);

  /**
   * Initial load effect.
   */
  useEffect(() => {
    mountedRef.current = true;

    if (!enabled) {
      setIsLoading(false);
      return;
    }

    // Check L1 cache first
    const l1Entry = l1Cache.get(key) as CacheEntry<T> | undefined;
    if (l1Entry && !isExpired(l1Entry)) {
      setData(l1Entry.data);
      setIsStale(isDataStale(l1Entry));
      setCacheStats((prev) => ({
        ...prev,
        l1Hits: prev.l1Hits + 1,
        age: Date.now() - l1Entry._cachedAt,
      }));
      onCacheEventRef.current?.("l1Hit", key);

      // If stale, trigger background refresh
      if (isDataStale(l1Entry)) {
        fetchData()
          .then((result) => {
            if (mountedRef.current && result !== undefined) {
              setData(result);
              setIsStale(false);
            }
          })
          .catch((err) => {
            if (mountedRef.current) {
              setError(err instanceof Error ? err : new Error(String(err)));
            }
          });
      }

      return;
    }

    // Check L2 cache (Redis L2 with sessionStorage fallback, or just sessionStorage)
    if (useRedisL2) {
      // Async: Try Redis L2, then fallback to sessionStorage
      (async () => {
        const redisEntry = await getFromRedisL2<T>(key);
        if (!mountedRef.current) return;

        if (redisEntry && !isExpired(redisEntry)) {
          handleL2Hit(redisEntry);
          return;
        }

        // Fallback to sessionStorage
        const l2Entry = getFromL2<T>(key);
        if (l2Entry && !isExpired(l2Entry)) {
          handleL2Hit(l2Entry);
          return;
        }

        // Cache miss
        handleCacheMiss();
      })();
    } else {
      // Sync: sessionStorage only
      const l2Entry = getFromL2<T>(key);
      if (l2Entry && !isExpired(l2Entry)) {
        handleL2Hit(l2Entry);
        return;
      }

      // Cache miss
      handleCacheMiss();
    }

    return () => {
      mountedRef.current = false;
    };
  }, [
    key,
    enabled,
    isExpired,
    isDataStale,
    fetchData,
    useRedisL2,
    handleL2Hit,
    handleCacheMiss,
  ]);

  // Re-run when data becomes undefined (after invalidation)
  useEffect(() => {
    if (enabled && data === undefined && !isLoading && !error) {
      // Check if we need to refetch after invalidation
      const l1Entry = l1Cache.get(key);
      const l2Entry = getFromL2(key);
      if (!l1Entry && !l2Entry) {
        refetch();
      }
    }
  }, [key, enabled, data, isLoading, error, refetch]);

  return {
    data,
    isLoading,
    isStale,
    error,
    invalidate,
    refetch,
    cacheStats,
  };
}
