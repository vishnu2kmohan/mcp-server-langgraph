/**
 * LoginPage Tests
 *
 * Tests for the OAuth2 + PKCE login page component.
 *
 * Per RFC 9700 (ADR-0071): ROPC MUST NOT be used. The login page now only
 * supports OAuth2 Authorization Code + PKCE flow via SSO buttons.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter, Routes, Route } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { LoginPage } from "./LoginPage";
import authSliceReducer from "../store/slices/authSlice";
import personaSliceReducer from "../store/slices/personaSlice";
import { INTENDED_ROUTE_KEY } from "../utils/intendedRoute";
import { getDisplayVersion, APP_VERSION } from "../config/version";

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

// Helper to render with location state (for testing intended route persistence)
const renderWithLocationState = (
  component: React.ReactNode,
  locationState?: {
    from?: { pathname: string; search?: string; hash?: string };
  },
) => {
  const store = createTestStore({});
  return {
    ...render(
      <Provider store={store}>
        <MemoryRouter
          initialEntries={[
            {
              pathname: "/login",
              state: locationState,
            },
          ]}
        >
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
    cleanup();
    localStorage.clear();
    sessionStorage.clear();
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

  describe("Version Contract", () => {
    /**
     * Version contract tests to prevent hardcoded version regressions.
     *
     * These tests ensure the LoginPage uses the dynamic version from
     * config/version.ts rather than hardcoded strings like "v0.1.0".
     *
     * Regression prevention for: version reverting from v2.9.0-dev to v0.1.0
     */

    it("should display version from getDisplayVersion()", () => {
      renderWithProviders(<LoginPage />);

      // Get the expected version from the config
      const expectedVersion = getDisplayVersion();

      // Find the version text in the footer
      const versionElement = screen.getByText(
        new RegExp(`Agent Studio ${expectedVersion}`),
      );
      expect(versionElement).toBeInTheDocument();
    });

    it("should NOT contain hardcoded 'v0.1.0' version", () => {
      renderWithProviders(<LoginPage />);

      // This is a regression test - v0.1.0 was accidentally hardcoded
      expect(screen.queryByText(/v0\.1\.0/)).not.toBeInTheDocument();
    });

    it("should NOT contain hardcoded version strings", () => {
      renderWithProviders(<LoginPage />);

      // Guard against common hardcoded version patterns
      // These would indicate the version was accidentally hardcoded instead
      // of using getDisplayVersion()
      const hardcodedPatterns = [
        /v0\.0\.1/,
        /v0\.1\.0/,
        /v1\.0\.0(?!-)/i, // v1.0.0 without suffix (but allow v1.0.0-dev)
        /version not set/i,
        /unknown version/i,
      ];

      hardcodedPatterns.forEach((pattern) => {
        expect(screen.queryByText(pattern)).not.toBeInTheDocument();
      });
    });

    it("should use the current APP_VERSION", () => {
      renderWithProviders(<LoginPage />);

      // The displayed version should contain the APP_VERSION
      expect(screen.getByText(new RegExp(APP_VERSION))).toBeInTheDocument();
    });

    it("should display version with 'v' prefix", () => {
      renderWithProviders(<LoginPage />);

      // The version should be prefixed with 'v' (e.g., "v2.9.0-dev")
      expect(
        screen.getByText(/Agent Studio v\d+\.\d+\.\d+/),
      ).toBeInTheDocument();
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

  describe("Provider Icons - All Switch Cases", () => {
    it("should render Microsoft icon", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [
            {
              alias: "microsoft",
              display_name: "Microsoft",
              provider_type: "social" as const,
              provider_id: "microsoft",
              icon: "microsoft",
              login_url: "/auth/microsoft",
            },
          ],
          has_social_login: true,
          has_enterprise_sso: false,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      const button = screen.getByRole("link", { name: /microsoft/i });
      expect(button.querySelector("svg")).toBeInTheDocument();
    });

    it("should render Facebook icon", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [
            {
              alias: "facebook",
              display_name: "Facebook",
              provider_type: "social" as const,
              provider_id: "facebook",
              icon: "facebook",
              login_url: "/auth/facebook",
            },
          ],
          has_social_login: true,
          has_enterprise_sso: false,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      const button = screen.getByRole("link", { name: /facebook/i });
      expect(button.querySelector("svg")).toBeInTheDocument();
    });

    it("should render LinkedIn icon", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [
            {
              alias: "linkedin",
              display_name: "LinkedIn",
              provider_type: "social" as const,
              provider_id: "linkedin",
              icon: "linkedin",
              login_url: "/auth/linkedin",
            },
          ],
          has_social_login: true,
          has_enterprise_sso: false,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      const button = screen.getByRole("link", { name: /linkedin/i });
      expect(button.querySelector("svg")).toBeInTheDocument();
    });

    it("should render Apple icon", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [
            {
              alias: "apple",
              display_name: "Apple",
              provider_type: "social" as const,
              provider_id: "apple",
              icon: "apple",
              login_url: "/auth/apple",
            },
          ],
          has_social_login: true,
          has_enterprise_sso: false,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      const button = screen.getByRole("link", { name: /apple/i });
      expect(button.querySelector("svg")).toBeInTheDocument();
    });

    it("should render Shield icon for SAML providers", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [
            {
              alias: "saml-idp",
              display_name: "SAML Provider",
              provider_type: "enterprise" as const,
              provider_id: "saml",
              icon: "shield",
              login_url: "/auth/saml",
            },
          ],
          has_social_login: false,
          has_enterprise_sso: true,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      const button = screen.getByRole("link", { name: /saml provider/i });
      expect(button.querySelector("svg")).toBeInTheDocument();
    });

    it("should render default ExternalLink icon for unknown provider icons", () => {
      mockedUseGetIdentityProvidersQuery.mockReturnValue({
        data: {
          identity_providers: [
            {
              alias: "custom-idp",
              display_name: "Custom Provider",
              provider_type: "enterprise" as const,
              provider_id: "custom",
              icon: "unknown-icon-type",
              login_url: "/auth/custom",
            },
          ],
          has_social_login: false,
          has_enterprise_sso: true,
        },
        isLoading: false,
        error: undefined,
      });

      renderWithProviders(<LoginPage />);

      const button = screen.getByRole("link", { name: /custom provider/i });
      expect(button.querySelector("svg")).toBeInTheDocument();
    });
  });

  describe("Intended Route Persistence (OAuth2 Flow)", () => {
    beforeEach(() => {
      sessionStorage.clear();
    });

    describe("when navigated from AuthGuard with 'from' state", () => {
      it("should save the intended route to sessionStorage", async () => {
        renderWithLocationState(<LoginPage />, {
          from: {
            pathname: "/studio/chat/123",
          },
        });

        await waitFor(() => {
          expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
            "/studio/chat/123",
          );
        });
      });

      it("should save the intended route with query string", async () => {
        renderWithLocationState(<LoginPage />, {
          from: {
            pathname: "/studio/canvas",
            search: "?artifact=abc&version=1",
          },
        });

        await waitFor(() => {
          expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
            "/studio/canvas?artifact=abc&version=1",
          );
        });
      });

      it("should save the intended route with hash", async () => {
        renderWithLocationState(<LoginPage />, {
          from: {
            pathname: "/studio/settings",
            hash: "#notifications",
          },
        });

        await waitFor(() => {
          expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
            "/studio/settings#notifications",
          );
        });
      });

      it("should save the intended route with query string and hash", async () => {
        renderWithLocationState(<LoginPage />, {
          from: {
            pathname: "/studio/workflow",
            search: "?id=456",
            hash: "#step-3",
          },
        });

        await waitFor(() => {
          expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBe(
            "/studio/workflow?id=456#step-3",
          );
        });
      });
    });

    describe("when navigated without 'from' state", () => {
      it("should not save anything to sessionStorage", async () => {
        renderWithLocationState(<LoginPage />);

        // Wait for page to render
        await waitFor(() => {
          expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
        });

        expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
      });
    });

    describe("excluded paths", () => {
      it("should not save /login as intended route", async () => {
        renderWithLocationState(<LoginPage />, {
          from: {
            pathname: "/login",
          },
        });

        await waitFor(() => {
          expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
        });

        expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
      });

      it("should not save /auth/callback as intended route", async () => {
        renderWithLocationState(<LoginPage />, {
          from: {
            pathname: "/auth/callback",
          },
        });

        await waitFor(() => {
          expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
        });

        expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
      });

      it("should not save root path as intended route", async () => {
        renderWithLocationState(<LoginPage />, {
          from: {
            pathname: "/",
          },
        });

        await waitFor(() => {
          expect(screen.getByText("Sign in to continue")).toBeInTheDocument();
        });

        expect(sessionStorage.getItem(INTENDED_ROUTE_KEY)).toBeNull();
      });
    });
  });
});
