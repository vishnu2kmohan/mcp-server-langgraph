/**
 * WebSocket Health Alerts Hook Tests
 *
 * TDD tests for the useWebSocketHealthAlerts hook that monitors
 * WebSocket connection health and triggers alerts when thresholds are exceeded.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useWebSocketHealthAlerts } from "./useWebSocketHealthAlerts";
import { websocketTelemetry } from "../utils/websocketTelemetry";
import type { AggregatedWebSocketMetrics } from "../utils/websocketTelemetry";

// =============================================================================
// Mock Data
// =============================================================================

function createMockMetrics(
  overrides: Partial<AggregatedWebSocketMetrics> = {},
): AggregatedWebSocketMetrics {
  return {
    totalConnections: 5,
    totalReconnectionAttempts: 10,
    totalSuccessfulReconnections: 8,
    avgSuccessRate: 80,
    failuresByReason: {},
    byEndpoint: {},
    ...overrides,
  };
}

// =============================================================================
// Tests
// =============================================================================

describe("useWebSocketHealthAlerts", () => {
  beforeEach(() => {
    websocketTelemetry.reset();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("initialization", () => {
    it("should return initial state with no alerts", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 95 }),
      );

      const { result } = renderHook(() => useWebSocketHealthAlerts());

      expect(result.current.alerts).toEqual([]);
      expect(result.current.hasActiveAlerts).toBe(false);
    });

    it("should return health status", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 85 }),
      );

      const { result } = renderHook(() => useWebSocketHealthAlerts());

      expect(result.current.healthStatus).toBe("warning");
    });
  });

  describe("success rate alerts", () => {
    it("should trigger critical alert when avgSuccessRate < 70", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 50 }),
      );

      const { result } = renderHook(() => useWebSocketHealthAlerts());

      expect(result.current.hasActiveAlerts).toBe(true);
      expect(result.current.alerts).toContainEqual(
        expect.objectContaining({
          type: "critical",
          reason: "low_success_rate",
        }),
      );
    });

    it("should trigger warning alert when 70 <= avgSuccessRate < 80", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 72 }),
      );

      const { result } = renderHook(() => useWebSocketHealthAlerts());

      expect(result.current.alerts).toContainEqual(
        expect.objectContaining({
          type: "warning",
          reason: "degraded_success_rate",
        }),
      );
    });

    it("should not trigger alerts when avgSuccessRate >= 80", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 90 }),
      );

      const { result } = renderHook(() => useWebSocketHealthAlerts());

      expect(
        result.current.alerts.filter((a) => a.reason.includes("success_rate")),
      ).toHaveLength(0);
    });
  });

  describe("reconnection rate alerts", () => {
    it("should trigger alert when reconnection rate exceeds threshold", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({
          totalConnections: 2,
          totalReconnectionAttempts: 20, // 10 per connection - high rate
        }),
      );

      const { result } = renderHook(() =>
        useWebSocketHealthAlerts({ reconnectionThreshold: 5 }),
      );

      expect(result.current.alerts).toContainEqual(
        expect.objectContaining({
          type: "warning",
          reason: "high_reconnection_rate",
        }),
      );
    });

    it("should not alert when reconnection rate is below threshold", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({
          totalConnections: 5,
          totalReconnectionAttempts: 10, // 2 per connection - normal
        }),
      );

      const { result } = renderHook(() =>
        useWebSocketHealthAlerts({ reconnectionThreshold: 5 }),
      );

      expect(
        result.current.alerts.filter(
          (a) => a.reason === "high_reconnection_rate",
        ),
      ).toHaveLength(0);
    });
  });

  describe("failure pattern alerts", () => {
    it("should trigger alert for recurring failure patterns", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({
          failuresByReason: {
            auth_failed: 5,
            timeout: 2,
          },
        }),
      );

      const { result } = renderHook(() =>
        useWebSocketHealthAlerts({ failurePatternThreshold: 3 }),
      );

      expect(result.current.alerts).toContainEqual(
        expect.objectContaining({
          type: "warning",
          reason: "recurring_failure_pattern",
          details: expect.objectContaining({ pattern: "auth_failed" }),
        }),
      );
    });
  });

  describe("alert callbacks", () => {
    it("should call onAlert callback when new alert is triggered", () => {
      const onAlert = vi.fn();

      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 50 }),
      );

      renderHook(() => useWebSocketHealthAlerts({ onAlert }));

      expect(onAlert).toHaveBeenCalled();
    });

    it("should not call onAlert for same alert type repeatedly", () => {
      const onAlert = vi.fn();

      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 50 }),
      );

      const { rerender } = renderHook(() =>
        useWebSocketHealthAlerts({ onAlert, checkInterval: 1000 }),
      );

      // Initial call
      expect(onAlert).toHaveBeenCalledTimes(1);

      // Advance time and rerender - same alert shouldn't trigger callback again
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      rerender();

      // Should still be 1 (no duplicate alerts)
      expect(onAlert).toHaveBeenCalledTimes(1);
    });
  });

  describe("alert dismissal", () => {
    it("should allow dismissing alerts", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({ avgSuccessRate: 50 }),
      );

      const { result } = renderHook(() => useWebSocketHealthAlerts());

      expect(result.current.alerts.length).toBeGreaterThan(0);

      const alertId = result.current.alerts[0].id;

      act(() => {
        result.current.dismissAlert(alertId);
      });

      expect(
        result.current.alerts.find((a) => a.id === alertId),
      ).toBeUndefined();
    });

    it("should allow clearing all alerts", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockMetrics({
          avgSuccessRate: 50,
          totalReconnectionAttempts: 100,
          totalConnections: 2,
        }),
      );

      const { result } = renderHook(() =>
        useWebSocketHealthAlerts({ reconnectionThreshold: 5 }),
      );

      expect(result.current.alerts.length).toBeGreaterThan(0);

      act(() => {
        result.current.clearAllAlerts();
      });

      expect(result.current.alerts).toHaveLength(0);
    });
  });

  describe("periodic checking", () => {
    it("should check metrics on specified interval", () => {
      const getMetricsSpy = vi
        .spyOn(websocketTelemetry, "getAggregatedMetrics")
        .mockReturnValue(createMockMetrics({ avgSuccessRate: 95 }));

      renderHook(() => useWebSocketHealthAlerts({ checkInterval: 2000 }));

      // Initial check (useState initializer + useEffect check)
      const initialCallCount = getMetricsSpy.mock.calls.length;
      expect(initialCallCount).toBeGreaterThanOrEqual(1);

      // Advance timer
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      // Should have additional call after interval
      expect(getMetricsSpy).toHaveBeenCalledTimes(initialCallCount + 1);

      // Advance again
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      // Another call
      expect(getMetricsSpy).toHaveBeenCalledTimes(initialCallCount + 2);
    });
  });
});
