/**
 * AlertsPanel Component Tests
 *
 * TDD tests for the infrastructure alerts panel in Admin dashboard.
 *
 * Features:
 * - Display alert list with severity indicators
 * - Filter controls (severity, state)
 * - Sound toggle
 * - Real-time badge counts
 * - Alert selection
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

import { AlertsPanel, type AlertsPanelProps } from "./AlertsPanel";
import alertReducer, { type Alert } from "../../store/slices/alertSlice";

// =============================================================================
// Test Data
// =============================================================================

const mockAlerts: Alert[] = [
  {
    alert_id: "alert-001",
    name: "HighCPU",
    severity: "critical",
    state: "firing",
    message: "CPU usage above 90% for 5 minutes",
    labels: { service: "api-server", pod: "api-123" },
    annotations: { summary: "High CPU usage detected" },
    started_at: "2024-01-15T10:30:00Z",
    ended_at: null,
    fingerprint: "fp-001",
  },
  {
    alert_id: "alert-002",
    name: "HighMemory",
    severity: "warning",
    state: "firing",
    message: "Memory usage above 80%",
    labels: { service: "worker", pod: "worker-456" },
    annotations: { summary: "High memory usage" },
    started_at: "2024-01-15T10:25:00Z",
    ended_at: null,
    fingerprint: "fp-002",
  },
  {
    alert_id: "alert-003",
    name: "DiskFull",
    severity: "critical",
    state: "resolved",
    message: "Disk 95% full",
    labels: { service: "storage" },
    annotations: {},
    started_at: "2024-01-15T09:00:00Z",
    ended_at: "2024-01-15T10:00:00Z",
    fingerprint: "fp-003",
  },
];

// =============================================================================
// Test Helpers
// =============================================================================

const createTestStore = (
  initialAlerts: Alert[] = [],
  soundEnabled = true,
  filters = {
    severity: ["critical", "warning"] as ("critical" | "warning")[],
    state: ["firing"] as ("firing" | "resolved")[],
  },
) =>
  configureStore({
    reducer: {
      alerts: alertReducer,
    },
    preloadedState: {
      alerts: {
        alerts: initialAlerts,
        selectedAlertId: null,
        pendingRemediations: [],
        soundEnabled,
        lastCriticalAlertTime: null,
        filters,
      },
    },
  });

const defaultProps: AlertsPanelProps = {
  onSelectAlert: vi.fn(),
  onSoundToggle: vi.fn(),
};

const renderWithStore = (ui: ReactNode, store = createTestStore(mockAlerts)) =>
  render(<Provider store={store}>{ui}</Provider>);

// =============================================================================
// Tests
// =============================================================================

describe("AlertsPanel", () => {
  // Clear localStorage before each test to avoid view mode persistence issues
  beforeEach(() => {
    localStorage.clear();
  });

  describe("Basic Rendering", () => {
    it("should render the panel header", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByText("Infrastructure Alerts")).toBeInTheDocument();
    });

    it("should render alert list", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByText("HighCPU")).toBeInTheDocument();
      expect(screen.getByText("HighMemory")).toBeInTheDocument();
    });

    it("should show empty state when no alerts", () => {
      const emptyStore = createTestStore([]);
      renderWithStore(<AlertsPanel {...defaultProps} />, emptyStore);

      expect(screen.getByText(/no alerts/i)).toBeInTheDocument();
    });

    it("should show loading state when loading", () => {
      renderWithStore(<AlertsPanel {...defaultProps} isLoading />);

      expect(screen.getByTestId("alerts-loading")).toBeInTheDocument();
    });
  });

  describe("Alert Items", () => {
    it("should display alert name", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByText("HighCPU")).toBeInTheDocument();
    });

    it("should display alert message", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(
        screen.getByText("CPU usage above 90% for 5 minutes"),
      ).toBeInTheDocument();
    });

    it("should show critical severity indicator", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      const criticalBadge = screen.getByTestId("severity-badge-alert-001");
      expect(criticalBadge).toHaveClass("bg-red-500");
    });

    it("should show warning severity indicator", () => {
      const warningStore = createTestStore(mockAlerts, true, {
        severity: ["critical", "warning"],
        state: ["firing"],
      });
      renderWithStore(<AlertsPanel {...defaultProps} />, warningStore);

      const warningBadge = screen.getByTestId("severity-badge-alert-002");
      expect(warningBadge).toHaveClass("bg-yellow-500");
    });

    it("should show firing state indicator", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByTestId("state-badge-alert-001")).toHaveTextContent(
        "Firing",
      );
    });
  });

  describe("Alert Selection", () => {
    it("should call onSelectAlert when alert is clicked", () => {
      const onSelectAlert = vi.fn();
      renderWithStore(
        <AlertsPanel {...defaultProps} onSelectAlert={onSelectAlert} />,
      );

      fireEvent.click(screen.getByTestId("alert-item-alert-001"));

      expect(onSelectAlert).toHaveBeenCalledWith("alert-001");
    });

    it("should highlight selected alert", () => {
      const storeWithSelection = configureStore({
        reducer: { alerts: alertReducer },
        preloadedState: {
          alerts: {
            alerts: mockAlerts,
            selectedAlertId: "alert-001",
            pendingRemediations: [],
            soundEnabled: true,
            lastCriticalAlertTime: null,
            filters: { severity: ["critical", "warning"], state: ["firing"] },
          },
        },
      });

      renderWithStore(<AlertsPanel {...defaultProps} />, storeWithSelection);

      const selectedItem = screen.getByTestId("alert-item-alert-001");
      expect(selectedItem).toHaveClass("border-blue-500");
    });
  });

  describe("Filter Controls", () => {
    it("should render severity filter buttons", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /critical/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /warning/i }),
      ).toBeInTheDocument();
    });

    it("should render state filter buttons", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      // Use getAllByRole since alert items also contain state badges with "Firing" text
      const firingButtons = screen.getAllByRole("button", { name: /firing/i });
      const resolvedButtons = screen.getAllByRole("button", {
        name: /resolved/i,
      });

      // At least one should be the filter button
      expect(firingButtons.length).toBeGreaterThan(0);
      expect(resolvedButtons.length).toBeGreaterThan(0);
    });

    it("should filter alerts by severity when filter is applied", () => {
      const criticalOnlyStore = createTestStore(mockAlerts, true, {
        severity: ["critical"],
        state: ["firing"],
      });
      renderWithStore(<AlertsPanel {...defaultProps} />, criticalOnlyStore);

      expect(screen.getByText("HighCPU")).toBeInTheDocument();
      expect(screen.queryByText("HighMemory")).not.toBeInTheDocument();
    });
  });

  describe("Sound Toggle", () => {
    it("should render sound toggle button", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByTestId("sound-toggle")).toBeInTheDocument();
    });

    it("should show sound enabled state", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      const toggle = screen.getByTestId("sound-toggle");
      expect(toggle).toHaveAttribute("aria-pressed", "true");
    });

    it("should show sound disabled state", () => {
      const soundDisabledStore = createTestStore(mockAlerts, false);
      renderWithStore(<AlertsPanel {...defaultProps} />, soundDisabledStore);

      const toggle = screen.getByTestId("sound-toggle");
      expect(toggle).toHaveAttribute("aria-pressed", "false");
    });

    it("should call onSoundToggle when clicked", () => {
      const onSoundToggle = vi.fn();
      renderWithStore(
        <AlertsPanel {...defaultProps} onSoundToggle={onSoundToggle} />,
      );

      fireEvent.click(screen.getByTestId("sound-toggle"));

      expect(onSoundToggle).toHaveBeenCalled();
    });
  });

  describe("Badge Counts", () => {
    it("should show critical alert count", () => {
      const storeWithCritical = createTestStore(mockAlerts, true, {
        severity: ["critical", "warning"],
        state: ["firing", "resolved"],
      });
      renderWithStore(<AlertsPanel {...defaultProps} />, storeWithCritical);

      // Note: selectCriticalAlertCount only counts FIRING critical alerts
      // In mockAlerts: HighCPU (critical, firing), DiskFull (critical, resolved)
      // So count should be 1, not 2
      expect(screen.getByTestId("critical-count")).toHaveTextContent("1");
    });

    it("should show warning alert count", () => {
      const storeWithWarning = createTestStore(mockAlerts, true, {
        severity: ["critical", "warning"],
        state: ["firing", "resolved"],
      });
      renderWithStore(<AlertsPanel {...defaultProps} />, storeWithWarning);

      expect(screen.getByTestId("warning-count")).toHaveTextContent("1");
    });
  });

  describe("Time Display", () => {
    it("should show relative time for alert start", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      // The component should display time in a human-readable format
      expect(screen.getByTestId("alert-time-alert-001")).toBeInTheDocument();
    });
  });

  describe("Labels", () => {
    it("should display service label", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByText("api-server")).toBeInTheDocument();
    });
  });

  describe("Connection Status", () => {
    it("should show connected status indicator", () => {
      renderWithStore(
        <AlertsPanel {...defaultProps} connectionStatus="connected" />,
      );

      expect(screen.getByTestId("connection-status")).toHaveClass(
        "bg-green-500",
      );
    });

    it("should show disconnected status indicator", () => {
      renderWithStore(
        <AlertsPanel {...defaultProps} connectionStatus="disconnected" />,
      );

      expect(screen.getByTestId("connection-status")).toHaveClass("bg-red-500");
    });

    it("should show connecting status indicator", () => {
      renderWithStore(
        <AlertsPanel {...defaultProps} connectionStatus="connecting" />,
      );

      expect(screen.getByTestId("connection-status")).toHaveClass(
        "bg-yellow-500",
      );
    });
  });

  describe("View Mode Toggle", () => {
    beforeEach(() => {
      // Clear view mode preference before each test
      localStorage.removeItem("alert-view-mode");
    });

    afterEach(() => {
      // Cleanup after each test
      localStorage.removeItem("alert-view-mode");
    });

    it("should show flat alert list when flat view is selected", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      // Flat view is default, so should show flat list
      expect(
        screen.queryByTestId("alert-groups-panel"),
      ).not.toBeInTheDocument();
      expect(screen.getByTestId("alert-item-alert-001")).toBeInTheDocument();
    });

    it("should render view mode toggle", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByTestId("view-mode-toggle")).toBeInTheDocument();
    });

    it("should default to flat view", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      expect(screen.getByTestId("view-mode-flat")).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(screen.getByTestId("view-mode-grouped")).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });

    it("should switch to grouped view when clicked", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      fireEvent.click(screen.getByTestId("view-mode-grouped"));

      expect(screen.getByTestId("view-mode-grouped")).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(screen.getByTestId("view-mode-flat")).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });

    it("should show AlertGroupsPanel when grouped view is selected", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      // Switch to grouped view
      fireEvent.click(screen.getByTestId("view-mode-grouped"));

      // Should render grouped panel
      expect(screen.getByTestId("alert-groups-panel")).toBeInTheDocument();
    });

    it("should toggle group expansion in grouped view", () => {
      renderWithStore(<AlertsPanel {...defaultProps} />);

      // Switch to grouped view
      fireEvent.click(screen.getByTestId("view-mode-grouped"));

      // Find a group header and click it
      const groupHeader = screen
        .getAllByRole("button")
        .find((btn) => btn.getAttribute("aria-expanded") !== null);
      expect(groupHeader).toBeInTheDocument();

      if (groupHeader) {
        // Initially collapsed
        expect(groupHeader).toHaveAttribute("aria-expanded", "false");

        // Click to expand
        fireEvent.click(groupHeader);

        // Should be expanded
        expect(groupHeader).toHaveAttribute("aria-expanded", "true");
      }
    });

    it("should persist view mode preference", () => {
      const { unmount } = renderWithStore(<AlertsPanel {...defaultProps} />);

      // Switch to grouped view
      fireEvent.click(screen.getByTestId("view-mode-grouped"));

      // Unmount and remount
      unmount();

      renderWithStore(<AlertsPanel {...defaultProps} />);

      // Should remember grouped view
      expect(screen.getByTestId("view-mode-grouped")).toHaveAttribute(
        "aria-pressed",
        "true",
      );
    });
  });

  describe("Edge Cases", () => {
    it("should handle reconnecting connection status", () => {
      renderWithStore(
        <AlertsPanel {...defaultProps} connectionStatus="reconnecting" />,
      );

      expect(screen.getByTestId("connection-status")).toHaveClass(
        "bg-yellow-500",
      );
    });

    it("should handle error connection status", () => {
      renderWithStore(
        <AlertsPanel {...defaultProps} connectionStatus="error" />,
      );

      expect(screen.getByTestId("connection-status")).toHaveClass("bg-red-500");
    });

    it("should handle undefined connection status (defaults to connected)", () => {
      // When connectionStatus is undefined, component defaults to "connected"
      renderWithStore(
        <AlertsPanel {...defaultProps} connectionStatus={undefined} />,
      );

      // Default value is "connected" which shows green
      expect(screen.getByTestId("connection-status")).toHaveClass(
        "bg-green-500",
      );
    });

    it("should display pod label when service label is missing", () => {
      // Use alert-002 from mockAlerts but modify it to have only pod label
      // The mockAlerts with default filters shows firing alerts
      const alertsWithPodOnly: Alert[] = [
        {
          alert_id: "alert-pod-only",
          name: "PodOnlyAlert",
          severity: "critical", // Use critical so default filters include it
          state: "firing", // Use firing so default filters include it
          message: "Pod issue",
          labels: { pod: "pod-xyz" }, // No service label, only pod
          annotations: {},
          started_at: "2024-01-15T10:30:00Z",
          ended_at: null,
          fingerprint: "fp-pod",
        },
      ];
      // Default filters: severity: ["critical", "warning"], state: ["firing"]
      const store = createTestStore(alertsWithPodOnly);
      renderWithStore(<AlertsPanel {...defaultProps} />, store);

      // The pod label should be displayed since there's no service label
      expect(screen.getByText("PodOnlyAlert")).toBeInTheDocument();
      expect(screen.getByText("pod-xyz")).toBeInTheDocument();
    });

    it("should handle alert without any labels", () => {
      const alertNoLabels: Alert = {
        alert_id: "alert-no-labels",
        name: "NoLabelAlert",
        severity: "warning",
        state: "firing",
        message: "Alert without labels",
        labels: {}, // No service or pod
        annotations: {},
        started_at: "2024-01-15T10:30:00Z",
        ended_at: null,
        fingerprint: "fp-no-label",
      };
      const store = createTestStore([alertNoLabels], true, {
        severity: ["warning"],
        state: ["firing"],
      });
      renderWithStore(<AlertsPanel {...defaultProps} />, store);

      expect(screen.getByText("NoLabelAlert")).toBeInTheDocument();
    });

    it("should show resolved state badge", () => {
      // Create an alert with resolved state that matches default filters
      const resolvedAlert: Alert = {
        alert_id: "alert-resolved",
        name: "ResolvedAlert",
        severity: "critical",
        state: "resolved",
        message: "Issue resolved",
        labels: { service: "test-service" },
        annotations: {},
        started_at: "2024-01-15T09:00:00Z",
        ended_at: "2024-01-15T10:00:00Z",
        fingerprint: "fp-resolved",
      };
      const resolvedStore = createTestStore([resolvedAlert], true, {
        severity: ["critical"],
        state: ["resolved"], // Only show resolved alerts
      });
      renderWithStore(<AlertsPanel {...defaultProps} />, resolvedStore);

      // The resolved state should show "Resolved" text (capitalized)
      expect(
        screen.getByTestId("state-badge-alert-resolved"),
      ).toHaveTextContent("Resolved");
    });

    it("should not call onFilterChange when it is undefined", () => {
      // Render without onFilterChange prop
      renderWithStore(
        <AlertsPanel onSelectAlert={vi.fn()} onSoundToggle={vi.fn()} />,
      );

      // Find filter buttons in the filter section - they have specific text content
      const allButtons = screen.getAllByRole("button");
      // Filter buttons have text "Critical" and "Warning" exactly (not "Critical:" or containing count)
      const criticalFilter = allButtons.find(
        (btn) => btn.textContent === "Critical",
      );
      const warningFilter = allButtons.find(
        (btn) => btn.textContent === "Warning",
      );

      // Click filter buttons - should not crash
      if (criticalFilter) fireEvent.click(criticalFilter);
      if (warningFilter) fireEvent.click(warningFilter);

      // If we get here without error, the test passes
      expect(screen.getByText("Infrastructure Alerts")).toBeInTheDocument();
    });

    it("should toggle state filter when clicked", () => {
      const onFilterChange = vi.fn();
      renderWithStore(
        <AlertsPanel {...defaultProps} onFilterChange={onFilterChange} />,
      );

      // Click firing filter button to toggle it off
      const firingButtons = screen.getAllByRole("button", { name: /firing/i });
      const filterButton = firingButtons[0]; // First one should be the filter
      fireEvent.click(filterButton);

      expect(onFilterChange).toHaveBeenCalled();
    });

    it("should add severity filter when not currently included", () => {
      // Store with only critical filter
      const store = createTestStore(mockAlerts, true, {
        severity: ["critical"],
        state: ["firing"],
      });
      const onFilterChange = vi.fn();
      renderWithStore(
        <AlertsPanel {...defaultProps} onFilterChange={onFilterChange} />,
        store,
      );

      // Click warning filter to add it
      fireEvent.click(screen.getByRole("button", { name: /warning/i }));

      expect(onFilterChange).toHaveBeenCalledWith({
        severity: expect.arrayContaining(["critical", "warning"]),
      });
    });

    it("should add state filter when not currently included", () => {
      const store = createTestStore(mockAlerts, true, {
        severity: ["critical", "warning"],
        state: ["firing"], // Only firing
      });
      const onFilterChange = vi.fn();
      renderWithStore(
        <AlertsPanel {...defaultProps} onFilterChange={onFilterChange} />,
        store,
      );

      // Click resolved filter to add it
      const resolvedButtons = screen.getAllByRole("button", {
        name: /resolved/i,
      });
      const filterButton = resolvedButtons[0];
      fireEvent.click(filterButton);

      expect(onFilterChange).toHaveBeenCalledWith({
        state: expect.arrayContaining(["firing", "resolved"]),
      });
    });

    it("should show empty state in grouped view with no groups", () => {
      const emptyStore = createTestStore([], true, {
        severity: ["critical", "warning"],
        state: ["firing"],
      });
      renderWithStore(<AlertsPanel {...defaultProps} />, emptyStore);

      // Switch to grouped view
      fireEvent.click(screen.getByTestId("view-mode-grouped"));

      expect(screen.getByText(/no alert groups/i)).toBeInTheDocument();
    });
  });
});
