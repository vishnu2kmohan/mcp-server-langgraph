/**
 * Frontend Cache MSW Handlers
 *
 * Mock Service Worker handlers for /api/v1/cache/* endpoints.
 * These handlers prevent "unhandled request" warnings during tests
 * and enable useTieredCache hook integration with Redis L2.
 *
 * Endpoints:
 * - GET /api/v1/cache/:key - Get cache value
 * - PUT /api/v1/cache/:key - Set cache value with TTL
 * - DELETE /api/v1/cache/:key - Delete cache key
 * - DELETE /api/v1/cache/prefix/:prefix - Delete all keys with prefix
 *
 * Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md
 */

import { http, HttpResponse } from "msw";

// =============================================================================
// Types
// =============================================================================

/**
 * Cache entry stored by useTieredCache hook
 */
interface CacheEntry<T = unknown> {
  data: T;
  _cachedAt: number;
}

/**
 * Cache SET request body
 */
interface CacheSetRequest {
  value: CacheEntry;
  ttl_seconds?: number;
}

// =============================================================================
// In-Memory Mock Store
// =============================================================================

/**
 * Simple in-memory store for mock cache operations.
 * This allows tests to verify get-after-set behavior.
 */
const mockCacheStore = new Map<string, CacheEntry>();

/**
 * Clear the mock cache store (useful in test cleanup)
 */
export function clearMockCacheStore(): void {
  mockCacheStore.clear();
}

// =============================================================================
// Default TTL
// =============================================================================

const DEFAULT_TTL_SECONDS = 300; // 5 minutes

// =============================================================================
// Handler Factories
// =============================================================================

/**
 * Create a custom cache GET handler with callback
 */
export function createCacheGetHandler(
  callback?: (key: string) => { hit: boolean; value: unknown | null },
) {
  return http.get("/api/v1/cache/:key", async ({ params }) => {
    const key = decodeURIComponent(params.key as string);

    if (callback) {
      const result = callback(key);
      return HttpResponse.json({
        key,
        hit: result.hit,
        value: result.value,
      });
    }

    // Default behavior: check mock store
    const entry = mockCacheStore.get(key);
    if (entry) {
      return HttpResponse.json({
        key,
        hit: true,
        value: entry,
      });
    }

    return HttpResponse.json({
      key,
      hit: false,
      value: null,
    });
  });
}

/**
 * Create a custom cache SET handler with callback
 */
export function createCacheSetHandler(
  callback?: (
    key: string,
    value: unknown,
    ttl: number,
  ) => Record<string, unknown>,
) {
  return http.put("/api/v1/cache/:key", async ({ params, request }) => {
    const key = decodeURIComponent(params.key as string);

    let body: CacheSetRequest;
    try {
      body = (await request.json()) as CacheSetRequest;
    } catch {
      // Handle malformed JSON gracefully
      return HttpResponse.json({ error: "Invalid JSON body" }, { status: 400 });
    }

    const ttl = body.ttl_seconds ?? DEFAULT_TTL_SECONDS;

    if (callback) {
      const customResponse = callback(key, body.value, ttl);
      return HttpResponse.json({
        key,
        success: true,
        ttl_seconds: ttl,
        ...customResponse,
      });
    }

    // Default behavior: store in mock store
    mockCacheStore.set(key, body.value);

    return HttpResponse.json({
      key,
      success: true,
      ttl_seconds: ttl,
    });
  });
}

/**
 * Create a custom cache DELETE handler with callback
 */
export function createCacheDeleteHandler(
  callback?: (key: string) => Record<string, unknown>,
) {
  return http.delete("/api/v1/cache/:key", async ({ params }) => {
    const key = decodeURIComponent(params.key as string);

    if (callback) {
      const customResponse = callback(key);
      return HttpResponse.json({
        key,
        deleted: true,
        ...customResponse,
      });
    }

    // Default behavior: remove from mock store
    mockCacheStore.delete(key);

    return HttpResponse.json({
      key,
      deleted: true,
    });
  });
}

/**
 * Create a custom cache prefix DELETE handler with callback
 */
export function createCachePrefixDeleteHandler(
  callback?: (prefix: string) => { deleted_count: number },
) {
  return http.delete("/api/v1/cache/prefix/:prefix", async ({ params }) => {
    const prefix = decodeURIComponent(params.prefix as string);

    if (callback) {
      const result = callback(prefix);
      return HttpResponse.json({
        prefix,
        deleted_count: result.deleted_count,
      });
    }

    // Default behavior: delete all keys with matching prefix
    let deletedCount = 0;
    for (const key of mockCacheStore.keys()) {
      if (key.startsWith(prefix)) {
        mockCacheStore.delete(key);
        deletedCount++;
      }
    }

    return HttpResponse.json({
      prefix,
      deleted_count: deletedCount,
    });
  });
}

// =============================================================================
// Default Cache Handlers
// =============================================================================

/**
 * Default cache handlers for MSW
 *
 * NOTE: Order matters! More specific paths (prefix) must come before
 * less specific paths (:key) to avoid route conflicts.
 */
export const cacheHandlers = [
  // Prefix delete endpoint (more specific - must come first)
  createCachePrefixDeleteHandler(),

  // Single key endpoints
  createCacheGetHandler(),
  createCacheSetHandler(),
  createCacheDeleteHandler(),
];

export default cacheHandlers;
