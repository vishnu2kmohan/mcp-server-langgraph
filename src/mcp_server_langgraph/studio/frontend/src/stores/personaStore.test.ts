/**
 * Persona Store Tests
 *
 * Tests for persona detection and management using Zustand.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { usePersonaStore } from './personaStore';

describe('personaStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    usePersonaStore.getState().reset();
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('should have default persona as user', () => {
      const { result } = renderHook(() => usePersonaStore());
      expect(result.current.persona).toBe('user');
    });

    it('should have isPersonaLoading as false initially', () => {
      const { result } = renderHook(() => usePersonaStore());
      expect(result.current.isPersonaLoading).toBe(false);
    });

    it('should have empty permissions array initially', () => {
      const { result } = renderHook(() => usePersonaStore());
      expect(result.current.permissions).toEqual([]);
    });
  });

  describe('Persona Detection', () => {
    it('should detect admin persona from roles', async () => {
      const { result } = renderHook(() => usePersonaStore());

      await act(async () => {
        await result.current.detectPersona(['admin', 'user']);
      });

      expect(result.current.persona).toBe('admin');
    });

    it('should detect developer persona from roles', async () => {
      const { result } = renderHook(() => usePersonaStore());

      await act(async () => {
        await result.current.detectPersona(['developer', 'user']);
      });

      expect(result.current.persona).toBe('developer');
    });

    it('should default to user persona when no special roles', async () => {
      const { result } = renderHook(() => usePersonaStore());

      await act(async () => {
        await result.current.detectPersona(['user']);
      });

      expect(result.current.persona).toBe('user');
    });

    it('should prioritize admin over developer', async () => {
      const { result } = renderHook(() => usePersonaStore());

      await act(async () => {
        await result.current.detectPersona(['developer', 'admin', 'user']);
      });

      expect(result.current.persona).toBe('admin');
    });

    it('should set isPersonaLoading during detection', async () => {
      const { result } = renderHook(() => usePersonaStore());

      // Start detection
      const promise = act(async () => {
        await result.current.detectPersona(['admin']);
      });

      // Should complete without errors
      await promise;
      expect(result.current.isPersonaLoading).toBe(false);
    });
  });

  describe('Persona Configuration', () => {
    it('should return admin default route for admin persona', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('admin');
      });

      expect(result.current.getDefaultRoute()).toBe('/admin/dashboard');
    });

    it('should return studio workflows route for developer persona', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('developer');
      });

      expect(result.current.getDefaultRoute()).toBe('/studio/workflows');
    });

    it('should return studio chat route for user persona', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('user');
      });

      expect(result.current.getDefaultRoute()).toBe('/studio/chat');
    });

    it('should return correct sidebar items for admin', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('admin');
      });

      const items = result.current.getSidebarItems();
      expect(items).toContain('dashboard');
      expect(items).toContain('users');
      expect(items).toContain('metrics');
      expect(items).toContain('audit');
      expect(items).toContain('orgs');
      expect(items).toContain('studio');
    });

    it('should return correct sidebar items for developer', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('developer');
      });

      const items = result.current.getSidebarItems();
      expect(items).toContain('workflows');
      expect(items).toContain('chat');
      expect(items).toContain('mcp');
      expect(items).toContain('observability');
      expect(items).toContain('sessions');
    });

    it('should return correct sidebar items for user', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('user');
      });

      const items = result.current.getSidebarItems();
      expect(items).toContain('chat');
      expect(items).toContain('sessions');
      expect(items).not.toContain('workflows');
    });
  });

  describe('Permission Checks', () => {
    it('should check if user has specific permission', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPermissions(['read:workflows', 'write:workflows']);
      });

      expect(result.current.hasPermission('read:workflows')).toBe(true);
      expect(result.current.hasPermission('delete:workflows')).toBe(false);
    });

    it('should return false for empty permissions', () => {
      const { result } = renderHook(() => usePersonaStore());

      expect(result.current.hasPermission('any:permission')).toBe(false);
    });

    it('should admin have all permissions', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('admin');
      });

      // Admin bypasses permission checks
      expect(result.current.hasPermission('any:permission')).toBe(true);
    });
  });

  describe('Route Access', () => {
    it('should allow admin to access admin routes', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('admin');
      });

      expect(result.current.canAccessRoute('/admin/dashboard')).toBe(true);
      expect(result.current.canAccessRoute('/admin/users')).toBe(true);
    });

    it('should not allow developer to access admin routes', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('developer');
      });

      expect(result.current.canAccessRoute('/admin/dashboard')).toBe(false);
      expect(result.current.canAccessRoute('/admin/users')).toBe(false);
    });

    it('should allow developer to access studio routes', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('developer');
      });

      expect(result.current.canAccessRoute('/studio/workflows')).toBe(true);
      expect(result.current.canAccessRoute('/studio/mcp')).toBe(true);
    });

    it('should allow user to access limited studio routes', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('user');
      });

      expect(result.current.canAccessRoute('/studio/chat')).toBe(true);
      expect(result.current.canAccessRoute('/studio/sessions')).toBe(true);
      expect(result.current.canAccessRoute('/studio/workflows')).toBe(false);
    });
  });

  describe('Reset', () => {
    it('should reset to initial state', () => {
      const { result } = renderHook(() => usePersonaStore());

      act(() => {
        result.current.setPersona('admin');
        result.current.setPermissions(['read:all']);
      });

      expect(result.current.persona).toBe('admin');

      act(() => {
        result.current.reset();
      });

      expect(result.current.persona).toBe('user');
      expect(result.current.permissions).toEqual([]);
    });
  });
});
