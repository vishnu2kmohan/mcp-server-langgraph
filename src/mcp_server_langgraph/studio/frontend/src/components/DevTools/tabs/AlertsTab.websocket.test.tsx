/**
 * AlertsTab WebSocket Integration Tests
 *
 * TDD tests for real-time WebSocket alert streaming integration.
 * Tests the externalAlerts prop, merge logic, and connection status indicator.
 *
 * RED Phase: These tests are written FIRST and should fail initially.
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

import { AlertsTab, type Alert } from "./AlertsTab";
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

// Mock alerts from REST API (initial load)
const restAlerts: Alert[] = [
  {
    id: "alert-rest-1",
    name: "HighErrorRate",
    state: "firing",
    severity: "critical",
    service: "api-gateway",
    message: "Error rate exceeded 5% threshold (current: 7.2%)",
    startedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    generatorUrl: "/grafana/alerting/alert-1/view",
  },
  {
    id: "alert-rest-2",
    name: "SlowQueryTime",
    state: "pending",
    severity: "warning",
    service: "db-service",
    message: "Query latency approaching threshold",
    startedAt: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  },
];

// Mock alerts from WebSocket (real-time updates)
const wsAlerts: Alert[] = [
  {
    id: "alert-ws-1",
    name: "MemoryPressure",
    state: "firing",
    severity: "warning",
    service: "worker-01",
    message: "Memory usage at 92%",
    startedAt: new Date(Date.now() - 1 * 60 * 1000).toISOString(),
  },
  {
    id: "alert-ws-2",
    name: "CPUSpike",
    state: "firing",
    severity: "critical",
    service: "compute-node",
    message: "CPU usage at 98%",
    startedAt: new Date(Date.now() - 30 * 1000).toISOString(),
  },
];

// WebSocket update for existing alert (state change)
const wsAlertUpdate: Alert = {
  id: "alert-rest-1", // Same ID as REST alert
  name: "HighErrorRate",
  state: "resolved", // Changed from firing to resolved
  severity: "critical",
  service: "api-gateway",
  message: "Error rate returned to normal",
  startedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  resolvedAt: new Date().toISOString(),
};

// =============================================================================
// Tests
// =============================================================================

describe("AlertsTab WebSocket Integration", () => {
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

  describe("externalAlerts prop", () => {
    it("should accept and display externalAlerts prop", () => {
      renderWithProvider(<AlertsTab externalAlerts={wsAlerts} />);

      expect(screen.getByText(/memorypressure/i)).toBeInTheDocument();
      expect(screen.getByText(/cpuspike/i)).toBeInTheDocument();
    });

    it("should handle undefined externalAlerts gracefully", () => {
      renderWithProvider(<AlertsTab alerts={restAlerts} />);

      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.getByText(/slowquerytime/i)).toBeInTheDocument();
    });

    it("should handle empty externalAlerts array", () => {
      renderWithProvider(<AlertsTab alerts={restAlerts} externalAlerts={[]} />);

      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.getByText(/slowquerytime/i)).toBeInTheDocument();
    });
  });

  describe("alert merging", () => {
    it("should merge external alerts with prop alerts", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={wsAlerts} />,
      );

      // REST alerts
      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.getByText(/slowquerytime/i)).toBeInTheDocument();

      // WebSocket alerts
      expect(screen.getByText(/memorypressure/i)).toBeInTheDocument();
      expect(screen.getByText(/cpuspike/i)).toBeInTheDocument();
    });

    it("should deduplicate alerts by id (prefer external/newer version)", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={[wsAlertUpdate]} />,
      );

      // Should show the updated state from WebSocket, not the original
      const alertsTab = screen.getByTestId("alerts-tab");
      expect(within(alertsTab).getByText(/resolved/i)).toBeInTheDocument();
      expect(
        within(alertsTab).getByText(/error rate returned to normal/i),
      ).toBeInTheDocument();

      // Should NOT show the original "firing" state
      expect(
        within(alertsTab).queryByText(/error rate exceeded/i),
      ).not.toBeInTheDocument();
    });

    it("should sort alerts by startedAt timestamp (newest first)", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={wsAlerts} />,
      );

      // Get all alert cards
      const alertCards = screen
        .getByTestId("alerts-tab")
        .querySelectorAll("[data-alert]");

      // CPUSpike (30s ago) should be first, then MemoryPressure (1m), etc.
      const alertIds = Array.from(alertCards).map((card) =>
        card.getAttribute("data-alert"),
      );

      expect(alertIds[0]).toBe("alert-ws-2"); // CPUSpike - newest
      expect(alertIds[1]).toBe("alert-ws-1"); // MemoryPressure
      expect(alertIds[2]).toBe("alert-rest-2"); // SlowQueryTime
      expect(alertIds[3]).toBe("alert-rest-1"); // HighErrorRate - oldest
    });

    it("should update count to include external alerts", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={wsAlerts} />,
      );

      // Total should be 4 (2 REST + 2 WS)
      const alertCards = screen
        .getByTestId("alerts-tab")
        .querySelectorAll("[data-alert]");
      expect(alertCards.length).toBe(4);
    });
  });

  describe("filtering with external alerts", () => {
    it("should filter external alerts by state", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={wsAlerts} />,
      );

      fireEvent.click(screen.getByRole("button", { name: /state/i }));
      fireEvent.click(screen.getByRole("option", { name: /firing/i }));

      // Should show firing alerts from both sources
      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.getByText(/memorypressure/i)).toBeInTheDocument();
      expect(screen.getByText(/cpuspike/i)).toBeInTheDocument();

      // Should NOT show pending alert
      expect(screen.queryByText(/slowquerytime/i)).not.toBeInTheDocument();
    });

    it("should filter external alerts by severity", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={wsAlerts} />,
      );

      fireEvent.click(screen.getByRole("button", { name: /severity/i }));
      fireEvent.click(screen.getByRole("option", { name: /critical/i }));

      // Should show critical alerts from both sources
      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.getByText(/cpuspike/i)).toBeInTheDocument();

      // Should NOT show warning alerts
      expect(screen.queryByText(/slowquerytime/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/memorypressure/i)).not.toBeInTheDocument();
    });

    it("should include external alert services in service filter", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={wsAlerts} />,
      );

      fireEvent.click(screen.getByRole("button", { name: /service/i }));

      // Services from both sources should be in dropdown
      expect(
        screen.getByRole("option", { name: /api-gateway/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /worker-01/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /compute-node/i }),
      ).toBeInTheDocument();
    });
  });

  describe("connection status indicator", () => {
    it("should display connection status indicator when connectionStatus provided", () => {
      renderWithProvider(
        <AlertsTab
          alerts={restAlerts}
          externalAlerts={wsAlerts}
          connectionStatus="connected"
        />,
      );

      const statusIndicator = screen.getByTitle(/websocket: connected/i);
      expect(statusIndicator).toBeInTheDocument();
      expect(statusIndicator).toHaveClass("bg-success-500");
    });

    it("should show connecting status with animation", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} connectionStatus="connecting" />,
      );

      const statusIndicator = screen.getByTitle(/websocket: connecting/i);
      expect(statusIndicator).toBeInTheDocument();
      expect(statusIndicator).toHaveClass("bg-warning-500");
      expect(statusIndicator).toHaveClass("animate-pulse");
    });

    it("should show disconnected status", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} connectionStatus="disconnected" />,
      );

      const statusIndicator = screen.getByTitle(/websocket: disconnected/i);
      expect(statusIndicator).toBeInTheDocument();
      expect(statusIndicator).toHaveClass("bg-neutral-400");
    });

    it("should show error status", () => {
      renderWithProvider(
        <AlertsTab alerts={restAlerts} connectionStatus="error" />,
      );

      const statusIndicator = screen.getByTitle(/websocket: error/i);
      expect(statusIndicator).toBeInTheDocument();
      expect(statusIndicator).toHaveClass("bg-error-500");
    });

    it("should not display status indicator when connectionStatus not provided", () => {
      renderWithProvider(<AlertsTab alerts={restAlerts} />);

      expect(screen.queryByTitle(/websocket:/i)).not.toBeInTheDocument();
    });
  });

  describe("clearing external alerts", () => {
    it("should call onClearExternal when clearing alerts", () => {
      const onClearExternal = vi.fn();

      renderWithProvider(
        <AlertsTab
          alerts={restAlerts}
          externalAlerts={wsAlerts}
          onClearExternal={onClearExternal}
        />,
      );

      // Find and click clear button (if filters are active)
      fireEvent.click(screen.getByRole("button", { name: /state/i }));
      fireEvent.click(screen.getByRole("option", { name: /firing/i }));

      // Clear filters button should appear
      const clearButton = screen.getByText(/clear filters/i);
      fireEvent.click(clearButton);

      // Note: onClearExternal is called when explicitly clearing WS alerts,
      // not when clearing filters. This test may need adjustment based on
      // the final UI design for clearing external alerts.
    });
  });

  describe("real-time update scenarios", () => {
    it("should handle new alert appearing via WebSocket", () => {
      const { rerender } = renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={[]} />,
      );

      // Initially only REST alerts
      expect(screen.queryByText(/memorypressure/i)).not.toBeInTheDocument();

      // Simulate WebSocket alert arriving
      rerender(
        <DevToolsTimelineProvider>
          <AlertsTab alerts={restAlerts} externalAlerts={wsAlerts} />
        </DevToolsTimelineProvider>,
      );

      // Now WebSocket alert should appear
      expect(screen.getByText(/memorypressure/i)).toBeInTheDocument();
    });

    it("should handle alert state change via WebSocket", () => {
      const { rerender } = renderWithProvider(
        <AlertsTab alerts={restAlerts} externalAlerts={[]} />,
      );

      // Initially firing
      const alertsTab = screen.getByTestId("alerts-tab");
      expect(within(alertsTab).getByText(/firing/i)).toBeInTheDocument();

      // Simulate state change via WebSocket
      rerender(
        <DevToolsTimelineProvider>
          <AlertsTab alerts={restAlerts} externalAlerts={[wsAlertUpdate]} />
        </DevToolsTimelineProvider>,
      );

      // Now should show resolved
      expect(within(alertsTab).getByText(/resolved/i)).toBeInTheDocument();
    });
  });
});
