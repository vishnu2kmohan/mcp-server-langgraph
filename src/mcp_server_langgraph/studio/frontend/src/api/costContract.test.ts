/**
 * Cost API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for cost endpoints.
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the Cost API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../mocks/server";

describe("Cost API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("GET /api/v1/cost/summary", () => {
    it("should return cost summary", async () => {
      const response = await fetch("/api/v1/cost/summary");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required cost summary fields
      expect(data).toHaveProperty("total_cost");
      expect(data).toHaveProperty("prompt_tokens");
      expect(data).toHaveProperty("completion_tokens");
      expect(data).toHaveProperty("total_tokens");
      expect(data).toHaveProperty("period_start");
      expect(data).toHaveProperty("period_end");
    });

    it("should return numeric cost values", async () => {
      const response = await fetch("/api/v1/cost/summary");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.total_cost).toBe("number");
      expect(typeof data.prompt_tokens).toBe("number");
      expect(typeof data.completion_tokens).toBe("number");
      expect(typeof data.total_tokens).toBe("number");

      // Validate non-negative values
      expect(data.total_cost).toBeGreaterThanOrEqual(0);
      expect(data.prompt_tokens).toBeGreaterThanOrEqual(0);
      expect(data.completion_tokens).toBeGreaterThanOrEqual(0);
      expect(data.total_tokens).toBeGreaterThanOrEqual(0);
    });

    it("should return valid ISO date strings for period", async () => {
      const response = await fetch("/api/v1/cost/summary");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.period_start).toBe("string");
      expect(typeof data.period_end).toBe("string");

      // Validate ISO date format
      expect(new Date(data.period_start).toISOString()).toBe(data.period_start);
      expect(new Date(data.period_end).toISOString()).toBe(data.period_end);

      // period_end should be after period_start
      expect(new Date(data.period_end).getTime()).toBeGreaterThan(
        new Date(data.period_start).getTime(),
      );
    });

    it("should have total_tokens equal to prompt + completion tokens", async () => {
      const response = await fetch("/api/v1/cost/summary");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.total_tokens).toBe(
        data.prompt_tokens + data.completion_tokens,
      );
    });
  });

  describe("GET /api/v1/cost/by-model", () => {
    it("should return array of model costs", async () => {
      const response = await fetch("/api/v1/cost/by-model");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    it("should return model costs with required fields", async () => {
      const response = await fetch("/api/v1/cost/by-model");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const modelCost = data[0];

      // Required model cost fields
      expect(modelCost).toHaveProperty("model");
      expect(modelCost).toHaveProperty("cost");
      expect(modelCost).toHaveProperty("requests");

      // Type validation
      expect(typeof modelCost.model).toBe("string");
      expect(typeof modelCost.cost).toBe("number");
      expect(typeof modelCost.requests).toBe("number");
    });

    it("should have non-negative cost and request values", async () => {
      const response = await fetch("/api/v1/cost/by-model");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const modelCost of data) {
        expect(modelCost.cost).toBeGreaterThanOrEqual(0);
        expect(modelCost.requests).toBeGreaterThanOrEqual(0);
      }
    });

    it("should have unique model names", async () => {
      const response = await fetch("/api/v1/cost/by-model");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const models = data.map((m: { model: string }) => m.model);
      const uniqueModels = new Set(models);
      expect(uniqueModels.size).toBe(models.length);
    });
  });

  describe("GET /api/v1/cost/history", () => {
    it("should return array of cost history points", async () => {
      const response = await fetch("/api/v1/cost/history");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    it("should return history points with required fields", async () => {
      const response = await fetch("/api/v1/cost/history");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const historyPoint = data[0];

      // Required history point fields
      expect(historyPoint).toHaveProperty("date");
      expect(historyPoint).toHaveProperty("cost");

      // Type validation
      expect(typeof historyPoint.date).toBe("string");
      expect(typeof historyPoint.cost).toBe("number");
    });

    it("should have valid date format (YYYY-MM-DD)", async () => {
      const response = await fetch("/api/v1/cost/history");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const datePattern = /^\d{4}-\d{2}-\d{2}$/;

      for (const point of data) {
        expect(point.date).toMatch(datePattern);
      }
    });

    it("should have chronologically ordered dates", async () => {
      const response = await fetch("/api/v1/cost/history");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (let i = 1; i < data.length; i++) {
        const prevDate = new Date(data[i - 1].date);
        const currDate = new Date(data[i].date);
        expect(currDate.getTime()).toBeGreaterThan(prevDate.getTime());
      }
    });

    it("should have non-negative cost values", async () => {
      const response = await fetch("/api/v1/cost/history");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const point of data) {
        expect(point.cost).toBeGreaterThanOrEqual(0);
      }
    });
  });
});
