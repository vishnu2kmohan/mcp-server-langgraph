/**
 * WebSocketMetricsPanel Test
 *
 * Tests for the WebSocket metrics observability panel.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import { WebSocketMetricsPanel } from "./WebSocketMetricsPanel";
import { websocketTelemetry } from "../../utils/websocketTelemetry";
import { createInitialReconnectionMetrics } from "../../types/websocket-metrics";

describe("WebSocketMetricsPanel", () => {
  beforeEach(() => {
    websocketTelemetry.reset();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    websocketTelemetry.reset();
  });

  it("should render empty state when no connections", () => {
    render(<WebSocketMetricsPanel />);

    expect(screen.getByTestId("ws-metrics-panel")).toBeInTheDocument();
    expect(screen.getByText("No WebSocket connections")).toBeInTheDocument();
  });

  it("should render connection metrics when connections exist", () => {
    // Add some test metrics
    const metrics = createInitialReconnectionMetrics();
    metrics.totalAttempts = 5;
    metrics.totalReconnections = 4;
    metrics.successRate = 80;
    websocketTelemetry.trackReconnectionMetrics("notifications", metrics);

    render(<WebSocketMetricsPanel />);

    expect(screen.getByTestId("ws-metrics-panel")).toBeInTheDocument();
    expect(screen.getByText("notifications")).toBeInTheDocument();
    // Check that metrics are displayed (appears in summary cards and table)
    expect(screen.getAllByText("5").length).toBeGreaterThan(0);
    // 80% appears in Avg Success Rate card and in table status badge
    expect(screen.getAllByText(/80/).length).toBeGreaterThan(0);
  });

  it("should display aggregated metrics header", () => {
    const metrics = createInitialReconnectionMetrics();
    metrics.totalAttempts = 10;
    metrics.totalReconnections = 8;
    websocketTelemetry.trackReconnectionMetrics("notifications", metrics);
    websocketTelemetry.trackReconnectionMetrics("alerts", metrics);

    render(<WebSocketMetricsPanel />);

    expect(screen.getByText("Total Connections")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument(); // 2 connections
  });

  it("should display failure breakdown when failures exist", () => {
    const metrics = createInitialReconnectionMetrics();
    metrics.totalAttempts = 10;
    metrics.totalReconnections = 7;
    metrics.failuresByReason.network_error = 2;
    metrics.failuresByReason.token_expired = 1;
    websocketTelemetry.trackReconnectionMetrics("notifications", metrics);

    render(<WebSocketMetricsPanel />);

    expect(screen.getByText("network_error")).toBeInTheDocument();
    expect(screen.getByText("token_expired")).toBeInTheDocument();
  });

  it("should respect refresh interval", async () => {
    vi.useFakeTimers();

    render(<WebSocketMetricsPanel refreshInterval={1000} />);

    // Add metrics after initial render
    const metrics = createInitialReconnectionMetrics();
    metrics.totalAttempts = 5;
    websocketTelemetry.trackReconnectionMetrics("notifications_test", metrics);

    // Fast-forward time with act() to properly handle state updates
    await act(async () => {
      vi.advanceTimersByTime(1100);
    });

    expect(screen.getByText("notifications_test")).toBeInTheDocument();

    vi.useRealTimers();
  });

  it("should apply custom className", () => {
    render(<WebSocketMetricsPanel className="custom-class" />);

    const panel = screen.getByTestId("ws-metrics-panel");
    expect(panel).toHaveClass("custom-class");
  });
});
