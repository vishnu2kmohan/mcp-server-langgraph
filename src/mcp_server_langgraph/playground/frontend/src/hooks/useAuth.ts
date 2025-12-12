/**
 * useAuth Hook
 *
 * Manages authentication state and operations for the playground.
 * Provides login, logout, and token refresh capabilities.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { getPlaygroundAPI } from '../api/playground';
import type { AuthUser, LoginRequest, AuthTokens } from '../api/types';

const TOKEN_STORAGE_KEY = 'playground_auth_tokens';
const TOKEN_REFRESH_BUFFER_MS = 5 * 60 * 1000; // Refresh 5 minutes before expiry

export interface UseAuthOptions {
  autoLogin?: boolean;
}

export interface UseAuthResult {
  // State
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (request: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

function getStoredTokens(): AuthTokens | null {
  try {
    const stored = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as AuthTokens;
    }
  } catch {
    // Invalid stored data
  }
  return null;
}

function storeTokens(tokens: AuthTokens | null): void {
  if (tokens) {
    localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export function useAuth(options: UseAuthOptions = {}): UseAuthResult {
  const { autoLogin = true } = options;

  const [user, setUser] = useState<AuthUser | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(getStoredTokens);
  const [isLoading, setIsLoading] = useState(autoLogin);
  const [error, setError] = useState<string | null>(null);

  const refreshTimeoutRef = useRef<number | null>(null);
  const api = getPlaygroundAPI();

  // Update API auth token when tokens change
  useEffect(() => {
    if (tokens?.accessToken) {
      api.setAuthToken(tokens.accessToken);
      storeTokens(tokens);
    } else {
      api.setAuthToken(null);
      storeTokens(null);
    }
  }, [tokens, api]);

  // Schedule token refresh before expiry
  const scheduleTokenRefresh = useCallback((expiresAt: number, refreshToken?: string) => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }

    if (!refreshToken) return;

    const now = Date.now();
    const refreshTime = expiresAt - TOKEN_REFRESH_BUFFER_MS;
    const delay = Math.max(0, refreshTime - now);

    if (delay > 0) {
      refreshTimeoutRef.current = window.setTimeout(async () => {
        try {
          const response = await api.refreshToken(refreshToken);
          setTokens(response.tokens);
          setUser(response.user);
          scheduleTokenRefresh(response.tokens.expiresAt, response.tokens.refreshToken);
        } catch {
          // Token refresh failed - user will need to re-login
          setTokens(null);
          setUser(null);
        }
      }, delay);
    }
  }, [api]);

  // Initialize auth state on mount
  useEffect(() => {
    if (!autoLogin) return;

    const initAuth = async () => {
      const storedTokens = getStoredTokens();
      if (!storedTokens) {
        setIsLoading(false);
        return;
      }

      // Check if token is expired
      if (storedTokens.expiresAt < Date.now()) {
        // Try to refresh if we have a refresh token
        if (storedTokens.refreshToken) {
          try {
            const response = await api.refreshToken(storedTokens.refreshToken);
            setTokens(response.tokens);
            setUser(response.user);
            scheduleTokenRefresh(response.tokens.expiresAt, response.tokens.refreshToken);
          } catch {
            // Refresh failed, clear tokens
            storeTokens(null);
          }
        } else {
          storeTokens(null);
        }
        setIsLoading(false);
        return;
      }

      // Token is valid, get current user
      try {
        api.setAuthToken(storedTokens.accessToken);
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
        setTokens(storedTokens);
        scheduleTokenRefresh(storedTokens.expiresAt, storedTokens.refreshToken);
      } catch {
        // Token is invalid, clear it
        storeTokens(null);
      }
      setIsLoading(false);
    };

    initAuth();

    // Cleanup refresh timeout on unmount
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [autoLogin, api, scheduleTokenRefresh]);

  const login = useCallback(
    async (request: LoginRequest): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await api.login(request);
        setTokens(response.tokens);
        setUser(response.user);
        scheduleTokenRefresh(response.tokens.expiresAt, response.tokens.refreshToken);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Login failed';
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [api, scheduleTokenRefresh]
  );

  const logout = useCallback(async (): Promise<void> => {
    try {
      await api.logout();
    } catch {
      // Ignore logout errors - we'll clear local state anyway
    } finally {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
      setTokens(null);
      setUser(null);
      setError(null);
    }
  }, [api]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    user,
    isAuthenticated: user !== null,
    isLoading,
    error,
    login,
    logout,
    clearError,
  };
}
