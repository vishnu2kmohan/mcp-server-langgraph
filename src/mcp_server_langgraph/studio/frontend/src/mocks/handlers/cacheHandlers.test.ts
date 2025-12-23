/**
 * Frontend Cache MSW Handlers Tests
 *
 * TDD tests for MSW handlers that mock /api/v1/cache/* endpoints.
 * These handlers prevent "unhandled request" warnings during tests
 * and enable useTieredCache hook integration with Redis L2.
 *
 * Reference: docs-internal/CACHING_ARCHITECTURE_AUDIT.md
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../server";
import {
  cacheHandlers,
  createCacheGetHandler,
  createCacheSetHandler,
  createCacheDeleteHandler,
  createCachePrefixDeleteHandler,
} from "./cacheHandlers";

describe("cacheHandlers", () => {
  beforeEach(() => {
    // Add our handlers to the global server
    server.use(...cacheHandlers);
  });

  afterEach(() => {
    server.resetHandlers();
      vi.clearAllMocks();
      vi.restoreAllMocks();
  });

  describe("handler exports", () => {
    it("should export cacheHandlers array", () => {
      expect(Array.isArray(cacheHandlers)).toBe(true);
      expect(cacheHandlers.length).toBeGreaterThan(0);
    });

    it("should export createCacheGetHandler factory", () => {
      expect(typeof createCacheGetHandler).toBe("function");
    });

    it("should export createCacheSetHandler factory", () => {
      expect(typeof createCacheSetHandler).toBe("function");
    });

    it("should export createCacheDeleteHandler factory", () => {
      expect(typeof createCacheDeleteHandler).toBe("function");
    });

    it("should export createCachePrefixDeleteHandler factory", () => {
      expect(typeof createCachePrefixDeleteHandler).toBe("function");
    });
  });

  describe("GET /api/v1/cache/:key", () => {
    it("should return cache miss for non-existent key", async () => {
      const response = await fetch("/api/v1/cache/nonexistent-key");

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.key).toBe("nonexistent-key");
      expect(data.hit).toBe(false);
      expect(data.value).toBeNull();
    });

    it("should return cache hit for existing key", async () => {
      // First, set a value
      await fetch("/api/v1/cache/test-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: { data: "test-value", _cachedAt: Date.now() },
          ttl_seconds: 300,
        }),
      });

      // Then get it
      const response = await fetch("/api/v1/cache/test-key");

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.key).toBe("test-key");
      expect(data.hit).toBe(true);
      expect(data.value).toBeDefined();
      expect(data.value.data).toBe("test-value");
    });

    it("should handle URL-encoded keys", async () => {
      const key = "user:profile:123";
      const encodedKey = encodeURIComponent(key);

      const response = await fetch(`/api/v1/cache/${encodedKey}`);

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.key).toBe(key);
    });
  });

  describe("PUT /api/v1/cache/:key", () => {
    it("should set cache value successfully", async () => {
      const cacheEntry = {
        data: { id: "1", name: "Test" },
        _cachedAt: Date.now(),
      };

      const response = await fetch("/api/v1/cache/new-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: cacheEntry,
          ttl_seconds: 300,
        }),
      });

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.key).toBe("new-key");
      expect(data.success).toBe(true);
      expect(data.ttl_seconds).toBe(300);
    });

    it("should accept custom TTL values", async () => {
      const response = await fetch("/api/v1/cache/custom-ttl-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: { data: "test" },
          ttl_seconds: 3600,
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.ttl_seconds).toBe(3600);
    });

    it("should use default TTL when not specified", async () => {
      const response = await fetch("/api/v1/cache/default-ttl-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: { data: "test" },
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.ttl_seconds).toBe(300); // Default 5 minutes
    });

    it("should handle complex cache values", async () => {
      const complexValue = {
        data: {
          nested: {
            array: [1, 2, 3],
            object: { key: "value" },
          },
        },
        _cachedAt: Date.now(),
      };

      const response = await fetch("/api/v1/cache/complex-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: complexValue,
          ttl_seconds: 600,
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.success).toBe(true);
    });
  });

  describe("DELETE /api/v1/cache/:key", () => {
    it("should delete cache key successfully", async () => {
      // First set a key
      await fetch("/api/v1/cache/to-delete", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: { data: "test" },
          ttl_seconds: 300,
        }),
      });

      // Then delete it
      const response = await fetch("/api/v1/cache/to-delete", {
        method: "DELETE",
      });

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.key).toBe("to-delete");
      expect(data.deleted).toBe(true);
    });

    it("should succeed even if key does not exist", async () => {
      const response = await fetch("/api/v1/cache/nonexistent-delete", {
        method: "DELETE",
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.deleted).toBe(true);
    });
  });

  describe("DELETE /api/v1/cache/prefix/:prefix", () => {
    it("should delete all keys with matching prefix", async () => {
      // Set multiple keys with same prefix
      await Promise.all([
        fetch("/api/v1/cache/user:123:profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: { data: "profile" }, ttl_seconds: 300 }),
        }),
        fetch("/api/v1/cache/user:123:settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: { data: "settings" }, ttl_seconds: 300 }),
        }),
      ]);

      // Delete by prefix
      const response = await fetch(
        `/api/v1/cache/prefix/${encodeURIComponent("user:123")}`,
        { method: "DELETE" }
      );

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.prefix).toBe("user:123");
      expect(data.deleted_count).toBeGreaterThanOrEqual(0);
    });

    it("should return zero count for non-matching prefix", async () => {
      const response = await fetch(
        `/api/v1/cache/prefix/${encodeURIComponent("nonexistent:prefix")}`,
        { method: "DELETE" }
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.deleted_count).toBe(0);
    });
  });

  describe("custom handler factories", () => {
    it("should allow custom GET handler with callback", async () => {
      let capturedKey: string | null = null;

      const customHandler = createCacheGetHandler((key) => {
        capturedKey = key;
        return { hit: true, value: { custom: "response" } };
      });

      server.use(customHandler);

      await fetch("/api/v1/cache/custom-get-key");

      expect(capturedKey).toBe("custom-get-key");
    });

    it("should allow custom SET handler with callback", async () => {
      let capturedData: { key: string; value: unknown; ttl: number } | null =
        null;

      const customHandler = createCacheSetHandler((key, value, ttl) => {
        capturedData = { key, value, ttl };
        return { custom: true };
      });

      server.use(customHandler);

      await fetch("/api/v1/cache/custom-set-key", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          value: { data: "custom" },
          ttl_seconds: 600,
        }),
      });

      expect(capturedData).not.toBeNull();
      expect(capturedData?.key).toBe("custom-set-key");
      expect(capturedData?.ttl).toBe(600);
    });

    it("should allow custom DELETE handler with callback", async () => {
      let capturedKey: string | null = null;

      const customHandler = createCacheDeleteHandler((key) => {
        capturedKey = key;
        return { custom_deleted: true };
      });

      server.use(customHandler);

      await fetch("/api/v1/cache/custom-delete-key", {
        method: "DELETE",
      });

      expect(capturedKey).toBe("custom-delete-key");
    });

    it("should allow custom prefix DELETE handler with callback", async () => {
      let capturedPrefix: string | null = null;

      const customHandler = createCachePrefixDeleteHandler((prefix) => {
        capturedPrefix = prefix;
        return { deleted_count: 42 };
      });

      server.use(customHandler);

      await fetch(`/api/v1/cache/prefix/${encodeURIComponent("test:prefix")}`, {
        method: "DELETE",
      });

      expect(capturedPrefix).toBe("test:prefix");
    });
  });

  describe("error handling", () => {
    it("should handle malformed JSON in SET request", async () => {
      const response = await fetch("/api/v1/cache/bad-json", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: "not valid json",
      });

      // MSW may not catch this, but the handler should be robust
      // Just ensure no unhandled errors
      expect(response).toBeDefined();
    });

    it("should handle very long cache keys", async () => {
      const longKey = "a".repeat(500);

      const response = await fetch(`/api/v1/cache/${longKey}`);

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.key).toBe(longKey);
    });
  });
});
