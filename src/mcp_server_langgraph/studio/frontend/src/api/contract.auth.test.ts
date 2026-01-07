/**
 * API Contract Tests - Auth Endpoints
 *
 * ADR-0091: Uses generated types for auth endpoint validation.
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import {
  isLoginResponse,
  isLogoutResponse,
  isIdentityProvider,
  isIdentityProvidersListResponse,
} from "./contract.validators.test-utils";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// Auth Endpoints Contract Tests (ADR-0091: Uses generated types)
// =============================================================================

describe("Auth Endpoints (Generated Types)", () => {
  it("should validate LoginResponse schema", () => {
    const validResponse = {
      access_token: "test-access-token-placeholder",
      refresh_token: "test-refresh-token-placeholder",
      token_type: "Bearer",
      expires_in: 3600,
    };
    expect(isLoginResponse(validResponse)).toBe(true);
  });

  it("should allow null refresh_token in LoginResponse", () => {
    const responseWithNull = {
      access_token: "test-access-token-placeholder",
      refresh_token: null,
      token_type: "Bearer",
      expires_in: 3600,
    };
    expect(isLoginResponse(responseWithNull)).toBe(true);
  });

  it("should validate LogoutResponse schema", () => {
    const validResponse = {
      success: true,
      message: "Successfully logged out",
    };
    expect(isLogoutResponse(validResponse)).toBe(true);
  });

  it("should allow minimal LogoutResponse", () => {
    const minimalResponse = {
      success: true,
    };
    expect(isLogoutResponse(minimalResponse)).toBe(true);
  });

  it("should validate IdentityProvider schema", () => {
    const validProvider = {
      alias: "google",
      display_name: "Sign in with Google",
      icon: "google",
      login_url: "/api/v1/auth/login?kc_idp_hint=google",
    };
    expect(isIdentityProvider(validProvider)).toBe(true);
  });

  it("should validate IdentityProvidersListResponse schema", () => {
    const validResponse = {
      identity_providers: [
        {
          alias: "google",
          display_name: "Sign in with Google",
          icon: "google",
          login_url: "/api/v1/auth/login?kc_idp_hint=google",
        },
        {
          alias: "github",
          display_name: "Sign in with GitHub",
          icon: "github",
          login_url: "/api/v1/auth/login?kc_idp_hint=github",
        },
      ],
    };
    expect(isIdentityProvidersListResponse(validResponse)).toBe(true);
  });

  it("should allow empty identity_providers array", () => {
    const emptyResponse = {
      identity_providers: [],
    };
    expect(isIdentityProvidersListResponse(emptyResponse)).toBe(true);
  });

  it("should allow undefined identity_providers (optional field)", () => {
    const minimalResponse = {};
    expect(isIdentityProvidersListResponse(minimalResponse)).toBe(true);
  });
});
