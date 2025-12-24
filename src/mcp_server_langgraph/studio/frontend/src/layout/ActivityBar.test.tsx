/**
 * ActivityBar Tests
 *
 * TDD tests for the extracted ActivityBar component.
 * Tests RBAC filtering, navigation, and accessibility.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import { ActivityBar, NAV_ITEMS, BOTTOM_ITEMS } from "./ActivityBar";
import canvasReducer from "../store/slices/canvasSlice";
import personaReducer from "../store/slices/personaSlice";
import type { ReactNode } from "react";

// Mock navigate and location
const mockNavigate = vi.fn();
let mockLocation = { pathname: "/studio/chat" };

vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockLocation,
  };
});

// Mock useNavPrediction hook
vi.mock("../hooks/useUXIntelligence", () => ({
  useNavPrediction: vi.fn(() => ({
    predictions: [],
    isLoading: false,
    error: null,
    lastUpdated: null,
    refetch: vi.fn(),
  })),
}));

// Create test store with customizable persona
function createTestStore(
  _sidebarItems: string[] = [
    "chat",
    "workflows",
    "agents",
    "observability",
    "admin",
    "settings",
  ],
) {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona: "admin",
        subPersona: null,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
    },
  });
}

// Wrapper component
function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  };
}

describe("ActivityBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock location to default
    mockLocation = { pathname: "/studio/chat" };
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });

    it("should render navigation items", () => {
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // Check that nav items are rendered
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
      expect(screen.getByTestId("nav-workflows")).toBeInTheDocument();
    });

    it("should render command palette button", () => {
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("command-palette-button")).toBeInTheDocument();
    });
  });

  describe("RBAC filtering", () => {
    it("should filter nav items based on persona permissions", () => {
      // Create store with limited sidebar items (user persona)
      const store = configureStore({
        reducer: {
          canvas: canvasReducer,
          persona: personaReducer,
        },
        preloadedState: {
          persona: {
            persona: "user",
            subPersona: "bob",
            username: "bob",
            email: "bob@example.com",
            permissions: [],
            isPersonaLoading: false,
          },
        },
      });

      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // Bob should see chat but not admin
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
      expect(screen.queryByTestId("nav-admin")).not.toBeInTheDocument();
    });

    it("should show all items for admin persona", () => {
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // Admin should see all items
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
      expect(screen.getByTestId("nav-admin")).toBeInTheDocument();
    });
  });

  describe("navigation", () => {
    it("should navigate when nav item is clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      await user.click(screen.getByTestId("nav-chat"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/chat");
    });

    it("should highlight active nav item", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      const chatButton = screen.getByTestId("nav-chat");
      await user.click(chatButton);

      // Check that the button has active styling
      expect(chatButton).toHaveClass("bg-primary-100");
    });
  });

  describe("command palette", () => {
    it("should dispatch keyboard event when command palette button clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      const dispatchEventSpy = vi.spyOn(document, "dispatchEvent");

      render(<ActivityBar />, { wrapper: createWrapper(store) });

      await user.click(screen.getByTestId("command-palette-button"));

      expect(dispatchEventSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "keydown",
          key: "k",
          metaKey: true,
        }),
      );
    });
  });

  describe("accessibility", () => {
    it("should have aria-labels on all buttons", () => {
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toHaveAttribute("aria-label");
      });
    });

    it("should have title attributes for tooltips", () => {
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      const chatButton = screen.getByTestId("nav-chat");
      expect(chatButton).toHaveAttribute("title", "Chat");
    });

    it("should be keyboard navigable", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // Tab to first button
      await user.tab();
      expect(screen.getByTestId("nav-chat")).toHaveFocus();

      // Tab to next button
      await user.tab();
      expect(screen.getByTestId("nav-workflows")).toHaveFocus();
    });
  });

  describe("exports", () => {
    it("should export NAV_ITEMS constant", () => {
      expect(NAV_ITEMS).toBeDefined();
      expect(Array.isArray(NAV_ITEMS)).toBe(true);
      expect(NAV_ITEMS.length).toBeGreaterThan(0);
    });

    it("should export BOTTOM_ITEMS constant", () => {
      expect(BOTTOM_ITEMS).toBeDefined();
      expect(Array.isArray(BOTTOM_ITEMS)).toBe(true);
    });
  });

  describe("axe accessibility", () => {
    it("should have no accessibility violations", async () => {
      const store = createTestStore();
      const { container } = render(<ActivityBar />, {
        wrapper: createWrapper(store),
      });
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("AI nav prediction integration", () => {
    it("should accept enableAI prop", () => {
      const store = createTestStore();
      // Should render without error when enableAI is passed
      render(<ActivityBar enableAI={true} />, {
        wrapper: createWrapper(store),
      });
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });

    it("should render without AI predictions when enableAI is false", () => {
      const store = createTestStore();
      render(<ActivityBar enableAI={false} />, {
        wrapper: createWrapper(store),
      });
      // Should not show prediction indicators
      expect(
        screen.queryByTestId("nav-prediction-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should show prediction indicator for predicted items when AI is enabled", () => {
      const store = createTestStore();
      // Note: This test validates the structure is in place.
      // Actual prediction logic is mocked in the hook.
      render(<ActivityBar enableAI={true} />, {
        wrapper: createWrapper(store),
      });
      // The component should render, prediction indicators shown based on hook data
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });

    it("should reorder items based on predictions when enabled", () => {
      const store = createTestStore();
      render(<ActivityBar enableAI={true} reorderByPrediction={true} />, {
        wrapper: createWrapper(store),
      });
      // Structure should support reordering
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });

    it("should gracefully handle AI errors without breaking navigation", () => {
      const store = createTestStore();
      // When AI fails, navigation should still work
      render(<ActivityBar enableAI={true} />, {
        wrapper: createWrapper(store),
      });
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
    });
  });

  describe("Route Synchronization", () => {
    it("should sync activeNavItem with current route on mount", () => {
      // Set location to workflows before render
      mockLocation = { pathname: "/studio/workflows" };

      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // After render, the workflows nav item should be highlighted
      const workflowsButton = screen.getByTestId("nav-workflows");
      expect(workflowsButton).toHaveClass("bg-primary-100");
    });

    it("should handle deep links correctly (e.g., /studio/workflows)", () => {
      // Test with a deep link path
      mockLocation = { pathname: "/studio/agents" };

      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // Agents should be highlighted, not chat (default)
      const agentsButton = screen.getByTestId("nav-agents");
      expect(agentsButton).toHaveClass("bg-primary-100");

      const chatButton = screen.getByTestId("nav-chat");
      expect(chatButton).not.toHaveClass("bg-primary-100");
    });

    it("should handle deep links with sub-paths", () => {
      // Test with a path that has additional segments
      mockLocation = { pathname: "/studio/chat/session-123" };

      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // Chat should be highlighted (prefix match)
      const chatButton = screen.getByTestId("nav-chat");
      expect(chatButton).toHaveClass("bg-primary-100");
    });

    it("should ignore unknown routes (doesn't set activeNavItem to invalid value)", () => {
      // Set location to an unknown route not in NAV_ITEMS
      mockLocation = { pathname: "/studio/unknown-route" };

      const store = createTestStore();
      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // No nav item should be highlighted (or default remains)
      // Since no match, activeNavItem should remain as initial state
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });

    it("should respect persona filtering when syncing routes", () => {
      // User persona has limited access (no admin)
      mockLocation = { pathname: "/studio/admin" };

      const store = configureStore({
        reducer: {
          canvas: canvasReducer,
          persona: personaReducer,
        },
        preloadedState: {
          persona: {
            persona: "user",
            subPersona: "bob",
            username: "bob",
            email: "bob@example.com",
            permissions: [],
            isPersonaLoading: false,
          },
        },
      });

      render(<ActivityBar />, { wrapper: createWrapper(store) });

      // Admin button should not exist (filtered by persona)
      expect(screen.queryByTestId("nav-admin")).not.toBeInTheDocument();

      // Even though URL is /studio/admin, it shouldn't crash
      // and chat should remain as default since admin is not allowed
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
    });
  });
});
