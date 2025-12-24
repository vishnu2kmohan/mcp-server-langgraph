/**
 * TopBar Tests
 *
 * TDD tests for the TopBar component.
 * Tests branding, user info, and persona display.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { TopBar } from "./TopBar";
import personaReducer from "../store/slices/personaSlice";
import type { ReactNode } from "react";

// Create test store with customizable persona state
function createTestStore(overrides?: {
  username?: string;
  persona?: string;
  email?: string;
}) {
  return configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona: (overrides?.persona ?? "admin") as
          | "admin"
          | "developer"
          | "user",
        subPersona: null,
        username: overrides?.username ?? "testuser",
        email: overrides?.email ?? "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
    },
  });
}

// Wrapper component with Router for useNavigate in UserMenuDropdown
function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  };
}

describe("TopBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      const store = createTestStore();
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("top-bar")).toBeInTheDocument();
    });

    it("should display app branding", () => {
      const store = createTestStore();
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("app-branding")).toBeInTheDocument();
    });

    it("should display default title", () => {
      const store = createTestStore();
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Agent Studio")).toBeInTheDocument();
    });

    it("should display custom title when provided", () => {
      const store = createTestStore();
      render(<TopBar title="Custom Title" />, {
        wrapper: createWrapper(store),
      });

      expect(screen.getByText("Custom Title")).toBeInTheDocument();
    });
  });

  describe("user info", () => {
    it("should display username from store", () => {
      const store = createTestStore({ username: "alice" });
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByText("alice")).toBeInTheDocument();
    });

    it("should display persona badge", () => {
      const store = createTestStore({ persona: "admin" });
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("persona-badge")).toBeInTheDocument();
      expect(screen.getByText(/admin/i)).toBeInTheDocument();
    });

    it("should display developer persona badge", () => {
      const store = createTestStore({ persona: "developer" });
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByText(/developer/i)).toBeInTheDocument();
    });

    it("should display user persona badge", () => {
      const store = createTestStore({ persona: "user", username: "alice" });
      render(<TopBar />, { wrapper: createWrapper(store) });

      const badge = screen.getByTestId("persona-badge");
      expect(badge).toHaveTextContent("user");
    });
  });

  describe("user menu", () => {
    it("should render user avatar button", () => {
      const store = createTestStore({ username: "alice" });
      render(<TopBar />, { wrapper: createWrapper(store) });

      const avatarButton = screen.getByTestId("user-avatar");
      expect(avatarButton).toBeInTheDocument();
    });

    it("should display first letter of username as avatar", () => {
      const store = createTestStore({ username: "alice" });
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByText("A")).toBeInTheDocument();
    });

    it("should call onUserMenuClick when avatar clicked", async () => {
      const user = userEvent.setup();
      const onUserMenuClick = vi.fn();
      const store = createTestStore();
      render(<TopBar onUserMenuClick={onUserMenuClick} />, {
        wrapper: createWrapper(store),
      });

      await user.click(screen.getByTestId("user-avatar"));
      expect(onUserMenuClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("styling", () => {
    it("should apply custom className", () => {
      const store = createTestStore();
      render(<TopBar className="custom-class" />, {
        wrapper: createWrapper(store),
      });

      expect(screen.getByTestId("top-bar")).toHaveClass("custom-class");
    });

    it("should have proper dark mode classes", () => {
      const store = createTestStore();
      render(<TopBar />, { wrapper: createWrapper(store) });

      const topBar = screen.getByTestId("top-bar");
      expect(topBar).toHaveClass("dark:bg-gray-800");
    });
  });

  describe("pending approvals badge", () => {
    it("should display approvals badge when pendingApprovals > 0", () => {
      const store = createTestStore();
      render(
        <TopBar pendingApprovals={3} onPendingApprovalsClick={() => {}} />,
        { wrapper: createWrapper(store) },
      );

      const badge = screen.getByTestId("review-approval-button");
      expect(badge).toBeInTheDocument();
    });

    it("should display approval count in badge", () => {
      const store = createTestStore();
      render(
        <TopBar pendingApprovals={5} onPendingApprovalsClick={() => {}} />,
        { wrapper: createWrapper(store) },
      );

      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("should not display approvals badge when pendingApprovals is 0", () => {
      const store = createTestStore();
      render(
        <TopBar pendingApprovals={0} onPendingApprovalsClick={() => {}} />,
        { wrapper: createWrapper(store) },
      );

      expect(
        screen.queryByTestId("review-approval-button"),
      ).not.toBeInTheDocument();
    });

    it("should not display approvals badge when pendingApprovals is undefined", () => {
      const store = createTestStore();
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(
        screen.queryByTestId("review-approval-button"),
      ).not.toBeInTheDocument();
    });

    it("should call onPendingApprovalsClick when badge is clicked", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      const store = createTestStore();
      render(
        <TopBar pendingApprovals={2} onPendingApprovalsClick={handleClick} />,
        {
          wrapper: createWrapper(store),
        },
      );

      await user.click(screen.getByTestId("review-approval-button"));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("should have amber styling for approvals badge", () => {
      const store = createTestStore();
      render(
        <TopBar pendingApprovals={1} onPendingApprovalsClick={() => {}} />,
        { wrapper: createWrapper(store) },
      );

      const badge = screen.getByTestId("review-approval-button");
      expect(badge).toHaveClass("bg-amber-100");
    });

    it("should have accessible aria-label for approvals badge", () => {
      const store = createTestStore();
      render(
        <TopBar pendingApprovals={3} onPendingApprovalsClick={() => {}} />,
        { wrapper: createWrapper(store) },
      );

      const badge = screen.getByTestId("review-approval-button");
      expect(badge).toHaveAttribute("aria-label", "3 pending agent approvals");
    });

    it("should display approvals badge for all personas", () => {
      const store = createTestStore({ persona: "user" });
      render(
        <TopBar pendingApprovals={2} onPendingApprovalsClick={() => {}} />,
        { wrapper: createWrapper(store) },
      );

      expect(screen.getByTestId("review-approval-button")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have role banner", () => {
      const store = createTestStore();
      render(<TopBar />, { wrapper: createWrapper(store) });

      expect(screen.getByRole("banner")).toBeInTheDocument();
    });

    it("should have aria-label on user avatar", () => {
      const store = createTestStore({ username: "alice" });
      render(<TopBar />, { wrapper: createWrapper(store) });

      const avatarButton = screen.getByTestId("user-avatar");
      expect(avatarButton).toHaveAttribute("aria-label", "User menu for alice");
    });

    it("should have no accessibility violations", async () => {
      const store = createTestStore();
      const { container } = render(<TopBar />, {
        wrapper: createWrapper(store),
      });
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
