/**
 * Auth Slice
 *
 * Redux slice for managing authentication state including:
 * - User session
 * - JWT tokens (access + refresh)
 * - Organization context
 * - Persona-based routing
 *
 * Uses localStorage persistence for token storage.
 */

import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../index";
import type { User, AuthTokens, Organization, Persona } from "../../types/auth";

// ============================================================================
// Constants
// ============================================================================

/** Storage key for auth tokens */
const AUTH_STORAGE_KEY = "studio-auth";

/** Buffer time before token expiration to trigger refresh (5 minutes) */
const TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000;

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Derive persona from user roles.
 * Priority: admin > developer > user
 */
export function derivePersona(roles: string[]): Persona {
  if (roles.includes("admin")) {
    return "admin";
  }
  if (roles.includes("developer")) {
    return "developer";
  }
  return "user";
}

/**
 * Check if a token is expired or about to expire.
 */
function isTokenExpired(expiresAt: number): boolean {
  return Date.now() >= expiresAt - TOKEN_REFRESH_BUFFER_MS;
}

/**
 * Load tokens from localStorage
 */
function loadTokensFromStorage(): AuthTokens | null {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      return data.state?.tokens || null;
    }
  } catch {
    // Ignore localStorage errors
  }
  return null;
}

/**
 * Save tokens to localStorage
 */
function saveTokensToStorage(tokens: AuthTokens | null): void {
  try {
    if (tokens) {
      localStorage.setItem(
        AUTH_STORAGE_KEY,
        JSON.stringify({ state: { tokens } }),
      );
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  } catch {
    // Ignore localStorage errors
  }
}

/**
 * Clear all auth-related localStorage keys.
 * Called during logout to ensure complete session cleanup.
 *
 * Clears:
 * - studio-auth: Main auth state (authSlice)
 * - access_token: OAuth2 PKCE tokens (LoginPage, AuthCallbackPage)
 * - refresh_token: OAuth2 refresh tokens
 * - auth_token: Legacy token key (deprecated)
 */
function clearAllAuthStorage(): void {
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("auth_token"); // Legacy key
  } catch {
    // Ignore localStorage errors
  }
}

// ============================================================================
// State Type
// ============================================================================

export interface AuthSliceState {
  user: User | null;
  tokens: AuthTokens | null;
  currentOrg: Organization | null;
  organizations: Organization[];
  isInitializing: boolean;
  isLoading: boolean;
  error: string | null;
}

// ============================================================================
// Initial State
// ============================================================================

// Load tokens at module init time to determine initial state
const storedTokens = loadTokensFromStorage();

export const initialAuthState: AuthSliceState = {
  user: null,
  tokens: storedTokens,
  currentOrg: null,
  organizations: [],
  // If we have stored tokens, start in initializing state
  // This prevents AuthGuard from redirecting to login before we can validate the tokens
  isInitializing: storedTokens !== null,
  isLoading: false,
  error: null,
};

// ============================================================================
// Async Thunks
// ============================================================================

export const initializeAuth = createAsyncThunk<
  {
    user: User;
    organizations: Organization[];
    currentOrg: Organization | null;
  } | null,
  void,
  { state: RootState; rejectValue: string }
>("auth/initialize", async (_, { getState, dispatch, rejectWithValue }) => {
  const storedTokens = getState().auth.tokens;

  if (!storedTokens) {
    return null;
  }

  // Check if refresh token is still valid
  if (isTokenExpired(storedTokens.refreshExpiresAt)) {
    dispatch(logout());
    return null;
  }

  // Refresh access token if needed
  if (isTokenExpired(storedTokens.expiresAt)) {
    await dispatch(refreshToken());
  }

  try {
    const currentTokens = getState().auth.tokens;
    const response = await fetch("/api/v1/me", {
      headers: {
        Authorization: `Bearer ${currentTokens?.accessToken}`,
      },
      // Include credentials (cookies) for forward-auth (Keycloak SSO)
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Failed to fetch user info");
    }

    const data = await response.json();
    // Map snake_case API response to camelCase User type
    const user: User = {
      id: data.user_id || data.keycloak_id || "",
      username: data.username || "",
      email: data.email || "",
      firstName: data.first_name,
      lastName: data.last_name,
      displayName: data.display_name,
      roles: data.roles || [],
      persona: data.persona || derivePersona(data.roles || []),
    };

    return {
      user,
      organizations: [],
      currentOrg: null,
    };
  } catch {
    dispatch(logout());
    return rejectWithValue("Failed to initialize auth");
  }
});

export const login = createAsyncThunk<
  { user: User; tokens: AuthTokens; organizations: Organization[] },
  { username: string; password: string },
  { rejectValue: string }
>("auth/login", async ({ username, password }, { rejectWithValue }) => {
  try {
    const response = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
      credentials: "include",
    });

    if (!response.ok) {
      const errorData = await response.json();
      return rejectWithValue(errorData.detail || "Login failed");
    }

    const data = await response.json();

    const user: User = {
      ...data.user,
      persona: derivePersona(data.user.roles || []),
    };

    // Save tokens to localStorage
    saveTokensToStorage(data.tokens);

    return {
      user,
      tokens: data.tokens,
      organizations: data.organizations || [],
    };
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Login failed",
    );
  }
});

export const refreshToken = createAsyncThunk<
  AuthTokens,
  void,
  { state: RootState; rejectValue: string }
