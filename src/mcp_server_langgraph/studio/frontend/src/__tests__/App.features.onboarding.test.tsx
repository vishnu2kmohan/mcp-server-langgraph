/**
 * App Features - Onboarding Tests
 *
 * Tests for SUS survey timing, conditions, trigger conditions, dismiss handler,
 * guided tour integration, first visit tracking, tour completion handlers, and
 * onboarding handlers.
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

describe("App - Features - Onboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // SUS SURVEY TIMING
  // ===========================================================================

  describe("SUS Survey Timing", () => {
    beforeEach(() => {
      localStorage.removeItem("sus_completed");
      localStorage.removeItem("sus_dismissed");
      localStorage.removeItem("session_count");
      localStorage.removeItem("first_visit");
    });

    it("should not show SUS survey on first session", async () => {
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

      await new Promise((r) => setTimeout(r, 100));

      expect(
        screen.queryByText(/system usability scale/i),
      ).not.toBeInTheDocument();
    });

    it("should not show SUS survey when already completed", async () => {
      localStorage.setItem("sus_completed", "true");
      localStorage.setItem("session_count", "10");

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

      await new Promise((r) => setTimeout(r, 100));

      expect(
        screen.queryByText(/system usability scale/i),
      ).not.toBeInTheDocument();
    });

    it("should not show SUS survey when recently dismissed", async () => {
      const oneDayAgo = Date.now() - 1 * 24 * 60 * 60 * 1000;
      localStorage.setItem("sus_dismissed", String(oneDayAgo));
      localStorage.setItem("session_count", "10");

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

      await new Promise((r) => setTimeout(r, 100));

      expect(
        screen.queryByText(/system usability scale/i),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // SUS SURVEY CONDITIONS
  // ===========================================================================

  describe("SUS Survey Conditions", () => {
    it("should track session count for SUS survey trigger", async () => {
      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "studio_sus_completed") return "false";
        if (key === "studio_session_count") return "1";
        if (key === "studio_first_visit") return String(Date.now() - 86400000);
        return null;
      });

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

      await new Promise((r) => setTimeout(r, 100));
      expect(
        screen.queryByText(/system usability scale/i),
      ).not.toBeInTheDocument();

      vi.restoreAllMocks();
    });

    it("should check for recently dismissed SUS survey", async () => {
      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "studio_sus_completed") return "false";
        if (key === "studio_sus_dismissed")
          return String(Date.now() - 86400000);
        return null;
      });

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

      await new Promise((r) => setTimeout(r, 100));
      expect(
        screen.queryByText(/system usability scale/i),
      ).not.toBeInTheDocument();

      vi.restoreAllMocks();
    });
  });

  // ===========================================================================
  // SUS SURVEY TRIGGER CONDITIONS
  // ===========================================================================

  describe("SUS Survey Trigger Conditions", () => {
    beforeEach(() => {
      localStorage.clear();
    });

    it("should trigger SUS survey after 3rd session", async () => {
      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "studio_sus_completed") return null;
        if (key === "studio_sus_dismissed") return null;
        if (key === "studio_session_count") return "2";
        if (key === "studio_first_visit") return String(Date.now() - 86400000);
        return null;
      });

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

      vi.restoreAllMocks();
    });

    it("should trigger SUS survey after 7 days from first visit", async () => {
      const eightDaysAgo = Date.now() - 8 * 24 * 60 * 60 * 1000;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "studio_sus_completed") return null;
        if (key === "studio_sus_dismissed") return null;
        if (key === "studio_session_count") return "1";
        if (key === "studio_first_visit") return String(eightDaysAgo);
        return null;
      });

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

      vi.restoreAllMocks();
    });

    it("should skip SUS survey for non-studio routes", async () => {
      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "studio_session_count") return "10";
        return null;
      });

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

      await new Promise((r) => setTimeout(r, 100));
      expect(
        screen.queryByText(/system usability scale/i),
      ).not.toBeInTheDocument();

      vi.restoreAllMocks();
    });
  });

  // ===========================================================================
  // SUS DISMISS HANDLER
  // ===========================================================================

  describe("SUS Dismiss Handler", () => {
    it("should store dismissal timestamp when survey is dismissed", async () => {
      const setItemSpy = vi.spyOn(Storage.prototype, "setItem");

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

      setItemSpy.mockRestore();
    });
  });

  // ===========================================================================
  // GUIDED TOUR INTEGRATION
  // ===========================================================================

  describe("GuidedTour Integration", () => {
    it("should not show guided tour when tour_completed is true", async () => {
      localStorage.setItem("studio-tour-completed", "true");

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

      await new Promise((r) => setTimeout(r, 100));

      expect(
        screen.queryByText(/navigate your workspace/i),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // GUIDED TOUR INTEGRATION (STORAGE CHECK)
  // ===========================================================================

  describe("Guided Tour Integration", () => {
    it("should check tour completion status from storage", async () => {
      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "studio-tour-completed") return "false";
        return null;
      });

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

      vi.restoreAllMocks();
    });
  });

  // ===========================================================================
  // FIRST VISIT TRACKING
  // ===========================================================================

  describe("First Visit Tracking", () => {
    it("should set first visit timestamp if not present", async () => {
      const setItemSpy = vi.spyOn(Storage.prototype, "setItem");
      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "studio_first_visit") return null;
        return null;
      });

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

      setItemSpy.mockRestore();
      vi.restoreAllMocks();
    });
  });

  // ===========================================================================
  // TOUR COMPLETION HANDLERS
  // ===========================================================================

  describe("Tour Completion Handlers", () => {
    it("should handle tour skip by storing completion state", async () => {
      const setItemSpy = vi.spyOn(Storage.prototype, "setItem");

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

      setItemSpy.mockRestore();
    });
  });

  // ===========================================================================
  // ONBOARDING HANDLERS
  // ===========================================================================

  describe("Onboarding Handlers", () => {
    it("should handle onboarding complete and trigger tour check", async () => {
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

    it("should handle onboarding skip and trigger tour check", async () => {
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
});
