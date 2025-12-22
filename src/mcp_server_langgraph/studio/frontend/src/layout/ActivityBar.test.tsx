/**
 * ActivityBar Tests
 *
 * TDD tests for the extracted ActivityBar component.
 * Tests RBAC filtering, navigation, and accessibility.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
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

// Mock navigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Create test store with customizable persona
function createTestStore(_sidebarItems: string[] = ["chat", "workflows", "agents", "observability", "admin", "settings"]) {
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

      expect(mockNavigate).toHaveBeenCalledWith("/studio/v2/chat");
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
        })
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
});
