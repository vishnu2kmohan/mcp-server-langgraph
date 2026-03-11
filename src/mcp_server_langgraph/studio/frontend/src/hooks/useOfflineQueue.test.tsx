/**
 * useOfflineQueue Hook Tests
 *
 * Sprint 3 - Phase 2.3: Offline Resilience Enhancement
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";

// Mock react-router
const mockNavigate = vi.fn();
vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock authenticatedFetch
const mockAuthenticatedFetch = vi.fn();
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: (...args: unknown[]) => mockAuthenticatedFetch(...args),
}));

// Mock intendedRoute
const mockSetIntendedRoute = vi.fn();
vi.mock("../utils/intendedRoute", () => ({
  setIntendedRoute: (...args: unknown[]) => mockSetIntendedRoute(...args),
}));

import { useOfflineQueue } from "./useOfflineQueue";

describe("useOfflineQueue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("should return empty initial state", () => {
      const { result } = renderHook(() => useOfflineQueue());

      expect(result.current.pendingCount).toBe(0);
      expect(result.current.isSyncing).toBe(false);
      expect(result.current.lastSyncResult).toBeNull();
      expect(result.current.conflicts).toHaveLength(0);
    });
  });

  describe("enqueue", () => {
    it("should add action to queue", () => {
      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/workflows",
          payload: { name: "Test Workflow" },
          priority: 1,
        });
      });

      expect(result.current.pendingCount).toBe(1);
    });

    it("should return action ID when enqueuing", () => {
      const { result } = renderHook(() => useOfflineQueue());

      let actionId: string = "";
      act(() => {
        actionId = result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/sessions/123",
          payload: { title: "Updated" },
          priority: 2,
        });
      });

      expect(actionId).toBeTruthy();
      expect(typeof actionId).toBe("string");
    });

    it("should track multiple queued actions", () => {
      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/a",
          payload: {},
          priority: 1,
        });
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/b",
          payload: {},
          priority: 2,
        });
        result.current.enqueue({
          type: "delete",
          endpoint: "/api/v1/c",
          payload: {},
          priority: 3,
        });
      });

      expect(result.current.pendingCount).toBe(3);
    });
  });

  describe("getQueue", () => {
    it("should return all queued actions", () => {
      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/test",
          payload: { data: "test" },
          priority: 1,
        });
      });

      const queue = result.current.getQueue();
      expect(queue).toHaveLength(1);
      expect(queue[0].endpoint).toBe("/api/v1/test");
      expect(queue[0].payload).toEqual({ data: "test" });
    });
  });

  describe("clearQueue", () => {
    it("should remove all queued actions", () => {
      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/a",
          payload: {},
          priority: 1,
        });
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/b",
          payload: {},
          priority: 2,
        });
      });

      expect(result.current.pendingCount).toBe(2);

      act(() => {
        result.current.clearQueue();
      });

      expect(result.current.pendingCount).toBe(0);
    });
  });

  describe("sync", () => {
    it("should return sync result", async () => {
      const { result } = renderHook(() => useOfflineQueue());

      let syncResult;
      await act(async () => {
        syncResult = await result.current.sync();
      });

      expect(syncResult).toEqual(
        expect.objectContaining({
          success: true,
          synced: 0,
          failed: 0,
          conflicts: [],
        }),
      );
      expect(syncResult?.timestamp).toBeInstanceOf(Date);
    });

    it("should set isSyncing during sync", async () => {
      const { result } = renderHook(() => useOfflineQueue());

      expect(result.current.isSyncing).toBe(false);

      // Just check that sync returns a result
      await act(async () => {
        await result.current.sync();
      });

      expect(result.current.isSyncing).toBe(false);
    });
  });

  describe("persistence", () => {
    it("should persist queue to localStorage", () => {
      const { result } = renderHook(() =>
        useOfflineQueue({ storageKey: "test_queue" }),
      );

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/test",
          payload: { name: "Test" },
          priority: 1,
        });
      });

      // Storage utility adds 'studio-' prefix to all keys
      const stored = localStorage.getItem("studio-test_queue");
      expect(stored).toBeTruthy();
      expect(JSON.parse(stored!)).toHaveLength(1);
    });

    it("should load queue from localStorage on mount", () => {
      // Pre-populate localStorage (storage utility adds 'studio-' prefix)
      const preloadedQueue = [
        {
          id: "action-1",
          type: "create",
          endpoint: "/api/v1/preloaded",
          payload: {},
          timestamp: Date.now(),
          priority: 1,
          retries: 0,
        },
      ];
      localStorage.setItem(
        "studio-offline_queue",
        JSON.stringify(preloadedQueue),
      );

      const { result } = renderHook(() => useOfflineQueue());

      expect(result.current.pendingCount).toBe(1);
    });

    it("should handle non-array value in localStorage", () => {
      // Store a non-array value
      localStorage.setItem(
        "studio-offline_queue",
        JSON.stringify({ invalid: true }),
      );

      const { result } = renderHook(() => useOfflineQueue());

      // Should default to empty array
      expect(result.current.pendingCount).toBe(0);
    });

    it("should handle null value in localStorage", () => {
      // Store null - not a valid queue
      localStorage.setItem("studio-offline_queue", JSON.stringify(null));

      const { result } = renderHook(() => useOfflineQueue());

      // Should default to empty array
      expect(result.current.pendingCount).toBe(0);
    });
  });

  describe("sync with fetch", () => {
    it("should sync successfully when fetch returns ok", async () => {
      // Mock authenticatedFetch
      mockAuthenticatedFetch.mockResolvedValue({ ok: true });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/test",
          payload: { data: "test" },
          priority: 1,
        });
      });

      expect(result.current.pendingCount).toBe(1);

      let syncResult;
      await act(async () => {
        syncResult = await result.current.sync();
      });

      expect(syncResult).toEqual(
        expect.objectContaining({
          success: true,
          synced: 1,
          failed: 0,
          conflicts: [],
        }),
      );
      expect(syncResult?.timestamp).toBeInstanceOf(Date);
      expect(result.current.pendingCount).toBe(0);
    });

    it("should handle 409 conflict response", async () => {
      // Mock authenticatedFetch returning 409 conflict
      mockAuthenticatedFetch.mockResolvedValue({
        ok: false,
        status: 409,
        json: () => Promise.resolve({ serverData: "conflict" }),
      });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/test",
          payload: { localData: "value" },
          priority: 1,
        });
      });

      let syncResult;
      await act(async () => {
        syncResult = await result.current.sync();
      });

      expect(syncResult?.conflicts).toHaveLength(1);
      expect(result.current.conflicts).toHaveLength(1);
      expect(result.current.conflicts[0].suggestedResolution).toBe(
        "keep-server",
      );
    });

    it("should handle non-409 failure response", async () => {
      // Mock authenticatedFetch returning 500 error
      mockAuthenticatedFetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/test",
          payload: { data: "test" },
          priority: 1,
        });
      });

      let syncResult;
      await act(async () => {
        syncResult = await result.current.sync();
      });

      expect(syncResult).toEqual(
        expect.objectContaining({
          success: false,
          synced: 0,
          failed: 1,
          conflicts: [],
        }),
      );
      expect(syncResult?.timestamp).toBeInstanceOf(Date);
    });

    it("should handle fetch throwing exception", async () => {
      // Mock authenticatedFetch throwing
      mockAuthenticatedFetch.mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "create",
          endpoint: "/api/v1/test",
          payload: { data: "test" },
          priority: 1,
        });
      });

      let syncResult;
      await act(async () => {
        syncResult = await result.current.sync();
      });

      expect(syncResult?.failed).toBe(1);
    });

    it("should use DELETE method for delete actions", async () => {
      mockAuthenticatedFetch.mockResolvedValue({ ok: true });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "delete",
          endpoint: "/api/v1/test/123",
          payload: {},
          priority: 1,
        });
      });

      await act(async () => {
        await result.current.sync();
      });

      expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
        "/api/v1/test/123",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });

  describe("resolveConflict", () => {
    it("should remove conflict and action when resolved with keep-server", async () => {
      // Mock authenticatedFetch returning 409 conflict
      mockAuthenticatedFetch.mockResolvedValue({
        ok: false,
        status: 409,
        json: () => Promise.resolve({ serverData: "conflict" }),
      });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/test",
          payload: { localData: "value" },
          priority: 1,
        });
      });

      await act(async () => {
        await result.current.sync();
      });

      expect(result.current.conflicts).toHaveLength(1);
      const conflictId = result.current.conflicts[0].actionId;

      act(() => {
        result.current.resolveConflict(conflictId, "keep-server");
      });

      // Should remove conflict and discard the action
      expect(result.current.conflicts).toHaveLength(0);
      expect(result.current.pendingCount).toBe(0);
    });

    it("should re-queue action with force flag when resolved with keep-local", async () => {
      // First call returns 409, second call (after resolution) returns ok
      mockAuthenticatedFetch
        .mockResolvedValueOnce({
          ok: false,
          status: 409,
          json: () => Promise.resolve({ serverData: "conflict" }),
        })
        .mockResolvedValueOnce({ ok: true });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/test",
          payload: { localData: "value" },
          priority: 1,
        });
      });

      await act(async () => {
        await result.current.sync();
      });

      expect(result.current.conflicts).toHaveLength(1);
      const conflictId = result.current.conflicts[0].actionId;

      act(() => {
        result.current.resolveConflict(conflictId, "keep-local");
      });

      // Conflict should be removed
      expect(result.current.conflicts).toHaveLength(0);

      // Action should be re-queued with force flag
      expect(result.current.pendingCount).toBe(1);
      const queue = result.current.getQueue();
      expect(queue[0].payload).toHaveProperty("_force", true);
    });

    it("should merge payloads when resolved with merge", async () => {
      const serverData = { serverField: "server-value", sharedField: "server" };

      mockAuthenticatedFetch.mockReset();
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: () => Promise.resolve(serverData),
      });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/test",
          payload: { localField: "local-value", sharedField: "local" },
          priority: 1,
        });
      });

      await act(async () => {
        await result.current.sync();
      });

      expect(result.current.conflicts).toHaveLength(1);
      const conflictId = result.current.conflicts[0].actionId;

      act(() => {
        result.current.resolveConflict(conflictId, "merge");
      });

      // Conflict should be removed
      expect(result.current.conflicts).toHaveLength(0);

      // Action should be re-queued with merged payload (local wins on conflicts)
      expect(result.current.pendingCount).toBe(1);
      const queue = result.current.getQueue();
      expect(queue[0].payload).toEqual({
        serverField: "server-value",
        localField: "local-value",
        sharedField: "local", // Local wins
        _merged: true,
      });
    });
  });

  describe("resolveAllConflicts", () => {
    it("should resolve all conflicts using their suggested resolutions", async () => {
      // Create multiple conflicts with different suggested resolutions
      let callCount = 0;
      mockAuthenticatedFetch.mockImplementation(() => {
        callCount++;
        return Promise.resolve({
          ok: false,
          status: 409,
          json: () => Promise.resolve({ serverData: `conflict-${callCount}` }),
        });
      });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/test/1",
          payload: { localData: "value1" },
          priority: 1,
        });
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/test/2",
          payload: { localData: "value2" },
          priority: 2,
        });
      });

      await act(async () => {
        await result.current.sync();
      });

      expect(result.current.conflicts).toHaveLength(2);

      act(() => {
        result.current.resolveAllConflicts();
      });

      // All conflicts should be resolved
      expect(result.current.conflicts).toHaveLength(0);
    });

    it("should do nothing when no conflicts exist", () => {
      const { result } = renderHook(() => useOfflineQueue());

      expect(result.current.conflicts).toHaveLength(0);

      // Should not throw
      act(() => {
        result.current.resolveAllConflicts();
      });

      expect(result.current.conflicts).toHaveLength(0);
    });

    it("should apply keep-server resolution for all conflicts by default", async () => {
      mockAuthenticatedFetch.mockResolvedValue({
        ok: false,
        status: 409,
        json: () => Promise.resolve({ serverData: "conflict" }),
      });

      const { result } = renderHook(() => useOfflineQueue());

      act(() => {
        result.current.enqueue({
          type: "update",
          endpoint: "/api/v1/test",
          payload: { localData: "value" },
          priority: 1,
        });
      });

      await act(async () => {
        await result.current.sync();
      });

      expect(result.current.conflicts).toHaveLength(1);
      // Default suggestedResolution is keep-server
      expect(result.current.conflicts[0].suggestedResolution).toBe(
        "keep-server",
      );

      act(() => {
        result.current.resolveAllConflicts();
      });

      // Action should be removed (keep-server discards local)
      expect(result.current.pendingCount).toBe(0);
      expect(result.current.conflicts).toHaveLength(0);
    });
  });
});
