/**
 * AlertGroupsPanel Tests
 *
 * TDD tests for the grouped alerts panel component.
 *
 * Features:
 * - Collapsible alert groups
 * - Group header: service name, alert count, severity badge
 * - Expand to show individual alerts
 * - Keyboard navigation
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AlertGroupsPanel } from "./AlertGroupsPanel";
import type { AlertGroup, Alert } from "../../store/slices/alertSlice";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Helpers
// =============================================================================

const createMockAlert = (overrides: Partial<Alert> = {}): Alert => ({
  alertId: `alert-${Math.random().toString(36).slice(2, 9)}`,
  name: "TestAlert",
  severity: "critical",
  state: "firing",
  message: "Test alert message",
  labels: { service: "test-service" },
  annotations: {},
  startedAt: new Date().toISOString(),
  endedAt: null,
  fingerprint: `fp-${Math.random().toString(36).slice(2, 9)}`,
  ...overrides,
});

const createMockGroup = (overrides: Partial<AlertGroup> = {}): AlertGroup => {
  const alert1 = createMockAlert({ alertId: "a1", name: "CPUHigh" });
  const alert2 = createMockAlert({ alertId: "a2", name: "CPUHigh" });

  return {
    groupKey: "api-server:CPUHigh",
    service: "api-server",
    alertName: "CPUHigh",
    severity: "critical",
    state: "firing",
    count: 2,
    mostRecentAlert: alert1,
    alerts: [alert1, alert2],
    firstFiredAt: "2025-12-20T10:00:00Z",
    lastUpdatedAt: "2025-12-20T10:30:00Z",
    ...overrides,
  };
};

// =============================================================================
// Tests
// =============================================================================

describe("AlertGroupsPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render alert groups", () => {
      const groups = [
        createMockGroup({
          groupKey: "api:CPUHigh",
          alertName: "CPUHigh",
          service: "api",
        }),
        createMockGroup({
          groupKey: "worker:MemoryHigh",
          alertName: "MemoryHigh",
          service: "worker",
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("alert-group-api:CPUHigh")).toBeInTheDocument();
      expect(
        screen.getByTestId("alert-group-worker:MemoryHigh"),
      ).toBeInTheDocument();
    });

    it("should display group header with service name and alert count", () => {
      const groups = [
        createMockGroup({
          groupKey: "api-server:CPUHigh",
          service: "api-server",
          alertName: "CPUHigh",
          count: 5,
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByText("CPUHigh")).toBeInTheDocument();
      expect(screen.getByText("api-server")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("should display severity badge with correct color", () => {
      const criticalGroup = createMockGroup({
        groupKey: "api:Critical",
        severity: "critical",
      });
      const warningGroup = createMockGroup({
        groupKey: "api:Warning",
        severity: "warning",
      });

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={[criticalGroup, warningGroup]}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      const criticalBadge = screen.getByTestId("severity-badge-api:Critical");
      const warningBadge = screen.getByTestId("severity-badge-api:Warning");

      expect(criticalBadge).toHaveClass("bg-error-9");
      expect(warningBadge).toHaveClass("bg-warning-9");
    });

    it("should show empty state when no groups", () => {
      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={[]}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/no alert groups/i)).toBeInTheDocument();
    });
  });

  describe("expand/collapse", () => {
    it("should call onToggleGroup when clicking group header", async () => {
      const user = userEvent.setup();
      const onToggleGroup = vi.fn();
      const groups = [createMockGroup({ groupKey: "api:CPUHigh" })];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={onToggleGroup}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("group-header-api:CPUHigh"));

      expect(onToggleGroup).toHaveBeenCalledWith("api:CPUHigh");
    });

    it("should show individual alerts when group is expanded", () => {
      const alert1 = createMockAlert({
        alertId: "a1",
        message: "First alert",
      });
      const alert2 = createMockAlert({
        alertId: "a2",
        message: "Second alert",
      });
      const groups = [
        createMockGroup({
          groupKey: "api:CPUHigh",
          alerts: [alert1, alert2],
          count: 2,
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set(["api:CPUHigh"])}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByText("First alert")).toBeInTheDocument();
      expect(screen.getByText("Second alert")).toBeInTheDocument();
    });

    it("should hide individual alerts when group is collapsed", () => {
      const alert1 = createMockAlert({
        alertId: "a1",
        message: "First alert",
      });
      const alert2 = createMockAlert({
        alertId: "a2",
        message: "Second alert",
      });
      const groups = [
        createMockGroup({
          groupKey: "api:CPUHigh",
          alerts: [alert1, alert2],
          count: 2,
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.queryByText("First alert")).not.toBeInTheDocument();
      expect(screen.queryByText("Second alert")).not.toBeInTheDocument();
    });

    it("should show expand/collapse icon based on state", () => {
      const groups = [
        createMockGroup({ groupKey: "api:Collapsed" }),
        createMockGroup({ groupKey: "api:Expanded" }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set(["api:Expanded"])}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("expand-icon-api:Collapsed"),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId("collapse-icon-api:Expanded"),
      ).toBeInTheDocument();
    });
  });

  describe("alert selection", () => {
    it("should call onSelectAlert when clicking an alert in expanded group", async () => {
      const user = userEvent.setup();
      const onSelectAlert = vi.fn();
      const alert1 = createMockAlert({ alertId: "a1" });
      const groups = [
        createMockGroup({
          groupKey: "api:CPUHigh",
          alerts: [alert1],
          count: 1,
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={onSelectAlert}
            expandedGroups={new Set(["api:CPUHigh"])}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("alert-item-a1"));

      expect(onSelectAlert).toHaveBeenCalledWith("a1");
    });

    it("should highlight selected alert", () => {
      const alert1 = createMockAlert({ alertId: "a1" });
      const alert2 = createMockAlert({ alertId: "a2" });
      const groups = [
        createMockGroup({
          groupKey: "api:CPUHigh",
          alerts: [alert1, alert2],
          count: 2,
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId="a1"
            onSelectAlert={vi.fn()}
            expandedGroups={new Set(["api:CPUHigh"])}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      const selectedItem = screen.getByTestId("alert-item-a1");
      const unselectedItem = screen.getByTestId("alert-item-a2");

      expect(selectedItem).toHaveClass("border-primary-9");
      expect(unselectedItem).not.toHaveClass("border-primary-9");
    });
  });

  describe("keyboard navigation", () => {
    it("should toggle group with Enter key", async () => {
      const user = userEvent.setup();
      const onToggleGroup = vi.fn();
      const groups = [createMockGroup({ groupKey: "api:CPUHigh" })];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={onToggleGroup}
          />
        </TestProvider>,
      );

      const header = screen.getByTestId("group-header-api:CPUHigh");
      header.focus();
      await user.keyboard("{Enter}");

      expect(onToggleGroup).toHaveBeenCalledWith("api:CPUHigh");
    });

    it("should toggle group with Space key", async () => {
      const user = userEvent.setup();
      const onToggleGroup = vi.fn();
      const groups = [createMockGroup({ groupKey: "api:CPUHigh" })];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={onToggleGroup}
          />
        </TestProvider>,
      );

      const header = screen.getByTestId("group-header-api:CPUHigh");
      header.focus();
      await user.keyboard(" ");

      expect(onToggleGroup).toHaveBeenCalledWith("api:CPUHigh");
    });
  });

  describe("state display", () => {
    it("should show firing state badge", () => {
      const groups = [
        createMockGroup({
          groupKey: "api:Firing",
          state: "firing",
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("state-badge-api:Firing")).toHaveTextContent(
        "Firing",
      );
    });

    it("should show resolved state badge", () => {
      const groups = [
        createMockGroup({
          groupKey: "api:Resolved",
          state: "resolved",
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("state-badge-api:Resolved")).toHaveTextContent(
        "Resolved",
      );
    });
  });

  describe("accessibility", () => {
    it("should have accessible group headers", () => {
      const groups = [
        createMockGroup({
          groupKey: "api:CPUHigh",
          alertName: "CPUHigh",
          count: 3,
        }),
      ];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set()}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      const header = screen.getByTestId("group-header-api:CPUHigh");
      expect(header).toHaveAttribute("role", "button");
      expect(header).toHaveAttribute("aria-expanded", "false");
    });

    it("should update aria-expanded when group is expanded", () => {
      const groups = [createMockGroup({ groupKey: "api:CPUHigh" })];

      render(
        <TestProvider>
          <AlertGroupsPanel
            groups={groups}
            selectedAlertId={null}
            onSelectAlert={vi.fn()}
            expandedGroups={new Set(["api:CPUHigh"])}
            onToggleGroup={vi.fn()}
          />
        </TestProvider>,
      );

      const header = screen.getByTestId("group-header-api:CPUHigh");
      expect(header).toHaveAttribute("aria-expanded", "true");
    });
  });
});
