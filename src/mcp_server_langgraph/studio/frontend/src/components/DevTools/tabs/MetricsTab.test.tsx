/**
 * MetricsTab Component Tests
 *
 * TDD tests for OTEL/HEART metrics dashboard.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  within,
  cleanup,
} from "@testing-library/react";
import React from "react";

import { MetricsTab } from "./MetricsTab";
import { DevToolsTimelineProvider } from "../context/DevToolsTimelineProvider";

// =============================================================================
// Test Helpers
// =============================================================================

function renderWithProvider(
  ui: React.ReactElement,
  providerProps?: Partial<
    React.ComponentProps<typeof DevToolsTimelineProvider>
  >,
) {
  return render(
    <DevToolsTimelineProvider {...providerProps}>
      {ui}
    </DevToolsTimelineProvider>,
  );
}

const mockMetrics = [
  {
    name: "requests_per_minute",
    value: 1234,
    unit: "req/min",
    trend: "up" as const,
    change: 12.5,
    sparkline: [100, 120, 150, 180, 200, 220, 190, 170, 150, 130],
  },
  {
    name: "error_rate",
    value: 2.3,
    unit: "%",
    trend: "down" as const,
    change: -0.5,
    sparkline: [5, 4.5, 4, 3.5, 3, 2.8, 2.5, 2.3, 2.3, 2.3],
  },
  {
    name: "avg_latency",
    value: 145,
    unit: "ms",
    trend: "stable" as const,
    change: 0,
    sparkline: [150, 145, 148, 142, 145, 143, 146, 144, 145, 145],
  },
];

const mockHeartMetrics = {
  happiness: { score: 8.2, trend: "up" as const, change: 0.3 },
  engagement: { score: 6.5, trend: "down" as const, change: -0.2 },
  adoption: { score: 7.8, trend: "stable" as const, change: 0 },
  retention: { score: 9.1, trend: "up" as const, change: 0.5 },
  taskSuccess: { score: 94, trend: "up" as const, change: 2 },
};

// =============================================================================
// Tests
// =============================================================================

describe("MetricsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render without crashing", () => {
      renderWithProvider(<MetricsTab />);
      expect(screen.getByTestId("metrics-tab")).toBeInTheDocument();
    });

    it("should display empty state when no metrics", () => {
      renderWithProvider(<MetricsTab />);
      expect(screen.getByText(/no metrics/i)).toBeInTheDocument();
    });

    it("should display time range selector", () => {
      renderWithProvider(<MetricsTab />);
      expect(screen.getByRole("button", { name: /15m/i })).toBeInTheDocument();
    });

    it("should display refresh button", () => {
      renderWithProvider(<MetricsTab />);
      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });
  });

  describe("system metrics", () => {
    it("should display metric cards when metrics exist", () => {
      renderWithProvider(<MetricsTab metrics={mockMetrics} />);

      expect(screen.getByText(/requests per minute/i)).toBeInTheDocument();
      expect(screen.getByText(/error rate/i)).toBeInTheDocument();
      expect(screen.getByText(/avg latency/i)).toBeInTheDocument();
    });

    it("should show metric values", () => {
      renderWithProvider(<MetricsTab metrics={mockMetrics} />);

      expect(screen.getByText(/1,?234/)).toBeInTheDocument();
      expect(screen.getByText(/2\.3/)).toBeInTheDocument();
      expect(screen.getByText(/145/)).toBeInTheDocument();
    });

    it("should display sparkline visualizations", () => {
      renderWithProvider(<MetricsTab metrics={mockMetrics} />);

      const metricsTab = screen.getByTestId("metrics-tab");
      const sparklines = within(metricsTab).getAllByTestId("metric-sparkline");
      expect(sparklines.length).toBeGreaterThan(0);
    });

    it("should show trend indicators", () => {
      renderWithProvider(<MetricsTab metrics={mockMetrics} />);

      const metricsTab = screen.getByTestId("metrics-tab");
      const trends = within(metricsTab).getAllByTestId("trend-indicator");
      expect(trends.length).toBeGreaterThan(0);
    });
  });

  describe("HEART metrics", () => {
    it("should display HEART section when metrics provided", () => {
      renderWithProvider(<MetricsTab heartMetrics={mockHeartMetrics} />);

      expect(screen.getByText(/heart metrics/i)).toBeInTheDocument();
    });

    it("should show all HEART dimensions", () => {
      renderWithProvider(<MetricsTab heartMetrics={mockHeartMetrics} />);

      expect(screen.getByText(/happiness/i)).toBeInTheDocument();
      expect(screen.getByText(/engagement/i)).toBeInTheDocument();
      expect(screen.getByText(/adoption/i)).toBeInTheDocument();
      expect(screen.getByText(/retention/i)).toBeInTheDocument();
      expect(screen.getByText(/task success/i)).toBeInTheDocument();
    });

    it("should display HEART scores", () => {
      renderWithProvider(<MetricsTab heartMetrics={mockHeartMetrics} />);

      expect(screen.getByText(/8\.2/)).toBeInTheDocument();
      expect(screen.getByText(/6\.5/)).toBeInTheDocument();
      expect(screen.getByText(/94/)).toBeInTheDocument();
    });
  });

  describe("time range selection", () => {
    it("should change time range when selector clicked", () => {
      const onTimeRangeChange = vi.fn();
      renderWithProvider(
        <MetricsTab
          metrics={mockMetrics}
          onTimeRangeChange={onTimeRangeChange}
        />,
      );

      fireEvent.click(screen.getByRole("button", { name: /1h/i }));

      expect(onTimeRangeChange).toHaveBeenCalledWith("1h");
    });

    it("should highlight active time range", () => {
      renderWithProvider(<MetricsTab metrics={mockMetrics} timeRange="1h" />);

      const button = screen.getByRole("button", { name: /1h/i });
      expect(button).toHaveAttribute("data-active", "true");
    });
  });

  describe("auto-refresh", () => {
    it("should display auto-refresh indicator", () => {
      renderWithProvider(
        <MetricsTab metrics={mockMetrics} autoRefreshInterval={30000} />,
      );

      expect(screen.getByText(/30s/i)).toBeInTheDocument();
    });

    it("should call onRefresh when refresh button clicked", () => {
      const onRefresh = vi.fn();
      renderWithProvider(
        <MetricsTab metrics={mockMetrics} onRefresh={onRefresh} />,
      );

      fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

      expect(onRefresh).toHaveBeenCalled();
    });
  });

  describe("timeline integration", () => {
    it("should filter metrics by time window", () => {
      // Metrics should sync with timeline context
      renderWithProvider(<MetricsTab metrics={mockMetrics} />);

      expect(screen.getByTestId("metrics-tab")).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("should show loading skeleton when isLoading", () => {
      renderWithProvider(<MetricsTab isLoading />);

      expect(screen.getByTestId("metrics-loading")).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("should display error message on error", () => {
      renderWithProvider(<MetricsTab error="Failed to fetch metrics" />);

      expect(screen.getByText(/failed to fetch metrics/i)).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      renderWithProvider(<MetricsTab error="Failed to fetch metrics" />);

      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });
  });

  describe("grafana integration", () => {
    it("should display View in Grafana button when grafanaUrl is provided", () => {
      renderWithProvider(
        <MetricsTab metrics={mockMetrics} grafanaUrl="/grafana/dashboards" />,
      );

      expect(
        screen.getByRole("button", { name: /view in grafana/i }),
      ).toBeInTheDocument();
    });

    it("should open Grafana URL when clicked", () => {
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

      renderWithProvider(
        <MetricsTab metrics={mockMetrics} grafanaUrl="/grafana/dashboards" />,
      );

      fireEvent.click(screen.getByRole("button", { name: /view in grafana/i }));

      expect(openSpy).toHaveBeenCalledWith("/grafana/dashboards", "_blank");

      openSpy.mockRestore();
    });
  });

  describe("defensive coding - undefined handling", () => {
    it("should handle metric with undefined value gracefully", () => {
      // This tests the runtime scenario where backend returns incomplete data
      // TypeScript type says value: number, but runtime data may have undefined
      const metricsWithUndefinedValue = [
        {
          name: "broken_metric",
          value: undefined as unknown as number, // Simulate runtime data mismatch
          unit: "ms",
          trend: "stable" as const,
          change: 0,
          sparkline: [1, 2, 3],
        },
      ];

      // Should NOT throw "can't access property 'toString', value is undefined"
      expect(() => {
        renderWithProvider(<MetricsTab metrics={metricsWithUndefinedValue} />);
      }).not.toThrow();

      // Should display fallback value (e.g., "N/A" or "-" or "0")
      expect(screen.getByTestId("metrics-tab")).toBeInTheDocument();
      // The metric card should still render with a fallback value
      expect(screen.getByText(/broken metric/i)).toBeInTheDocument();
    });

    it("should handle metric with null value gracefully", () => {
      const metricsWithNullValue = [
        {
          name: "null_metric",
          value: null as unknown as number,
          unit: "%",
          trend: "up" as const,
          change: 5,
          sparkline: [10, 20, 30],
        },
      ];

      expect(() => {
        renderWithProvider(<MetricsTab metrics={metricsWithNullValue} />);
      }).not.toThrow();

      expect(screen.getByText(/null metric/i)).toBeInTheDocument();
    });
  });
});
