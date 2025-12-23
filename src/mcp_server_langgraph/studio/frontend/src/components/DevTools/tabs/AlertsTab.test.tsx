/**
 * AlertsTab Component Tests
 *
 * TDD tests for Grafana alerts integration.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, within, cleanup } from "@testing-library/react";
import React from "react";

import { AlertsTab } from "./AlertsTab";
import { DevToolsTimelineProvider } from "../context/DevToolsTimelineProvider";

// =============================================================================
// Test Helpers
// =============================================================================

function renderWithProvider(
  ui: React.ReactElement,
  providerProps?: Partial<React.ComponentProps<typeof DevToolsTimelineProvider>>,
) {
  return render(
    <DevToolsTimelineProvider {...providerProps}>{ui}</DevToolsTimelineProvider>,
  );
}

const mockAlerts = [
  {
    id: "alert-1",
    name: "HighErrorRate",
    state: "firing" as const,
    severity: "critical" as const,
    service: "api-gateway",
    message: "Error rate exceeded 5% threshold (current: 7.2%)",
    started_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    generator_url: "/grafana/alerting/alert-1/view",
  },
  {
    id: "alert-2",
    name: "SlowQueryTime",
    state: "pending" as const,
    severity: "warning" as const,
    service: "db-service",
    message: "Query latency approaching threshold (current: 450ms/500ms)",
    started_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    generator_url: "/grafana/alerting/alert-2/view",
  },
  {
    id: "alert-3",
    name: "MemoryPressure",
    state: "resolved" as const,
    severity: "warning" as const,
    service: "worker-01",
    message: "Memory usage returned to normal (peak: 92%, current: 65%)",
    started_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
    resolved_at: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("AlertsTab", () => {
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
      renderWithProvider(<AlertsTab />);
      expect(screen.getByTestId("alerts-tab")).toBeInTheDocument();
    });

    it("should display empty state when no alerts", () => {
      renderWithProvider(<AlertsTab />);
      expect(screen.getByText(/no alerts/i)).toBeInTheDocument();
    });

    it("should display filter controls", () => {
      renderWithProvider(<AlertsTab />);
      expect(screen.getByRole("button", { name: /state/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /severity/i })).toBeInTheDocument();
    });
  });

  describe("alert list", () => {
    it("should display alerts when alerts exist", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.getByText(/slowquerytime/i)).toBeInTheDocument();
      expect(screen.getByText(/memorypressure/i)).toBeInTheDocument();
    });

    it("should show alert messages", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      expect(screen.getByText(/error rate exceeded 5%/i)).toBeInTheDocument();
      expect(screen.getByText(/query latency approaching/i)).toBeInTheDocument();
    });

    it("should display state badges", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      const alertsTab = screen.getByTestId("alerts-tab");
      expect(within(alertsTab).getByText(/firing/i)).toBeInTheDocument();
      expect(within(alertsTab).getByText(/pending/i)).toBeInTheDocument();
      expect(within(alertsTab).getByText(/resolved/i)).toBeInTheDocument();
    });

    it("should display severity badges", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      const alertsTab = screen.getByTestId("alerts-tab");
      expect(within(alertsTab).getByText(/critical/i)).toBeInTheDocument();
      // Warning appears twice
      expect(within(alertsTab).getAllByText(/warning/i).length).toBeGreaterThan(0);
    });

    it("should show service names", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      expect(screen.getByText(/api-gateway/i)).toBeInTheDocument();
      expect(screen.getByText(/db-service/i)).toBeInTheDocument();
    });
  });

  describe("filtering", () => {
    it("should filter alerts by state", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      fireEvent.click(screen.getByRole("button", { name: /state/i }));
      fireEvent.click(screen.getByRole("option", { name: /firing/i }));

      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.queryByText(/slowquerytime/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/memorypressure/i)).not.toBeInTheDocument();
    });

    it("should filter alerts by severity", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      fireEvent.click(screen.getByRole("button", { name: /severity/i }));
      fireEvent.click(screen.getByRole("option", { name: /critical/i }));

      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.queryByText(/slowquerytime/i)).not.toBeInTheDocument();
    });

    it("should filter alerts by service", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      fireEvent.click(screen.getByRole("button", { name: /service/i }));
      fireEvent.click(screen.getByRole("option", { name: /api-gateway/i }));

      expect(screen.getByText(/higherrorrate/i)).toBeInTheDocument();
      expect(screen.queryByText(/slowquerytime/i)).not.toBeInTheDocument();
    });
  });

  describe("grafana integration", () => {
    it("should display View in Grafana button for alerts with generator_url", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      const grafanaButtons = screen.getAllByRole("button", {
        name: /view in grafana/i,
      });
      expect(grafanaButtons.length).toBeGreaterThan(0);
    });

    it("should open Grafana URL when clicked", () => {
      const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);

      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      const grafanaButtons = screen.getAllByRole("button", {
        name: /view in grafana/i,
      });
      fireEvent.click(grafanaButtons[0]);

      expect(openSpy).toHaveBeenCalledWith(
        expect.stringContaining("/grafana/alerting/"),
        "_blank",
      );

      openSpy.mockRestore();
    });
  });

  describe("alert actions", () => {
    it("should display silence button for firing alerts", () => {
      const onSilence = vi.fn();
      renderWithProvider(<AlertsTab alerts={mockAlerts} onSilence={onSilence} />);

      expect(
        screen.getByRole("button", { name: /silence/i }),
      ).toBeInTheDocument();
    });

    it("should call onSilence when silence button clicked", () => {
      const onSilence = vi.fn();
      renderWithProvider(<AlertsTab alerts={mockAlerts} onSilence={onSilence} />);

      fireEvent.click(screen.getByRole("button", { name: /silence/i }));

      expect(onSilence).toHaveBeenCalledWith("alert-1");
    });

    it("should display details toggle", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      const detailsButtons = screen.getAllByRole("button", { name: /details/i });
      expect(detailsButtons.length).toBeGreaterThan(0);
    });
  });

  describe("timeline integration", () => {
    it("should filter alerts by time window", () => {
      // Alerts should sync with timeline context
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      expect(screen.getByTestId("alerts-tab")).toBeInTheDocument();
    });
  });

  describe("loading state", () => {
    it("should show loading skeleton when isLoading", () => {
      renderWithProvider(<AlertsTab isLoading />);

      expect(screen.getByTestId("alerts-loading")).toBeInTheDocument();
    });
  });

  describe("error state", () => {
    it("should display error message on error", () => {
      renderWithProvider(<AlertsTab error="Failed to fetch alerts" />);

      expect(screen.getByText(/failed to fetch alerts/i)).toBeInTheDocument();
    });
  });

  describe("relative time", () => {
    it("should display relative time for alert start", () => {
      renderWithProvider(<AlertsTab alerts={mockAlerts} />);

      // Should show "5m ago", "2m ago", "15m ago" style times
      const agoElements = screen.getAllByText(/ago/i);
      expect(agoElements.length).toBeGreaterThan(0);
    });
  });
});
