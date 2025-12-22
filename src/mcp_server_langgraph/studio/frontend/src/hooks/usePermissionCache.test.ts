/**
 * usePermissionCache Tests
 *
 * TDD tests for the permission caching hook.
 * Implements the PERMISSION_CACHE pattern from the plan:
 * - Cache permissions for 5 minutes (maxAge)
 * - Invalidate on 401/403 errors
 * - Store in memory (not localStorage)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import {
  usePermissionCache,
  PermissionCacheProvider,
  PERMISSION_CACHE_CONFIG,
} from "./usePermissionCache.tsx";
import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona: "developer" as const,
        username: "alice",
        email: "alice@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        user: {
          id: "user-1",
          username: "alice",
          email: "alice@example.com",
          roles: ["developer"],
          persona: "developer" as const,
        },
        tokens: {
          accessToken: "mock-token",
          refreshToken: "mock-refresh",
          expiresAt: Date.now() + 3600000,
          refreshExpiresAt: Date.now() + 86400000,
        },
        currentOrg: null,
        organizations: [],
        isInitializing: false,
        isLoading: false,
        error: null,
      },
    },
  });

const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      Provider,
      { store },
      React.createElement(PermissionCacheProvider, null, children),
    );
  };
};

// =============================================================================
// Tests
// =============================================================================

describe("usePermissionCache", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Configuration", () => {
    it("should have correct cache configuration", () => {
      expect(PERMISSION_CACHE_CONFIG.maxAge).toBe(5 * 60 * 1000); // 5 minutes
      expect(PERMISSION_CACHE_CONFIG.invalidateOn).toEqual([401, 403]);
      expect(PERMISSION_CACHE_CONFIG.storage).toBe("memory");
    });
  });

  describe("Cache Behavior", () => {
    it("should return cached permissions without refetching", async () => {
      const store = createTestStore();
      const fetchPermissions = vi.fn().mockResolvedValue(["read", "write"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Initial fetch
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(1);

      // Second check should use cache
      await act(async () => {
        await result.current.checkPermission("write");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(1); // Still 1, used cache
    });

    it("should refetch after cache expires", async () => {
      const store = createTestStore();
      const fetchPermissions = vi.fn().mockResolvedValue(["read", "write"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Initial fetch
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(1);

      // Advance time past cache expiration (5 minutes + 1ms)
      await act(async () => {
        vi.advanceTimersByTime(PERMISSION_CACHE_CONFIG.maxAge + 1);
      });

      // Should refetch after expiration
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(2);
    });

    it("should store permissions in memory, not localStorage", async () => {
      const store = createTestStore();
      const fetchPermissions = vi.fn().mockResolvedValue(["read"]);

      const { result } = renderHook(() => usePermissionCache({ fetchPermissions }), {
        wrapper: createWrapper(store),
      });

      // Wait for any initial effects to complete
      await act(async () => {
        await result.current.checkPermission("read");
      });

      // Check localStorage is not used for permissions
      expect(localStorage.getItem("permissions")).toBeNull();
      expect(localStorage.getItem("permission_cache")).toBeNull();
    });
  });

  describe("Permission Checking", () => {
    it("should return true for granted permission", async () => {
      const store = createTestStore();
      const fetchPermissions = vi.fn().mockResolvedValue(["read", "write"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      let hasPermission: boolean = false;
      await act(async () => {
        hasPermission = await result.current.checkPermission("read");
      });

      expect(hasPermission).toBe(true);
    });

    it("should return false for denied permission", async () => {
      const store = createTestStore();
      const fetchPermissions = vi.fn().mockResolvedValue(["read"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      let hasPermission: boolean = true;
      await act(async () => {
        hasPermission = await result.current.checkPermission("delete");
      });

      expect(hasPermission).toBe(false);
    });

    it("should check multiple permissions at once", async () => {
      const store = createTestStore();
      const fetchPermissions = vi
        .fn()
        .mockResolvedValue(["read", "write", "update"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      let results: boolean[] = [];
      await act(async () => {
        results = await result.current.checkPermissions([
          "read",
          "write",
          "delete",
        ]);
      });

      expect(results).toEqual([true, true, false]);
    });

    it("should return true for all permissions for admin", async () => {
      const adminStore = configureStore({
        reducer: {
          persona: personaReducer,
          auth: authReducer,
        },
        preloadedState: {
          persona: {
            persona: "admin" as const,
            username: "admin",
            email: "admin@example.com",
            permissions: [],
            isPersonaLoading: false,
          },
          auth: {
            user: {
              id: "admin-1",
              username: "admin",
              email: "admin@example.com",
              roles: ["admin"],
              persona: "admin" as const,
            },
            tokens: {
              accessToken: "mock-token",
              refreshToken: "mock-refresh",
              expiresAt: Date.now() + 3600000,
              refreshExpiresAt: Date.now() + 86400000,
            },
            currentOrg: null,
            organizations: [],
            isInitializing: false,
            isLoading: false,
            error: null,
          },
        },
      });

      const fetchPermissions = vi.fn().mockResolvedValue([]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(adminStore) },
      );

      let hasPermission: boolean = false;
      await act(async () => {
        hasPermission = await result.current.checkPermission("anything");
      });

      // Admin bypasses permission checks
      expect(hasPermission).toBe(true);
      // Shouldn't even fetch for admin
      expect(fetchPermissions).not.toHaveBeenCalled();
    });
  });

  describe("Cache Invalidation", () => {
    it("should invalidate cache on 401 error", async () => {
      const store = createTestStore();
      const fetchPermissions = vi
        .fn()
        .mockResolvedValueOnce(["read"])
        .mockResolvedValueOnce(["read", "write"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Initial fetch
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(1);

      // Simulate 401 error
      await act(async () => {
        result.current.invalidateOnError(401);
      });

      // Should refetch after invalidation
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(2);
    });

    it("should invalidate cache on 403 error", async () => {
      const store = createTestStore();
      const fetchPermissions = vi
        .fn()
        .mockResolvedValueOnce(["read"])
        .mockResolvedValueOnce(["read", "write"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Initial fetch
      await act(async () => {
        await result.current.checkPermission("read");
      });

      // Simulate 403 error
      await act(async () => {
        result.current.invalidateOnError(403);
      });

      // Should refetch after invalidation
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(2);
    });

    it("should not invalidate on other errors", async () => {
      const store = createTestStore();
      const fetchPermissions = vi.fn().mockResolvedValue(["read"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Initial fetch
      await act(async () => {
        await result.current.checkPermission("read");
      });

      // Simulate 500 error (should not invalidate)
      await act(async () => {
        result.current.invalidateOnError(500);
      });

      // Should still use cache
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(1);
    });

    it("should provide manual invalidation method", async () => {
      const store = createTestStore();
      const fetchPermissions = vi
        .fn()
        .mockResolvedValueOnce(["read"])
        .mockResolvedValueOnce(["read", "write"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Initial fetch
      await act(async () => {
        await result.current.checkPermission("read");
      });

      // Manual invalidation
      await act(async () => {
        result.current.invalidateCache();
      });

      // Should refetch after invalidation
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(2);
    });
  });

  describe("Loading State", () => {
    it("should track loading state during fetch", async () => {
      // Use real timers for this test since it involves async Promise resolution
      vi.useRealTimers();

      const store = createTestStore();
      let resolvePermissions: (value: string[]) => void;
      const fetchPermissions = vi.fn().mockImplementation(
        () =>
          new Promise<string[]>((resolve) => {
            resolvePermissions = resolve;
          }),
      );

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Start fetch (don't await) - wrap in act to handle state updates
      let checkPromise: Promise<boolean>;
      await act(async () => {
        checkPromise = result.current.checkPermission("read");
        // Give React a moment to update state
        await new Promise((r) => setTimeout(r, 10));
      });

      // Should be loading
      expect(result.current.isLoading).toBe(true);

      // Resolve fetch and wait for state update
      await act(async () => {
        resolvePermissions!(["read"]);
        await checkPromise!;
        // Give React a moment to update state
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.isLoading).toBe(false);

      // Restore fake timers for other tests
      vi.useFakeTimers();
    });
  });

  describe("Error Handling", () => {
    it("should handle fetch errors gracefully", async () => {
      const store = createTestStore();
      const fetchPermissions = vi
        .fn()
        .mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      let hasPermission: boolean = true;
      await act(async () => {
        hasPermission = await result.current.checkPermission("read");
      });

      // Should deny by default on error
      expect(hasPermission).toBe(false);
      expect(result.current.error).toBe("Network error");
    });

    it("should retry on error after cache invalidation", async () => {
      const store = createTestStore();
      const fetchPermissions = vi
        .fn()
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce(["read"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // First attempt fails
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(result.current.error).toBe("Network error");

      // Invalidate and retry
      await act(async () => {
        result.current.invalidateCache();
      });

      let hasPermission: boolean = false;
      await act(async () => {
        hasPermission = await result.current.checkPermission("read");
      });

      expect(hasPermission).toBe(true);
      expect(result.current.error).toBeNull();
    });
  });

  describe("Token Refresh Integration", () => {
    it("should invalidate cache when tokens are refreshed", async () => {
      const store = createTestStore();
      const fetchPermissions = vi
        .fn()
        .mockResolvedValueOnce(["read"])
        .mockResolvedValueOnce(["read", "write"]);

      const { result } = renderHook(
        () => usePermissionCache({ fetchPermissions }),
        { wrapper: createWrapper(store) },
      );

      // Initial fetch
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(1);

      // Simulate token refresh by calling onTokenRefresh
      await act(async () => {
        result.current.onTokenRefresh();
      });

      // Should refetch after token refresh
      await act(async () => {
        await result.current.checkPermission("read");
      });

      expect(fetchPermissions).toHaveBeenCalledTimes(2);
    });
  });
});
