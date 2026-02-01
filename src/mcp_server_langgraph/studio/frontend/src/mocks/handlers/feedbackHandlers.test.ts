/**
 * Feedback Handlers MSW Tests
 *
 * TDD tests for MSW handlers that mock feedback API endpoints.
 * These handlers prevent "unhandled request" warnings during tests.
 *
 * Endpoints:
 * - GET /api/v1/feedback/summary - Aggregated feedback metrics
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { server } from "../server";
import {
  feedbackHandlers,
  createFeedbackSummaryHandler,
  createMockFeedbackSummary,
} from "./feedbackHandlers";
import { transformSnakeToCamel } from "../../api/transforms";

describe("feedbackHandlers", () => {
  beforeEach(() => {
    server.use(...feedbackHandlers);
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });

  describe("handler exports", () => {
    it("should export feedbackHandlers array", () => {
      expect(Array.isArray(feedbackHandlers)).toBe(true);
      expect(feedbackHandlers.length).toBeGreaterThan(0);
    });

    it("should export createFeedbackSummaryHandler factory", () => {
      expect(typeof createFeedbackSummaryHandler).toBe("function");
    });

    it("should export createMockFeedbackSummary factory", () => {
      expect(typeof createMockFeedbackSummary).toBe("function");
    });
  });

  describe("GET /api/v1/feedback/summary", () => {
    it("should return feedback summary with default timeframe", async () => {
      const response = await fetch("/api/v1/feedback/summary");

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();
      expect(data.timeframe).toBe("7d");
      expect(typeof data.total_feedback).toBe("number");
      expect(typeof data.positive_count).toBe("number");
      expect(typeof data.negative_count).toBe("number");
      expect(typeof data.positive_rate).toBe("number");
      expect(typeof data.hallucination_reports).toBe("number");
    });

    it("should accept timeframe query parameter", async () => {
      const response = await fetch("/api/v1/feedback/summary?timeframe=30d");

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.timeframe).toBe("30d");
    });

    it("should include hallucination_categories in response", async () => {
      const response = await fetch("/api/v1/feedback/summary");
      const data = await response.json();

      expect(data.hallucination_categories).toBeDefined();
      expect(typeof data.hallucination_categories.factual_error).toBe("number");
      expect(typeof data.hallucination_categories.outdated_info).toBe("number");
      expect(typeof data.hallucination_categories.made_up_source).toBe(
        "number",
      );
      expect(typeof data.hallucination_categories.other).toBe("number");
    });

    it("should have positive_rate between 0 and 1", async () => {
      const response = await fetch("/api/v1/feedback/summary");
      const data = await response.json();

      expect(data.positive_rate).toBeGreaterThanOrEqual(0);
      expect(data.positive_rate).toBeLessThanOrEqual(1);
    });

    it("should have consistent counts (positive + negative = total)", async () => {
      const response = await fetch("/api/v1/feedback/summary");
      const data = await response.json();

      // Allow for floating point imprecision
      expect(data.positive_count + data.negative_count).toBe(
        data.total_feedback,
      );
    });
  });

  describe("createMockFeedbackSummary factory", () => {
    it("should create mock with default values", () => {
      const mock = createMockFeedbackSummary();

      expect(mock.timeframe).toBe("7d");
      expect(mock.total_feedback).toBeGreaterThanOrEqual(0);
      expect(mock.hallucination_categories).toBeDefined();
    });

    it("should allow overriding timeframe", () => {
      const mock = createMockFeedbackSummary({ timeframe: "90d" });
      expect(mock.timeframe).toBe("90d");
    });

    it("should allow overriding hallucination_reports", () => {
      const mock = createMockFeedbackSummary({ hallucination_reports: 25 });
      expect(mock.hallucination_reports).toBe(25);
    });

    it("should allow overriding hallucination_categories", () => {
      const mock = createMockFeedbackSummary({
        hallucination_categories: {
          factual_error: 10,
          outdated_info: 5,
          made_up_source: 3,
          other: 2,
        },
      });
      expect(mock.hallucination_categories?.factual_error).toBe(10);
      expect(mock.hallucination_categories?.outdated_info).toBe(5);
    });

    it("should calculate positive_rate correctly", () => {
      const mock = createMockFeedbackSummary({
        total_feedback: 100,
        positive_count: 80,
        negative_count: 20,
      });
      expect(mock.positive_rate).toBeCloseTo(0.8, 2);
    });
  });

  describe("custom handler factories", () => {
    it("should allow custom feedback summary handler", async () => {
      const customHandler = createFeedbackSummaryHandler(() => ({
        timeframe: "custom",
        total_feedback: 999,
        positive_count: 900,
        negative_count: 99,
        positive_rate: 0.9009,
        hallucination_reports: 50,
        hallucination_categories: {
          factual_error: 20,
          outdated_info: 15,
          made_up_source: 10,
          other: 5,
        },
      }));

      server.use(customHandler);

      const response = await fetch("/api/v1/feedback/summary");
      const data = await response.json();

      expect(data.timeframe).toBe("custom");
      expect(data.total_feedback).toBe(999);
      expect(data.hallucination_reports).toBe(50);
    });

    it("should receive timeframe parameter in callback", async () => {
      let receivedTimeframe: string | null = null;

      const customHandler = createFeedbackSummaryHandler((timeframe) => {
        receivedTimeframe = timeframe;
        return createMockFeedbackSummary({ timeframe });
      });

      server.use(customHandler);

      await fetch("/api/v1/feedback/summary?timeframe=14d");

      expect(receivedTimeframe).toBe("14d");
    });
  });

  describe("edge cases", () => {
    it("should handle zero feedback gracefully", async () => {
      const customHandler = createFeedbackSummaryHandler(() =>
        createMockFeedbackSummary({
          total_feedback: 0,
          positive_count: 0,
          negative_count: 0,
          positive_rate: 0,
          hallucination_reports: 0,
        }),
      );

      server.use(customHandler);

      const response = await fetch("/api/v1/feedback/summary");
      const data = await response.json();

      expect(data.total_feedback).toBe(0);
      expect(data.hallucination_reports).toBe(0);
    });

    it("should handle high volume feedback", async () => {
      const customHandler = createFeedbackSummaryHandler(() =>
        createMockFeedbackSummary({
          total_feedback: 100000,
          positive_count: 85000,
          negative_count: 15000,
          hallucination_reports: 500,
        }),
      );

      server.use(customHandler);

      const response = await fetch("/api/v1/feedback/summary");
      const data = await response.json();

      expect(data.total_feedback).toBe(100000);
      expect(data.hallucination_reports).toBe(500);
    });
  });

  describe("API Contract Transformation", () => {
    it("should return feedback summary in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/feedback/summary");
      const rawData = await response.json();

      // Verify transformation works
      const transformedData = transformSnakeToCamel(rawData);
      expect(transformedData).toBeDefined();
    });
  });
});
