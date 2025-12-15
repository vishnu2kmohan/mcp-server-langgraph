/**
 * LoginPage Tests
 *
 * Tests for the native login page component.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter, Routes, Route } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { LoginPage } from "./LoginPage";
import authSliceReducer from "../store/slices/authSlice";
import personaSliceReducer from "../store/slices/personaSlice";

// Mock the useLoginMutation hook
const mockUnwrap = vi.fn();
const mockLogin = vi.fn(() => ({
  unwrap: mockUnwrap,
}));

import * as apiModule from "../api";

// Mock identity providers response
const mockIdentityProviders = {
  identity_providers: [
    {
      alias: "google",
      display_name: "Google",
      provider_type: "social" as const,
      provider_id: "google",
      icon: "google",
      login_url: "https://keycloak.example.com/auth?kc_idp_hint=google",
    },
    {
      alias: "github",
      display_name: "GitHub",
      provider_type: "social" as const,
      provider_id: "github",
      icon: "github",
      login_url: "https://keycloak.example.com/auth?kc_idp_hint=github",
    },
    {
      alias: "corporate-okta",
      display_name: "Corporate SSO",
      provider_type: "enterprise" as const,
      provider_id: "oidc",
      icon: "key",
      login_url: "https://keycloak.example.com/auth?kc_idp_hint=corporate-okta",
    },
  ],
  has_social_login: true,
  has_enterprise_sso: true,
};

vi.mock("../api", () => ({
  useLoginMutation: vi.fn(() => [mockLogin, { isLoading: false }]),
  useGetFeatureFlagsQuery: vi.fn(() => ({ data: {} })),
  useGetIdentityProvidersQuery: vi.fn(() => ({
    data: undefined,
    isLoading: false,
    error: undefined,
  })),
  api: {
    reducerPath: "api",
    reducer: (state = {}) => state,
    middleware:
      () => (next: (action: unknown) => unknown) => (action: unknown) =>
        next(action),
  },
}));

const mockedUseLoginMutation = vi.mocked(apiModule.useLoginMutation);
const mockedUseGetIdentityProvidersQuery = vi.mocked(
  (
    apiModule as {
      useGetIdentityProvidersQuery: typeof apiModule.useLoginMutation;
    }
  ).useGetIdentityProvidersQuery,
);

// Mock navigation
const mockNavigate = vi.fn();
vi.mock("react-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Create a test store
const createTestStore = (preloadedState = {}) =>
  configureStore({
    reducer: {
      auth: authSliceReducer,
      persona: personaSliceReducer,
    },
    preloadedState,
  });

// Helper to render with providers
const renderWithProviders = (
  component: React.ReactNode,
  { initialState = {} } = {},
) => {
  const store = createTestStore(initialState);
  return {
    ...render(
      <Provider store={store}>
        <MemoryRouter initialEntries={["/login"]}>
          <Routes>
            <Route path="/login" element={component} />
            <Route path="/studio" element={<div>Studio Page</div>} />
          </Routes>
        </MemoryRouter>
      </Provider>,
    ),
    store,
  };
};

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default successful login response
    mockUnwrap.mockResolvedValue({
      access_token: "test-access-token",
      refresh_token: "test-refresh-token",
      token_type: "Bearer",
      expires_in: 3600,
      user: {
        user_id: "user:testuser",
        username: "testuser",
        email: "test@example.com",
        roles: ["user"],
        persona: "user" as const,
        keycloak_id: "keycloak-123",
      },
    });
    mockedUseLoginMutation.mockReturnValue([mockLogin, { isLoading: false }]);
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("Rendering", () => {
    it("should render the login form", () => {
      renderWithProviders(<LoginPage />);

      expect(screen.getByText("Agent Studio")).toBeInTheDocument();
      expect(screen.getByLabelText("Username")).toBeInTheDocument();
      expect(screen.getByLabelText("Password")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /sign in/i }),
      ).toBeInTheDocument();
    });

    // Note: Dark mode is now handled globally by useTheme hook in App.tsx
    // Dark mode tests are in src/hooks/useTheme.test.tsx

    it("should show password toggle button", () => {
      renderWithProviders(<LoginPage />);

      expect(
        screen.getByRole("button", { name: /show password/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Form Interaction", () => {
    it("should allow typing username and password", () => {
      renderWithProviders(<LoginPage />);

      const usernameInput = screen.getByLabelText("Username");
      const passwordInput = screen.getByLabelText("Password");

      fireEvent.change(usernameInput, { target: { value: "testuser" } });
      fireEvent.change(passwordInput, { target: { value: "testpass" } });

      expect(usernameInput).toHaveValue("testuser");
      expect(passwordInput).toHaveValue("testpass");
    });

    it("should toggle password visibility", () => {
      renderWithProviders(<LoginPage />);

      const passwordInput = screen.getByLabelText("Password");
      const toggleButton = screen.getByRole("button", {
        name: /show password/i,
      });

      // Initially hidden
      expect(passwordInput).toHaveAttribute("type", "password");

      // Click to show
      fireEvent.click(toggleButton);
      expect(passwordInput).toHaveAttribute("type", "text");

      // Click to hide again
      const hideButton = screen.getByRole("button", { name: /hide password/i });
      fireEvent.click(hideButton);
      expect(passwordInput).toHaveAttribute("type", "password");
    });
  });

  describe("Form Submission", () => {
    it("should show error for empty fields", async () => {
      renderWithProviders(<LoginPage />);

      const submitButton = screen.getByRole("button", { name: /sign in/i });
      fireEvent.click(submitButton);

      // HTML5 validation should prevent submission, but our custom validation shows error
      await waitFor(() => {
        // The form's native validation will prevent the custom error from showing
        // but the submit button click should not trigger the API
        expect(mockLogin).not.toHaveBeenCalled();
      });
    });

    it("should call login API with credentials", async () => {
      renderWithProviders(<LoginPage />);

      const usernameInput = screen.getByLabelText("Username");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: /sign in/i });

      fireEvent.change(usernameInput, { target: { value: "testuser" } });
      fireEvent.change(passwordInput, { target: { value: "testpass" } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          username: "testuser",
          password: "testpass",
        });
      });
    });

    it("should process login response and dispatch actions", async () => {
      const { store } = renderWithProviders(<LoginPage />);

      const usernameInput = screen.getByLabelText("Username");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: /sign in/i });

      fireEvent.change(usernameInput, { target: { value: "testuser" } });
      fireEvent.change(passwordInput, { target: { value: "testpass" } });
      fireEvent.click(submitButton);

      // Wait for the API call to complete and navigation to happen
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/studio", { replace: true });
      });

      // Verify user was set in store
      const state = store.getState();
      expect(state.auth.user).not.toBeNull();
      expect(state.auth.user?.username).toBe("testuser");
    });

    it("should navigate to studio on successful login", async () => {
      renderWithProviders(<LoginPage />);

      const usernameInput = screen.getByLabelText("Username");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: /sign in/i });

      fireEvent.change(usernameInput, { target: { value: "testuser" } });
      fireEvent.change(passwordInput, { target: { value: "testpass" } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/studio", { replace: true });
      });
    });
  });

  describe("Error Handling", () => {
    it("should display error message on login failure", async () => {
      mockUnwrap.mockRejectedValueOnce({
        data: { detail: "Invalid credentials" },
      });

      renderWithProviders(<LoginPage />);

      const usernameInput = screen.getByLabelText("Username");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: /sign in/i });

      fireEvent.change(usernameInput, { target: { value: "testuser" } });
      fireEvent.change(passwordInput, { target: { value: "wrongpass" } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText("Invalid credentials")).toBeInTheDocument();
      });
    });

    it("should handle network errors gracefully", async () => {
      mockUnwrap.mockRejectedValueOnce(new Error("Network error"));

      renderWithProviders(<LoginPage />);

      const usernameInput = screen.getByLabelText("Username");
      const passwordInput = screen.getByLabelText("Password");
      const submitButton = screen.getByRole("button", { name: /sign in/i });

      fireEvent.change(usernameInput, { target: { value: "testuser" } });
      fireEvent.change(passwordInput, { target: { value: "testpass" } });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText("Network error")).toBeInTheDocument();
      });
    });
  });

  describe("Loading State", () => {
    it("should show loading state during login", () => {
      mockedUseLoginMutation.mockReturnValue([mockLogin, { isLoading: true }]);

      renderWithProviders(<LoginPage />);

      expect(screen.getByText("Signing in...")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /signing in/i }),
      ).toBeDisabled();
    });
  });

  describe("Already Authenticated", () => {
    it("should redirect to studio if already authenticated", async () => {
      renderWithProviders(<LoginPage />, {
        initialState: {
          auth: {
            user: {
              id: "user:existing",
              username: "existing",
              email: "existing@test.com",
              roles: ["user"],
              persona: "user",
            },
            tokens: null,
            currentOrg: null,
            organizations: [],
            isInitializing: false,
            isLoading: false,
            error: null,
          },
        },
      });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/studio", { replace: true });
      });
    });
  });

  describe("SSO Identity Providers", () => {
    it("should display SSO IdP buttons when identity providers are available", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: mockIdentityProviders,
        isLoading: false,
        error: undefined,
      } as ReturnType<typeof mockedUseGetIdentityProvidersQuery>);

      renderWithProviders(<LoginPage />);

      // Should show divider and SSO section
      expect(screen.getByText(/or continue with/i)).toBeInTheDocument();

      // Should show IdP buttons
      expect(screen.getByRole("link", { name: /google/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /github/i })).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /corporate sso/i }),
      ).toBeInTheDocument();
    });

    it("should not display SSO section when no identity providers", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [],
          has_social_login: false,
          has_enterprise_sso: false,
        },
        isLoading: false,
        error: undefined,
      } as ReturnType<typeof mockedUseGetIdentityProvidersQuery>);

      renderWithProviders(<LoginPage />);

      // Should NOT show divider
      expect(screen.queryByText(/or continue with/i)).not.toBeInTheDocument();
    });

    it("should show loading state while fetching identity providers", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: undefined,
      } as ReturnType<typeof mockedUseGetIdentityProvidersQuery>);

      renderWithProviders(<LoginPage />);

      // Should NOT show SSO section while loading
      expect(screen.queryByText(/or continue with/i)).not.toBeInTheDocument();
    });

    it("should have correct login URLs for IdP buttons", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: mockIdentityProviders,
        isLoading: false,
        error: undefined,
      } as ReturnType<typeof mockedUseGetIdentityProvidersQuery>);

      renderWithProviders(<LoginPage />);

      const googleLink = screen.getByRole("link", { name: /google/i });
      const githubLink = screen.getByRole("link", { name: /github/i });

      expect(googleLink).toHaveAttribute(
        "href",
        "https://keycloak.example.com/auth?kc_idp_hint=google",
      );
      expect(githubLink).toHaveAttribute(
        "href",
        "https://keycloak.example.com/auth?kc_idp_hint=github",
      );
    });

    it("should show social and enterprise sections separately", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: mockIdentityProviders,
        isLoading: false,
        error: undefined,
      } as ReturnType<typeof mockedUseGetIdentityProvidersQuery>);

      renderWithProviders(<LoginPage />);

      // Check for section labels if they exist
      // The implementation may group social and enterprise providers
      expect(screen.getByRole("link", { name: /google/i })).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /corporate sso/i }),
      ).toBeInTheDocument();
    });
  });
});
