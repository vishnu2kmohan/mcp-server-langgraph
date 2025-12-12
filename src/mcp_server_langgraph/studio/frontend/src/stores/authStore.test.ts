/**
 * authStore Tests
 *
 * TDD tests for authentication store.
 * Tests cover:
 * - Initial state
 * - Login flow
 * - Logout flow
 * - Token refresh
 * - Persona detection
 * - Organization switching
 * - Error handling
 */

import { describe, it, expect, beforeEach, afterEach, vi, type Mock } from 'vitest';
import { createTestAuthStore, derivePersona } from './authStore';
import type { AuthStore } from '../types/auth';

// Mock fetch
const mockFetch = vi.fn() as Mock;

describe('authStore', () => {
  let store: ReturnType<typeof createTestAuthStore>;

  beforeEach(() => {
    // Create fresh store for each test
    store = createTestAuthStore();
    // Reset mock and stub globally
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('initial state', () => {
    it('should have null user when not authenticated', () => {
      expect(store.getState().user).toBeNull();
    });

    it('should have null tokens when not authenticated', () => {
      expect(store.getState().tokens).toBeNull();
    });

    it('should have no current organization when not authenticated', () => {
      expect(store.getState().currentOrg).toBeNull();
    });

    it('should have empty organizations array when not authenticated', () => {
      expect(store.getState().organizations).toEqual([]);
    });

    it('should not be initializing by default', () => {
      expect(store.getState().isInitializing).toBe(false);
    });

    it('should not be loading by default', () => {
      expect(store.getState().isLoading).toBe(false);
    });

    it('should have no error by default', () => {
      expect(store.getState().error).toBeNull();
    });
  });

  describe('derivePersona', () => {
    it('should return admin for admin role', () => {
      expect(derivePersona(['admin', 'user'])).toBe('admin');
    });

    it('should return developer for developer role', () => {
      expect(derivePersona(['developer'])).toBe('developer');
    });

    it('should return user for no special roles', () => {
      expect(derivePersona([])).toBe('user');
      expect(derivePersona(['viewer'])).toBe('user');
    });

    it('should prioritize admin over developer', () => {
      expect(derivePersona(['developer', 'admin'])).toBe('admin');
    });
  });

  describe('login', () => {
    it('should set isLoading to true during login', async () => {
      // Arrange - create a promise we control
      let resolveLogin!: () => void;
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) => {
            resolveLogin = () =>
              resolve({
                ok: true,
                json: () =>
                  Promise.resolve({
                    user: { id: '1', username: 'test', email: 'test@example.com', roles: [] },
                    tokens: {
                      accessToken: 'token',
                      refreshToken: 'refresh',
                      expiresAt: Date.now() + 3600000,
                      refreshExpiresAt: Date.now() + 86400000,
                    },
                  }),
              });
          })
      );

      // Act - start login without awaiting
      const loginPromise = store.getState().login('test', 'password');

      // Assert - should be loading immediately
      expect(store.getState().isLoading).toBe(true);

      // Cleanup
      resolveLogin();
      await loginPromise;
    });

    it('should set user and tokens on successful login', async () => {
      // Arrange
      const mockUser = {
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        roles: ['user'],
      };
      const mockTokens = {
        accessToken: 'access-token-123',
        refreshToken: 'refresh-token-123',
        expiresAt: Date.now() + 3600000,
        refreshExpiresAt: Date.now() + 86400000,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user: mockUser,
            tokens: mockTokens,
            organizations: [{ id: 'org-1', name: 'Test Org', role: 'member', tier: 'hybrid' }],
          }),
      });

      // Act
      await store.getState().login('testuser', 'password123');

      // Assert
      const state = store.getState();
      expect(state.user?.id).toBe('user-123');
      expect(state.user?.username).toBe('testuser');
      expect(state.user?.persona).toBe('user');
      expect(state.tokens?.accessToken).toBe('access-token-123');
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });

    it('should set error on failed login', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Invalid credentials' }),
      });

      // Act
      await store.getState().login('wrong', 'credentials');

      // Assert
      const state = store.getState();
      expect(state.user).toBeNull();
      expect(state.tokens).toBeNull();
      expect(state.error).toBe('Invalid credentials');
      expect(state.isLoading).toBe(false);
    });

    it('should derive admin persona from roles correctly', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user: {
              id: 'admin-1',
              username: 'admin',
              email: 'admin@example.com',
              roles: ['admin', 'user'],
            },
            tokens: {
              accessToken: 'token',
              refreshToken: 'refresh',
              expiresAt: Date.now() + 3600000,
              refreshExpiresAt: Date.now() + 86400000,
            },
          }),
      });

      // Act
      await store.getState().login('admin', 'password');

      // Assert
      expect(store.getState().user?.persona).toBe('admin');
    });

    it('should derive developer persona for developer role', async () => {
      // Arrange
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            user: {
              id: 'dev-1',
              username: 'dev',
              email: 'dev@example.com',
              roles: ['developer'],
            },
            tokens: {
              accessToken: 'token',
              refreshToken: 'refresh',
              expiresAt: Date.now() + 3600000,
              refreshExpiresAt: Date.now() + 86400000,
            },
          }),
      });

      // Act
      await store.getState().login('dev', 'password');

      // Assert
      expect(store.getState().user?.persona).toBe('developer');
    });
  });

  describe('logout', () => {
    it('should clear all auth state on logout', () => {
      // Arrange - set up authenticated state
      store.setState({
        user: {
          id: '1',
          username: 'test',
          email: 'test@example.com',
          roles: [],
          persona: 'user',
        },
        tokens: {
          accessToken: 'token',
          refreshToken: 'refresh',
          expiresAt: Date.now() + 3600000,
          refreshExpiresAt: Date.now() + 86400000,
        },
        currentOrg: { id: 'org-1', name: 'Org', role: 'member', tier: 'hybrid' },
        organizations: [{ id: 'org-1', name: 'Org', role: 'member', tier: 'hybrid' }],
      } as Partial<AuthStore>);

      // Act
      store.getState().logout();

      // Assert
      const state = store.getState();
      expect(state.user).toBeNull();
      expect(state.tokens).toBeNull();
      expect(state.currentOrg).toBeNull();
      expect(state.organizations).toEqual([]);
    });
  });

  describe('refreshToken', () => {
    it('should refresh tokens successfully', async () => {
      // Arrange
      store.setState({
        user: {
          id: '1',
          username: 'test',
          email: 'test@example.com',
          roles: [],
          persona: 'user',
        },
        tokens: {
          accessToken: 'old-access-token',
          refreshToken: 'refresh-token',
          expiresAt: Date.now() - 1000,
          refreshExpiresAt: Date.now() + 86400000,
        },
      } as Partial<AuthStore>);

      const newTokens = {
        accessToken: 'new-access-token',
        refreshToken: 'new-refresh-token',
        expiresAt: Date.now() + 3600000,
        refreshExpiresAt: Date.now() + 86400000,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ tokens: newTokens }),
      });

      // Act
      await store.getState().refreshToken();

      // Assert
      expect(store.getState().tokens?.accessToken).toBe('new-access-token');
    });

    it('should logout if refresh fails', async () => {
      // Arrange
      store.setState({
        user: {
          id: '1',
          username: 'test',
          email: 'test@example.com',
          roles: [],
          persona: 'user',
        },
        tokens: {
          accessToken: 'old-token',
          refreshToken: 'expired-refresh',
          expiresAt: Date.now() - 1000,
          refreshExpiresAt: Date.now() - 1000,
        },
      } as Partial<AuthStore>);

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: 'Refresh token expired' }),
      });

      // Act
      await store.getState().refreshToken();

      // Assert
      expect(store.getState().user).toBeNull();
      expect(store.getState().tokens).toBeNull();
    });

    it('should logout if no refresh token exists', async () => {
      // Arrange
      store.setState({
        user: {
          id: '1',
          username: 'test',
          email: 'test@example.com',
          roles: [],
          persona: 'user',
        },
        tokens: null,
      } as Partial<AuthStore>);

      // Act
      await store.getState().refreshToken();

      // Assert
      expect(store.getState().user).toBeNull();
    });
  });

  describe('switchOrganization', () => {
    it('should switch to a different organization', async () => {
      // Arrange
      const orgs = [
        { id: 'org-1', name: 'Org 1', role: 'admin' as const, tier: 'hybrid' as const },
        { id: 'org-2', name: 'Org 2', role: 'member' as const, tier: 'shared' as const },
      ];
      store.setState({
        user: {
          id: '1',
          username: 'test',
          email: 'test@example.com',
          roles: [],
          persona: 'user',
        },
        tokens: {
          accessToken: 'token',
          refreshToken: 'refresh',
          expiresAt: Date.now() + 3600000,
          refreshExpiresAt: Date.now() + 86400000,
        },
        currentOrg: orgs[0],
        organizations: orgs,
      } as Partial<AuthStore>);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      });

      // Act
      await store.getState().switchOrganization('org-2');

      // Assert
      expect(store.getState().currentOrg?.id).toBe('org-2');
      expect(store.getState().currentOrg?.name).toBe('Org 2');
    });

    it('should set error when switching to non-existent organization', async () => {
      // Arrange
      store.setState({
        user: {
          id: '1',
          username: 'test',
          email: 'test@example.com',
          roles: [],
          persona: 'user',
        },
        tokens: {
          accessToken: 'token',
          refreshToken: 'refresh',
          expiresAt: Date.now() + 3600000,
          refreshExpiresAt: Date.now() + 86400000,
        },
        currentOrg: { id: 'org-1', name: 'Org 1', role: 'admin', tier: 'hybrid' },
        organizations: [{ id: 'org-1', name: 'Org 1', role: 'admin', tier: 'hybrid' }],
      } as Partial<AuthStore>);

      // Act
      await store.getState().switchOrganization('non-existent');

      // Assert
      expect(store.getState().error).toBe('Organization not found');
    });
  });

  describe('getAccessToken', () => {
    it('should return access token if not expired', async () => {
      // Arrange
      store.setState({
        user: {
          id: '1',
          username: 'test',
          email: 'test@example.com',
          roles: [],
          persona: 'user',
        },
        tokens: {
          accessToken: 'valid-token',
          refreshToken: 'refresh',
          expiresAt: Date.now() + 3600000, // 1 hour from now
          refreshExpiresAt: Date.now() + 86400000,
        },
      } as Partial<AuthStore>);

      // Act
      const token = await store.getState().getAccessToken();

      // Assert
      expect(token).toBe('valid-token');
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('should return null if not authenticated', async () => {
      // Act
      const token = await store.getState().getAccessToken();

      // Assert
      expect(token).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      // Arrange
      store.setState({ error: 'Some error' } as Partial<AuthStore>);

      // Act
      store.getState().clearError();

      // Assert
      expect(store.getState().error).toBeNull();
    });
  });

  describe('initialize', () => {
    it('should set isInitializing to false when no tokens stored', async () => {
      // Act
      await store.getState().initialize();

      // Assert
      expect(store.getState().isInitializing).toBe(false);
    });
  });
});
