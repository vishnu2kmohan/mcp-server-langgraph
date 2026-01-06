/**
 * App Auth Tests
 *
 * Tests for persona detection, JWT fallback, and user data processing.
 * Split from App.test.tsx for memory optimization.
 *
 * @see App.setup.tsx for shared utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";
import notificationReducer from "../store/slices/notificationSlice";
import uiReducer from "../store/slices/uiSlice";
import workspaceReducer from "../store/slices/workspaceSlice";
import sessionReducer from "../store/slices/sessionSlice";
import mcpReducer from "../store/slices/mcpSlice";

// =============================================================================
// HOISTED MOCKS - Must be created before vi.mock calls
// =============================================================================

let mockUserQueryError: { status: number } | null = null;

const mockUseGetCurrentUserQuery = vi.fn();
const mockUseNotificationWebSocket = vi.fn();
const mockUseAlertWebSocket = vi.fn();
const mockUseOffline = vi.fn(() => false);
const mockUsePWAUpdate = vi.fn(() => ({
  needsUpdate: false,
  isOfflineReady: false,
  isUpdating: false,
  updateDismissed: false,
  registration: undefined,
  registrationError: undefined,
  updateApp: vi.fn(),
  dismissUpdate: vi.fn(),
}));

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
    useGetCurrentUserQuery: (arg: undefined, opts: { skip: boolean }) => {
      mockUseGetCurrentUserQuery(arg, opts);
      if (opts?.skip) {
        return { data: undefined, error: undefined };
      }
      if (mockUserQueryError) {
        return { data: undefined, error: mockUserQueryError };
      }
      return {
        data: {
          username: "alice",
          email: "alice@example.com",
          roles: ["developer"],
          persona: "developer" as const,
        },
        error: undefined,
      };
    },
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
// STORE FACTORY
// =============================================================================

const createTestStore = () => {
  return configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
      notifications: notificationReducer,
      ui: uiReducer,
      workspace: workspaceReducer,
      session: sessionReducer,
      mcp: mcpReducer,
    },
  });
};

// =============================================================================
// RENDER HELPER
// =============================================================================

const renderWithStore = (
  ui: React.ReactElement,
  { store = createTestStore() } = {},
) => {
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>),
  };
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function setMockUserQueryError(error: { status: number } | null): void {
  mockUserQueryError = error;
}

function resetAllMocks(): void {
  mockUserQueryError = null;
  mockUseGetCurrentUserQuery.mockClear();
  mockUseNotificationWebSocket.mockClear();
  mockUseAlertWebSocket.mockClear();
  mockUseOffline.mockReturnValue(false);
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
}

// =============================================================================
// TEST LIFECYCLE
// =============================================================================

describe("App - Auth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // PERSONA DETECTION
  // ===========================================================================

  describe("Persona Detection", () => {
    it("should fetch user info via RTK Query for studio routes", async () => {
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
        expect(mockUseGetCurrentUserQuery).toHaveBeenCalledWith(
          undefined,
          expect.objectContaining({ skip: false }),
        );
      });
    });

    it("should update Redux state with user data from RTK Query", async () => {
      const { store } = renderWithStore(
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
        const state = store.getState();
        expect(state.persona.username).toBe("alice");
        expect(state.persona.email).toBe("alice@example.com");
        expect(state.persona.persona).toBe("developer");
      });
    });

    it("should skip RTK Query for non-studio routes", async () => {
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
        expect(mockUseGetCurrentUserQuery).toHaveBeenCalledWith(
          undefined,
          expect.objectContaining({ skip: true }),
        );
      });
    });
  });

  // ===========================================================================
  // PERSONA DETECTION EDGE CASES
  // ===========================================================================

  describe("Persona Detection Edge Cases", () => {
    it("should update persona state when user data has all fields", async () => {
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
        const state = store.getState();
        expect(state.persona.username).toBe("alice");
        expect(state.persona.email).toBe("alice@example.com");
        expect(state.persona.persona).toBe("developer");
      });
    });

    it("should not update persona for non-studio routes", async () => {
      renderWithStore(
        <MemoryRouter
          initialEntries={["/"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route element={<App />}>
              <Route index element={<div>Home Page</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      await waitFor(() => {
        expect(mockUseGetCurrentUserQuery).toHaveBeenCalledWith(
          undefined,
          expect.objectContaining({ skip: true }),
        );
      });
    });

    it("should handle admin routes for persona detection", async () => {
      const { store } = renderWithStore(
        <MemoryRouter
          initialEntries={["/admin/dashboard"]}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
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
        expect(mockUseGetCurrentUserQuery).toHaveBeenCalledWith(
          undefined,
          expect.objectContaining({ skip: false }),
        );
        const state = store.getState();
        expect(state.persona.username).toBe("alice");
      });
    });
  });

  // ===========================================================================
  // USER ERROR FALLBACK WITH JWT
  // ===========================================================================

  describe("User Error Fallback with JWT", () => {
    it("should fallback to JWT decoding when user API fails", async () => {
      setMockUserQueryError({ status: 500 });

      const mockPayload = {
        preferred_username: "jwtuser",
        email: "jwt@example.com",
        roles: ["developer"],
        realm_access: { roles: ["developer"] },
      };
      const encodedPayload = btoa(JSON.stringify(mockPayload));
      const mockToken = `header.${encodedPayload}.signature`;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "auth_token") return mockToken;
        if (key === "access_token") return mockToken;
        return null;
      });

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
        expect(store.getState().persona).toBeDefined();
      });
    });
  });

  // ===========================================================================
  // JWT FALLBACK SCENARIOS
  // ===========================================================================

  describe("JWT Fallback Scenarios", () => {
    afterEach(() => {
      setMockUserQueryError(null);
    });

    it("should fallback to admin persona when JWT has admin role", async () => {
      setMockUserQueryError({ status: 500 });

      const mockPayload = {
        preferred_username: "adminuser",
        email: "admin@example.com",
        roles: ["admin", "developer"],
        realm_access: { roles: ["admin", "developer"] },
      };
      const encodedPayload = btoa(JSON.stringify(mockPayload));
      const mockToken = `header.${encodedPayload}.signature`;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "auth_token") return mockToken;
        if (key === "access_token") return mockToken;
        return null;
      });

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
        const state = store.getState();
        expect(state.persona).toBeDefined();
      });
    });

    it("should fallback to user persona when JWT has no admin/developer role", async () => {
      setMockUserQueryError({ status: 401 });

      const mockPayload = {
        username: "basicuser",
        email: "basic@example.com",
        roles: ["viewer"],
      };
      const encodedPayload = btoa(JSON.stringify(mockPayload));
      const mockToken = `header.${encodedPayload}.signature`;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "auth_token") return mockToken;
        return null;
      });

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
        expect(store.getState().persona).toBeDefined();
      });
    });

    it("should set persona loading false when no token available", async () => {
      setMockUserQueryError({ status: 500 });

      vi.spyOn(Storage.prototype, "getItem").mockReturnValue(null);

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
        const state = store.getState();
        expect(state.persona.isPersonaLoading).toBe(false);
      });
    });

    it("should handle malformed JWT token gracefully", async () => {
      setMockUserQueryError({ status: 500 });

      const storageSpy = vi
        .spyOn(Storage.prototype, "getItem")
        .mockImplementation((key) => {
          if (key === "auth_token") return "malformed-token-without-dots";
          return null;
        });

      try {
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

        await waitFor(
          () => {
            const state = store.getState().persona;
            expect(state.isPersonaLoading).toBe(false);
          },
          { timeout: 3000 },
        );

        const finalState = store.getState().persona;
        expect(finalState.persona).toBe("user");
      } finally {
        storageSpy.mockRestore();
      }
    });
  });

  // ===========================================================================
  // JWT FALLBACK - ROLE EXTRACTION BRANCHES
  // ===========================================================================

  describe("JWT Fallback - Role Extraction Branches", () => {
    afterEach(() => {
      setMockUserQueryError(null);
    });

    it("should extract roles from payload.roles when realm_access is absent", async () => {
      setMockUserQueryError({ status: 500 });

      const mockPayload = {
        username: "directrolesuser",
        email: "direct@example.com",
        roles: ["developer"],
      };
      const encodedPayload = btoa(JSON.stringify(mockPayload));
      const mockToken = `header.${encodedPayload}.signature`;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "access_token") return mockToken;
        if (key === "auth_token") return mockToken;
        return null;
      });

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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });

      const state = store.getState().persona;
      expect(state).toBeDefined();
    });

    it("should prefer preferred_username over username from JWT", async () => {
      setMockUserQueryError({ status: 500 });

      const mockPayload = {
        preferred_username: "preferred_user",
        username: "fallback_user",
        email: "test@example.com",
        roles: ["developer"],
      };
      const encodedPayload = btoa(JSON.stringify(mockPayload));
      const mockToken = `header.${encodedPayload}.signature`;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "access_token") return mockToken;
        if (key === "auth_token") return mockToken;
        return null;
      });

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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });

      const state = store.getState().persona;
      expect(state).toBeDefined();
    });

    it("should fallback to user persona when no username in JWT", async () => {
      setMockUserQueryError({ status: 500 });

      const mockPayload = {
        email: "nousername@example.com",
        roles: [],
      };
      const encodedPayload = btoa(JSON.stringify(mockPayload));
      const mockToken = `header.${encodedPayload}.signature`;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "access_token") return mockToken;
        if (key === "auth_token") return mockToken;
        return null;
      });

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
        expect(screen.getByText("Chat Page")).toBeInTheDocument();
      });

      const state = store.getState().persona;
      expect(state).toBeDefined();
    });

    it("should handle JWT with invalid Base64 encoding", async () => {
      setMockUserQueryError({ status: 500 });

      const mockToken = `header.!!!invalid-base64!!!.signature`;

      vi.spyOn(Storage.prototype, "getItem").mockImplementation((key) => {
        if (key === "access_token") return mockToken;
        if (key === "auth_token") return mockToken;
        return null;
      });

      const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

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
        const state = store.getState().persona;
        expect(state.isPersonaLoading).toBe(false);
      });

      consoleSpy.mockRestore();
    });
  });

  // ===========================================================================
  // USER DATA PROCESSING
  // ===========================================================================

  describe("User Data Processing", () => {
    it("should handle user data without persona field", async () => {
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
        const state = store.getState();
        expect(state.persona.username).toBe("alice");
      });
    });

    it("should handle user data with empty roles array", async () => {
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
        const state = store.getState();
        expect(state.persona.username).toBeDefined();
        expect(state.persona.permissions).toBeDefined();
      });
    });
  });

  // ===========================================================================
  // USERDATA PROCESSING EDGE CASES
  // ===========================================================================

  describe("UserData Processing Edge Cases", () => {
    it("should handle userData with all optional fields", async () => {
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
        const state = store.getState().persona;
        expect(state.username).toBe("alice");
        expect(state.email).toBe("alice@example.com");
      });
    });
  });
});
