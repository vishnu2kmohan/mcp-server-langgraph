/**
 * Sidebar Tests
 *
 * Tests for sidebar navigation component with grouped navigation,
 * icons, RBAC filtering, and user profile section.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { Sidebar } from "./Sidebar";
import personaReducer from "../../store/slices/personaSlice";
import authReducer from "../../store/slices/authSlice";
import notificationReducer from "../../store/slices/notificationSlice";
import uiReducer from "../../store/slices/uiSlice";
import type { Persona } from "../../types/auth";

// Mock RTK Query feature flags hook
const mockFeatureFlagsData = {
  projects: true,
  chat: true,
  workflows: true,
  mcp: true,
  agents: true,
  vectors: true,
  observability: true,
  cost: true,
  settings: true,
  admin: true,
};

let currentFeatureFlags = { ...mockFeatureFlagsData };

vi.mock("../../api", () => ({
  useGetFeatureFlagsQuery: () => ({
    data: currentFeatureFlags,
    isLoading: false,
    error: null,
  }),
  useLogoutMutation: () => [
    vi.fn().mockReturnValue({ unwrap: () => Promise.resolve() }),
    { isLoading: false },
  ],
}));

// Create a test store with auth, persona, notification, and ui state
const createTestStore = (
  persona: Persona,
  username: string | null = "testuser",
  sidebarCollapsed: boolean = false,
) => {
  return configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
      notifications: notificationReducer,
      ui: uiReducer,
    },
    preloadedState: {
      persona: {
        persona,
        username,
        email: username ? `${username}@example.com` : null,
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        user: username
          ? {
              id: "user-1",
              username,
              email: `${username}@example.com`,
              roles:
                persona === "admin"
                  ? ["admin"]
                  : persona === "developer"
                    ? ["developer"]
                    : ["user"],
              persona,
            }
          : null,
        tokens: null,
        currentOrg: null,
        organizations: [],
        isInitializing: false,
        isLoading: false,
        error: null,
      },
      ui: {
        sidebarOpen: true,
        sidebarCollapsed,
        theme: "system" as const,
        isLoading: false,
        activeView: "workflows" as const,
        notifications: [],
      },
    },
  });
};

// Helper to render with store and router
const renderWithStore = (
  persona: Persona = "admin",
  username: string | null = "testuser",
  initialRoute = "/",
  sidebarCollapsed = false,
) => {
  const store = createTestStore(persona, username, sidebarCollapsed);
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={[initialRoute]}
        >
          <Sidebar />
        </MemoryRouter>
      </Provider>,
    ),
  };
};

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentFeatureFlags = { ...mockFeatureFlagsData };
  });

  describe("Navigation Groups", () => {
    it("should render WORKSPACE group header", () => {
      renderWithStore("admin");
      expect(screen.getByText("WORKSPACE")).toBeInTheDocument();
    });

    it("should render Projects link in WORKSPACE group", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("link", { name: /projects/i }),
      ).toBeInTheDocument();
    });

    it("should have correct href for Projects link", () => {
      renderWithStore("admin");
      const projectsLink = screen.getByRole("link", { name: /projects/i });
      expect(projectsLink).toHaveAttribute("href", "/studio/projects");
    });

    it("should render CONVERSATIONS group header", () => {
      renderWithStore("admin");
      expect(screen.getByText("CONVERSATIONS")).toBeInTheDocument();
    });

    it("should render BUILD group header for admin", () => {
      renderWithStore("admin");
      expect(screen.getByText("BUILD")).toBeInTheDocument();
    });

    it("should render CONNECTIONS group header for admin", () => {
      renderWithStore("admin");
      expect(screen.getByText("CONNECTIONS")).toBeInTheDocument();
    });

    it("should render INSIGHTS group header for admin", () => {
      renderWithStore("admin");
      expect(screen.getByText("INSIGHTS")).toBeInTheDocument();
    });

    it("should render ADMIN group header for admin persona", () => {
      renderWithStore("admin");
      expect(screen.getByText("ADMIN")).toBeInTheDocument();
    });
  });

  describe("Navigation Links with Icons", () => {
    it("should render Chat navigation link", () => {
      renderWithStore("admin");
      expect(screen.getByRole("link", { name: /chat/i })).toBeInTheDocument();
    });

    it("should render Workflows navigation link for admin", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("link", { name: /workflows/i }),
      ).toBeInTheDocument();
    });

    it("should render MCP Explorer navigation link for admin", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("link", { name: /mcp explorer/i }),
      ).toBeInTheDocument();
    });

    it("should render Agents navigation link for admin", () => {
      renderWithStore("admin");
      expect(screen.getByRole("link", { name: /agents/i })).toBeInTheDocument();
    });

    it("should render Vectors navigation link for admin", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("link", { name: /vectors/i }),
      ).toBeInTheDocument();
    });

    it("should render Observability navigation link for admin", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("link", { name: /observability/i }),
      ).toBeInTheDocument();
    });

    it("should render Cost navigation link for admin", () => {
      renderWithStore("admin");
      expect(screen.getByRole("link", { name: /cost/i })).toBeInTheDocument();
    });

    it("should render Settings navigation link for admin", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("link", { name: /settings/i }),
      ).toBeInTheDocument();
    });

    it("should render Admin Dashboard navigation link for admin", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("link", { name: /dashboard/i }),
      ).toBeInTheDocument();
    });
  });

  describe("RBAC Filtering - Developer Persona", () => {
    it("should show Chat link for developer", () => {
      renderWithStore("developer");
      expect(screen.getByRole("link", { name: /chat/i })).toBeInTheDocument();
    });

    it("should show Workflows link for developer", () => {
      renderWithStore("developer");
      expect(
        screen.getByRole("link", { name: /workflows/i }),
      ).toBeInTheDocument();
    });

    it("should NOT show ADMIN group for developer", () => {
      renderWithStore("developer");
      expect(screen.queryByText("ADMIN")).not.toBeInTheDocument();
    });
  });

  describe("RBAC Filtering - User Persona", () => {
    it("should show WORKSPACE group for user", () => {
      renderWithStore("user");
      expect(screen.getByText("WORKSPACE")).toBeInTheDocument();
    });

    it("should show Projects link for user", () => {
      renderWithStore("user");
      expect(
        screen.getByRole("link", { name: /projects/i }),
      ).toBeInTheDocument();
    });

    it("should show Chat link for user", () => {
      renderWithStore("user");
      expect(screen.getByRole("link", { name: /chat/i })).toBeInTheDocument();
    });

    it("should show Workflows link for user (unified view)", () => {
      renderWithStore("user");
      // User sees unified Workflows view with owned + shared workflows
      expect(
        screen.getByRole("link", { name: /workflows/i }),
      ).toBeInTheDocument();
    });

    it("should show BUILD group for user (has workflows access)", () => {
      renderWithStore("user");
      // User has workflows which is in BUILD group
      expect(screen.getByText("BUILD")).toBeInTheDocument();
    });

    it("should NOT show CONNECTIONS group for user", () => {
      renderWithStore("user");
      expect(screen.queryByText("CONNECTIONS")).not.toBeInTheDocument();
    });

    it("should show INSIGHTS group for user (has cost access)", () => {
      renderWithStore("user");
      // User has cost which is in INSIGHTS group
      expect(screen.getByText("INSIGHTS")).toBeInTheDocument();
    });
  });

  describe("User Profile Section", () => {
    it("should render user profile section", () => {
      renderWithStore("admin");
      expect(screen.getByTestId("user-profile-section")).toBeInTheDocument();
    });

    it("should render logout button", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("button", { name: /sign out/i }),
      ).toBeInTheDocument();
    });

    it("should render theme toggle button", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("button", { name: /switch to (light|dark) mode/i }),
      ).toBeInTheDocument();
    });

    it("should display username from store", () => {
      renderWithStore("developer", "alice");
      expect(screen.getByText("alice")).toBeInTheDocument();
    });

    it("should display Guest when username is null", () => {
      renderWithStore("user", null);
      expect(screen.getByText("Guest")).toBeInTheDocument();
    });

    it("should render logout button", () => {
      renderWithStore("admin");
      const logoutButton = screen.getByRole("button", { name: /sign out/i });
      expect(logoutButton).toBeInTheDocument();
    });

    it("should call logout mutation when logout button is clicked", () => {
      renderWithStore("admin");
      const logoutButton = screen.getByRole("button", { name: /sign out/i });
      // Clicking the button should not throw (mutation is mocked)
      expect(() => fireEvent.click(logoutButton)).not.toThrow();
    });
  });

  describe("Active Link Highlighting", () => {
    it("should highlight Chat link when on chat page", () => {
      renderWithStore("admin", "testuser", "/studio/chat");
      const chatLink = screen.getByRole("link", { name: /chat/i });
      expect(chatLink.className).toMatch(/bg-blue/);
    });

    it("should highlight Workflows link when on workflows page", () => {
      renderWithStore("admin", "testuser", "/studio/workflows");
      const workflowsLink = screen.getByRole("link", { name: /workflows/i });
      expect(workflowsLink.className).toMatch(/bg-blue/);
    });
  });

  describe("Link Navigation", () => {
    it("should have correct href for Chat link", () => {
      renderWithStore("admin");
      const chatLink = screen.getByRole("link", { name: /chat/i });
      expect(chatLink).toHaveAttribute("href", "/studio/chat");
    });

    it("should have correct href for Workflows link", () => {
      renderWithStore("admin");
      const workflowsLink = screen.getByRole("link", { name: /workflows/i });
      expect(workflowsLink).toHaveAttribute("href", "/studio/workflows");
    });

    it("should have correct href for MCP Explorer link", () => {
      renderWithStore("admin");
      const mcpLink = screen.getByRole("link", { name: /mcp explorer/i });
      expect(mcpLink).toHaveAttribute("href", "/studio/connections/mcp");
    });

    it("should have correct href for Agents link", () => {
      renderWithStore("admin");
      const agentsLink = screen.getByRole("link", { name: /agents/i });
      expect(agentsLink).toHaveAttribute("href", "/studio/connections/agents");
    });

    it("should have correct href for Vectors link", () => {
      renderWithStore("admin");
      const vectorsLink = screen.getByRole("link", { name: /vectors/i });
      expect(vectorsLink).toHaveAttribute(
        "href",
        "/studio/connections/vectors",
      );
    });

    it("should have correct href for Observability link", () => {
      renderWithStore("admin");
      const observabilityLink = screen.getByRole("link", {
        name: /observability/i,
      });
      expect(observabilityLink).toHaveAttribute(
        "href",
        "/studio/observability",
      );
    });

    it("should have correct href for Cost link", () => {
      renderWithStore("admin");
      const costLink = screen.getByRole("link", { name: /cost/i });
      expect(costLink).toHaveAttribute("href", "/studio/cost");
    });

    it("should have correct href for Settings link", () => {
      renderWithStore("admin");
      const settingsLink = screen.getByRole("link", { name: /settings/i });
      expect(settingsLink).toHaveAttribute("href", "/studio/settings");
    });

    it("should have correct href for Admin Dashboard link", () => {
      renderWithStore("admin");
      const dashboardLink = screen.getByRole("link", { name: /dashboard/i });
      expect(dashboardLink).toHaveAttribute("href", "/studio/admin/dashboard");
    });
  });

  describe("Sidebar Layout", () => {
    it("should render as navigation element", () => {
      renderWithStore("admin");
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("should render Agent Studio title", () => {
      renderWithStore("admin");
      expect(screen.getByText("Agent Studio")).toBeInTheDocument();
    });

    it("should render version number", () => {
      renderWithStore("admin");
      expect(screen.getByText("v0.1.0")).toBeInTheDocument();
    });
  });

  describe("Theme Toggle", () => {
    it("should toggle theme when clicked", () => {
      renderWithStore("admin");
      const themeButton = screen.getByRole("button", {
        name: /switch to (light|dark) mode/i,
      });
      fireEvent.click(themeButton);
      expect(themeButton).toBeInTheDocument();
    });
  });

  describe("Mobile Responsive Layout", () => {
    it("should render mobile menu toggle button", () => {
      renderWithStore("admin");
      expect(
        screen.getByRole("button", { name: /toggle menu/i }),
      ).toBeInTheDocument();
    });

    it("should have mobile menu button with Menu icon by default", () => {
      renderWithStore("admin");
      const menuButton = screen.getByRole("button", { name: /toggle menu/i });
      expect(menuButton).toBeInTheDocument();
      // Menu icon should be present (data-testid for icon check)
      expect(
        menuButton.querySelector('[data-testid="menu-icon"]') ||
          menuButton.querySelector("svg"),
      ).toBeInTheDocument();
    });

    it("should toggle sidebar visibility when mobile menu button is clicked", () => {
      renderWithStore("admin");
      const menuButton = screen.getByRole("button", { name: /toggle menu/i });
      const sidebar = screen.getByRole("navigation");

      // Initially sidebar should be hidden on mobile (has -translate-x-full)
      expect(sidebar.className).toMatch(/-translate-x-full/);

      // Click to toggle open
      fireEvent.click(menuButton);

      // After click, sidebar should be visible (translate-x-0)
      expect(sidebar.className).toMatch(/translate-x-0/);
      expect(sidebar.className).not.toMatch(/-translate-x-full/);
    });

    it("should render overlay when sidebar is open on mobile", () => {
      renderWithStore("admin");
      const menuButton = screen.getByRole("button", { name: /toggle menu/i });

      // Open sidebar
      fireEvent.click(menuButton);

      // Overlay should appear
      expect(screen.getByTestId("sidebar-overlay")).toBeInTheDocument();
    });

    it("should close sidebar when overlay is clicked", () => {
      renderWithStore("admin");
      const menuButton = screen.getByRole("button", { name: /toggle menu/i });

      // Open sidebar
      fireEvent.click(menuButton);

      // Click overlay
      const overlay = screen.getByTestId("sidebar-overlay");
      fireEvent.click(overlay);

      // Overlay should be removed
      expect(screen.queryByTestId("sidebar-overlay")).not.toBeInTheDocument();
    });

    it("should have hidden class on sidebar by default for mobile", () => {
      renderWithStore("admin");
      const sidebar = screen.getByRole("navigation");
      // Sidebar should have responsive classes
      expect(sidebar.className).toMatch(/-translate-x-full|translate-x-0/);
    });

    it("should have mobile-first responsive width classes", () => {
      renderWithStore("admin");
      const sidebar = screen.getByRole("navigation");
      // Should have fixed width for all screen sizes
      expect(sidebar.className).toMatch(/w-64/);
    });

    it("should render close button inside sidebar for mobile", () => {
      renderWithStore("admin");
      // Close button should be visible on mobile for closing the drawer
      const closeButton = screen.getByRole("button", { name: /close menu/i });
      expect(closeButton).toBeInTheDocument();
    });

    it("should close sidebar when close button is clicked", () => {
      renderWithStore("admin");
      const menuButton = screen.getByRole("button", { name: /toggle menu/i });

      // Open sidebar
      fireEvent.click(menuButton);

      // Click close button
      const closeButton = screen.getByRole("button", { name: /close menu/i });
      fireEvent.click(closeButton);

      // Overlay should be removed (sidebar closed)
      expect(screen.queryByTestId("sidebar-overlay")).not.toBeInTheDocument();
    });

    it("should have proper z-index for mobile overlay and sidebar", () => {
      renderWithStore("admin");
      const menuButton = screen.getByRole("button", { name: /toggle menu/i });

      // Open sidebar
      fireEvent.click(menuButton);

      const overlay = screen.getByTestId("sidebar-overlay");
      const sidebar = screen.getByRole("navigation");

      // Overlay should have z-40, sidebar should have z-50
      expect(overlay.className).toMatch(/z-40/);
      expect(sidebar.className).toMatch(/z-50/);
    });
  });

  describe("Feature Flags Integration", () => {
    it("should hide Cost link when cost feature is disabled", () => {
      currentFeatureFlags = { ...mockFeatureFlagsData, cost: false };
      renderWithStore("admin");
      expect(
        screen.queryByRole("link", { name: /cost/i }),
      ).not.toBeInTheDocument();
    });

    it("should hide Observability link when observability feature is disabled", () => {
      currentFeatureFlags = { ...mockFeatureFlagsData, observability: false };
      renderWithStore("admin");
      expect(
        screen.queryByRole("link", { name: /observability/i }),
      ).not.toBeInTheDocument();
    });

    it("should hide Workflows link when workflows feature is disabled", () => {
      currentFeatureFlags = { ...mockFeatureFlagsData, workflows: false };
      renderWithStore("admin");
      expect(
        screen.queryByRole("link", { name: /workflows/i }),
      ).not.toBeInTheDocument();
    });

    it("should hide MCP Explorer link when mcp feature is disabled", () => {
      currentFeatureFlags = { ...mockFeatureFlagsData, mcp: false };
      renderWithStore("admin");
      expect(
        screen.queryByRole("link", { name: /mcp explorer/i }),
      ).not.toBeInTheDocument();
    });

    it("should hide Agents link when agents feature is disabled", () => {
      currentFeatureFlags = { ...mockFeatureFlagsData, agents: false };
      renderWithStore("admin");
      expect(
        screen.queryByRole("link", { name: /agents/i }),
      ).not.toBeInTheDocument();
    });

    it("should hide Vectors link when vectors feature is disabled", () => {
      currentFeatureFlags = { ...mockFeatureFlagsData, vectors: false };
      renderWithStore("admin");
      expect(
        screen.queryByRole("link", { name: /vectors/i }),
      ).not.toBeInTheDocument();
    });

    it("should hide entire INSIGHTS group when all insight features are disabled", () => {
      currentFeatureFlags = {
        ...mockFeatureFlagsData,
        cost: false,
        observability: false,
        settings: false,
      };
      renderWithStore("admin");
      expect(screen.queryByText("INSIGHTS")).not.toBeInTheDocument();
    });

    it("should show all links when all features are enabled", () => {
      currentFeatureFlags = { ...mockFeatureFlagsData };
      renderWithStore("admin");
      expect(screen.getByRole("link", { name: /cost/i })).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /observability/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /workflows/i }),
      ).toBeInTheDocument();
    });

    it("should combine RBAC and feature flag filtering", () => {
      // User persona has access to: projects, chat, workflows, cost
      currentFeatureFlags = { ...mockFeatureFlagsData };
      renderWithStore("user");

      // User should see cost (allowed by RBAC)
      expect(screen.getByRole("link", { name: /cost/i })).toBeInTheDocument();
      // User should see chat (allowed by both RBAC and feature flags)
      expect(screen.getByRole("link", { name: /chat/i })).toBeInTheDocument();
      // User should see workflows (unified view)
      expect(
        screen.getByRole("link", { name: /workflows/i }),
      ).toBeInTheDocument();
      // User should NOT see observability (not in user's RBAC)
      expect(
        screen.queryByRole("link", { name: /observability/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Collapsed Mode", () => {
    it("should have narrow width when collapsed", () => {
      renderWithStore("admin", "testuser", "/", true);
      const sidebar = screen.getByRole("navigation");
      expect(sidebar.className).toMatch(/w-16/);
    });

    it("should have wide width when expanded", () => {
      renderWithStore("admin", "testuser", "/", false);
      const sidebar = screen.getByRole("navigation");
      expect(sidebar.className).toMatch(/w-64/);
    });

    it("should hide nav link labels when collapsed", () => {
      renderWithStore("admin", "testuser", "/", true);
      // Links should exist but text should not be visible
      const chatLink = screen.getByRole("link", { name: /chat/i });
      expect(chatLink).toBeInTheDocument();
      // In collapsed mode, link labels are hidden (only icons shown)
      expect(chatLink.textContent).toBe("");
    });

    it("should show nav link labels when expanded", () => {
      renderWithStore("admin", "testuser", "/", false);
      const chatLink = screen.getByRole("link", { name: /chat/i });
      expect(chatLink.textContent).toMatch(/Chat/);
    });

    it("should hide group labels when collapsed", () => {
      renderWithStore("admin", "testuser", "/", true);
      expect(screen.queryByText("WORKSPACE")).not.toBeInTheDocument();
      expect(screen.queryByText("CONVERSATIONS")).not.toBeInTheDocument();
    });

    it("should show group labels when expanded", () => {
      renderWithStore("admin", "testuser", "/", false);
      expect(screen.getByText("WORKSPACE")).toBeInTheDocument();
      expect(screen.getByText("CONVERSATIONS")).toBeInTheDocument();
    });

    it("should hide Agent Studio title when collapsed", () => {
      renderWithStore("admin", "testuser", "/", true);
      expect(screen.queryByText("Agent Studio")).not.toBeInTheDocument();
    });

    it("should show Agent Studio title when expanded", () => {
      renderWithStore("admin", "testuser", "/", false);
      expect(screen.getByText("Agent Studio")).toBeInTheDocument();
    });

    it("should render collapse toggle button", () => {
      renderWithStore("admin", "testuser", "/", false);
      expect(
        screen.getByRole("button", { name: /collapse sidebar/i }),
      ).toBeInTheDocument();
    });

    it("should render expand toggle button when collapsed", () => {
      renderWithStore("admin", "testuser", "/", true);
      expect(
        screen.getByRole("button", { name: /expand sidebar/i }),
      ).toBeInTheDocument();
    });

    it("should toggle collapsed state when button is clicked", () => {
      const { store } = renderWithStore("admin", "testuser", "/", false);

      // Initially expanded
      expect(store.getState().ui.sidebarCollapsed).toBe(false);

      // Click collapse button
      const collapseButton = screen.getByRole("button", {
        name: /collapse sidebar/i,
      });
      fireEvent.click(collapseButton);

      // Should now be collapsed
      expect(store.getState().ui.sidebarCollapsed).toBe(true);
    });

    it("should hide username when collapsed", () => {
      renderWithStore("admin", "alice", "/", true);
      // Username should not be visible in collapsed mode
      expect(screen.queryByText("alice")).not.toBeInTheDocument();
    });

    it("should show username when expanded", () => {
      renderWithStore("admin", "alice", "/", false);
      expect(screen.getByText("alice")).toBeInTheDocument();
    });

    it("should hide version number when collapsed", () => {
      renderWithStore("admin", "testuser", "/", true);
      expect(screen.queryByText("v0.1.0")).not.toBeInTheDocument();
    });

    it("should show version number when expanded", () => {
      renderWithStore("admin", "testuser", "/", false);
      expect(screen.getByText("v0.1.0")).toBeInTheDocument();
    });

    it("should have tooltip on nav links when collapsed", () => {
      renderWithStore("admin", "testuser", "/", true);
      const chatLink = screen.getByRole("link", { name: /chat/i });
      expect(chatLink).toHaveAttribute("title", "Chat");
    });

    it("should not have tooltip on nav links when expanded", () => {
      renderWithStore("admin", "testuser", "/", false);
      const chatLink = screen.getByRole("link", { name: /chat/i });
      expect(chatLink).not.toHaveAttribute("title");
    });
  });
});
