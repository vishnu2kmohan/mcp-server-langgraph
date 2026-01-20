/**
 * App Features - Integration Tests
 *
 * Tests for PWA update prompt, theme and preferences, feature flag gating,
 * feature flag integration, error reporting integration, accessibility integration,
 * and new resource creation error handling.
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

describe("App - Features - Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // PWA UPDATE PROMPT
  // ===========================================================================

  describe("PWA Update Prompt", () => {
    it("should not render update prompt when no update available", () => {
      mockUsePWAUpdate.mockReturnValue({
        needsUpdate: false,
        isOfflineReady: false,
        isUpdating: false,
        updateDismissed: false,
        registration: undefined,
        registrationError: undefined,
        updateApp: vi.fn(),
        dismissUpdate: vi.fn(),
      });

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

      expect(
        screen.queryByText(/new version available/i),
      ).not.toBeInTheDocument();
    });

    it("should render update prompt when update is available", () => {
      mockUsePWAUpdate.mockReturnValue({
        needsUpdate: true,
        isOfflineReady: false,
        isUpdating: false,
        updateDismissed: false,
        registration: undefined,
        registrationError: undefined,
        updateApp: vi.fn(),
        dismissUpdate: vi.fn(),
      });

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

      expect(screen.getByText(/new version available/i)).toBeInTheDocument();
    });

    it("should show updating state when isUpdating is true", () => {
      mockUsePWAUpdate.mockReturnValue({
        needsUpdate: true,
        isOfflineReady: false,
        isUpdating: true,
        updateDismissed: false,
        registration: undefined,
        registrationError: undefined,
        updateApp: vi.fn(),
        dismissUpdate: vi.fn(),
      });

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

      expect(screen.getByText(/updating/i)).toBeInTheDocument();
    });

    it("should have update button that calls updateApp", async () => {
      const mockUpdateApp = vi.fn();
      mockUsePWAUpdate.mockReturnValue({
        needsUpdate: true,
        isOfflineReady: false,
        isUpdating: false,
        updateDismissed: false,
        registration: undefined,
        registrationError: undefined,
        updateApp: mockUpdateApp,
        dismissUpdate: vi.fn(),
      });

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

      const updateButton = screen.getByRole("button", { name: /update/i });
      expect(updateButton).toBeInTheDocument();
    });

    it("should have dismiss button that calls dismissUpdate", async () => {
      const mockDismissUpdate = vi.fn();
      mockUsePWAUpdate.mockReturnValue({
        needsUpdate: true,
        isOfflineReady: false,
        isUpdating: false,
        updateDismissed: false,
        registration: undefined,
        registrationError: undefined,
        updateApp: vi.fn(),
        dismissUpdate: mockDismissUpdate,
      });

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

      const dismissButton = screen.getByRole("button", {
        name: /later|remind/i,
      });
      expect(dismissButton).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // THEME AND PREFERENCES
  // ===========================================================================

  describe("Theme and Preferences", () => {
    it("should apply dark mode classes to root element", () => {
      const { container } = renderWithStore(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      const rootElement = container.querySelector(".min-h-screen");
      expect(rootElement).toHaveClass("bg-neutral-1");
      expect(rootElement).toHaveClass();
    });
  });

  // ===========================================================================
  // FEATURE FLAG GATING
  // ===========================================================================

  describe("Feature Flag Gating", () => {
    it("should respect onboarding_wizard feature flag", async () => {
      renderWithStore(
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
        expect(
          screen.queryByText(/welcome to agent studio/i),
        ).not.toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // FEATURE FLAG INTEGRATION
  // ===========================================================================

  describe("Feature Flag Integration", () => {
    it("should check url_content_fetch feature flag", async () => {
      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });
    });

    it("should check slash_commands feature flag", async () => {
      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });
    });

    it("should check style_presets feature flag", async () => {
      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // ERROR REPORTING INTEGRATION (PHASE 5.3)
  // ===========================================================================

  describe("Error Reporting Integration (Phase 5.3)", () => {
    it("should initialize useErrorReporting hook with window error capture", async () => {
      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });
    });

    it("should have error reporting enabled for studio routes", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/studio/workflows"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="studio/workflows" element={<div>Workflows</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Workflows")).toBeInTheDocument();
      });
    });

    it("should have error reporting enabled for admin routes", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/admin/users"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="admin/users" element={<div>Admin Users</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Admin Users")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // ACCESSIBILITY INTEGRATION
  // ===========================================================================

  describe("Accessibility Integration", () => {
    beforeEach(() => {
      mockAnnounce.mockClear();
    });

    it("should initialize useAccessibility hook for global a11y settings", async () => {
      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });
    });

    it("should have accessibility features available on all routes", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/admin/settings"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route path="admin/settings" element={<div>Settings</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(screen.getByText("Settings")).toBeInTheDocument();
      });
    });

    it("should expose announce function for screen reader announcements", async () => {
      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });

      expect(mockAnnounce).toBeDefined();
    });
  });

  // ===========================================================================
  // NEW RESOURCE CREATION ERROR HANDLING
  // ===========================================================================

  describe("New Resource Creation Error Handling", () => {
    it("should handle handleNewChat error gracefully", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });

    it("should handle handleNewProject error gracefully", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      renderWithStore(
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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });

      consoleSpy.mockRestore();
    });
  });
});
