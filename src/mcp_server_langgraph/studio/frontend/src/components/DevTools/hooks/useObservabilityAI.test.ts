/**
 * useObservabilityAI Hook Tests
 *
 * TDD tests for AI-powered observability insights.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

import {
  useObservabilityAI,
  analyzeTraceAnomalies,
  correlateAlerts,
  predictCostTrends,
  generateRootCauseAnalysis,
} from "./useObservabilityAI";

// =============================================================================
// Tests
// =============================================================================

describe("useObservabilityAI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("analyzeTraceAnomalies", () => {
    it("should identify slow spans", () => {
      const spans = [
        { spanId: "s1", durationMs: 50, name: "fast" },
        { spanId: "s2", durationMs: 5000, name: "slow" },
        { spanId: "s3", durationMs: 100, name: "normal" },
      ];

      const anomalies = analyzeTraceAnomalies(spans);

      expect(anomalies.slowSpans).toHaveLength(1);
      expect(anomalies.slowSpans[0].spanId).toBe("s2");
    });

    it("should identify error patterns", () => {
      const spans = [
        { spanId: "s1", durationMs: 50, status: "ok", name: "success" },
        { spanId: "s2", durationMs: 50, status: "error", name: "failed" },
        { spanId: "s3", durationMs: 50, status: "error", name: "failed" },
      ];

      const anomalies = analyzeTraceAnomalies(spans);

      expect(anomalies.errorPatterns).toHaveLength(1);
      expect(anomalies.errorPatterns[0].count).toBe(2);
    });

    it("should calculate performance percentiles", () => {
      const spans = Array.from({ length: 100 }, (_, i) => ({
        spanId: `s${i}`,
        durationMs: (i + 1) * 10,
        name: "span",
        status: "ok",
      }));

      const anomalies = analyzeTraceAnomalies(spans);

      expect(anomalies.percentiles.p50).toBeDefined();
      expect(anomalies.percentiles.p95).toBeDefined();
      expect(anomalies.percentiles.p99).toBeDefined();
    });
  });

  describe("correlateAlerts", () => {
    it("should group related alerts by time proximity", () => {
      const alerts = [
        { id: "a1", startedAt: "2024-01-01T12:00:00Z", service: "api" },
        { id: "a2", startedAt: "2024-01-01T12:00:30Z", service: "db" },
        { id: "a3", startedAt: "2024-01-01T14:00:00Z", service: "api" },
      ];

      const correlations = correlateAlerts(alerts);

      // First two should be correlated (within 5 min)
      expect(correlations).toHaveLength(2);
      expect(correlations[0].alerts).toContain("a1");
      expect(correlations[0].alerts).toContain("a2");
    });

    it("should identify service dependencies in correlated alerts", () => {
      const alerts = [
        {
          id: "a1",
          startedAt: "2024-01-01T12:00:00Z",
          service: "api-gateway",
        },
        { id: "a2", startedAt: "2024-01-01T12:00:30Z", service: "db-primary" },
      ];

      const correlations = correlateAlerts(alerts);

      expect(correlations[0].services).toContain("api-gateway");
      expect(correlations[0].services).toContain("db-primary");
    });
  });

  describe("predictCostTrends", () => {
    it("should calculate token usage trend", () => {
      const metrics = [
        { name: "tokens_used", value: 1000, timestamp: 1 },
        { name: "tokens_used", value: 1200, timestamp: 2 },
        { name: "tokens_used", value: 1400, timestamp: 3 },
      ];

      const prediction = predictCostTrends(metrics);

      expect(prediction.trend).toBe("increasing");
      expect(prediction.projectedDaily).toBeGreaterThan(0);
    });

    it("should identify cost anomalies", () => {
      const metrics = [
        { name: "tokens_used", value: 1000, timestamp: 1 },
        { name: "tokens_used", value: 1100, timestamp: 2 },
        { name: "tokens_used", value: 5000, timestamp: 3 }, // Spike!
      ];

      const prediction = predictCostTrends(metrics);

      expect(prediction.anomalies).toHaveLength(1);
      expect(prediction.anomalies[0].timestamp).toBe(3);
    });
  });

  describe("generateRootCauseAnalysis", () => {
    it("should generate hypothesis for error cascade", () => {
      const context = {
        alerts: [
          { id: "a1", service: "db", message: "Connection timeout" },
          { id: "a2", service: "api", message: "5xx error spike" },
        ],
        spans: [
          {
            spanId: "s1",
            name: "db.query",
            status: "error",
            durationMs: 30000,
          },
        ],
      };

      const analysis = generateRootCauseAnalysis(context);

      expect(analysis.hypothesis).toBeDefined();
      expect(analysis.confidence).toBeGreaterThan(0);
      // Multiple patterns can match (db + timeout), so check for at least 1
      expect(analysis.suggestedActions.length).toBeGreaterThanOrEqual(1);
    });

    it("should prioritize root causes by likelihood", () => {
      const context = {
        alerts: [
          { id: "a1", service: "db", message: "Connection pool exhausted" },
          { id: "a2", service: "api", message: "Request timeout" },
          { id: "a3", service: "cache", message: "Cache miss rate high" },
        ],
        spans: [],
      };

      const analysis = generateRootCauseAnalysis(context);

      expect(analysis.rootCauses).toBeDefined();
      expect(analysis.rootCauses[0].likelihood).toBeGreaterThanOrEqual(
        analysis.rootCauses[1]?.likelihood || 0,
      );
    });
  });

  describe("hook exports", () => {
    it("should export useObservabilityAI hook", () => {
      // Verify hook is a function
      expect(typeof useObservabilityAI).toBe("function");
    });

    it("should export analysis functions", () => {
      // Verify all utility functions are exported
      expect(typeof analyzeTraceAnomalies).toBe("function");
      expect(typeof correlateAlerts).toBe("function");
      expect(typeof predictCostTrends).toBe("function");
      expect(typeof generateRootCauseAnalysis).toBe("function");
    });
  });
});
