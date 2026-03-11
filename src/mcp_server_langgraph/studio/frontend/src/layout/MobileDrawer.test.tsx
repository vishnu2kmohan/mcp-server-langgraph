/**
 * MobileDrawer Component Tests (Sprint 5.1)
 *
 * TDD tests for mobile drawer navigation.
 * The drawer provides navigation for mobile breakpoints,
 * reusing content from ActivityBar and SessionNav.
 *
 * Gated behind feature flag: mobile_drawer
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor as _waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import type { ReactNode } from "react";

expect.extend(toHaveNoViolations);

// Mock react-router
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: "/studio/chat" }),
    // Mock useRouteLoaderData to avoid data router requirement
    useRouteLoaderData: (routeId: string) => {
      if (routeId === "studio") {
        return {
          sessions: [
            {
              id: "session-1",
              name: "Test Session 1",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              status: "active",
            },
          ],
        };
      }
      return undefined;
    },
  };
});

// Mock feature flag context
vi.mock("../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: vi.fn((flag: string) => {
      if (flag === "mobile_drawer") return true;
      return false;
    }),
    FeatureFlagProvider: ({ children }: { children: ReactNode }) => (
      <>{children}</>
    ),
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

// Import reducers
import canvasReducer from "../store/slices/canvasSlice";
import personaReducer from "../store/slices/personaSlice";
import sessionReducer, {
  initialSessionState,
} from "../store/slices/sessionSlice";

// Import component AFTER mocks
import { MobileDrawer } from "./MobileDrawer";
import { HamburgerMenu } from "./HamburgerMenu";

import { TestProvider } from "@/test-utils";

// =============================================================================
// TEST HELPERS
// =============================================================================

function createTestStore() {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
      persona: personaReducer,
      session: sessionReducer,
    },
    preloadedState: {
      persona: {
        persona: "admin",
        subPersona: null,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
        visibleModules: [],
        featureFlags: {},
        apiVersion: null,
      },
      session: { ...initialSessionState },
    },
  });
}

function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  };
}

// =============================================================================
// MOBILE DRAWER TESTS
// =============================================================================

describe("MobileDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("rendering", () => {
    it("should render with data-testid when open", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      expect(screen.getByTestId("mobile-drawer")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen={false} onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      expect(screen.queryByTestId("mobile-drawer")).not.toBeInTheDocument();
    });

    it("should render navigation items", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      // Should show main navigation items
      expect(screen.getByTestId("mobile-nav-chat")).toBeInTheDocument();
      expect(screen.getByTestId("mobile-nav-workflows")).toBeInTheDocument();
    });

    it("should render overlay backdrop", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      expect(screen.getByTestId("mobile-drawer-backdrop")).toBeInTheDocument();
    });

    it("should render close button", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      expect(screen.getByTestId("mobile-drawer-close")).toBeInTheDocument();
    });
  });

  describe("interactions", () => {
    it("should call onClose when backdrop is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const store = createTestStore();

      render(<MobileDrawer isOpen onClose={onClose} />, {
        wrapper: createWrapper(store),
      });

      await user.click(screen.getByTestId("mobile-drawer-backdrop"));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("should call onClose when close button is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const store = createTestStore();

      render(<MobileDrawer isOpen onClose={onClose} />, {
        wrapper: createWrapper(store),
      });

      await user.click(screen.getByTestId("mobile-drawer-close"));
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("should navigate and close when nav item is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const store = createTestStore();

      render(<MobileDrawer isOpen onClose={onClose} />, {
        wrapper: createWrapper(store),
      });

      await user.click(screen.getByTestId("mobile-nav-workflows"));

      expect(mockNavigate).toHaveBeenCalledWith("/studio/workflows");
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("should close on Escape key press", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();
      const store = createTestStore();

      render(<MobileDrawer isOpen onClose={onClose} />, {
        wrapper: createWrapper(store),
      });

      await user.keyboard("{Escape}");
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("RBAC filtering", () => {
    it("should filter nav items based on persona permissions", () => {
      const store = configureStore({
        reducer: {
          canvas: canvasReducer,
          persona: personaReducer,
          session: sessionReducer,
        },
        preloadedState: {
          persona: {
            persona: "user",
            subPersona: "bob",
            username: "bob",
            email: "bob@example.com",
            permissions: [],
            isPersonaLoading: false,
            visibleModules: [],
            featureFlags: {},
            apiVersion: null,
          },
          session: { ...initialSessionState },
        },
      });

      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      // Bob should see chat but not admin
      expect(screen.getByTestId("mobile-nav-chat")).toBeInTheDocument();
      expect(screen.queryByTestId("mobile-nav-admin")).not.toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have aria-modal attribute", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      const drawer = screen.getByTestId("mobile-drawer");
      expect(drawer).toHaveAttribute("aria-modal", "true");
    });

    it("should have role dialog", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      const drawer = screen.getByTestId("mobile-drawer");
      expect(drawer).toHaveAttribute("role", "dialog");
    });

    it("should have aria-label", () => {
      const store = createTestStore();
      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      const drawer = screen.getByTestId("mobile-drawer");
      expect(drawer).toHaveAttribute("aria-label", "Mobile navigation");
    });

    it("should have no accessibility violations", async () => {
      const store = createTestStore();
      const { container } = render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("focus trap", () => {
    it("should trap focus within drawer when open", async () => {
      const user = userEvent.setup();
      const store = createTestStore();

      render(<MobileDrawer isOpen onClose={vi.fn()} />, {
        wrapper: createWrapper(store),
      });

      // Tab through elements - should stay within drawer
      const closeButton = screen.getByTestId("mobile-drawer-close");
      closeButton.focus();

      await user.tab();
      // Focus should move to first nav item or stay in drawer
      expect(document.activeElement).not.toBe(document.body);
    });
  });
});

// =============================================================================
// HAMBURGER MENU TESTS
// =============================================================================

describe("HamburgerMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(
        <TestProvider>
          <HamburgerMenu onClick={vi.fn()} />
        </TestProvider>,
      );
      expect(screen.getByTestId("hamburger-menu")).toBeInTheDocument();
    });

    it("should render hamburger icon by default", () => {
      render(
        <TestProvider>
          <HamburgerMenu onClick={vi.fn()} />
        </TestProvider>,
      );
      expect(screen.getByTestId("hamburger-icon")).toBeInTheDocument();
    });

    it("should render close icon when isOpen is true", () => {
      render(
        <TestProvider>
          <HamburgerMenu onClick={vi.fn()} isOpen />
        </TestProvider>,
      );
      expect(screen.getByTestId("hamburger-close-icon")).toBeInTheDocument();
    });
  });

  describe("interactions", () => {
    it("should call onClick when clicked", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      render(
        <TestProvider>
          <HamburgerMenu onClick={onClick} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("hamburger-menu"));
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it("should be keyboard accessible", async () => {
      const user = userEvent.setup();
      const onClick = vi.fn();

      render(
        <TestProvider>
          <HamburgerMenu onClick={onClick} />
        </TestProvider>,
      );

      const button = screen.getByTestId("hamburger-menu");
      button.focus();
      await user.keyboard("{Enter}");

      expect(onClick).toHaveBeenCalledTimes(1);
    });
  });

  describe("accessibility", () => {
    it("should have aria-label", () => {
      render(
        <TestProvider>
          <HamburgerMenu onClick={vi.fn()} />
        </TestProvider>,
      );
      const button = screen.getByTestId("hamburger-menu");
      expect(button).toHaveAttribute("aria-label");
    });

    it("should have aria-expanded matching isOpen prop", () => {
      const { rerender } = render(
        <TestProvider>
          <HamburgerMenu onClick={vi.fn()} />
        </TestProvider>,
      );
      let button = screen.getByTestId("hamburger-menu");
      expect(button).toHaveAttribute("aria-expanded", "false");

      rerender(<HamburgerMenu onClick={vi.fn()} isOpen />);
      button = screen.getByTestId("hamburger-menu");
      expect(button).toHaveAttribute("aria-expanded", "true");
    });

    it("should have aria-controls for drawer", () => {
      render(
        <TestProvider>
          <HamburgerMenu onClick={vi.fn()} />
        </TestProvider>,
      );
      const button = screen.getByTestId("hamburger-menu");
      expect(button).toHaveAttribute("aria-controls", "mobile-drawer");
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <HamburgerMenu onClick={vi.fn()} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
