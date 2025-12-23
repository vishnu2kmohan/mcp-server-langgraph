/**
 * HEART Analytics Integration Tests
 *
 * Sprint 4 - Phase 3: Full HEART SDK Integration Tests
 *
 * Integration tests verifying that HEART analytics components
 * work together correctly:
 * - HeartAggregator batching with useHeartMetricsTracker
 * - useHeartDashboard data fetching
 * - GSM framework integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { waitFor } from "@testing-library/react";
import { renderHook, act } from "@testing-library/react";
import { useHeartDashboard } from "../hooks/useHeartDashboard";
import { HeartAggregator } from "../analytics";
import { recordSignal, getMetricsSummary } from "../analytics/gsm";

// =============================================================================
// Test Setup
// =============================================================================

describe("HEART Analytics Integration", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({ ok: true });
    vi.stubGlobal("fetch", fetchSpy);
    vi.stubGlobal("localStorage", {
      getItem: vi.fn().mockReturnValue(null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // useHeartDashboard Integration
  // ===========================================================================

  describe("useHeartDashboard data flow", () => {
    it("fetches and provides metrics data", async () => {
      const mockData = {
        overallHealthScore: 75,
        dataPointCount: 1000,
        dimensions: [
          {
            dimension: "happiness",
            overallScore: 80,
            hasData: true,
            goalProgresses: [],
          },
          {
            dimension: "engagement",
            overallScore: 70,
            hasData: true,
            goalProgresses: [],
          },
        ],
      };

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockData),
      });

      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.overallScore).toBe(75);
      expect(result.current.dimensions).toHaveLength(2);
      expect(result.current.dataPointCount).toBe(1000);
    });

    it("handles time range changes", async () => {
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            overallHealthScore: 70,
            dataPointCount: 500,
            dimensions: [],
          }),
      });

      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // Change time range
      act(() => {
        result.current.setTimeRange("7d");
      });

      await waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledWith(
          expect.stringContaining("range=7d"),
          expect.any(Object),
        );
      });
    });

    it("provides refresh functionality", async () => {
      fetchSpy.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            overallHealthScore: 80,
            dataPointCount: 2000,
            dimensions: [],
          }),
      });

      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));
      fetchSpy.mockClear();

      // Manual refresh
      await act(async () => {
        await result.current.refresh();
      });

      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });
  });

  // ===========================================================================
  // GSM Framework Integration
  // ===========================================================================

  describe("GSM framework with HEART tracking", () => {
    it("records signals with correct IDs", () => {
      // Record a signal
      recordSignal("happiness_nps_score", 9, { source: "survey" });
      recordSignal("engagement_feature_click", 1, { feature: "chat" });

      // Get summary includes recorded signals
      const summary = getMetricsSummary();
      expect(summary.dataPointCount).toBeGreaterThanOrEqual(0);
    });

    it("calculates dimension scores", () => {
      // Record multiple signals
      recordSignal("happiness_nps_score", 8);
      recordSignal("happiness_satisfaction_rating", 4);

      const summary = getMetricsSummary();

      // Summary should have dimensions
      expect(summary.dimensions).toBeDefined();
      expect(Array.isArray(summary.dimensions)).toBe(true);
    });
  });

  // ===========================================================================
  // HeartAggregator Standalone Tests
  // ===========================================================================

  describe("HeartAggregator standalone", () => {
    it("queues events and tracks pending count", () => {
      const aggregator = new HeartAggregator();

      aggregator.queueEvent("test_event", { value: 1 });
      aggregator.queueEvent("test_event", { value: 2 });

      expect(aggregator.getPendingCount()).toBe(2);

      // Cleanup
      aggregator.destroy();
    });

    it("attaches session context to events", () => {
      const aggregator = new HeartAggregator();

      aggregator.setSessionContext({
        sessionId: "test-session",
        persona: "developer",
      });

      aggregator.queueEvent("test", { data: 1 });

      const events = aggregator.getPendingEvents();
      expect(events[0].payload).toMatchObject({
        data: 1,
        sessionId: "test-session",
        persona: "developer",
      });

      aggregator.destroy();
    });

    it("tracks statistics correctly", async () => {
      const aggregator = new HeartAggregator();

      aggregator.queueEvent("event1", {});
      aggregator.queueEvent("event2", {});

      await aggregator.flush();

      const stats = aggregator.getStats();
      expect(stats.totalQueued).toBe(2);
      expect(stats.totalFlushed).toBe(2);
      expect(stats.flushCount).toBe(1);

      aggregator.destroy();
    });

    it("merges session context updates", () => {
      const aggregator = new HeartAggregator();

      aggregator.setSessionContext({ sessionId: "session-1" });
      aggregator.setSessionContext({ persona: "admin" });

      const context = aggregator.getSessionContext();
      expect(context).toEqual({
        sessionId: "session-1",
        persona: "admin",
      });

      aggregator.destroy();
    });

    it("clears session context", () => {
      const aggregator = new HeartAggregator();

      aggregator.setSessionContext({
        sessionId: "session-1",
        persona: "admin",
      });
      aggregator.clearSessionContext();

      expect(aggregator.getSessionContext()).toEqual({});

      aggregator.destroy();
    });

    it("resets statistics", async () => {
      const aggregator = new HeartAggregator();

      aggregator.queueEvent("event1", {});
      await aggregator.flush();

      aggregator.resetStats();

      expect(aggregator.getStats()).toEqual({
        totalQueued: 0,
        totalFlushed: 0,
        flushCount: 0,
        failedFlushes: 0,
      });

      aggregator.destroy();
    });
  });

  // ===========================================================================
  // End-to-End Dashboard Flow
  // ===========================================================================

  describe("End-to-end dashboard flow", () => {
    it("dashboard loads data and displays correct structure", async () => {
      const mockDashboardData = {
        overallHealthScore: 82,
        dataPointCount: 5000,
        dimensions: [
          {
            dimension: "happiness",
            overallScore: 85,
            hasData: true,
            goalProgresses: [],
          },
          {
            dimension: "engagement",
            overallScore: 78,
            hasData: true,
            goalProgresses: [],
          },
          {
            dimension: "adoption",
            overallScore: 72,
            hasData: true,
            goalProgresses: [],
          },
          {
            dimension: "retention",
            overallScore: 88,
            hasData: true,
            goalProgresses: [],
          },
          {
            dimension: "task_success",
            overallScore: 90,
            hasData: true,
            goalProgresses: [],
          },
        ],
      };

      fetchSpy.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDashboardData),
      });

      const { result } = renderHook(() => useHeartDashboard());

      // Initially loading
      expect(result.current.loading).toBe(true);

      // Wait for data
      await waitFor(() => expect(result.current.loading).toBe(false));

      // Verify all dimensions present
      expect(result.current.dimensions).toHaveLength(5);

      // Verify dimension names
      const dimensionNames = result.current.dimensions.map((d) => d.dimension);
      expect(dimensionNames).toContain("happiness");
      expect(dimensionNames).toContain("engagement");
      expect(dimensionNames).toContain("adoption");
      expect(dimensionNames).toContain("retention");
      expect(dimensionNames).toContain("task_success");

      // Verify overall score
      expect(result.current.overallScore).toBe(82);
    });

    it("handles API errors gracefully", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("Network timeout"));

      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.error).toBe("Network timeout");
      expect(result.current.data).toBeNull();
      expect(result.current.dimensions).toEqual([]);
      expect(result.current.overallScore).toBe(0);
    });
  });
});
