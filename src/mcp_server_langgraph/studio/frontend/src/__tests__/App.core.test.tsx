/**
 * App Core Tests
 *
 * Tests for rendering, outlet, toaster, and basic functionality.
 * Split from App.test.tsx for memory optimization.
 *
 * @see App.setup.tsx for shared utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render as _render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

// Import shared setup
import {
  renderWithStore,
  resetAllMocks,
  mockUseNotificationWebSocket,
  mockUseAlertWebSocket,
  mockUsePWAUpdate,
  mockUseOffline,
} from "./App.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

vi.mock("sonner", () => ({
  Toaster: ({ position }: { position: string }) => (
    <div data-testid="toaster" data-position={position}>
      Toast Notifications
    </div>
  ),
}));

vi.mock("react-resizable-panels", async () => {
  const { mockReactResizablePanels } =
    await import("../mocks/components/react-resizable-panels");
  return mockReactResizablePanels;
});

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    useGetFeatureFlagsQuery: () => ({
      data: {
        workflows: true,
        cost: true,
        observability: true,
        projects: true,
        chat: true,
      },
      isLoading: false,
      error: null,
    }),
    useGetCurrentUserQuery: () => ({
      data: {
        username: "alice",
        email: "alice@example.com",
        roles: ["developer"],
        persona: "developer" as const,
      },
      error: undefined,
    }),
    useGetWorkflowTemplatesQuery: () => ({
      data: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    }),
    useLogoutMutation: () => [
      vi.fn(() => ({ unwrap: () => Promise.resolve() })),
      { isLoading: false },
    ],
    useCreateSessionMutation: () => [
      vi.fn(() => ({
        unwrap: () =>
          Promise.resolve({ session_id: "test-session-id", name: "New Chat" }),
      })),
      { isLoading: false },
    ],
    useCreateProjectMutation: () => [
      vi.fn(() => ({
        unwrap: () =>
          Promise.resolve({ id: "test-project-id", name: "New Project" }),
      })),
      { isLoading: false },
    ],
    useGetHealthQuery: () => ({
      data: { status: "healthy", version: "1.0.0" },
      isLoading: false,
      isError: false,
    }),
    useListSessionsQuery: () => ({
      data: { items: [], total: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
    }),
    useListProjectsQuery: () => ({
      data: { items: [], total: 0 },
      isLoading: false,
      isFetching: false,
      isError: false,
    }),
  };
});

vi.mock("../hooks/useOnboarding", () => ({
  useOnboarding: () => ({
    isCompleted: true,
    shouldShowModal: false,
    complete: vi.fn(),
    skip: vi.fn(),
    reset: vi.fn(),
    isLoading: false,
  }),
}));

vi.mock("../hooks/useNotificationWebSocket", () => ({
  useNotificationWebSocket: (options?: { enabled?: boolean }) => {
    mockUseNotificationWebSocket(options);
    return {
      status: "connected" as const,
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    };
  },
}));

vi.mock("../hooks/useAlertWebSocket", () => ({
  useAlertWebSocket: (options?: { enabled?: boolean }) => {
    mockUseAlertWebSocket(options);
    return {
      status: "connected" as const,
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    };
  },
}));

vi.mock("../hooks/useAlertSoundIntegration", () => ({
  useAlertSoundIntegration: () => {},
}));

vi.mock("../hooks/useOffline", () => ({
  useOffline: () => mockUseOffline(),
}));

vi.mock("../hooks/usePWAUpdate", () => ({
  usePWAUpdate: () => mockUsePWAUpdate(),
}));

vi.mock("../hooks/useTabNavigation", () => ({
  useTabNavigation: () => vi.fn(),
}));

vi.mock("../hooks/useRouteTabSync", () => ({
  useRouteTabSync: () => {},
}));

vi.mock("../hooks/useErrorReporting", () => ({
  useErrorReporting: () => ({
    reportError: vi.fn(),
    lastError: null,
    isReporting: false,
    isEnabled: true,
    enable: vi.fn(),
    disable: vi.fn(),
    getStats: () => ({
      totalReported: 0,
      rateLimited: 0,
      failed: 0,
      queued: 0,
    }),
    flush: vi.fn(),
  }),
}));

vi.mock("../hooks/useAccessibility", () => ({
  useAccessibility: () => ({
    screenReaderMode: false,
    reducedMotion: false,
    highContrast: false,
    fontSize: "medium",
    enhancedFocus: false,
    setScreenReaderMode: vi.fn(),
    setReducedMotion: vi.fn(),
    setHighContrast: vi.fn(),
    setFontSize: vi.fn(),
    setEnhancedFocus: vi.fn(),
    resetToDefaults: vi.fn(),
    announce: vi.fn(),
  }),
}));

// Import App after mocks
import { App } from "../App";

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("App - Core", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // RENDERING
  // ===========================================================================

  describe("Rendering", () => {
    it("should render without crashing", () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByText("Home Content")).toBeInTheDocument();
    });

    it("should render with correct root class", () => {
      const { container } = renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      const rootDiv = container.querySelector(".min-h-screen");
      expect(rootDiv).toBeInTheDocument();
    });

    it("should have dark mode classes", () => {
      const { container } = renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      const rootDiv = container.querySelector(".bg-neutral-1");
      expect(rootDiv).toBeInTheDocument();
      expect(rootDiv).toHaveClass("min-h-screen", "bg-neutral-1");
    });
  });

  // ===========================================================================
  // OUTLET
  // ===========================================================================

  describe("Outlet", () => {
    it("should render child routes via Outlet", () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/"]}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                index
                element={<div data-testid="child">Child Component</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("child")).toBeInTheDocument();
    });

    it("should render different routes", () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/test"]}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home</div>} />
              <Route
                path="test"
                element={<div data-testid="test-route">Test Route</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("test-route")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // TOASTER
  // ===========================================================================

  describe("Toaster", () => {
    it("should render Toaster component", () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByTestId("toaster")).toBeInTheDocument();
    });

    it("should have correct position", () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      const toaster = screen.getByTestId("toaster");
      expect(toaster).toHaveAttribute("data-position", "bottom-right");
    });
  });

  // ===========================================================================
  // PWA OFFLINE SUPPORT
  // ===========================================================================

  describe("PWA Offline Support", () => {
    it("should show offline banner when offline", () => {
      mockUseOffline.mockReturnValue(true);

      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByText(/offline/i)).toBeInTheDocument();
    });

    it("should not show offline banner when online", () => {
      mockUseOffline.mockReturnValue(false);

      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.queryByText(/You are offline/i)).not.toBeInTheDocument();
    });
  });
});
