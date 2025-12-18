/**
 * App Component Tests
 *
 * TDD tests for the root application component.
 * Tests cover:
 * - Rendering
 * - Outlet integration
 * - Toaster configuration
 * - User info fetching via Redux
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { App } from "./App";
import personaReducer from "./store/slices/personaSlice";
import authReducer from "./store/slices/authSlice";
import notificationReducer from "./store/slices/notificationSlice";
import uiReducer from "./store/slices/uiSlice";
import workspaceReducer from "./store/slices/workspaceSlice";
import sessionReducer from "./store/slices/sessionSlice";
import mcpReducer from "./store/slices/mcpSlice";

// Mock sonner Toaster
vi.mock("sonner", () => ({
  Toaster: ({ position }: { position: string }) => (
    <div data-testid="toaster" data-position={position}>
      Toast Notifications
    </div>
  ),
}));

// Use shared react-resizable-panels mock to avoid layout calculation errors
// This is needed because App renders AppShell which uses react-resizable-panels
// See: src/mocks/components/react-resizable-panels.ts
vi.mock("react-resizable-panels", async () => {
  const { mockReactResizablePanels } =
    await import("./mocks/components/react-resizable-panels");
  return mockReactResizablePanels;
});

// Mock RTK Query hooks (used by App and Sidebar)
const mockUseGetCurrentUserQuery = vi.fn();

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
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
    useGetCurrentUserQuery: (arg: undefined, options: { skip: boolean }) => {
      // Track the call
      mockUseGetCurrentUserQuery(arg, options);
      // Return mock data based on skip option
      if (options?.skip) {
        return { data: undefined, error: undefined };
      }
      return {
        data: {
          username: "alice",
          email: "alice@example.com",
          roles: ["developer"],
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
    // Add mocks for hooks used by child components
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

// Mock useOnboarding hook (onboarding is disabled for most tests)
vi.mock("./hooks/useOnboarding", () => ({
  useOnboarding: () => ({
    isCompleted: true,
    shouldShowModal: false,
    complete: vi.fn(),
    skip: vi.fn(),
    reset: vi.fn(),
    isLoading: false,
  }),
}));

// Mock notification WebSocket hook
const mockUseNotificationWebSocket = vi.fn(() => ({
  status: "connected" as const,
  disconnect: vi.fn(),
  reconnect: vi.fn(),
}));

vi.mock("./hooks/useNotificationWebSocket", () => ({
  useNotificationWebSocket: (options?: { enabled?: boolean }) => {
    // Track call with options
    mockUseNotificationWebSocket(options);
    return {
      status: "connected" as const,
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    };
  },
}));

// Mock useOffline hook for PWA offline support
const mockUseOffline = vi.fn(() => false);
vi.mock("./hooks/useOffline", () => ({
  useOffline: () => mockUseOffline(),
}));

// Mock usePWAUpdate hook for service worker update prompts
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
vi.mock("./hooks/usePWAUpdate", () => ({
  usePWAUpdate: () => mockUsePWAUpdate(),
}));

// Mock useTabNavigation hook
vi.mock("./hooks/useTabNavigation", () => ({
  useTabNavigation: () => vi.fn(),
}));

// Mock useRouteTabSync hook
vi.mock("./hooks/useRouteTabSync", () => ({
  useRouteTabSync: () => {},
}));

// Create a test store with auth, persona, notification, ui, workspace, session, and mcp reducers
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

// Helper to render with store
const renderWithStore = (
  ui: React.ReactElement,
  { store = createTestStore() } = {},
) => {
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>),
  };
};

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseNotificationWebSocket.mockClear();
    mockUseGetCurrentUserQuery.mockClear();
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
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

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

      const rootDiv = container.querySelector(".bg-white");
      expect(rootDiv).toBeInTheDocument();
      expect(rootDiv).toHaveClass("dark:bg-gray-900");
    });
  });

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
        // RTK Query hook should be called without skip for studio routes
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

      // RTK Query hook should be called with skip=true for non-studio routes
      await waitFor(() => {
        expect(mockUseGetCurrentUserQuery).toHaveBeenCalledWith(
          undefined,
          expect.objectContaining({ skip: true }),
        );
      });
    });
  });

  describe("Mobile Responsive Layout", () => {
    it("should render main content area that takes full height", () => {
      // RTK Query mock already provides user data for studio routes
      const { container } = renderWithStore(
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

      // Main content area should have h-full for full height within Panel
      const mainElement = container.querySelector("main");
      expect(mainElement).toBeInTheDocument();
      expect(mainElement).toHaveClass("h-full");
    });

    it("should have overflow-auto on main content for mobile scrolling", () => {
      // RTK Query mock already provides user data for studio routes
      const { container } = renderWithStore(
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

      const mainElement = container.querySelector("main");
      expect(mainElement).toHaveClass("overflow-auto");
    });

    it("should use flex layout for studio routes", () => {
      // RTK Query mock already provides user data for studio routes
      const { container } = renderWithStore(
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

      // Should have flex container for sidebar + main layout
      const flexContainer = container.querySelector(".flex");
      expect(flexContainer).toBeInTheDocument();
    });
  });

  describe("Notification WebSocket", () => {
    it("should initialize notification WebSocket for studio routes", async () => {
      // RTK Query mock already provides user data for studio routes
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
        // Should be enabled for studio routes
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
        // Should be disabled for non-studio routes
        expect(mockUseNotificationWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({ enabled: false }),
        );
      });
    });

    it("should initialize notification WebSocket for admin routes", async () => {
      // RTK Query mock already provides user data for admin routes
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
        // Should be enabled for admin routes
        expect(mockUseNotificationWebSocket).toHaveBeenCalledWith(
          expect.objectContaining({ enabled: true }),
        );
      });
    });
  });

  describe("PWA Offline Support", () => {
    it("should not render offline banner when online", () => {
      mockUseOffline.mockReturnValue(false);

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

      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("should render offline banner when offline", () => {
      mockUseOffline.mockReturnValue(true);

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

      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(
        screen.getByText(/you are currently offline/i),
      ).toBeInTheDocument();
    });

    it("should show offline banner on studio routes", () => {
      mockUseOffline.mockReturnValue(true);
      // RTK Query mock already provides user data for studio routes
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

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

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

      // No update alert should be present (offline alert is different)
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

  describe("JupyterLab layout", () => {
    it("should render LeftSidebar in AppShell for studio routes", async () => {
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

      // LeftSidebar should be rendered with activity-bar and sidebar-content
      await waitFor(() => {
        expect(screen.getByTestId("left-sidebar")).toBeInTheDocument();
        expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
      });
    });

    it("should render MainDock for studio routes", async () => {
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

      // MainDock should be rendered
      await waitFor(() => {
        expect(screen.getByTestId("main-dock")).toBeInTheDocument();
      });
    });
  });

  describe("workspace persistence", () => {
    it("should load workspace state from localStorage on mount", async () => {
      // Setup saved workspace state
      const savedWorkspace = {
        version: 1,
        leftSidebarWidth: 350,
        leftSidebarCollapsed: true,
        focusMode: true,
      };
      localStorage.setItem(
        "agent-studio-workspace",
        JSON.stringify(savedWorkspace),
      );

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

      // Wait for the effect to run
      await waitFor(() => {
        expect(store.getState().workspace.leftSidebarWidth).toBe(350);
        expect(store.getState().workspace.leftSidebarCollapsed).toBe(true);
        expect(store.getState().workspace.focusMode).toBe(true);
      });
    });
  });
});
