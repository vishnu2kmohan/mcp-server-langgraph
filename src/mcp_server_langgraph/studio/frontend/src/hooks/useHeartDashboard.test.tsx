/**
 * useHeartDashboard Hook Tests
 *
 * TDD - Sprint 4 - Phase 3.3: HEART Metrics Analytics Dashboard
 *
 * Tests for the dashboard data fetching hook:
 * - Time range selection
 * - Data fetching and caching
 * - Loading and error states
 * - Dimension extraction
 * - Auto-refresh functionality
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useHeartDashboard } from "./useHeartDashboard";
import type { MetricsSummary } from "../analytics/gsm";

// =============================================================================
// Test Setup
// =============================================================================

const mockMetricsData: MetricsSummary = {
  overallHealthScore: 78,
  dataPointCount: 15000,
  dimensions: [
    {
      dimension: "happiness",
      overallScore: 82,
      hasData: true,
      goalProgresses: [],
    },
    {
      dimension: "engagement",
      overallScore: 75,
      hasData: true,
      goalProgresses: [],
    },
    {
      dimension: "adoption",
      overallScore: 68,
      hasData: true,
      goalProgresses: [],
    },
    {
      dimension: "retention",
      overallScore: 80,
      hasData: true,
      goalProgresses: [],
    },
    {
      dimension: "task_success",
      overallScore: 85,
      hasData: true,
      goalProgresses: [],
    },
  ],
};

describe("useHeartDashboard", () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockMetricsData),
    });
    vi.stubGlobal("fetch", fetchSpy);

    // Mock localStorage for auth token
    vi.stubGlobal("localStorage", {
      getItem: vi.fn().mockReturnValue("test-token"),
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
  // Initial State Tests
  // ===========================================================================

  describe("initial state", () => {
    it("starts with loading state", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      // Initially loading
      expect(result.current.loading).toBe(true);
      expect(result.current.error).toBeNull();
      expect(result.current.data).toBeNull();

      // Wait for fetch to complete
      await waitFor(() => expect(result.current.loading).toBe(false));
    });

    it("uses default time range of 30d", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      expect(result.current.timeRange).toBe("30d");
      await waitFor(() => expect(result.current.loading).toBe(false));
    });

    it("fetches data on mount", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/v1/metrics/heart/aggregate?range=30d",
        expect.objectContaining({
          credentials: "include",
        }),
      );
    });
  });

  // ===========================================================================
  // Data Fetching Tests
  // ===========================================================================

  describe("data fetching", () => {
    it("sets data after successful fetch", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.data).toEqual(mockMetricsData);
      expect(result.current.error).toBeNull();
    });

    it("includes auth token in request headers", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(fetchSpy).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        }),
      );
    });

    it("handles fetch errors gracefully", async () => {
      fetchSpy.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toBe("Network error");
      expect(result.current.data).toBeNull();
    });

    it("handles non-OK responses", async () => {
      fetchSpy.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });

      expect(result.current.error).toContain("500");
    });
  });

  // ===========================================================================
  // Time Range Tests
  // ===========================================================================

  describe("time range", () => {
    it("allows changing time range", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      await act(async () => {
        result.current.setTimeRange("7d");
      });

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.timeRange).toBe("7d");
    });

    it("refetches data when time range changes", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));
      fetchSpy.mockClear();

      act(() => {
        result.current.setTimeRange("90d");
      });

      await waitFor(() => {
        expect(fetchSpy).toHaveBeenCalledWith(
          "/api/v1/metrics/heart/aggregate?range=90d",
          expect.any(Object),
        );
      });
    });

    it("supports 7d, 30d, and 90d time ranges", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // Test 7d
      await act(async () => {
        result.current.setTimeRange("7d");
      });
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.timeRange).toBe("7d");

      // Test 90d
      await act(async () => {
        result.current.setTimeRange("90d");
      });
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.timeRange).toBe("90d");

      // Test 30d (back to default)
      await act(async () => {
        result.current.setTimeRange("30d");
      });
      await waitFor(() => expect(result.current.loading).toBe(false));
      expect(result.current.timeRange).toBe("30d");
    });
  });

  // ===========================================================================
  // Dimension Data Tests
  // ===========================================================================

  describe("dimension data", () => {
    it("provides dimensions array", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.dimensions).toHaveLength(5);
      expect(result.current.dimensions[0].dimension).toBe("happiness");
    });

    it("provides overall health score", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.overallScore).toBe(78);
    });

    it("provides data point count", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(result.current.dataPointCount).toBe(15000);
    });

    it("returns empty dimensions when loading", () => {
      // Use a never-resolving promise to keep it loading
      fetchSpy.mockImplementationOnce(() => new Promise(() => {}));

      const { result } = renderHook(() => useHeartDashboard());

      // Before fetch completes
      expect(result.current.dimensions).toEqual([]);
      expect(result.current.overallScore).toBe(0);
    });
  });

  // ===========================================================================
  // Refresh Tests
  // ===========================================================================

  describe("refresh", () => {
    it("provides manual refresh function", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(typeof result.current.refresh).toBe("function");
    });

    it("refetches data on manual refresh", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));
      fetchSpy.mockClear();

      await act(async () => {
        await result.current.refresh();
      });

      expect(fetchSpy).toHaveBeenCalledTimes(1);
    });

    it("sets loading state during refresh", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // Start refresh
      let refreshPromise: Promise<void>;
      act(() => {
        refreshPromise = result.current.refresh();
      });

      // Loading should be true during refresh
      expect(result.current.loading).toBe(true);

      await act(async () => {
        await refreshPromise;
      });
    });
  });

  // ===========================================================================
  // Auto-Refresh Tests
  // ===========================================================================

  describe("auto-refresh", () => {
    it("accepts autoRefreshMs option", async () => {
      // Verify the hook accepts the option without error
      const { result } = renderHook(() =>
        useHeartDashboard({ autoRefreshMs: 60000 }),
      );

      await waitFor(() => expect(result.current.loading).toBe(false));

      // Hook should work with autoRefreshMs
      expect(result.current.data).toEqual(mockMetricsData);
    });

    it("does not auto-refresh when autoRefreshMs not set", async () => {
      const { result } = renderHook(() => useHeartDashboard());

      await waitFor(() => expect(result.current.loading).toBe(false));

      // Initial fetch should have occurred
      expect(fetchSpy).toHaveBeenCalledTimes(1);

      // No additional fetches should happen without auto-refresh
      fetchSpy.mockClear();

      // Wait a bit to ensure no auto-refresh happens
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(fetchSpy).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Initial Time Range Option
  // ===========================================================================

  describe("options", () => {
    it("accepts initial time range", async () => {
      const { result } = renderHook(() =>
        useHeartDashboard({ initialTimeRange: "7d" }),
      );

      expect(result.current.timeRange).toBe("7d");

      await waitFor(() => expect(result.current.loading).toBe(false));

      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/v1/metrics/heart/aggregate?range=7d",
        expect.any(Object),
      );
    });
  });
});
