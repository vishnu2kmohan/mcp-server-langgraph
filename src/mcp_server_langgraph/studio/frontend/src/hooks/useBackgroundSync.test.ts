/**
 * Background Sync Hook Tests
 *
 * TDD tests for the useBackgroundSync hook that manages
 * offline request queuing and background sync.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useBackgroundSync, InMemoryQueueStorage } from "./useBackgroundSync";

// Mock fetch for testing request replay
const mockFetch = vi.fn();

describe("useBackgroundSync", () => {
  const originalServiceWorker = navigator.serviceWorker;
  let mockStorage: InMemoryQueueStorage;

  beforeEach(() => {
    vi.clearAllMocks();

    // Create fresh in-memory storage for each test
    mockStorage = new InMemoryQueueStorage();

    // Stub fetch globally
    vi.stubGlobal("fetch", mockFetch);
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({}) });

    // Mock navigator.serviceWorker
    Object.defineProperty(navigator, "serviceWorker", {
      value: {
        ready: Promise.resolve({
          sync: {
            register: vi.fn().mockResolvedValue(undefined),
            getTags: vi.fn().mockResolvedValue([]),
          },
        }),
        controller: { postMessage: vi.fn() },
      },
      configurable: true,
      writable: true,
    });

    // Ensure navigator.onLine is true by default
    Object.defineProperty(navigator, "onLine", {
      value: true,
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, "serviceWorker", {
      value: originalServiceWorker,
      configurable: true,
      writable: true,
    });

    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  describe("Initial State", () => {
    it("should return initial state with empty queue", async () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.pendingCount).toBe(0);
      expect(result.current.isSyncing).toBe(false);
    });

    it("should detect if background sync is supported", async () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.isSupported).toBe(true);
    });

    it("should expose queueRequest function", () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      expect(typeof result.current.queueRequest).toBe("function");
    });

    it("should expose syncNow function", () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      expect(typeof result.current.syncNow).toBe("function");
    });

    it("should expose clearQueue function", () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      expect(typeof result.current.clearQueue).toBe("function");
    });
  });

  describe("Queue Management", () => {
    it("should queue a request when offline", async () => {
      // Set offline
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/chat/messages",
          method: "POST",
          body: JSON.stringify({ message: "Hello" }),
        });
      });

      expect(result.current.pendingCount).toBe(1);
    });

    it("should execute request immediately when online", async () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/chat/messages",
          method: "POST",
          body: JSON.stringify({ message: "Hello" }),
        });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/chat/messages",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });

    it("should queue multiple requests when offline", async () => {
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/chat/messages",
          method: "POST",
          body: JSON.stringify({ message: "First" }),
        });
        await result.current.queueRequest({
          url: "/api/v1/chat/messages",
          method: "POST",
          body: JSON.stringify({ message: "Second" }),
        });
      });

      expect(result.current.pendingCount).toBe(2);
    });

    it("should clear the queue", async () => {
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/chat/messages",
          method: "POST",
          body: JSON.stringify({ message: "Test" }),
        });
      });

      expect(result.current.pendingCount).toBe(1);

      await act(async () => {
        await result.current.clearQueue();
      });

      expect(result.current.pendingCount).toBe(0);
    });
  });

  describe("Sync Operations", () => {
    it("should sync pending requests when syncNow is called", async () => {
      // Start offline to queue requests
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/chat/messages",
          method: "POST",
          body: JSON.stringify({ message: "Queued" }),
        });
      });

      expect(result.current.pendingCount).toBe(1);

      // Go online and sync
      Object.defineProperty(navigator, "onLine", {
        value: true,
        configurable: true,
        writable: true,
      });

      await act(async () => {
        await result.current.syncNow();
      });

      expect(mockFetch).toHaveBeenCalled();
      expect(result.current.pendingCount).toBe(0);
    });

    it("should set isSyncing during sync operation", async () => {
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/test",
          method: "POST",
          body: "{}",
        });
      });

      Object.defineProperty(navigator, "onLine", {
        value: true,
        configurable: true,
        writable: true,
      });

      // After sync completes, isSyncing should be false
      await act(async () => {
        await result.current.syncNow();
      });

      expect(result.current.isSyncing).toBe(false);
    });

    it("should handle sync failure gracefully", async () => {
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/failing",
          method: "POST",
          body: "{}",
        });
      });

      // Mock fetch to fail
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      Object.defineProperty(navigator, "onLine", {
        value: true,
        configurable: true,
        writable: true,
      });

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      await act(async () => {
        await result.current.syncNow();
      });

      // Request should remain in queue on failure
      expect(result.current.pendingCount).toBe(1);
      expect(result.current.lastError).toBeDefined();

      consoleSpy.mockRestore();
    });
  });

  describe("Online/Offline Events", () => {
    it("should track online status", async () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.isOnline).toBe(true);
    });

    it("should update when going offline", async () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      // Simulate going offline
      act(() => {
        Object.defineProperty(navigator, "onLine", {
          value: false,
          configurable: true,
          writable: true,
        });
        window.dispatchEvent(new Event("offline"));
      });

      await waitFor(() => {
        expect(result.current.isOnline).toBe(false);
      });
    });

    it("should auto-sync when coming back online", async () => {
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ autoSync: true, storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/test",
          method: "POST",
          body: "{}",
        });
      });

      expect(result.current.pendingCount).toBe(1);

      // Go back online
      act(() => {
        Object.defineProperty(navigator, "onLine", {
          value: true,
          configurable: true,
          writable: true,
        });
        window.dispatchEvent(new Event("online"));
      });

      await waitFor(() => {
        expect(result.current.pendingCount).toBe(0);
      });

      expect(mockFetch).toHaveBeenCalled();
    });
  });

  describe("Request Options", () => {
    it("should preserve request headers", async () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/chat/messages",
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer token123",
          },
          body: JSON.stringify({ message: "Test" }),
        });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/chat/messages",
        expect.objectContaining({
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            Authorization: "Bearer token123",
          }),
        }),
      );
    });

    it("should support different HTTP methods", async () => {
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/resource/123",
          method: "DELETE",
        });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/resource/123",
        expect.objectContaining({
          method: "DELETE",
        }),
      );
    });

    it("should queue with metadata for tracking", async () => {
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
        writable: true,
      });

      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      const timestamp = Date.now();

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/test",
          method: "POST",
          body: "{}",
          metadata: {
            timestamp,
            retryCount: 0,
            type: "chat-message",
          },
        });
      });

      const queue = result.current.getQueue();
      expect(queue[0].metadata).toEqual({
        timestamp,
        retryCount: 0,
        type: "chat-message",
      });
    });
  });

  describe("Not Supported Environment", () => {
    it("should report not supported when serviceWorker is missing", async () => {
      // Remove serviceWorker
      Object.defineProperty(navigator, "serviceWorker", {
        value: undefined,
        configurable: true,
        writable: true,
      });

      // Don't provide storage to test truly unsupported environment
      const { result } = renderHook(() => useBackgroundSync());

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.isSupported).toBe(false);
    });

    it("should fallback to immediate execution when not supported", async () => {
      Object.defineProperty(navigator, "serviceWorker", {
        value: undefined,
        configurable: true,
        writable: true,
      });

      // Provide storage so hook can still work
      const { result } = renderHook(() =>
        useBackgroundSync({ storage: mockStorage }),
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/test",
          method: "POST",
          body: "{}",
        });
      });

      // Should still try to execute immediately
      expect(mockFetch).toHaveBeenCalled();
    });
  });
});
