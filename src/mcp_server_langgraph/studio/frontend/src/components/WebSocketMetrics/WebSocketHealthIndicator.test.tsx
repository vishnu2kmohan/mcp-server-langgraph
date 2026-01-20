/**
 * WebSocket Health Indicator Tests
 *
 * TDD tests for the aggregate WebSocket health indicator component.
 * Tests the visual representation of WebSocket connection health.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import "@testing-library/jest-dom";
import { WebSocketHealthIndicator } from "./WebSocketHealthIndicator";
import { websocketTelemetry } from "../../utils/websocketTelemetry";
import type { AggregatedWebSocketMetrics } from "../../utils/websocketTelemetry";

// =============================================================================
// Mock Data Helpers
// =============================================================================

function createMockAggregatedMetrics(
  overrides: Partial<AggregatedWebSocketMetrics> = {},
): AggregatedWebSocketMetrics {
  return {
    totalConnections: 5,
    totalReconnectionAttempts: 10,
    totalSuccessfulReconnections: 8,
    avgSuccessRate: 80,
    failuresByReason: { timeout: 2 },
    byEndpoint: {},
    ...overrides,
  };
}

// =============================================================================
// Component Tests
// =============================================================================

describe("WebSocketHealthIndicator", () => {
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

  describe("rendering", () => {
    it("should render the health indicator component", () => {
      render(<WebSocketHealthIndicator />);

      expect(screen.getByTestId("ws-health-indicator")).toBeInTheDocument();
    });

    it("should display total connections count", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ totalConnections: 7 }),
      );

      render(<WebSocketHealthIndicator />);

      expect(screen.getByText(/7/)).toBeInTheDocument();
    });

    it("should show 'No connections' when totalConnections is 0", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({
          totalConnections: 0,
          avgSuccessRate: null,
        }),
      );

      render(<WebSocketHealthIndicator />);

      expect(screen.getByText(/no connections/i)).toBeInTheDocument();
    });
  });

  describe("health status colors", () => {
    it("should show green/healthy status when avgSuccessRate >= 90", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: 95 }),
      );

      render(<WebSocketHealthIndicator />);

      const indicator = screen.getByTestId("ws-health-status");
      expect(indicator).toHaveClass("bg-success-9");
    });

    it("should show yellow/warning status when 70 <= avgSuccessRate < 90", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: 75 }),
      );

      render(<WebSocketHealthIndicator />);

      const indicator = screen.getByTestId("ws-health-status");
      expect(indicator).toHaveClass("bg-warning-9");
    });

    it("should show red/critical status when avgSuccessRate < 70", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: 50 }),
      );

      render(<WebSocketHealthIndicator />);

      const indicator = screen.getByTestId("ws-health-status");
      expect(indicator).toHaveClass("bg-error-9");
    });

    it("should show gray/unknown status when avgSuccessRate is null", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: null }),
      );

      render(<WebSocketHealthIndicator />);

      const indicator = screen.getByTestId("ws-health-status");
      expect(indicator).toHaveClass("bg-neutral-4");
    });
  });

  describe("health status labels", () => {
    it("should display 'Healthy' label when avgSuccessRate >= 90", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: 92 }),
      );

      render(<WebSocketHealthIndicator showLabel />);

      expect(screen.getByText(/healthy/i)).toBeInTheDocument();
    });

    it("should display 'Warning' label when 70 <= avgSuccessRate < 90", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: 78 }),
      );

      render(<WebSocketHealthIndicator showLabel />);

      expect(screen.getByText(/warning/i)).toBeInTheDocument();
    });

    it("should display 'Critical' label when avgSuccessRate < 70", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: 45 }),
      );

      render(<WebSocketHealthIndicator showLabel />);

      expect(screen.getByText(/critical/i)).toBeInTheDocument();
    });
  });

  describe("tooltip/details", () => {
    it("should show success rate percentage in tooltip", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ avgSuccessRate: 85 }),
      );

      render(<WebSocketHealthIndicator showDetails />);

      expect(screen.getByText(/85%/)).toBeInTheDocument();
    });

    it("should show total reconnection attempts in details", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics({ totalReconnectionAttempts: 15 }),
      );

      render(<WebSocketHealthIndicator showDetails />);

      expect(screen.getByText(/15/)).toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("should render only the status dot in compact mode", () => {
      vi.spyOn(websocketTelemetry, "getAggregatedMetrics").mockReturnValue(
        createMockAggregatedMetrics(),
      );

      render(<WebSocketHealthIndicator compact />);

      const indicator = screen.getByTestId("ws-health-indicator");
      expect(indicator).toHaveClass("compact");
    });
  });

  describe("refresh behavior", () => {
    it("should update metrics on interval when autoRefresh is enabled", () => {
      const getMetricsSpy = vi
        .spyOn(websocketTelemetry, "getAggregatedMetrics")
        .mockReturnValue(createMockAggregatedMetrics({ avgSuccessRate: 90 }));

      render(<WebSocketHealthIndicator autoRefresh refreshInterval={5000} />);

      // Initial call
      expect(getMetricsSpy).toHaveBeenCalledTimes(1);

      // Advance timer
      vi.advanceTimersByTime(5000);

      // Should have been called again
      expect(getMetricsSpy).toHaveBeenCalledTimes(2);
    });
  });
});

// =============================================================================
// Hook Tests
// =============================================================================

describe("useWebSocketHealth hook", () => {
  // These tests will verify the hook logic separately
  it.todo("should return health status based on aggregated metrics");
  it.todo("should calculate reconnection rate per minute");
  it.todo("should trigger alert when reconnection rate exceeds threshold");
});
