/**
 * LoginPage Tests
 *
 * Tests for the OAuth2 + PKCE login page component.
 *
 * Per RFC 9700 (ADR-0071): ROPC MUST NOT be used. The login page now only
 * supports OAuth2 Authorization Code + PKCE flow via SSO buttons.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter, Routes, Route } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { LoginPage } from "./LoginPage";
import authSliceReducer from "../store/slices/authSlice";
import personaSliceReducer from "../store/slices/personaSlice";

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

const mockedUseGetIdentityProvidersQuery = vi.mocked(
  (
    apiModule as {
      useGetIdentityProvidersQuery: () => {
        data: typeof mockIdentityProviders | undefined;
        isLoading: boolean;
        error: unknown;
      };
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
    // Default: no IdPs loaded yet
    mockedUseGetIdentityProvidersQuery.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: undefined,
    });
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("Rendering", () => {
    it("should render the login page with title and branding", () => {
      renderWithProviders(<LoginPage />);

      expect(screen.getByText("Agent Studio")).toBeInTheDocument();
      expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
    });

    it("should render the main SSO login button", () => {
      renderWithProviders(<LoginPage />);

      // Main SSO button - it's a link (<a>) not a button
      const ssoLink = screen.getByRole("link", { name: /sign in with sso/i });
      expect(ssoLink).toBeInTheDocument();
      expect(ssoLink).toHaveAttribute("href", "/api/v1/auth/login");
    });

    it("should show OAuth2 + PKCE compliance text", () => {
      renderWithProviders(<LoginPage />);

      expect(
        screen.getByText(/secure oauth2 \+ pkce authentication/i),
      ).toBeInTheDocument();
    });

    it("should show version footer", () => {
      renderWithProviders(<LoginPage />);

      expect(screen.getByText(/agent studio v/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner while fetching identity providers", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      // Should show loading spinner with accessible role="status"
      expect(screen.getByRole("status")).toBeInTheDocument();
      expect(screen.getByLabelText(/loading/i)).toBeInTheDocument();
    });

    it("should not show SSO button while loading", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      // Main SSO button should not be visible during loading
      expect(
        screen.queryByRole("link", { name: /sign in with sso/i }),
      ).not.toBeInTheDocument();
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

    it("should not redirect when not authenticated", async () => {
      renderWithProviders(<LoginPage />);

      // Wait a tick to ensure useEffect has run
      await waitFor(() => {
        expect(mockNavigate).not.toHaveBeenCalled();
      });
    });
  });

  describe("SSO Identity Providers", () => {
    it("should display SSO IdP buttons when identity providers are available", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: mockIdentityProviders,
        isLoading: false,
        error: undefined,
      });

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

    it("should not display divider when no identity providers", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [],
          has_social_login: false,
          has_enterprise_sso: false,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      // Should NOT show divider
      expect(screen.queryByText(/or continue with/i)).not.toBeInTheDocument();
    });

    it("should have correct login URLs for IdP buttons", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: mockIdentityProviders,
        isLoading: false,
        error: undefined,
      });

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

    it("should show social and enterprise providers when both exist", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: mockIdentityProviders,
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      // Both social (Google, GitHub) and enterprise (Corporate SSO) should be shown
      expect(screen.getByRole("link", { name: /google/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /github/i })).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /corporate sso/i }),
      ).toBeInTheDocument();
    });

    it("should only show available IdP types", () => {
      // Only social providers
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [mockIdentityProviders.identity_providers[0]], // Only Google
          has_social_login: true,
          has_enterprise_sso: false,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      expect(screen.getByRole("link", { name: /google/i })).toBeInTheDocument();
      expect(
        screen.queryByRole("link", { name: /corporate sso/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("OAuth2 + PKCE Flow (RFC 9700 Compliance)", () => {
    it("should NOT have username/password form fields (ROPC removed)", () => {
      renderWithProviders(<LoginPage />);

      // These should NOT exist per RFC 9700
      expect(screen.queryByLabelText("Username")).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
    });

    it("should NOT have a form submit button (ROPC removed)", () => {
      renderWithProviders(<LoginPage />);

      // No form submit button - only SSO links
      expect(
        screen.queryByRole("button", { name: /sign in/i }),
      ).not.toBeInTheDocument();
    });

    it("should use link-based navigation for SSO (no form POST)", () => {
      renderWithProviders(<LoginPage />);

      // Main SSO button should be a link, not a form button
      const ssoLink = screen.getByRole("link", { name: /sign in with sso/i });
      expect(ssoLink.tagName).toBe("A");
      expect(ssoLink).toHaveAttribute("href", "/api/v1/auth/login");
    });

    it("should indicate PKCE authentication method", () => {
      renderWithProviders(<LoginPage />);

      // The page should indicate it uses PKCE
      expect(
        screen.getByText(/secure oauth2 \+ pkce authentication/i),
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible main heading", () => {
      renderWithProviders(<LoginPage />);

      expect(
        screen.getByRole("heading", { name: /agent studio/i }),
      ).toBeInTheDocument();
    });

    it("should have accessible link names for IdP buttons", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: mockIdentityProviders,
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      // All IdP buttons should be accessible links with descriptive names
      expect(screen.getByRole("link", { name: /google/i })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /github/i })).toBeInTheDocument();
      expect(
        screen.getByRole("link", { name: /corporate sso/i }),
      ).toBeInTheDocument();
    });
  });
});
