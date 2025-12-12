/**
 * useAuth Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from './useAuth';

// Mock the playground API
const mockLogin = vi.fn();
const mockLogout = vi.fn();
const mockRefreshToken = vi.fn();
const mockGetCurrentUser = vi.fn();
const mockSetAuthToken = vi.fn();

vi.mock('../api/playground', () => ({
  getPlaygroundAPI: () => ({
    login: mockLogin,
    logout: mockLogout,
    refreshToken: mockRefreshToken,
    getCurrentUser: mockGetCurrentUser,
    setAuthToken: mockSetAuthToken,
  }),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(global, 'localStorage', { value: localStorageMock });

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  it('should_start_with_no_user', () => {
    const { result } = renderHook(() => useAuth({ autoLogin: false }));

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.isLoading).toBe(false);
  });

  it('should_login_successfully', async () => {
    const mockUser = { id: '1', username: 'testuser', roles: ['user'] };
    const mockTokens = {
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      expiresAt: Date.now() + 3600000,
    };

    mockLogin.mockResolvedValueOnce({ user: mockUser, tokens: mockTokens });

    const { result } = renderHook(() => useAuth({ autoLogin: false }));

    await act(async () => {
      await result.current.login({ username: 'testuser', password: 'password' });
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
    expect(mockSetAuthToken).toHaveBeenCalledWith('access-token');
  });

  it('should_handle_login_error', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));

    const { result } = renderHook(() => useAuth({ autoLogin: false }));

    await act(async () => {
      try {
        await result.current.login({ username: 'test', password: 'wrong' });
      } catch {
        // Expected to throw
      }
    });

    await waitFor(() => {
      expect(result.current.error).toBe('Invalid credentials');
    });
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should_logout_successfully', async () => {
    const mockUser = { id: '1', username: 'testuser', roles: ['user'] };
    const mockTokens = {
      accessToken: 'access-token',
      refreshToken: 'refresh-token',
      expiresAt: Date.now() + 3600000,
    };

    mockLogin.mockResolvedValueOnce({ user: mockUser, tokens: mockTokens });
    mockLogout.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useAuth({ autoLogin: false }));

    await act(async () => {
      await result.current.login({ username: 'testuser', password: 'password' });
    });

    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should_clear_error', async () => {
    mockLogin.mockRejectedValueOnce(new Error('Invalid credentials'));

    const { result } = renderHook(() => useAuth({ autoLogin: false }));

    await act(async () => {
      try {
        await result.current.login({ username: 'test', password: 'wrong' });
      } catch {
        // Expected to throw
      }
    });

    await waitFor(() => {
      expect(result.current.error).toBe('Invalid credentials');
    });

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });

  it('should_set_api_auth_token_after_login', async () => {
    const mockUser = { id: '1', username: 'testuser', roles: ['user'] };
    const mockTokens = {
      accessToken: 'new-access-token',
      refreshToken: 'new-refresh-token',
      expiresAt: Date.now() + 3600000,
    };

    mockLogin.mockResolvedValueOnce({ user: mockUser, tokens: mockTokens });

    const { result } = renderHook(() => useAuth({ autoLogin: false }));

    await act(async () => {
      await result.current.login({ username: 'testuser', password: 'password' });
    });

    // Verify API token is set after login
    expect(mockSetAuthToken).toHaveBeenCalledWith('new-access-token');
  });
});
