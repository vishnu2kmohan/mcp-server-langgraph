/**
 * AI Cache Hook
 *
 * Provides caching layer for AI Intelligence hooks to reduce API calls.
 * Used by useNavPrediction, useContextualHelp, useLearningPath, etc.
 *
 * Features:
 * - Configurable stale time (TTL)
 * - Cache invalidation
 * - Memory-efficient storage
 * - Cache key generation
 * - Stale-while-revalidate pattern
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// =============================================================================
// Types
// =============================================================================

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  staleTime: number;
}

export interface UseAICacheOptions<T> {
  /** Unique cache key */
  cacheKey: string;
  /** Function to fetch data */
  fetchFn: () => Promise<T>;
  /** Time in ms before cache is considered stale (default: 5 minutes) */
  staleTime?: number;
  /** Whether caching is enabled (default: true) */
  enabled?: boolean;
  /** Return stale data on error (default: true) */
  returnStaleOnError?: boolean;
}

export interface UseAICacheResult<T> {
  /** Cached data or null */
  data: T | null;
  /** Whether data is currently loading */
  isLoading: boolean;
  /** Whether cached data is stale */
  isStale: boolean;
  /** Error from last fetch attempt */
  error: Error | null;
  /** When data was cached */
  cachedAt: Date | null;
  /** Refetch data (uses cache if not stale) */
  refetch: () => void;
  /** Force refetch, bypassing cache */
  forceRefetch: () => void;
  /** Invalidate cache entry */
  invalidate: () => void;
}

// =============================================================================
// Global Cache Store
// =============================================================================

// In-memory cache store (shared across hook instances)
const cacheStore = new Map<string, CacheEntry<unknown>>();

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Create a consistent cache key from task type and parameters
 */
export function createCacheKey(
  taskType: string,
  params: Record<string, unknown>
): string {
  const sortedParams = Object.keys(params)
    .sort()
    .map((key) => `${key}:${JSON.stringify(params[key])}`)
    .join("|");
  return `${taskType}::${sortedParams}`;
}

/**
 * Check if a cache entry is stale
 */
function isEntryStale(entry: CacheEntry<unknown>): boolean {
  const now = Date.now();
  return now - entry.timestamp > entry.staleTime;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for caching AI Intelligence data with configurable TTL.
 *
 * @param options - Cache configuration options
 * @returns Cached data and cache management functions
 */
export function useAICache<T>(options: UseAICacheOptions<T>): UseAICacheResult<T> {
  const {
    cacheKey,
    fetchFn,
    staleTime = 5 * 60 * 1000, // 5 minutes default
    enabled = true,
    returnStaleOnError = true,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isStale, setIsStale] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [cachedAt, setCachedAt] = useState<Date | null>(null);

  // Track if component is mounted
  const isMounted = useRef(true);

  // Store fetchFn in ref to avoid dependency issues
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  /**
   * Get cached entry if available and not stale
   */
  const getCachedEntry = useCallback((): CacheEntry<T> | null => {
    const entry = cacheStore.get(cacheKey) as CacheEntry<T> | undefined;
    if (!entry) return null;
    return entry;
  }, [cacheKey]);

  /**
   * Set cache entry
   */
  const setCacheEntry = useCallback(
    (value: T) => {
      const entry: CacheEntry<T> = {
        data: value,
        timestamp: Date.now(),
        staleTime,
      };
      cacheStore.set(cacheKey, entry);
      return entry;
    },
    [cacheKey, staleTime]
  );

  /**
   * Perform the fetch operation
   */
  const doFetch = useCallback(
    async (force: boolean = false) => {
      if (!enabled) return;

      // Check cache first (unless forcing)
      if (!force) {
        const cached = getCachedEntry();
        if (cached && !isEntryStale(cached)) {
          // Return cached value without loading
          if (isMounted.current) {
            setData(cached.data);
            setCachedAt(new Date(cached.timestamp));
            setIsStale(false);
            setIsLoading(false);
          }
          return;
        }
      }

      // Need to fetch
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetchFnRef.current();

        if (isMounted.current) {
          const entry = setCacheEntry(result);
          setData(result);
          setCachedAt(new Date(entry.timestamp));
          setIsStale(false);
          setError(null);
        }
      } catch (err) {
        if (isMounted.current) {
          const fetchError = err instanceof Error ? err : new Error(String(err));
          setError(fetchError);

          // Return stale data if available and configured
          if (returnStaleOnError) {
            const cached = getCachedEntry();
            if (cached) {
              setData(cached.data);
              setCachedAt(new Date(cached.timestamp));
              setIsStale(true);
            }
          }
        }
      } finally {
        if (isMounted.current) {
          setIsLoading(false);
        }
      }
    },
    [enabled, getCachedEntry, setCacheEntry, returnStaleOnError]
  );

  /**
   * Refetch data (uses cache if not stale)
   */
  const refetch = useCallback(() => {
    doFetch(false);
  }, [doFetch]);

  /**
   * Force refetch, bypassing cache
   */
  const forceRefetch = useCallback(() => {
    doFetch(true);
  }, [doFetch]);

  /**
   * Invalidate cache entry
   */
  const invalidate = useCallback(() => {
    cacheStore.delete(cacheKey);
    setData(null);
    setCachedAt(null);
    setIsStale(false);
  }, [cacheKey]);

  // Initial fetch on mount
  useEffect(() => {
    isMounted.current = true;

    if (enabled) {
      doFetch(false);
    }

    return () => {
      isMounted.current = false;
    };
  }, [enabled, cacheKey, doFetch]); // Re-fetch when key changes

  return useMemo(
    () => ({
      data,
      isLoading,
      isStale,
      error,
      cachedAt,
      refetch,
      forceRefetch,
      invalidate,
    }),
    [data, isLoading, isStale, error, cachedAt, refetch, forceRefetch, invalidate]
  );
}

// =============================================================================
// Cache Management Utilities
// =============================================================================

/**
 * Clear all AI cache entries
 */
export function clearAllAICache(): void {
  cacheStore.clear();
}

/**
 * Clear AI cache entries matching a prefix
 */
export function clearAICacheByPrefix(prefix: string): void {
  for (const key of cacheStore.keys()) {
    if (key.startsWith(prefix)) {
      cacheStore.delete(key);
    }
  }
}

/**
 * Get cache statistics
 */
export function getAICacheStats(): {
  size: number;
  entries: { key: string; isStale: boolean; age: number }[];
} {
  const entries = Array.from(cacheStore.entries()).map(([key, entry]) => ({
    key,
    isStale: isEntryStale(entry),
    age: Date.now() - entry.timestamp,
  }));

  return {
    size: cacheStore.size,
    entries,
  };
}
