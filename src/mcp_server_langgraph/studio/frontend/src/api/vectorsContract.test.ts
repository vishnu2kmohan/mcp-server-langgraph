/**
 * Vectors API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for vector endpoints.
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the Vectors API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../mocks/server";

describe("Vectors API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("GET /api/v1/vectors/collections", () => {
    it("should return array of collections", async () => {
      const response = await fetch("/api/v1/vectors/collections");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    it("should return collections with required fields", async () => {
      const response = await fetch("/api/v1/vectors/collections");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const collection = data[0];

      // Required collection fields
      expect(collection).toHaveProperty("name");
      expect(collection).toHaveProperty("vectors_count");

      // Type validation
      expect(typeof collection.name).toBe("string");
      expect(typeof collection.vectors_count).toBe("number");
    });

    it("should have non-negative vectors count", async () => {
      const response = await fetch("/api/v1/vectors/collections");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const collection of data) {
        expect(collection.vectors_count).toBeGreaterThanOrEqual(0);
      }
    });

    it("should have unique collection names", async () => {
      const response = await fetch("/api/v1/vectors/collections");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const names = data.map((c: { name: string }) => c.name);
      const uniqueNames = new Set(names);
      expect(uniqueNames.size).toBe(names.length);
    });
  });

  describe("POST /api/v1/vectors/search-text", () => {
    it("should return search results", async () => {
      const response = await fetch("/api/v1/vectors/search-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "test query",
          collection: "documents",
          limit: 10,
        }),
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("results");
      expect(Array.isArray(data.results)).toBe(true);
    });

    it("should return results with required fields", async () => {
      const response = await fetch("/api/v1/vectors/search-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "test query",
          collection: "documents",
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.results.length).toBeGreaterThan(0);
      const result = data.results[0];

      // Required search result fields
      expect(result).toHaveProperty("id");
      expect(result).toHaveProperty("score");
      expect(result).toHaveProperty("payload");

      // Type validation
      expect(typeof result.id).toBe("string");
      expect(typeof result.score).toBe("number");
      expect(typeof result.payload).toBe("object");
    });

    it("should have scores between 0 and 1", async () => {
      const response = await fetch("/api/v1/vectors/search-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "test query",
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const result of data.results) {
        expect(result.score).toBeGreaterThanOrEqual(0);
        expect(result.score).toBeLessThanOrEqual(1);
      }
    });

    it("should return results ordered by score (descending)", async () => {
      const response = await fetch("/api/v1/vectors/search-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "test query",
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (let i = 1; i < data.results.length; i++) {
        expect(data.results[i - 1].score).toBeGreaterThanOrEqual(
          data.results[i].score,
        );
      }
    });

    it("should have payload with text field", async () => {
      const response = await fetch("/api/v1/vectors/search-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: "test query",
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const result of data.results) {
        expect(result.payload).toHaveProperty("text");
        expect(typeof result.payload.text).toBe("string");
      }
    });
  });
});
