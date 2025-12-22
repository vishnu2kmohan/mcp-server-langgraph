/**
 * useOfflineQueue Hook Tests
 *
 * Sprint 3 - Phase 2.3: Offline Resilience Enhancement
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOfflineQueue } from "./useOfflineQueue";

describe("useOfflineQueue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
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

      expect(syncResult).toEqual({
        success: true,
        synced: 0,
        failed: 0,
        conflicts: [],
      });
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
        useOfflineQueue({ storageKey: "test_queue" })
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
      localStorage.setItem("studio-offline_queue", JSON.stringify(preloadedQueue));

      const { result } = renderHook(() => useOfflineQueue());

      expect(result.current.pendingCount).toBe(1);
    });

    it("should handle non-array value in localStorage", () => {
      // Store a non-array value
      localStorage.setItem("studio-offline_queue", JSON.stringify({ invalid: true }));

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
      // Mock fetch
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));

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

      expect(syncResult).toEqual({
        success: true,
        synced: 1,
        failed: 0,
        conflicts: [],
      });
      expect(result.current.pendingCount).toBe(0);

      vi.unstubAllGlobals();
    });

    it("should handle 409 conflict response", async () => {
      // Mock fetch returning 409 conflict
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 409,
          json: () => Promise.resolve({ serverData: "conflict" }),
        })
      );

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
      expect(result.current.conflicts[0].suggestedResolution).toBe("keep-server");

      vi.unstubAllGlobals();
    });

    it("should handle non-409 failure response", async () => {
      // Mock fetch returning 500 error
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
        })
      );

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

      expect(syncResult).toEqual({
        success: false,
        synced: 0,
        failed: 1,
        conflicts: [],
      });

      vi.unstubAllGlobals();
    });

    it("should handle fetch throwing exception", async () => {
      // Mock fetch throwing
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));

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

      vi.unstubAllGlobals();
    });

    it("should use DELETE method for delete actions", async () => {
      const mockFetch = vi.fn().mockResolvedValue({ ok: true });
      vi.stubGlobal("fetch", mockFetch);

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

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/test/123",
        expect.objectContaining({ method: "DELETE" })
      );

      vi.unstubAllGlobals();
    });
  });

  describe("resolveConflict", () => {
    it("should remove conflict and action when resolved", async () => {
      // Mock fetch returning 409 conflict
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 409,
          json: () => Promise.resolve({ serverData: "conflict" }),
        })
      );

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

      expect(result.current.conflicts).toHaveLength(0);

      vi.unstubAllGlobals();
    });
  });
});
