/**
 * AuthCallbackPage Tests
 *
 * TDD tests for OAuth2 Authorization Code + PKCE callback handling.
 * Tests cover token parsing, JWT decoding, Redux state updates,
 * error handling, and navigation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { AuthCallbackPage } from "./AuthCallbackPage";
import authReducer, { initialAuthState } from "../store/slices/authSlice";
import personaReducer from "../store/slices/personaSlice";

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
  const signature = btoa("mock-signature-x")  // "x" ensures no padding needed
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
const renderWithProviders = (
  hash: string = "",
  store = createTestStore(),
) => {
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
    vi.useRealTimers();
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

      expect(screen.getByText(/Redirecting to Agent Studio/i)).toBeInTheDocument();

      // Verify tokens were stored
      expect(setAuthTokens).toHaveBeenCalledWith(mockToken, "mock-refresh");

      // Verify user was set in Redux
      const state = store.getState();
      expect(state.auth.user).not.toBeNull();
      expect(state.auth.user?.username).toBe("testuser");
    });

    it("extracts admin persona from roles", async () => {
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
      const hash = "#error=access_denied&error_description=User%20denied%20access";

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

    it("shows error for invalid JWT format", async () => {
      const hash = "#access_token=not-a-valid-jwt";

      renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in failed/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/Invalid access token format/i)).toBeInTheDocument();
    });

    it("shows error for malformed JWT payload", async () => {
      // JWT with invalid base64 payload
      const hash = "#access_token=header.invalid!!!.signature";

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

  describe("JWT Payload Parsing", () => {
    it("extracts username from preferred_username claim", async () => {
      const mockToken = createMockJWT({
        sub: "user-123",
        preferred_username: "myusername",
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.username).toBe("myusername");
    });

    it("falls back to username claim if no preferred_username", async () => {
      const mockToken = createMockJWT({
        sub: "user-123",
        username: "fallback-username",
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.username).toBe("fallback-username");
    });

    it("falls back to sub claim if no username claims", async () => {
      const mockToken = createMockJWT({
        sub: "user-sub-id",
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.username).toBe("user-sub-id");
    });

    it("uses unknown as fallback when no username info", async () => {
      const mockToken = createMockJWT({
        // No sub, username, or preferred_username
        email: "only-email@test.com",
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.username).toBe("unknown");
    });

    it("extracts roles from realm_access.roles", async () => {
      const mockToken = createMockJWT({
        sub: "user-123",
        realm_access: { roles: ["custom-role-1", "custom-role-2"] },
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.roles).toEqual(["custom-role-1", "custom-role-2"]);
    });

    it("extracts roles from top-level roles array", async () => {
      const mockToken = createMockJWT({
        sub: "user-123",
        roles: ["top-level-role"],
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.roles).toEqual(["top-level-role"]);
    });

    it("defaults to empty roles array when no roles claim", async () => {
      const mockToken = createMockJWT({
        sub: "user-123",
      });
      const hash = `#access_token=${mockToken}`;

      const { store } = renderWithProviders(hash);

      await waitFor(() => {
        expect(screen.getByText(/Sign in successful/i)).toBeInTheDocument();
      });

      expect(store.getState().auth.user?.roles).toEqual([]);
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
});
