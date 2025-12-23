/**
 * usePersonaCacheInvalidation Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Invalidates AI cache when persona changes.
 *
 * Features:
 * - Clears frontend AI cache on persona change
 * - Calls backend cache invalidation endpoint
 * - Tracks invalidation state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

// Mock the cache utilities
vi.mock("./useAICache", () => ({
  clearAllAICache: vi.fn(),
  clearAICacheByPrefix: vi.fn(),
  getAICacheStats: vi.fn(() => ({ size: 0, entries: [] })),
}));

// Mock the API
vi.mock("../api", () => ({
  useInvalidateUserCacheMutation: vi.fn(() => [
    vi.fn().mockResolvedValue({ data: { invalidated_count: 5 } }),
    { isLoading: false, isError: false },
  ]),
}));

import { usePersonaCacheInvalidation } from "./usePersonaCacheInvalidation";
import { clearAllAICache } from "./useAICache";
import personaReducer, {
  setUserInfo,
  setSubPersona,
} from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// =============================================================================
// Test Utilities
// =============================================================================

function createTestStore(initialPersona = "user") {
  return configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona: initialPersona,
        subPersona: null,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        isAuthenticated: true,
        accessToken: "test-token",
        refreshToken: null,
        expiresAt: null,
        user: {
          id: "user-123",
          username: "testuser",
          email: "test@example.com",
          roles: [],
        },
        isLoading: false,
        error: null,
      },
    },
  });
}

function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

// =============================================================================
// Tests
// =============================================================================

describe("usePersonaCacheInvalidation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  describe("basic functionality", () => {
    it("should return hook state", () => {
      const store = createTestStore();
      const { result } = renderHook(() => usePersonaCacheInvalidation(), {
        wrapper: createWrapper(store),
      });

      expect(result.current).toHaveProperty("isInvalidating");
      expect(result.current).toHaveProperty("lastInvalidatedAt");
      expect(result.current).toHaveProperty("invalidateNow");
    });

    it("should not invalidate on initial mount", () => {
      const store = createTestStore();
      renderHook(() => usePersonaCacheInvalidation(), {
        wrapper: createWrapper(store),
      });

      // Should not clear cache on mount
      expect(clearAllAICache).not.toHaveBeenCalled();
    });
  });

  describe("persona change detection", () => {
    it("should clear cache when persona changes", async () => {
      const store = createTestStore("user");
      renderHook(() => usePersonaCacheInvalidation(), {
        wrapper: createWrapper(store),
      });

      // Change persona
      act(() => {
        store.dispatch(
          setUserInfo({
            username: "admin",
            email: "admin@example.com",
            roles: ["admin"],
            persona: "admin",
          }),
        );
      });

      await waitFor(() => {
        expect(clearAllAICache).toHaveBeenCalled();
      });
    });

    it("should not clear cache when persona stays the same", () => {
      const store = createTestStore("user");
      renderHook(() => usePersonaCacheInvalidation(), {
        wrapper: createWrapper(store),
      });

      // Update user info but keep same persona
      act(() => {
        store.dispatch(
          setUserInfo({
            username: "newname",
            email: "new@example.com",
            roles: [],
            persona: "user", // Same persona
          }),
        );
      });

      // Should not clear cache when persona doesn't change
      expect(clearAllAICache).not.toHaveBeenCalled();
    });
  });

  describe("manual invalidation", () => {
    it("should provide invalidateNow function", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => usePersonaCacheInvalidation(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.invalidateNow).toBe("function");

      // Call manual invalidation
      await act(async () => {
        await result.current.invalidateNow();
      });

      expect(clearAllAICache).toHaveBeenCalled();
    });

    it("should update lastInvalidatedAt after manual invalidation", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => usePersonaCacheInvalidation(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.lastInvalidatedAt).toBeNull();

      await act(async () => {
        await result.current.invalidateNow();
      });

      expect(result.current.lastInvalidatedAt).not.toBeNull();
    });
  });

  describe("subPersona changes", () => {
    it("should clear cache when subPersona changes", async () => {
      const store = createTestStore("admin");
      renderHook(() => usePersonaCacheInvalidation(), {
        wrapper: createWrapper(store),
      });

      // Change subPersona using the dedicated action
      act(() => {
        store.dispatch(setSubPersona("security-admin"));
      });

      await waitFor(() => {
        expect(clearAllAICache).toHaveBeenCalled();
      });
    });
  });

  describe("configuration options", () => {
    it("should respect enabled option", () => {
      const store = createTestStore("user");
      renderHook(() => usePersonaCacheInvalidation({ enabled: false }), {
        wrapper: createWrapper(store),
      });

      // Change persona
      act(() => {
        store.dispatch(
          setUserInfo({
            username: "admin",
            email: "admin@example.com",
            roles: ["admin"],
            persona: "admin",
          }),
        );
      });

      // Should not clear cache when disabled
      expect(clearAllAICache).not.toHaveBeenCalled();
    });
  });

  describe("backend cache invalidation", () => {
    it("should call backend API when invalidateBackend is true", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ deleted_count: 3 }),
      });
      global.fetch = mockFetch;

      const store = createTestStore();
      const { result } = renderHook(
        () => usePersonaCacheInvalidation({ invalidateBackend: true }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await result.current.invalidateNow();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/cache/prefix/"),
        expect.objectContaining({
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    it("should not call backend API when invalidateBackend is false", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ deleted_count: 0 }),
      });
      global.fetch = mockFetch;

      const store = createTestStore();
      const { result } = renderHook(
        () => usePersonaCacheInvalidation({ invalidateBackend: false }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await result.current.invalidateNow();
      });

      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should handle backend API errors gracefully", async () => {
      const consoleWarnSpy = vi
        .spyOn(console, "warn")
        .mockImplementation(() => {});
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      });
      global.fetch = mockFetch;

      const store = createTestStore();
      const { result } = renderHook(
        () => usePersonaCacheInvalidation({ invalidateBackend: true }),
        { wrapper: createWrapper(store) },
      );

      // Should not throw
      await act(async () => {
        await result.current.invalidateNow();
      });

      // Should log warning
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("Backend invalidation failed"),
        expect.any(Error),
      );

      // Should still update lastInvalidatedAt
      expect(result.current.lastInvalidatedAt).not.toBeNull();

      consoleWarnSpy.mockRestore();
    });
  });
});
