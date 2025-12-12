/**
 * Authentication Store
 *
 * Zustand store for managing authentication state including:
 * - User session
 * - JWT tokens (access + refresh)
 * - Organization context
 * - Persona-based routing
 *
 * Uses localStorage persistence for token storage.
 */

import { create, StateCreator } from 'zustand';
import { persist, createJSONStorage, PersistOptions } from 'zustand/middleware';
import type {
  AuthStore,
  AuthState,
  User,
  AuthTokens,
  Organization,
  Persona,
} from '../types/auth';

/** Storage key for auth tokens */
const AUTH_STORAGE_KEY = 'studio-auth';

/** Buffer time before token expiration to trigger refresh (5 minutes) */
const TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000;

/**
 * Derive persona from user roles.
 * Priority: admin > developer > user
 */
export function derivePersona(roles: string[]): Persona {
  if (roles.includes('admin')) {
    return 'admin';
  }
  if (roles.includes('developer')) {
    return 'developer';
  }
  return 'user';
}

/**
 * Check if a token is expired or about to expire.
 */
function isTokenExpired(expiresAt: number): boolean {
  return Date.now() >= expiresAt - TOKEN_REFRESH_BUFFER_MS;
}

/**
 * Initial auth state.
 */
export const initialAuthState: AuthState = {
  user: null,
  tokens: null,
  currentOrg: null,
  organizations: [],
  isInitializing: false,
  isLoading: false,
  error: null,
};

/**
 * Create the auth store state and actions.
 */
const createAuthStore: StateCreator<AuthStore> = (set, get) => ({
  ...initialAuthState,

  /**
   * Initialize auth state from stored tokens.
   * Called on app startup to restore session.
   */
  initialize: async () => {
    set({ isInitializing: true, error: null });

    try {
      const storedTokens = get().tokens;

      if (!storedTokens) {
        set({ isInitializing: false });
        return;
      }

      // Check if refresh token is still valid
      if (isTokenExpired(storedTokens.refreshExpiresAt)) {
        // Refresh token expired, clear state
        set({
          ...initialAuthState,
          isInitializing: false,
        });
        return;
      }

      // Refresh access token if needed
      if (isTokenExpired(storedTokens.expiresAt)) {
        await get().refreshToken();
      }

      // Fetch user info with current token
      const response = await fetch('/api/v1/auth/me', {
        headers: {
          Authorization: `Bearer ${get().tokens?.accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch user info');
      }

      const data = await response.json();
      const user: User = {
        ...data.user,
        persona: derivePersona(data.user.roles || []),
      };

      set({
        user,
        organizations: data.organizations || [],
        currentOrg: data.organizations?.[0] || null,
        isInitializing: false,
      });
    } catch {
      // Clear invalid state
      set({
        ...initialAuthState,
        isInitializing: false,
      });
    }
  },

  /**
   * Login with username and password.
   */
  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Login failed');
      }

      const data = await response.json();

      // Derive persona from roles
      const user: User = {
        ...data.user,
        persona: derivePersona(data.user.roles || []),
      };

      const tokens: AuthTokens = data.tokens;
      const organizations: Organization[] = data.organizations || [];

      set({
        user,
        tokens,
        organizations,
        currentOrg: organizations[0] || null,
        isLoading: false,
        error: null,
      });
    } catch (error) {
      set({
        user: null,
        tokens: null,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Login failed',
      });
    }
  },

  /**
   * Logout and clear all auth state.
   */
  logout: () => {
    // Clear persisted storage
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch {
      // Ignore localStorage errors in test/SSR environments
    }

    // Reset to initial state
    set({
      ...initialAuthState,
    });
  },

  /**
   * Refresh access token using refresh token.
   */
  refreshToken: async () => {
    const currentTokens = get().tokens;

    if (!currentTokens?.refreshToken) {
      get().logout();
      return;
    }

    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refreshToken: currentTokens.refreshToken,
        }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();

      set({
        tokens: data.tokens,
        error: null,
      });
    } catch {
      // Refresh failed, logout
      get().logout();
    }
  },

  /**
   * Switch to a different organization.
   */
  switchOrganization: async (orgId: string) => {
    const { organizations, tokens } = get();

    // Find the organization
    const org = organizations.find((o) => o.id === orgId);

    if (!org) {
      set({ error: 'Organization not found' });
      return;
    }

    try {
      // Notify backend of org switch (for audit logging)
      await fetch('/api/v1/auth/switch-org', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${tokens?.accessToken}`,
          'X-Organization-ID': orgId,
        },
        body: JSON.stringify({ orgId }),
      });

      set({
        currentOrg: org,
        error: null,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to switch organization',
      });
    }
  },

  /**
   * Clear any authentication errors.
   */
  clearError: () => {
    set({ error: null });
  },

  /**
   * Get current access token, refreshing if needed.
   * Returns null if not authenticated.
   */
  getAccessToken: async () => {
    const { tokens } = get();

    if (!tokens) {
      return null;
    }

    // Check if token needs refresh
    if (isTokenExpired(tokens.expiresAt)) {
      // Check if refresh is possible
      if (isTokenExpired(tokens.refreshExpiresAt)) {
        get().logout();
        return null;
      }

      await get().refreshToken();
      return get().tokens?.accessToken ?? null;
    }

    return tokens.accessToken;
  },
});

/**
 * Persist options for the auth store.
 */
const persistOptions: PersistOptions<AuthStore, Pick<AuthStore, 'tokens'>> = {
  name: AUTH_STORAGE_KEY,
  storage: createJSONStorage(() => localStorage),
  // Only persist tokens, restore other state on initialize
  partialize: (state) => ({
    tokens: state.tokens,
  }),
};

/**
 * Authentication store with Zustand.
 * Persists tokens to localStorage for session restoration.
 */
export const useAuthStore = create<AuthStore>()(
  persist(createAuthStore, persistOptions)
);

/**
 * Create a test store without persistence.
 * Use this in tests to avoid localStorage issues.
 */
export const createTestAuthStore = () => create<AuthStore>()(createAuthStore);
