/**
 * Tests for useTraceIntelligence hooks.
 *
 * Sprint 5: Trace Intelligence + Cost Projection
 * - Trace summary provides one-sentence summary of agent execution
 * - Trace anomaly detection identifies bottlenecks and issues
 * - Cost projection estimates real-time session costs
 * - Token prediction forecasts token usage
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

// Mock the API module - single mock at top level to avoid memory leaks
vi.mock("../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            trace_summarize: {
              summary: "Agent completed 5-step workflow in 2.3s with 2 tool calls",
              total_duration_ms: 2300,
              step_count: 5,
              tool_call_count: 2,
              success: true,
              key_actions: ["Retrieved data", "Processed request", "Generated response"],
            },
            trace_anomaly: {
              anomalies: [
                {
                  type: "slow_step",
                  step_name: "database_query",
                  severity: "warning",
                  message: "Step took 1.5s, 3x slower than average",
                  suggested_fix: "Consider adding index or caching",
                },
              ],
              bottlenecks: [
                {
                  step_name: "database_query",
                  duration_ms: 1500,
                  percentage_of_total: 65,
                },
              ],
              health_score: 0.72,
              optimization_suggestions: ["Consider parallel execution for independent steps"],
            },
            cost_project: {
              current_cost: 0.0023,
              projected_cost: 0.015,
              cost_breakdown: {
                input_tokens: 0.001,
                output_tokens: 0.0013,
              },
              budget_remaining: 4.985,
              budget_percentage_used: 0.3,
              estimated_remaining_messages: 320,
            },
            token_predict: {
              current_tokens: 4500,
              projected_tokens: 8200,
              context_utilization: 0.45,
              optimization_available: true,
              optimization_savings: 1200,
              recommended_action: "Consider summarizing older messages",
            },
          },
          cross_insights: [],
          failed_analyses: [],
          total_cost: "0.002",
        }),
    })),
    { isLoading: false },
  ]),
}));

// =============================================================================
// Test Utilities
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}

const createWrapper = () => {
  const store = createTestStore();
  return function Wrapper({ children }: WrapperProps) {
    return <Provider store={store}>{children}</Provider>;
  };
};

// =============================================================================
// Trace Intelligence Hook Tests
// =============================================================================

describe("Trace Intelligence Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("useTraceSummary", () => {
    it("returns trace summary with key metrics", async () => {
      const { useTraceSummary } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useTraceSummary({
            userId: "test-user",
            sessionId: "session-123",
            traceId: "trace-456",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.summary).toContain("Agent completed");
      expect(result.current.totalDurationMs).toBe(2300);
      expect(result.current.stepCount).toBe(5);
      expect(result.current.toolCallCount).toBe(2);
      expect(result.current.success).toBe(true);
      expect(result.current.keyActions).toHaveLength(3);
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useTraceSummary } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useTraceSummary({
            userId: "test-user",
            sessionId: "session-123",
            traceId: "trace-456",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.summary).toBeNull();
    });

    it("handles empty traceId", async () => {
      const { useTraceSummary } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useTraceSummary({
            userId: "test-user",
            sessionId: "session-123",
            traceId: "",
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.summary).toBeNull();
    });
  });

  describe("useTraceAnomaly", () => {
    it("returns anomaly detection results", async () => {
      const { useTraceAnomaly } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useTraceAnomaly({
            userId: "test-user",
            sessionId: "session-123",
            traceId: "trace-456",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.anomalies).toHaveLength(1);
      expect(result.current.anomalies[0].type).toBe("slow_step");
      expect(result.current.bottlenecks).toHaveLength(1);
      expect(result.current.bottlenecks[0].step_name).toBe("database_query");
      expect(result.current.healthScore).toBe(0.72);
      expect(result.current.optimizationSuggestions).toHaveLength(1);
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useTraceAnomaly } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useTraceAnomaly({
            userId: "test-user",
            sessionId: "session-123",
            traceId: "trace-456",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.anomalies).toEqual([]);
    });
  });

  describe("useCostProjection", () => {
    it("returns cost projection with breakdown", async () => {
      const { useCostProjection } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useCostProjection({
            userId: "test-user",
            sessionId: "session-123",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.currentCost).toBe(0.0023);
      expect(result.current.projectedCost).toBe(0.015);
      expect(result.current.costBreakdown).toBeDefined();
      expect(result.current.costBreakdown?.input_tokens).toBe(0.001);
      expect(result.current.budgetRemaining).toBe(4.985);
      expect(result.current.budgetPercentageUsed).toBe(0.3);
      expect(result.current.estimatedRemainingMessages).toBe(320);
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useCostProjection } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useCostProjection({
            userId: "test-user",
            sessionId: "session-123",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.currentCost).toBeNull();
    });
  });

  describe("useTokenPrediction", () => {
    it("returns token prediction with optimization info", async () => {
      const { useTokenPrediction } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useTokenPrediction({
            userId: "test-user",
            sessionId: "session-123",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.currentTokens).toBe(4500);
      expect(result.current.projectedTokens).toBe(8200);
      expect(result.current.contextUtilization).toBe(0.45);
      expect(result.current.optimizationAvailable).toBe(true);
      expect(result.current.optimizationSavings).toBe(1200);
      expect(result.current.recommendedAction).toContain("summarizing");
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useTokenPrediction } = await import("./useTraceIntelligence");

      const { result } = renderHook(
        () =>
          useTokenPrediction({
            userId: "test-user",
            sessionId: "session-123",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.currentTokens).toBeNull();
    });
  });
});
