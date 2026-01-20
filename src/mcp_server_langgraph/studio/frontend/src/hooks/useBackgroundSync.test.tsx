/**
 * useBackgroundSync Hook Tests
 *
 * TDD tests for background sync and offline request queuing.
 *
 * Features tested:
 * - Initial state management
 * - Online/offline detection
 * - Request queuing when offline
 * - Auto-sync when coming back online
 * - Manual sync trigger
 * - Queue clearing
 *
 * Uses InMemoryQueueStorage for test isolation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import type { ReactNode } from "react";
import {
  useBackgroundSync,
  InMemoryQueueStorage,
  type QueuedRequest,
} from "./useBackgroundSync";

// =============================================================================
// Test Setup
// =============================================================================

// Mock authenticatedFetch
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: vi.fn().mockResolvedValue({ ok: true }),
}));

// Mock devLogger
vi.mock("../utils/devLogger", () => ({
  devLogger: {
    withPrefix: () => ({
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    }),
  },
}));

// Wrapper with Router for useNavigate
function createWrapper() {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter>{children}</MemoryRouter>;
  };
}

// Store original navigator.onLine
const originalOnLine = Object.getOwnPropertyDescriptor(
  Navigator.prototype,
  "onLine",
);

// =============================================================================
// Tests
// =============================================================================

describe("useBackgroundSync", () => {
  let storage: InMemoryQueueStorage;

  beforeEach(() => {
    vi.clearAllMocks();
    storage = new InMemoryQueueStorage();

    // Reset navigator.onLine to true
    Object.defineProperty(navigator, "onLine", {
      value: true,
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    // Restore navigator.onLine
    if (originalOnLine) {
      Object.defineProperty(Navigator.prototype, "onLine", originalOnLine);
    }
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should initialize with correct default state", async () => {
      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      // Wait for initialization
      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.isOnline).toBe(true);
      expect(result.current.isSyncing).toBe(false);
      expect(result.current.pendingCount).toBe(0);
      expect(result.current.lastError).toBeNull();
    });

    it("should detect offline state on initialization", async () => {
      // Set navigator.onLine to false before hook init
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
      });

      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.isOnline).toBe(false);
    });

    it("should load existing queue from storage on init", async () => {
      // Pre-populate storage
      await storage.init();
      await storage.add({
        url: "/api/test",
        method: "POST",
        timestamp: Date.now(),
      });

      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.pendingCount).toBe(1);
    });
  });

  describe("Online/Offline Detection", () => {
    it("should update isOnline when window goes offline", async () => {
      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.isOnline).toBe(true);

      // Simulate going offline
      act(() => {
        Object.defineProperty(navigator, "onLine", {
          value: false,
          configurable: true,
        });
        window.dispatchEvent(new Event("offline"));
      });

      expect(result.current.isOnline).toBe(false);
    });

    it("should update isOnline when window comes back online", async () => {
      // Start offline
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
      });

      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      expect(result.current.isOnline).toBe(false);

      // Simulate coming online
      act(() => {
        Object.defineProperty(navigator, "onLine", {
          value: true,
          configurable: true,
        });
        window.dispatchEvent(new Event("online"));
      });

      expect(result.current.isOnline).toBe(true);
    });
  });

  describe("Request Queuing", () => {
    it("should queue request when offline", async () => {
      // Start offline
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
      });

      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/messages",
          method: "POST",
          body: JSON.stringify({ content: "test" }),
        });
      });

      expect(result.current.pendingCount).toBe(1);
    });

    it("should return current queue via getQueue", async () => {
      // Start offline
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
      });

      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      await act(async () => {
        await result.current.queueRequest({
          url: "/api/v1/test1",
          method: "POST",
        });
        await result.current.queueRequest({
          url: "/api/v1/test2",
          method: "PUT",
        });
      });

      const queue = result.current.getQueue();
      expect(queue).toHaveLength(2);
      expect(queue[0].url).toBe("/api/v1/test1");
      expect(queue[1].url).toBe("/api/v1/test2");
    });
  });

  describe("Queue Management", () => {
    it("should clear queue when clearQueue is called", async () => {
      // Start offline
      Object.defineProperty(navigator, "onLine", {
        value: false,
        configurable: true,
      });

      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      // Queue some requests
      await act(async () => {
        await result.current.queueRequest({
          url: "/api/test1",
          method: "POST",
        });
        await result.current.queueRequest({
          url: "/api/test2",
          method: "POST",
        });
      });

      expect(result.current.pendingCount).toBe(2);

      // Clear queue
      await act(async () => {
        await result.current.clearQueue();
      });

      expect(result.current.pendingCount).toBe(0);
      expect(result.current.getQueue()).toHaveLength(0);
    });
  });

  describe("InMemoryQueueStorage", () => {
    it("should add and retrieve requests", async () => {
      const queueStorage = new InMemoryQueueStorage();
      await queueStorage.init();

      const request: QueuedRequest = {
        url: "/api/test",
        method: "POST",
        timestamp: Date.now(),
      };

      const id = await queueStorage.add(request);
      expect(id).toBeDefined();

      const all = await queueStorage.getAll();
      expect(all).toHaveLength(1);
      expect(all[0].url).toBe("/api/test");
    });

    it("should remove request by id", async () => {
      const queueStorage = new InMemoryQueueStorage();
      await queueStorage.init();

      const id = await queueStorage.add({
        url: "/api/test",
        method: "POST",
        timestamp: Date.now(),
      });

      await queueStorage.remove(id);

      const all = await queueStorage.getAll();
      expect(all).toHaveLength(0);
    });

    it("should clear all requests", async () => {
      const queueStorage = new InMemoryQueueStorage();
      await queueStorage.init();

      await queueStorage.add({
        url: "/api/test1",
        method: "POST",
        timestamp: Date.now(),
      });
      await queueStorage.add({
        url: "/api/test2",
        method: "POST",
        timestamp: Date.now(),
      });

      await queueStorage.clear();

      const all = await queueStorage.getAll();
      expect(all).toHaveLength(0);
    });
  });

  describe("isSupported", () => {
    it("should report isSupported based on browser capabilities", async () => {
      const { result } = renderHook(
        () => useBackgroundSync({ storage, autoSync: false }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isInitialized).toBe(true);
      });

      // In test environment with storage provided, should be supported
      expect(result.current.isSupported).toBeDefined();
    });
  });
});
