/**
 * AdminDashboard Tests
 *
 * Tests for the Admin dashboard component with system health metrics.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { AdminDashboard } from "./AdminDashboard";

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
      render(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("Admin Dashboard")).toBeInTheDocument();
    });

    it("should render system health section", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("System Health")).toBeInTheDocument();
    });

    it("should render HEART metrics section", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("HEART Metrics")).toBeInTheDocument();
    });

    it("should display uptime percentage", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("99.9%")).toBeInTheDocument();
    });

    it("should display active users count", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("150")).toBeInTheDocument();
    });

    it("should display health status indicator", () => {
      render(<AdminDashboard {...defaultProps} />);

      const healthIndicator = screen.getByTestId("health-status");
      expect(healthIndicator).toHaveClass("bg-green-500");
    });
  });

  describe("Health Status Variants", () => {
    it("should show green indicator for healthy status", () => {
      render(<AdminDashboard {...defaultProps} />);

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

      render(<AdminDashboard {...props} />);

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

      render(<AdminDashboard {...props} />);

      const indicator = screen.getByTestId("health-status");
      expect(indicator).toHaveClass("bg-red-500");
    });
  });

  describe("HEART Metrics", () => {
    it("should display all five HEART metrics", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("Happiness")).toBeInTheDocument();
      expect(screen.getByText("Engagement")).toBeInTheDocument();
      expect(screen.getByText("Adoption")).toBeInTheDocument();
      expect(screen.getByText("Retention")).toBeInTheDocument();
      expect(screen.getByText("Task Success")).toBeInTheDocument();
    });

    it("should display metric values", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(screen.getByText("85%")).toBeInTheDocument(); // Happiness
      expect(screen.getByText("72%")).toBeInTheDocument(); // Engagement
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(<AdminDashboard {...defaultProps} isLoading={true} />);

      expect(screen.getByTestId("dashboard-loading")).toBeInTheDocument();
    });

    it("should hide content when loading", () => {
      render(<AdminDashboard {...defaultProps} isLoading={true} />);

      expect(screen.queryByText("System Health")).not.toBeInTheDocument();
    });
  });

  describe("Refresh", () => {
    it("should render refresh button", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /refresh/i }),
      ).toBeInTheDocument();
    });

    it("should call onRefresh when refresh button is clicked", async () => {
      const onRefresh = vi.fn();
      render(<AdminDashboard {...defaultProps} onRefresh={onRefresh} />);

      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      refreshButton.click();

      expect(onRefresh).toHaveBeenCalledTimes(1);
    });
  });

  describe("Tabs", () => {
    it("should render Overview and Users tabs", () => {
      render(<AdminDashboard {...defaultProps} />);

      expect(
        screen.getByRole("tab", { name: /overview/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /users/i })).toBeInTheDocument();
    });

    it("should show Overview tab as active by default", () => {
      render(<AdminDashboard {...defaultProps} />);

      const overviewTab = screen.getByRole("tab", { name: /overview/i });
      expect(overviewTab).toHaveAttribute("aria-selected", "true");
    });

    it("should switch to Users tab when clicked", async () => {
      render(<AdminDashboard {...defaultProps} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(usersTab).toHaveAttribute("aria-selected", "true");
    });

    it("should show user management content when Users tab is active", async () => {
      render(<AdminDashboard {...defaultProps} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(screen.getByText("User Management")).toBeInTheDocument();
    });

    it("should hide System Health when Users tab is active", async () => {
      render(<AdminDashboard {...defaultProps} />);

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
      render(<AdminDashboard {...userManagementProps} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(screen.getByText("Alice")).toBeInTheDocument();
      expect(screen.getByText("alice@test.com")).toBeInTheDocument();
    });

    it("should show loading state for users when usersLoading is true", async () => {
      render(<AdminDashboard {...userManagementProps} usersLoading={true} />);

      const usersTab = screen.getByRole("tab", { name: /users/i });
      await act(async () => {
        usersTab.click();
      });

      expect(screen.getByTestId("user-loading")).toBeInTheDocument();
    });
  });
});
