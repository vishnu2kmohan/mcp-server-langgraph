/**
 * authSlice Test Utilities
 *
 * Shared mock data, store factory, and test setup helpers.
 */

import { vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import authReducer, { initialAuthState } from "./authSlice";
import type { AuthSliceState } from "./authSlice";
import type { User, AuthTokens, Organization } from "../../types/auth";

// =============================================================================
// Mock Data
// =============================================================================

export const mockUser: User = {
  id: "user-1",
  username: "testuser",
  email: "test@example.com",
  roles: ["user"],
  persona: "user",
};

export const mockTokens: AuthTokens = {
  accessToken: "mock-access-token",
  refreshToken: "mock-refresh-token",
  expiresAt: Date.now() + 3600000, // 1 hour from now
  refreshExpiresAt: Date.now() + 86400000, // 24 hours from now
};

export const mockOrg: Organization = {
  id: "org-1",
  name: "Test Org",
  role: "admin",
  tier: "shared",
};

// =============================================================================
// Store Factory
// =============================================================================

export const createTestStore = (preloadedState?: Partial<AuthSliceState>) => {
  return configureStore({
    reducer: { auth: authReducer },
    preloadedState: preloadedState
      ? { auth: { ...initialAuthState, ...preloadedState } }
      : undefined,
  });
};

// =============================================================================
// Mock Setup
// =============================================================================

export const createMockLocalStorage = () => {
  const mockLocalStorage: Record<string, string> = {};
  return {
    storage: mockLocalStorage,
    setup: () => {
      vi.stubGlobal("localStorage", {
        getItem: vi.fn((key: string) => mockLocalStorage[key] || null),
        setItem: vi.fn((key: string, value: string) => {
          mockLocalStorage[key] = value;
        }),
        removeItem: vi.fn((key: string) => {
          delete mockLocalStorage[key];
        }),
      });
    },
    cleanup: () => {
      Object.keys(mockLocalStorage).forEach(
        (key) => delete mockLocalStorage[key],
      );
    },
  };
};

export const createMockFetch = () => {
  const mockFetch = vi.fn();
  return {
    mock: mockFetch,
    setup: () => {
      vi.stubGlobal("fetch", mockFetch);
    },
  };
};