>("auth/refreshToken", async (_, { getState, dispatch, rejectWithValue }) => {
  const currentTokens = getState().auth.tokens;

  if (!currentTokens?.refreshToken) {
    dispatch(logout());
    return rejectWithValue("No refresh token");
  }

  try {
    const response = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refreshToken: currentTokens.refreshToken,
      }),
      credentials: "include",
    });

    if (!response.ok) {
      throw new Error("Token refresh failed");
    }

    const data = await response.json();

    // Save new tokens to localStorage
    saveTokensToStorage(data.tokens);

    return data.tokens;
  } catch {
    dispatch(logout());
    return rejectWithValue("Token refresh failed");
  }
});

export const switchOrganization = createAsyncThunk<
  Organization,
  string,
  { state: RootState; rejectValue: string }
>("auth/switchOrganization", async (orgId, { getState, rejectWithValue }) => {
  const { organizations, tokens } = getState().auth;

  const org = organizations.find((o) => o.id === orgId);
  if (!org) {
    return rejectWithValue("Organization not found");
  }

  try {
    await fetch("/api/v1/auth/switch-org", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${tokens?.accessToken}`,
        "X-Organization-ID": orgId,
      },
      body: JSON.stringify({ orgId }),
      credentials: "include",
    });

    return org;
  } catch (error) {
    return rejectWithValue(
      error instanceof Error ? error.message : "Failed to switch organization",
    );
  }
});

// ============================================================================
// Slice
// ============================================================================

export const authSlice = createSlice({
  name: "auth",
  initialState: initialAuthState,
  reducers: {
    logout: (state) => {
      // Clear all auth-related localStorage keys (not just studio-auth)
      // This ensures complete cleanup including OAuth2 PKCE tokens
      clearAllAuthStorage();

      // Reset state
      state.user = null;
      state.tokens = null;
      state.currentOrg = null;
      state.organizations = [];
      state.isInitializing = false;
      state.isLoading = false;
      state.error = null;
    },

    clearAuthError: (state) => {
      state.error = null;
    },

    setTokens: (state, action: PayloadAction<AuthTokens>) => {
      state.tokens = action.payload;
      saveTokensToStorage(action.payload);
    },

    /**
     * Set user from native login response.
     * Used when authenticating via the native login form.
     */
    setUser: (
      state,
      action: PayloadAction<{
        username: string;
        email?: string;
        roles: string[];
        persona: Persona;
      }>,
    ) => {
      state.user = {
        id: `user:${action.payload.username}`,
        username: action.payload.username,
        email: action.payload.email ?? "",
        roles: action.payload.roles,
        persona: action.payload.persona,
      };
      state.isInitializing = false;
      state.isLoading = false;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // initializeAuth
    builder
      .addCase(initializeAuth.pending, (state) => {
        state.isInitializing = true;
        state.error = null;
      })
      .addCase(initializeAuth.fulfilled, (state, action) => {
        state.isInitializing = false;
        if (action.payload) {
          state.user = action.payload.user;
          state.organizations = action.payload.organizations;
          state.currentOrg = action.payload.currentOrg;
        }
      })
      .addCase(initializeAuth.rejected, (state) => {
        state.isInitializing = false;
        state.user = null;
        state.tokens = null;
      });

    // login
    builder
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.user = action.payload.user;
        state.tokens = action.payload.tokens;
        state.organizations = action.payload.organizations;
        state.currentOrg = action.payload.organizations[0] || null;
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.user = null;
        state.tokens = null;
        state.error = action.payload || "Login failed";
      });

    // refreshToken
    builder
      .addCase(refreshToken.fulfilled, (state, action) => {
        state.tokens = action.payload;
        state.error = null;
      })
      .addCase(refreshToken.rejected, (state) => {
        state.user = null;
        state.tokens = null;
      });

    // switchOrganization
    builder
      .addCase(switchOrganization.fulfilled, (state, action) => {
        state.currentOrg = action.payload;
        state.error = null;
      })
      .addCase(switchOrganization.rejected, (state, action) => {
        state.error = action.payload || "Failed to switch organization";
      });
  },
});

// ============================================================================
// Actions
// ============================================================================

export const { logout, clearAuthError, setTokens, setUser } = authSlice.actions;

// ============================================================================
// Selectors
// ============================================================================

export const selectUser = (state: RootState) => state.auth.user;
export const selectTokens = (state: RootState) => state.auth.tokens;
export const selectCurrentOrg = (state: RootState) => state.auth.currentOrg;
export const selectOrganizations = (state: RootState) =>
  state.auth.organizations;
export const selectIsInitializing = (state: RootState) =>
  state.auth.isInitializing;
export const selectIsLoading = (state: RootState) => state.auth.isLoading;
export const selectAuthError = (state: RootState) => state.auth.error;
export const selectIsAuthenticated = (state: RootState) =>
  state.auth.user !== null;
export const selectUserPersona = (state: RootState) =>
  state.auth.user?.persona ?? null;

// ============================================================================
// Thunk for getting access token (with auto-refresh)
// ============================================================================

export const getAccessToken = createAsyncThunk<
  string | null,
  void,
  { state: RootState }
>("auth/getAccessToken", async (_, { getState, dispatch }) => {
  const { tokens } = getState().auth;

  if (!tokens) {
    return null;
  }

  // Check if token needs refresh
  if (isTokenExpired(tokens.expiresAt)) {
    // Check if refresh is possible
    if (isTokenExpired(tokens.refreshExpiresAt)) {
      dispatch(logout());
      return null;
    }

    await dispatch(refreshToken());
    return getState().auth.tokens?.accessToken ?? null;
  }

  return tokens.accessToken;
});

// ============================================================================
// Export
// ============================================================================

export default authSlice.reducer;
