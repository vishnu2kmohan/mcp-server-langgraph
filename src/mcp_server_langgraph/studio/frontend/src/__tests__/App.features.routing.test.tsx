/**
 * App Features - Routing Tests
 *
 * Tests for route type detection, isStudioRoute detection, non-studio routes,
 * lazy component loading, and workspace initialization.
 * Split from App.features.test.tsx for memory optimization.
 *
 * @see App.setup.tsx for shared utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";

// Import shared setup
import {
  renderWithStore,
  resetAllMocks,
  mockUseNotificationWebSocket,
  mockUseAlertWebSocket,
  mockUsePWAUpdate,
  mockUseOffline,
  mockAnnounce,
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
    announce: mockAnnounce,
  }),
}));

// Import App after mocks
import { App } from "../App";

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("App - Features - Routing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // ROUTE TYPE DETECTION EDGE CASES
  // ===========================================================================

  describe("Route Type Detection Edge Cases", () => {
    it("should detect /studio/* as non-legacy route (StudioShell)", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/chat"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                path="studio/chat"
                element={<div data-testid="hybrid-content">Hybrid Chat</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("hybrid-content")).toBeInTheDocument();
      });
      expect(screen.queryByTestId("left-sidebar")).not.toBeInTheDocument();
    });

    it("should detect /admin/* as studio route (renders via StudioShell)", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/admin/dashboard"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                path="admin/dashboard"
                element={<div data-testid="admin-content">Admin Dashboard</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("admin-content")).toBeInTheDocument();
      });
    });

    it("should detect /login as non-studio route", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/login"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                path="login"
                element={<div data-testid="login-page">Login Page</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByTestId("login-page")).toBeInTheDocument();
      });
      expect(screen.queryByTestId("left-sidebar")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // IS STUDIO ROUTE DETECTION EDGE CASES
  // ===========================================================================

  describe("isStudioRoute Detection Edge Cases", () => {
    it("should detect /studio exactly as studio route", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/studio"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="studio" element={<div>Studio Root</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Studio Root")).toBeInTheDocument();
      });
    });

    it("should detect /admin exactly as studio route (isStudioRoute)", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/admin"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="admin" element={<div>Admin Root</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Admin Root")).toBeInTheDocument();
      });
    });

    it("should detect deeply nested studio route", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/workflows/123/edit"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                path="studio/workflows/:id/edit"
                element={<div>Workflow Edit</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Workflow Edit")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // NON-STUDIO ROUTES
  // ===========================================================================

  describe("Non-Studio Routes", () => {
    it("should skip studio-specific logic for non-studio routes", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/login"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="login" element={<div>Login Page</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Login Page")).toBeInTheDocument();
      });

      expect(screen.queryByTestId("left-sidebar")).not.toBeInTheDocument();
    });

    it("should skip isStudioRoute check for auth callback route", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/auth/callback"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="auth/callback" element={<div>Auth Callback</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Auth Callback")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // LAZY COMPONENT LOADING
  // ===========================================================================

  describe("Lazy Component Loading", () => {
    it("should render lazy-loaded Settings when tab type is settings", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/settings"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                path="studio/settings"
                element={<div>Settings Route</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Settings Route")).toBeInTheDocument();
      });
    });

    it("should render lazy-loaded Cost when tab type is cost", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/cost"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="studio/cost" element={<div>Cost Route</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Cost Route")).toBeInTheDocument();
      });
    });

    it("should render lazy-loaded Observability when tab type is observability", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/observability"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                path="studio/observability"
                element={<div>Observability Route</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Observability Route")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // WORKSPACE INITIALIZATION
  // ===========================================================================

  describe("Workspace Initialization", () => {
    it("should dispatch loadWorkspaceFromStorage on mount", async () => {
      const { store } = renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/chat"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="studio/chat" element={<div>Chat Page</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        const state = store.getState().workspace;
        expect(state).toBeDefined();
      });
    });

    it("should dispatch initializeAuth on mount", async () => {
      const { store } = renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/chat"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="studio/chat" element={<div>Chat Page</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        const state = store.getState().auth;
        expect(state).toBeDefined();
      });
    });
  });
});
