/**
 * AICacheMetricsDashboard Component Tests
 *
 * TDD tests for the AI Cache Metrics Dashboard component.
 * Tests cache hit/miss ratios, error rates, and per-feature breakdowns.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  AICacheMetricsDashboard,
  type AICacheMetricsDashboardProps,
} from "./AICacheMetricsDashboard";

// =============================================================================
// Test Fixtures
// =============================================================================

const mockMetricsSnapshot = {
  requestCount: 100,
  errorCount: 5,
  cacheHits: 80,
  cacheMisses: 20,
  averageLatency: 150,
  errorRate: 0.05,
  cacheHitRatio: 0.8,
  timestamp: Date.now(),
};

const mockFeatureMetrics = {
  nav_prediction: {
    requestCount: 40,
    errorCount: 2,
    averageLatency: 120,
    totalLatency: 4800,
  },
  contextual_help: {
    requestCount: 30,
    errorCount: 1,
    averageLatency: 180,
    totalLatency: 5400,
  },
  risk_assessment: {
    requestCount: 30,
    errorCount: 2,
    averageLatency: 160,
    totalLatency: 4800,
  },
};

const defaultProps: AICacheMetricsDashboardProps = {
  snapshot: mockMetricsSnapshot,
  featureMetrics: mockFeatureMetrics,
};

// =============================================================================
// Test Suite
// =============================================================================

describe("AICacheMetricsDashboard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });
  describe("Rendering", () => {
    it("renders dashboard with testid", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(
        screen.getByTestId("ai-cache-metrics-dashboard"),
      ).toBeInTheDocument();
    });

    it("displays dashboard title", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("AI Cache Metrics")).toBeInTheDocument();
    });

    it("displays cache hit ratio as percentage", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("80.0%")).toBeInTheDocument();
      expect(screen.getByText("Cache Hit Ratio")).toBeInTheDocument();
    });

    it("displays total cache hits count", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("80")).toBeInTheDocument();
      expect(screen.getByText("Cache Hits")).toBeInTheDocument();
    });

    it("displays total cache misses count", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("20")).toBeInTheDocument();
      expect(screen.getByText("Cache Misses")).toBeInTheDocument();
    });

    it("displays error rate as percentage", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("5.0%")).toBeInTheDocument();
      expect(screen.getByText("Error Rate")).toBeInTheDocument();
    });

    it("displays average latency in milliseconds", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("150ms")).toBeInTheDocument();
      expect(screen.getByText("Avg Latency")).toBeInTheDocument();
    });

    it("displays request count", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("100")).toBeInTheDocument();
      expect(screen.getByText("Total Requests")).toBeInTheDocument();
    });
  });

  describe("Cache Hit Ratio Progress Bar", () => {
    it("renders cache hit ratio progress bar", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      const progressBar = screen.getByRole("progressbar", {
        name: /cache hit ratio/i,
      });
      expect(progressBar).toBeInTheDocument();
      expect(progressBar).toHaveAttribute("aria-valuenow", "80");
    });

    it("shows green color for high cache hit ratio (>= 70%)", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      const progressBar = screen.getByTestId("cache-hit-progress-bar");
      expect(progressBar).toHaveClass("bg-success-9");
    });

    it("shows yellow color for medium cache hit ratio (50-70%)", () => {
      const lowHitSnapshot = { ...mockMetricsSnapshot, cacheHitRatio: 0.6 };
      render(
        <AICacheMetricsDashboard {...defaultProps} snapshot={lowHitSnapshot} />,
      );
      const progressBar = screen.getByTestId("cache-hit-progress-bar");
      expect(progressBar).toHaveClass("bg-warning-9");
    });

    it("shows red color for low cache hit ratio (< 50%)", () => {
      const veryLowHitSnapshot = { ...mockMetricsSnapshot, cacheHitRatio: 0.3 };
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          snapshot={veryLowHitSnapshot}
        />,
      );
      const progressBar = screen.getByTestId("cache-hit-progress-bar");
      expect(progressBar).toHaveClass("bg-error-9");
    });
  });

  describe("Feature Breakdown", () => {
    it("renders feature breakdown section", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("Per-Feature Breakdown")).toBeInTheDocument();
    });

    it("displays each feature name", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(screen.getByText("nav_prediction")).toBeInTheDocument();
      expect(screen.getByText("contextual_help")).toBeInTheDocument();
      expect(screen.getByText("risk_assessment")).toBeInTheDocument();
    });

    it("displays request count for each feature", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      // Check that request counts are displayed
      expect(
        screen.getByTestId("feature-nav_prediction-requests"),
      ).toHaveTextContent("40");
      expect(
        screen.getByTestId("feature-contextual_help-requests"),
      ).toHaveTextContent("30");
    });

    it("displays average latency for each feature", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(
        screen.getByTestId("feature-nav_prediction-latency"),
      ).toHaveTextContent("120ms");
      expect(
        screen.getByTestId("feature-contextual_help-latency"),
      ).toHaveTextContent("180ms");
    });
  });

  describe("Compact Mode", () => {
    it("renders in compact mode when prop is set", () => {
      render(<AICacheMetricsDashboard {...defaultProps} compact />);
      const dashboard = screen.getByTestId("ai-cache-metrics-dashboard");
      expect(dashboard).toHaveAttribute("data-compact", "true");
    });

    it("hides feature breakdown in compact mode", () => {
      render(<AICacheMetricsDashboard {...defaultProps} compact />);
      expect(
        screen.queryByText("Per-Feature Breakdown"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Refresh Button", () => {
    it("renders refresh button", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });

    it("calls onRefresh when clicked", () => {
      const onRefresh = vi.fn();
      render(
        <AICacheMetricsDashboard {...defaultProps} onRefresh={onRefresh} />,
      );

      fireEvent.click(screen.getByRole("button", { name: /refresh/i }));
      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe("Empty State", () => {
    it("shows empty state when no data", () => {
      const emptySnapshot = {
        ...mockMetricsSnapshot,
        requestCount: 0,
        cacheHits: 0,
        cacheMisses: 0,
        cacheHitRatio: 0,
      };
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          snapshot={emptySnapshot}
          featureMetrics={{}}
        />,
      );
      expect(screen.getByText(/no cache data/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("shows loading indicator when isLoading is true", () => {
      render(<AICacheMetricsDashboard {...defaultProps} isLoading />);
      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has accessible progress bar", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      const progressBar = screen.getByRole("progressbar");
      expect(progressBar).toHaveAttribute("aria-valuemin", "0");
      expect(progressBar).toHaveAttribute("aria-valuemax", "100");
    });

    it("refresh button is keyboard accessible", () => {
      const onRefresh = vi.fn();
      render(
        <AICacheMetricsDashboard {...defaultProps} onRefresh={onRefresh} />,
      );

      const button = screen.getByRole("button", { name: /refresh/i });
      button.focus();
      expect(document.activeElement).toBe(button);
    });
  });

  describe("Color Coding", () => {
    it("shows green error rate when below 5%", () => {
      const lowErrorSnapshot = { ...mockMetricsSnapshot, errorRate: 0.02 };
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          snapshot={lowErrorSnapshot}
        />,
      );
      const errorRateElement = screen.getByTestId("error-rate-value");
      expect(errorRateElement).toHaveClass("text-success-10");
    });

    it("shows yellow error rate between 5-10%", () => {
      const medErrorSnapshot = { ...mockMetricsSnapshot, errorRate: 0.07 };
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          snapshot={medErrorSnapshot}
        />,
      );
      const errorRateElement = screen.getByTestId("error-rate-value");
      expect(errorRateElement).toHaveClass("text-warning-9");
    });

    it("shows red error rate above 10%", () => {
      const highErrorSnapshot = { ...mockMetricsSnapshot, errorRate: 0.15 };
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          snapshot={highErrorSnapshot}
        />,
      );
      const errorRateElement = screen.getByTestId("error-rate-value");
      expect(errorRateElement).toHaveClass("text-error-10");
    });
  });

  describe("Tiered Cache Stats (L1/L2)", () => {
    const mockTieredCacheStats = {
      l1Hits: 50,
      l2Hits: 30,
      misses: 20,
      age: 45000, // 45 seconds
    };

    it("displays L1/L2 breakdown section when tieredCacheStats is provided", () => {
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={mockTieredCacheStats}
        />,
      );
      expect(screen.getByText("Tiered Cache Breakdown")).toBeInTheDocument();
    });

    it("does not show tiered breakdown when tieredCacheStats is not provided", () => {
      render(<AICacheMetricsDashboard {...defaultProps} />);
      expect(
        screen.queryByText("Tiered Cache Breakdown"),
      ).not.toBeInTheDocument();
    });

    it("displays L1 (in-memory) hits count", () => {
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={mockTieredCacheStats}
        />,
      );
      expect(screen.getByTestId("l1-hits-value")).toHaveTextContent("50");
      expect(screen.getByText(/L1.*Memory/i)).toBeInTheDocument();
    });

    it("displays L2 (sessionStorage) hits count", () => {
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={mockTieredCacheStats}
        />,
      );
      expect(screen.getByTestId("l2-hits-value")).toHaveTextContent("30");
      expect(screen.getByText(/L2.*Session/i)).toBeInTheDocument();
    });

    it("displays cache misses count", () => {
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={mockTieredCacheStats}
        />,
      );
      expect(screen.getByTestId("tiered-misses-value")).toHaveTextContent("20");
    });

    it("displays cache age in human-readable format", () => {
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={mockTieredCacheStats}
        />,
      );
      expect(screen.getByTestId("cache-age-value")).toHaveTextContent("45s");
    });

    it("displays cache age in minutes when over 60 seconds", () => {
      const oldCache = { ...mockTieredCacheStats, age: 180000 }; // 3 minutes
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={oldCache}
        />,
      );
      expect(screen.getByTestId("cache-age-value")).toHaveTextContent("3m");
    });

    it("shows tiered cache progress bar visualization", () => {
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={mockTieredCacheStats}
        />,
      );
      expect(screen.getByTestId("tiered-cache-bar")).toBeInTheDocument();
    });

    it("hides tiered breakdown in compact mode", () => {
      render(
        <AICacheMetricsDashboard
          {...defaultProps}
          tieredCacheStats={mockTieredCacheStats}
          compact
        />,
      );
      expect(
        screen.queryByText("Tiered Cache Breakdown"),
      ).not.toBeInTheDocument();
    });
  });
});
