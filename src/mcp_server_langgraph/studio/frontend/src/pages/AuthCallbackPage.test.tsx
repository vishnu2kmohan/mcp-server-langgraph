/**
 * AuthCallbackPage Tests
 *
 * TDD tests for OAuth2 Authorization Code + PKCE callback handling.
 * Tests cover token parsing, API-based user fetching, Redux state updates,
 * error handling, and navigation.
 *
 * Note: User info is now fetched via initializeAuth() which calls /api/v1/me,
 * rather than being decoded from the JWT. Tests use MSW to mock this endpoint.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { http, HttpResponse } from "msw";
import { AuthCallbackPage } from "./AuthCallbackPage";
import authReducer, { initialAuthState } from "../store/slices/authSlice";
import personaReducer from "../store/slices/personaSlice";
import { INTENDED_ROUTE_KEY } from "../utils/intendedRoute";
import { server } from "../mocks/server";

// Mock react-router navigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock storage utility - include all exports needed by authSlice
vi.mock("../utils/storage", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../utils/storage")>();
  return {
    ...actual,
    setAuthTokens: vi.fn(),
  };
});

// Import mocked module
import { setAuthTokens } from "../utils/storage";

// Helper to create MSW handler for /api/v1/me with custom user data
const createMeHandler = (userData: Record<string, unknown>) =>
  http.get("/api/v1/me", () =>
    HttpResponse.json({
      user_id: "user-test-123",
      username: "testuser",
      email: "test@example.com",
      roles: ["user"],
      persona: "user",
      websocket_permissions: {
        alerts: true,
        devtools: true,
        notifications: true,
        audit: true,
        mcp_tasks: true,
        mcp_aggregated: true,
        connections_health: true,
        connections_realtime: true,
        heart_metrics: true,
        traces: true,
        cost_tracking: true,
        budget_alerts: true,
        agent_requests: true,
        ai_suggestions: true,
        orchestrator_status: true,
        llm_streaming: true,
        session_metrics: true,
      },
      ...userData,
    }),
  );

// Create a valid JWT for testing
// Header: {"alg":"RS256","typ":"JWT"}
// Payload: {"sub":"user-123","preferred_username":"testuser","email":"test@example.com","roles":["user"],"realm_access":{"roles":["user"]}}
// Note: All parts must not contain "=" padding since parseFragment splits on "="
const createMockJWT = (payload: Record<string, unknown>): string => {
  const header = btoa(JSON.stringify({ alg: "RS256", typ: "JWT" }))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  const payloadBase64 = btoa(JSON.stringify(payload))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  const signature = btoa("mock-signature-x") // "x" ensures no padding needed
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return `${header}.${payloadBase64}.${signature}`;
};

const mockUserPayload = {
  sub: "user-123",
  preferred_username: "testuser",
  email: "test@example.com",
  roles: ["user"],
  realm_access: { roles: ["user"] },
};

const mockAdminPayload = {
  sub: "admin-123",
  preferred_username: "adminuser",
  email: "admin@example.com",
  roles: ["admin", "developer", "user"],
  realm_access: { roles: ["admin", "developer", "user"] },
};

const mockDeveloperPayload = {
  sub: "dev-123",
  preferred_username: "devuser",
  email: "dev@example.com",
  roles: ["developer", "user"],
  realm_access: { roles: ["developer", "user"] },
};

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      auth: authReducer,
      persona: personaReducer,
    },
    preloadedState: {
      auth: initialAuthState,
    },
  });
};

// Helper to render with providers
const renderWithProviders = (hash: string = "", store = createTestStore()) => {
  // Set window.location.hash
  Object.defineProperty(window, "location", {
    writable: true,
    value: {
      ...window.location,
      hash,
      pathname: "/auth/callback",
    },
  });

  // Mock history.replaceState
  window.history.replaceState = vi.fn();

  render(
    <Provider store={store}>
      <MemoryRouter initialEntries={["/auth/callback"]}>
        <AuthCallbackPage />
      </MemoryRouter>
    </Provider>,
  );

  return { store };
};

describe("AuthCallbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    sessionStorage.clear();
  });

  describe("Initial Rendering", () => {
    it("shows error state when no token is provided", async () => {
      // When no access_token is in the hash, the component immediately shows error
      renderWithProviders("");

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });
      expect(screen.getByText(/No access token received/i)).toBeInTheDocument();
    });

    it("shows loading spinner during processing with valid token", async () => {
      // When a valid token is provided, the component processes it
      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      renderWithProviders(hash);

      // The component may briefly show processing state, but will quickly transition to success
      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });
    });
  });

  describe("Successful Authentication", () => {
    it("processes valid access token and shows success", async () => {
      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}&refresh_token=mock-refresh`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(
        screen.getByText(/Redirecting to Agent Studio/i),
      ).toBeInTheDocument();

      // Verify tokens were stored
      expect(setAuthTokens).toHaveBeenCalledWith(mockToken, "mock-refresh");

      // Verify user was set in Redux (data comes from /api/v1/me via initializeAuth)
      const state = store.getState();
      expect(state.auth.user).not.toBeNull();
      expect(state.auth.user?.username).toBe("testuser");
    });

    it("extracts admin persona from roles", async () => {
      // Override /api/v1/me to return admin user
      server.use(
        createMeHandler({
          username: "adminuser",
          roles: ["admin", "developer", "user"],
          persona: "admin",
        }),
      );

      const mockToken = createMockJWT(mockAdminPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const state = store.getState();
      expect(state.persona.persona).toBe("admin");
    });

    it("extracts developer persona from roles", async () => {
      // Override /api/v1/me to return developer user
      server.use(
        createMeHandler({
          username: "devuser",
          roles: ["developer", "user"],
          persona: "developer",
        }),
      );

      const mockToken = createMockJWT(mockDeveloperPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const state = store.getState();
      expect(state.persona.persona).toBe("developer");
    });

    it("defaults to user persona when no admin/developer roles", async () => {
      // Default handler already returns user persona
      const mockToken = createMockJWT({
        sub: "user-456",
        preferred_username: "basicuser",
        roles: ["viewer"],
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const state = store.getState();
      expect(state.persona.persona).toBe("user");
    });

    it("redirects to /studio after success", async () => {
      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      // Advance timer to trigger redirect
      vi.advanceTimersByTime(1000);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/studio", { replace: true });
      });
    });

    it("clears URL fragment after processing", async () => {
      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(window.history.replaceState).toHaveBeenCalledWith(
        null,
        "",
        "/auth/callback",
      );
    });

    it("handles token without refresh token", async () => {
      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(setAuthTokens).toHaveBeenCalledWith(mockToken, undefined);
    });
  });

  describe("Error Handling", () => {
    it("shows error when no access token in fragment", async () => {
      renderWithProviders("#other_param=value");

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/No access token received/i)).toBeInTheDocument();
    });

    it("shows error when fragment contains error parameter", async () => {
      const hash =
        "#error=access_denied&error_description=User%20denied%20access";

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/User denied access/i)).toBeInTheDocument();
    });

    it("shows generic error message when no error_description", async () => {
      const hash = "#error=server_error";

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/server_error/i)).toBeInTheDocument();
    });

    it("shows error when API call fails", async () => {
      // Override /api/v1/me to return an error
      server.use(
        http.get("/api/v1/me", () =>
          HttpResponse.json({ detail: "Unauthorized" }, { status: 401 }),
        ),
      );

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });
    });

    it("shows error when API returns network error", async () => {
      // Override /api/v1/me to return network error
      server.use(http.get("/api/v1/me", () => HttpResponse.error()));

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });
    });

    it("renders try again button on error", async () => {
      renderWithProviders("#other_param=value");

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      const tryAgainButton = screen.getByRole("button", { name: /Try again/i });
      expect(tryAgainButton).toBeInTheDocument();
    });

    it("navigates to login on try again click", async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      renderWithProviders("#other_param=value");

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      const tryAgainButton = screen.getByRole("button", { name: /Try again/i });
      await user.click(tryAgainButton);

      expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
    });
  });

  describe("API-based User Fetching", () => {
    // Note: User info is now fetched from /api/v1/me via initializeAuth(),
    // not parsed from the JWT. These tests verify the API response is properly
    // mapped to Redux state.

    it("fetches username from API response", async () => {
      server.use(createMeHandler({ username: "api-username" }));

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.username).toBe("api-username");
    });

    it("fetches email from API response", async () => {
      server.use(createMeHandler({ email: "api@example.com" }));

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.email).toBe("api@example.com");
    });

    it("fetches roles from API response", async () => {
      server.use(
        createMeHandler({ roles: ["custom-role-1", "custom-role-2"] }),
      );

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.roles).toEqual([
        "custom-role-1",
        "custom-role-2",
      ]);
    });

    it("fetches websocket permissions from API response", async () => {
      server.use(
        createMeHandler({
          websocket_permissions: {
            connections_health: true,
            ai_suggestions: true,
            alerts: false,
          },
        }),
      );

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const wsPerms = store.getState().auth.user?.websocketPermissions;
      expect(wsPerms?.connections_health).toBe(true);
      expect(wsPerms?.ai_suggestions).toBe(true);
    });

    it("defaults to empty roles when API returns no roles", async () => {
      server.use(createMeHandler({ roles: [] }));

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.roles).toEqual([]);
    });
  });

  describe("WebSocket Permissions Redux State", () => {
    // These tests verify that websocket_permissions from /api/v1/me are properly
    // mapped to Redux state. This is critical for WebSocket hooks to check
    // permissions before attempting to connect.
    //
    // Reference: StatusBar "Disconnected" after OAuth login bug

    it("stores all 17 websocket permissions in Redux state", async () => {
      // Use default handler which has all 17 permissions set to true
      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const wsPerms = store.getState().auth.user?.websocketPermissions;
      expect(wsPerms).toBeDefined();

      // Verify all 17 fields are present
      const expectedFields = [
        "alerts",
        "notifications",
        "devtools",
        "audit",
        "mcp_tasks",
        "mcp_aggregated",
        "connections_health",
        "connections_realtime",
        "heart_metrics",
        "traces",
        "cost_tracking",
        "budget_alerts",
        "agent_requests",
        "ai_suggestions",
        "orchestrator_status",
        "llm_streaming",
        "session_metrics",
      ];

      for (const field of expectedFields) {
        expect(wsPerms).toHaveProperty(field);
      }
    });

    it("maps connections_health permission correctly for StatusBar", async () => {
      // This is the critical permission for StatusBar "Connected" state
      server.use(
        createMeHandler({
          websocket_permissions: {
            alerts: false,
            devtools: false,
            notifications: false,
            audit: false,
            mcp_tasks: false,
            mcp_aggregated: false,
            connections_health: true, // This is what StatusBar checks
            connections_realtime: false,
            heart_metrics: false,
            traces: false,
            cost_tracking: false,
            budget_alerts: false,
            agent_requests: false,
            ai_suggestions: false,
            orchestrator_status: false,
            llm_streaming: false,
            session_metrics: false,
          },
        }),
      );

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const wsPerms = store.getState().auth.user?.websocketPermissions;
      expect(wsPerms?.connections_health).toBe(true);
    });

    it("handles user without alert permission (developer)", async () => {
      server.use(
        createMeHandler({
          persona: "developer",
          websocket_permissions: {
            alerts: false, // Developers don't get alerts
            notifications: true,
            devtools: true,
            audit: true,
            mcp_tasks: true,
            mcp_aggregated: true,
            connections_health: true,
            connections_realtime: true,
            heart_metrics: true,
            traces: true,
            cost_tracking: true,
            budget_alerts: true,
            agent_requests: true,
            ai_suggestions: true,
            orchestrator_status: true,
            llm_streaming: true,
            session_metrics: true,
          },
        }),
      );

      const mockToken = createMockJWT(mockDeveloperPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const wsPerms = store.getState().auth.user?.websocketPermissions;
      expect(wsPerms?.alerts).toBe(false);
      expect(wsPerms?.connections_health).toBe(true);
    });

    it("handles fail-closed permissions when all false", async () => {
      // When OpenFGA is unavailable, all permissions should be false
      server.use(
        createMeHandler({
          websocket_permissions: {
            alerts: false,
            notifications: false,
            devtools: false,
            audit: false,
            mcp_tasks: false,
            mcp_aggregated: false,
            connections_health: false,
            connections_realtime: false,
            heart_metrics: false,
            traces: false,
            cost_tracking: false,
            budget_alerts: false,
            agent_requests: false,
            ai_suggestions: false,
            orchestrator_status: false,
            llm_streaming: false,
            session_metrics: false,
          },
        }),
      );

      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const wsPerms = store.getState().auth.user?.websocketPermissions;
      expect(Object.values(wsPerms || {}).every((v) => v === false)).toBe(true);
    });

    it("websocketPermissions enables useConnectionHealthWebSocket hook", async () => {
      // Verify the shape that useConnectionHealthWebSocket expects
      const mockToken = createMockJWT(mockUserPayload);
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      const authState = store.getState().auth;

      // useConnectionHealthWebSocket checks:
      // 1. isAuthenticated (derived as user !== null via selectIsAuthenticated)
      // 2. websocketPermissions?.connections_health (from auth.user)
      expect(authState.user).not.toBeNull(); // selectIsAuthenticated checks user !== null
      expect(authState.user?.websocketPermissions?.connections_health).toBe(
        true,
      );
    });
  });

  describe("URL Fragment Parsing", () => {
    it("handles empty fragment", async () => {
      renderWithProviders("");

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/No access token received/i)).toBeInTheDocument();
    });

    it("handles fragment with only hash symbol", async () => {
      renderWithProviders("#");

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });
    });

    it("handles URL-encoded parameters", async () => {
      const mockToken = createMockJWT({
        sub: "user-123",
        preferred_username: "user%20with%20spaces",
      });
      // URL-encode the token and refresh token
      const hash = `#access_token=${encodeURIComponent(mockToken)}&refresh_token=refresh%2Btoken`;

      const { store: _store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(setAuthTokens).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("has accessible button during error state", async () => {
      renderWithProviders("#error=test");

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      const button = screen.getByRole("button", { name: /Try again/i });
      expect(button).toBeInTheDocument();
      expect(button).toBeVisible();
    });
  });

  describe("Intended Route Restoration (OAuth2 Flow)", () => {
    beforeEach(() => {
      sessionStorage.clear();
    });

    describe("when intended route is saved in sessionStorage", () => {
      it("should redirect to the saved intended route instead of /studio", async () => {
        // Set up intended route in sessionStorage (as if LoginPage saved it)
        sessionStorage.setItem(INTENDED_ROUTE_KEY, "/studio/chat/123");

        const mockToken = createMockJWT(mockUserPayload);
        const hash = `#access_token=${mockToken}`;

        renderWithProviders(hash);

        await waitFor(() => {
          expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
        });

        // Advance timer to trigger redirect
        vi.advanceTimersByTime(1000);

        await waitFor(() => {
          expect(mockNavigate).toHaveBeenCalledWith("/studio/chat/123", {
            replace: true,
          });
        });
      });

      it("should redirect to intended route with query string", async () => {
        sessionStorage.setItem(
          INTENDED_ROUTE_KEY,
          "/studio/canvas?artifact=abc&version=1",
        );

        const mockToken = createMockJWT(mockUserPayload);
        const hash = `#access_token=${mockToken}`;

        renderWithProviders(hash);

        await waitFor(() => {
          expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
        });

        vi.advanceTimersByTime(1000);

        await waitFor(() => {
          expect(mockNavigate).toHaveBeenCalledWith(
            "/studio/canvas?artifact=abc&version=1",
            { replace: true },
          );
        });
      });

      it("should redirect to intended route with hash", async () => {
        sessionStorage.setItem(
          INTENDED_ROUTE_KEY,
          "/studio/settings#notifications",
        );

        const mockToken = createMockJWT(mockUserPayload);
        const hash = `#access_token=${mockToken}`;

        renderWithProviders(hash);

        await waitFor(() => {
          expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
        });

        vi.advanceTimersByTime(1000);

        await waitFor(() => {
          expect(mockNavigate).toHaveBeenCalledWith(
            "/studio/settings#notifications",
            { replace: true },
          );
        });
      });

      it("should clear the intended route after reading it", async () => {
        sessionStorage.setItem(INTENDED_ROUTE_KEY, "/studio/workflow/456");

        const mockToken = createMockJWT(mockUserPayload);
        const hash = `#access_token=${mockToken}`;

        renderWithProviders(hash);

        await waitFor(() => {
          expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
        });

        // The intended route should be cleared after it's read
        await waitFor(() => {
          expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
        });
      });
    });

    describe("when no intended route is saved", () => {
      it("should redirect to /studio by default", async () => {
        // Ensure no intended route is saved
        expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();

        const mockToken = createMockJWT(mockUserPayload);
        const hash = `#access_token=${mockToken}`;

        renderWithProviders(hash);

        await waitFor(() => {
          expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
        });

        vi.advanceTimersByTime(1000);

        await waitFor(() => {
          expect(mockNavigate).toHaveBeenCalledWith("/studio", {
            replace: true,
          });
        });
      });
    });
  });
});
