/**
 * App WebSocket Tests
 *
 * Tests for notification WebSocket and alert WebSocket integration.
 * Split from App.test.tsx for memory optimization.
 *
 * @see App.setup.tsx for shared utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen as _screen, waitFor, cleanup } from "@testing-library/react";
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

describe("App - WebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // NOTIFICATION WEBSOCKET
  // ===========================================================================

  describe("Notification WebSocket", () => {
    it("should initialize notification WebSocket for studio routes", async () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/studio/chat"]}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="studio/chat" element={<div>Chat Page</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockUseNotificationWebSocket).toHaveBeenCalled();
        expect(mockUseNotificationWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({ enabled: true }),
        );
      });
    });

    it("should disable notification WebSocket for non-studio routes", async () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/"]}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home Page</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockUseNotificationWebSocket).toHaveBeenCalled();
        expect(mockUseNotificationWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({ enabled: false }),
        );
      });
    });

    it("should initialize notification WebSocket for admin routes", async () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/admin/dashboard"]}
        >
          <Routes>
            <Route element={<App />}>
              <Route
                path="admin/dashboard"
                element={<div>Admin Dashboard</div>}
              />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockUseNotificationWebSocket).toHaveBeenCalled();
        expect(mockUseNotificationWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({ enabled: true }),
        );
      });
    });
  });

  // ===========================================================================
  // ALERT WEBSOCKET (ADR-0026)
  // ===========================================================================

  describe("Alert WebSocket (ADR-0026)", () => {
    it("should initialize alert WebSocket for admin routes", async () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/admin/dashboard"]}
        >
          <Routes>
            <Route path="/admin/*" element={<App />}>
              <Route path="dashboard" element={<div>Admin Dashboard</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockUseAlertWebSocket).toHaveBeenCalled();
        expect(mockUseAlertWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({ enabled: true }),
        );
      });
    });

    it("should disable alert WebSocket for non-admin routes", async () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/"]}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home Content</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockUseAlertWebSocket).toHaveBeenCalled();
        expect(mockUseAlertWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({ enabled: false }),
        );
      });
    });

    it("should enable alert WebSocket for studio routes with admin persona", async () => {
      renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={["/studio/chat"]}
        >
          <Routes>
            <Route path="/studio/*" element={<App />}>
              <Route path="chat" element={<div>Chat</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockUseAlertWebSocket).toHaveBeenCalled();
      });
    });
  });
});
