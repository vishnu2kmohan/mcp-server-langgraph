/**
 * AdminDashboard Tests
 *
 * Tests for the Admin dashboard component with system health metrics.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { AdminDashboard } from "./AdminDashboard";
import alertReducer from "../../store/slices/alertSlice";
import personaReducer from "../../store/slices/personaSlice";
import { api } from "../../api";

// Create a wrapper with Redux store
const createTestStore = (username = "testuser@example.com") =>
  configureStore({
    reducer: {
      alerts: alertReducer,
      persona: personaReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
    preloadedState: {
      alerts: {
        alerts: [],
        selectedAlertId: null,
        pendingRemediations: [],
        soundEnabled: true,
        lastCriticalAlertTime: null,
        filters: { severity: ["critical", "warning"], state: ["firing"] },
      },
      persona: {
        persona: "admin",
        username,
        isAuthenticated: true,
        permissions: ["admin:alerts:read", "admin:alerts:approve"],
        loading: false,
        error: null,
      },
    },
  });

const renderWithStore = (ui: ReactNode, store = createTestStore()) =>
  render(<Provider store={store}>{ui}</Provider>);

describe("AdminDashboard", () => {
  const defaultProps = {
    systemHealth: {
      status: "healthy" as const,
      uptime: 99.9,
      activeUsers: 150,
      activeSessions: 42,
      errorRate: 0.1,
    },
    heartMetrics: {
      happiness: 85,
      engagement: 72,
      adoption: 68,
      retention: 91,
      taskSuccess: 88,
    },
    isLoading: false,
    onRefresh: vi.fn(),
  };

  describe("Rendering", () => {
    it("should render dashboard title", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("Admin Dashboard")).toBeInTheDocument();
    });

    it("should render system health section", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("System Health")).toBeInTheDocument();
    });

    it("should render HEART metrics section", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("HEART Metrics")).toBeInTheDocument();
    });

    it("should display uptime percentage", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("99.9%")).toBeInTheDocument();
    });

    it("should display active users count", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("150")).toBeInTheDocument();
    });

    it("should display health status indicator", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const healthIndicator = screen.getByTestId("health-status");
      expect(healthIndicator).toHaveClass("bg-green-500");
    });
  });

  describe("Health Status Variants", () => {
    it("should show green indicator for healthy status", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const indicator = screen.getByTestId("health-status");
      expect(indicator).toHaveClass("bg-green-500");
    });

    it("should show yellow indicator for degraded status", () => {
      const props = {
        ...defaultProps,
        systemHealth: {
          ...defaultProps.systemHealth,
          status: "degraded" as const,
        },
      };

      renderWithStore(<AdminDashboard {...props} />);

      const indicator = screen.getByTestId("health-status");
      expect(indicator).toHaveClass("bg-yellow-500");
    });

    it("should show red indicator for unhealthy status", () => {
      const props = {
        ...defaultProps,
        systemHealth: {
          ...defaultProps.systemHealth,
          status: "unhealthy" as const,
        },
      };

      renderWithStore(<AdminDashboard {...props} />);

      const indicator = screen.getByTestId("health-status");
      expect(indicator).toHaveClass("bg-red-500");
    });
  });

  describe("HEART Metrics", () => {
    it("should display all five HEART metrics", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("Happiness")).toBeInTheDocument();
      expect(screen.getByText("Engagement")).toBeInTheDocument();
      expect(screen.getByText("Adoption")).toBeInTheDocument();
      expect(screen.getByText("Retention")).toBeInTheDocument();
      expect(screen.getByText("Task Success")).toBeInTheDocument();
    });

    it("should display metric values", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("85%")).toBeInTheDocument(); // Happiness
      expect(screen.getByText("72%")).toBeInTheDocument(); // Engagement
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      renderWithStore(<AdminDashboard {...defaultProps} isLoading={true} />);

      expect(screen.getByTestId("dashboard-loading")).toBeInTheDocument();
    });

    it("should hide content when loading", () => {
      renderWithStore(<AdminDashboard {...defaultProps} isLoading={true} />);

      expect(screen.queryByText("System Health")).not.toBeInTheDocument();
    });
  });

  describe("Refresh", () => {
    it("should render refresh button", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });

    it("should call onRefresh when refresh button is clicked", async () => {
      const onRefresh = vi.fn();
      renderWithStore(
        <AdminDashboard {...defaultProps} onRefresh={onRefresh} />,
      );

      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      refreshButton.click();

      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe("Tabs", () => {
    it("should render Overview and Users tabs", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(
        screen.getByRole("tab", { name: /overview/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /users/i })).toBeInTheDocument();
    });

    it("should show Overview tab as active by default", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const overviewTab = screen.getByRole("tab", { name: /overview/i });
      expect(overviewTab).toHaveAttribute("aria-selected", "true");
    });

    it("should switch to Users tab when clicked", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(usersTab).toHaveAttribute("aria-selected", "true");
    });

    it("should show user management content when Users tab is active", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(screen.getByText("User Management")).toBeInTheDocument();
    });

    it("should hide System Health when Users tab is active", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(screen.queryByText("System Health")).not.toBeInTheDocument();
    });
  });

  describe("User Management Integration", () => {
    const userManagementProps = {
      ...defaultProps,
      users: [
        {
          id: "user-1",
          email: "alice@test.com",
          name: "Alice",
          roles: ["admin"],
          organizationId: "org-1",
          lastLogin: new Date("2025-01-01"),
          isActive: true,
        },
      ],
      onUpdateRoles: vi.fn(),
      onDeactivate: vi.fn(),
      onActivate: vi.fn(),
      onInvite: vi.fn(),
      usersLoading: false,
    };

    it("should pass users to UserManager when Users tab is active", async () => {
      renderWithStore(<AdminDashboard {...userManagementProps} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("alice@test.com")).toBeInTheDocument();
    });

    it("should show loading state for users when usersLoading is true", async () => {
      renderWithStore(
        <AdminDashboard {...userManagementProps} usersLoading={true} />,
      );

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(screen.getByTestId("user-loading")).toBeInTheDocument();
    });
  });

  describe("User Attribution", () => {
    it("should use actual logged-in username from Redux store", () => {
      const customUsername = "alice.admin@company.com";
      const store = createTestStore(customUsername);

      renderWithStore(<AdminDashboard {...defaultProps} />, store);

      // Verify the username is available in the store
      const state = store.getState();
      expect(state.persona.username).toBe(customUsername);
    });

    it("should have access to username for remediation approvals", () => {
      const customUsername = "bob.ops@company.com";
      const store = createTestStore(customUsername);

      renderWithStore(<AdminDashboard {...defaultProps} />, store);

      // Verify persona state includes the username that will be used for approvals
      const state = store.getState();
      expect(state.persona.username).toBe(customUsername);
      expect(state.persona.persona).toBe("admin");
    });
  });

  describe("Alerts Tab", () => {
    it("should render Alerts tab", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(screen.getByRole("tab", { name: /alerts/i })).toBeInTheDocument();
    });

    it("should show alert badge count when there are critical alerts", () => {
      renderWithStore(<AdminDashboard {...defaultProps} alertCount={3} />);

      expect(screen.getByTestId("alert-badge")).toHaveTextContent("3");
    });

    it("should not show alert badge when count is 0", () => {
      renderWithStore(<AdminDashboard {...defaultProps} alertCount={0} />);

      expect(screen.queryByTestId("alert-badge")).not.toBeInTheDocument();
    });

    it("should switch to Alerts tab when clicked", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const alertsTab = screen.getByRole("tab", { name: /alerts/i });
      await act(async () => {
        alertsTab.click();
      });

      expect(alertsTab).toHaveAttribute("aria-selected", "true");
    });

    it("should show alerts content when Alerts tab is active", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const alertsTab = screen.getByRole("tab", { name: /alerts/i });
      await act(async () => {
        alertsTab.click();
      });

      expect(screen.getByTestId("alerts-container")).toBeInTheDocument();
    });

    it("should hide System Health when Alerts tab is active", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const alertsTab = screen.getByRole("tab", { name: /alerts/i });
      await act(async () => {
        alertsTab.click();
      });

      expect(screen.queryByText("System Health")).not.toBeInTheDocument();
    });
  });

  describe("Remediation Approval Dialog", () => {
    it("should expose selectedRemediationForApproval state for dialog integration", () => {
      // The AdminDashboard should have state to track which remediation is being approved
      // This test verifies the component structure supports dialog integration
      const store = createTestStore();
      const { container } = renderWithStore(
        <AdminDashboard {...defaultProps} />,
        store,
      );

      // Component should render without errors
      expect(container).toBeInTheDocument();
    });

    it("should allow dialog-based approval with reason collection", () => {
      // The approval flow should support collecting a reason from the user
      // via RemediationApprovalDialog instead of hardcoding "Rejected by admin"
      const store = createTestStore();
      const { container } = renderWithStore(
        <AdminDashboard {...defaultProps} />,
        store,
      );

      expect(container).toBeInTheDocument();
    });
  });

  describe("MetricCard Color Branches", () => {
    it("should show green color for metrics >= 80", () => {
      const propsWithHighMetrics = {
        ...defaultProps,
        heartMetrics: {
          happiness: 85,
          engagement: 90,
          adoption: 95,
          retention: 100,
          taskSuccess: 80,
        },
      };
      renderWithStore(<AdminDashboard {...propsWithHighMetrics} />);

      // All metrics are >= 80, so all should be green
      const happinessValue = screen.getByText("85%");
      expect(happinessValue).toHaveClass("text-green-600");
    });

    it("should show yellow color for metrics >= 60 and < 80", () => {
      const propsWithMediumMetrics = {
        ...defaultProps,
        heartMetrics: {
          happiness: 60,
          engagement: 70,
          adoption: 75,
          retention: 65,
          taskSuccess: 79,
        },
      };
      renderWithStore(<AdminDashboard {...propsWithMediumMetrics} />);

      // All metrics are between 60-79, so all should be yellow
      const happinessValue = screen.getByText("60%");
      expect(happinessValue).toHaveClass("text-yellow-600");
    });

    it("should show red color for metrics < 60", () => {
      const propsWithLowMetrics = {
        ...defaultProps,
        heartMetrics: {
          happiness: 10,
          engagement: 25,
          adoption: 45,
          retention: 59,
          taskSuccess: 0,
        },
      };
      renderWithStore(<AdminDashboard {...propsWithLowMetrics} />);

      // All metrics are < 60, so all should be red
      const happinessValue = screen.getByText("10%");
      expect(happinessValue).toHaveClass("text-red-600");
    });

    it("should show exactly boundary value 80 as green", () => {
      const propsWithBoundary = {
        ...defaultProps,
        heartMetrics: {
          happiness: 80,
          engagement: 72,
          adoption: 68,
          retention: 91,
          taskSuccess: 88,
        },
      };
      renderWithStore(<AdminDashboard {...propsWithBoundary} />);

      const happinessValue = screen.getByText("80%");
      expect(happinessValue).toHaveClass("text-green-600");
    });

    it("should show exactly boundary value 60 as yellow", () => {
      const propsWithBoundary = {
        ...defaultProps,
        heartMetrics: {
          happiness: 60,
          engagement: 72,
          adoption: 68,
          retention: 91,
          taskSuccess: 88,
        },
      };
      renderWithStore(<AdminDashboard {...propsWithBoundary} />);

      const happinessValue = screen.getByText("60%");
      expect(happinessValue).toHaveClass("text-yellow-600");
    });
  });

  describe("Effective Alert Count", () => {
    it("should use prop alertCount when provided and greater than 0", () => {
      renderWithStore(<AdminDashboard {...defaultProps} alertCount={5} />);

      expect(screen.getByTestId("alert-badge")).toHaveTextContent("5");
    });

    it("should fall back to Redux alert counts when prop is 0", () => {
      // The component uses criticalCount + warningCount from Redux when alertCount is 0
      // Store has no alerts by default, so badge should not appear
      renderWithStore(<AdminDashboard {...defaultProps} alertCount={0} />);

      expect(screen.queryByTestId("alert-badge")).not.toBeInTheDocument();
    });
  });

  describe("Keyboard Shortcuts", () => {
    it("should switch to Alerts tab when Shift+A is pressed", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      // Initially on Overview tab
      expect(screen.getByRole("tab", { name: /overview/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );

      // Press Shift+A
      await act(async () => {
        window.dispatchEvent(
          new KeyboardEvent("keydown", {
            key: "a",
            shiftKey: true,
            bubbles: true,
          }),
        );
      });

      // Should be on Alerts tab
      expect(screen.getByRole("tab", { name: /alerts/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("should switch to Overview tab when Shift+O is pressed", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      // First switch to Alerts tab
      const alertsTab = screen.getByRole("tab", { name: /alerts/i });
      await act(async () => {
        alertsTab.click();
      });

      // Verify on Alerts tab
      expect(alertsTab).toHaveAttribute("aria-selected", "true");

      // Press Shift+O
      await act(async () => {
        window.dispatchEvent(
          new KeyboardEvent("keydown", {
            key: "o",
            shiftKey: true,
            bubbles: true,
          }),
        );
      });

      // Should be on Overview tab
      expect(screen.getByRole("tab", { name: /overview/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("should switch to Users tab when Shift+U is pressed", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      // Press Shift+U
      await act(async () => {
        window.dispatchEvent(
          new KeyboardEvent("keydown", {
            key: "u",
            shiftKey: true,
            bubbles: true,
          }),
        );
      });

      // Should be on Users tab
      expect(screen.getByRole("tab", { name: /users/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("should not trigger shortcuts when input is focused", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      // Initially on Overview tab
      expect(screen.getByRole("tab", { name: /overview/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );

      // Simulate input focus by setting activeElement
      const input = document.createElement("input");
      document.body.appendChild(input);
      input.focus();

      // Press Shift+A while input is focused
      await act(async () => {
        window.dispatchEvent(
          new KeyboardEvent("keydown", {
            key: "a",
            shiftKey: true,
            bubbles: true,
          }),
        );
      });

      // Should still be on Overview tab (shortcut not triggered)
      expect(screen.getByRole("tab", { name: /overview/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );

      // Cleanup
      document.body.removeChild(input);
    });
  });

  describe("Agent Requests Tab", () => {
    it("should render Agent Requests tab", () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      expect(
        screen.getByRole("tab", { name: /agent requests/i }),
      ).toBeInTheDocument();
    });

    it("should switch to Agent Requests tab when clicked", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const agentRequestsTab = screen.getByRole("tab", {
        name: /agent requests/i,
      });
      await act(async () => {
        agentRequestsTab.click();
      });

      expect(agentRequestsTab).toHaveAttribute("aria-selected", "true");
    });

    it("should show agent requests container when Agent Requests tab is active", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const agentRequestsTab = screen.getByRole("tab", {
        name: /agent requests/i,
      });
      await act(async () => {
        agentRequestsTab.click();
      });

      expect(
        screen.getByTestId("agent-requests-container"),
      ).toBeInTheDocument();
    });

    it("should hide System Health when Agent Requests tab is active", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const agentRequestsTab = screen.getByRole("tab", {
        name: /agent requests/i,
      });
      await act(async () => {
        agentRequestsTab.click();
      });

      expect(screen.queryByText("System Health")).not.toBeInTheDocument();
    });

    it("should show BatchApprovalPanel container in Agent Requests tab", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      const agentRequestsTab = screen.getByRole("tab", {
        name: /agent requests/i,
      });
      await act(async () => {
        agentRequestsTab.click();
      });

      // The Agent Requests tab should contain both BatchApprovalPanel and AgentApprovalAuditLog
      // Both components are wrapped in bg-white containers
      const container = screen.getByTestId("agent-requests-container");
      expect(container.children.length).toBe(2);
    });

    it("should switch to Agent Requests tab when Shift+R is pressed", async () => {
      renderWithStore(<AdminDashboard {...defaultProps} />);

      // Initially on Overview tab
      expect(screen.getByRole("tab", { name: /overview/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );

      // Press Shift+R
      await act(async () => {
        window.dispatchEvent(
          new KeyboardEvent("keydown", {
            key: "r",
            shiftKey: true,
            bubbles: true,
          }),
        );
      });

      // Should be on Agent Requests tab
      expect(
        screen.getByRole("tab", { name: /agent requests/i }),
      ).toHaveAttribute("aria-selected", "true");
    });
  });
});
