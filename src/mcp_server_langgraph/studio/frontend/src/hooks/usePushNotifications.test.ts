/**
 * Push Notifications Hook Tests
 *
 * TDD tests for the usePushNotifications hook that manages
 * Web Push notification subscriptions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { usePushNotifications } from "./usePushNotifications";

// Mock navigator.serviceWorker
const mockPushManager = {
  getSubscription: vi.fn(),
  subscribe: vi.fn(),
};

const mockRegistration = {
  pushManager: mockPushManager,
};

// Mock fetch for API calls - use vi.stubGlobal to properly override
const mockFetch = vi.fn();

describe("usePushNotifications", () => {
  const originalNavigator = navigator.serviceWorker;
  const originalNotification = window.Notification;
  const originalPushManager = window.PushManager;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock fetch globally before MSW can intercept
    vi.stubGlobal("fetch", mockFetch);

    // Mock PushManager class
    Object.defineProperty(window, "PushManager", {
      value: class MockPushManager {},
      configurable: true,
      writable: true,
    });

    // Mock navigator.serviceWorker
    Object.defineProperty(navigator, "serviceWorker", {
      value: {
        ready: Promise.resolve(mockRegistration),
        getRegistrations: vi.fn().mockResolvedValue([]),
      },
      configurable: true,
      writable: true,
    });

    // Mock Notification API
    Object.defineProperty(window, "Notification", {
      value: {
        permission: "default",
        requestPermission: vi.fn().mockResolvedValue("granted"),
      },
      configurable: true,
      writable: true,
    });

    // Reset mock implementations
    mockPushManager.getSubscription.mockResolvedValue(null);
    mockPushManager.subscribe.mockResolvedValue({
      endpoint: "https://push.example.com/123",
      unsubscribe: vi.fn().mockResolvedValue(true),
      toJSON: () => ({
        endpoint: "https://push.example.com/123",
        keys: {
          p256dh: "test-key-p256dh",
          auth: "test-key-auth",
        },
      }),
    });

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, "serviceWorker", {
      value: originalNavigator,
      configurable: true,
      writable: true,
    });

    Object.defineProperty(window, "Notification", {
      value: originalNotification,
      configurable: true,
      writable: true,
    });

    Object.defineProperty(window, "PushManager", {
      value: originalPushManager,
      configurable: true,
      writable: true,
    });

    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  describe("Initial State", () => {
    it("should return initial state with not subscribed", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isSubscribed).toBe(false);
      expect(result.current.subscription).toBeNull();
    });

    it("should expose subscribe function", async () => {
      const { result } = renderHook(() => usePushNotifications());

      // Wait for async initialization to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(typeof result.current.subscribe).toBe("function");
    });

    it("should expose unsubscribe function", async () => {
      const { result } = renderHook(() => usePushNotifications());

      // Wait for async initialization to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(typeof result.current.unsubscribe).toBe("function");
    });

    it("should check for existing subscription on mount", async () => {
      renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(mockPushManager.getSubscription).toHaveBeenCalled();
      });
    });
  });

  describe("Permission Check", () => {
    it("should return permission status", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.permission).toBe("default");
    });

    it("should detect if notifications are supported", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isSupported).toBe(true);
    });

    it("should return not supported when Notification API is missing", async () => {
      // Delete the Notification property entirely to simulate missing API
      const originalNotificationDesc = Object.getOwnPropertyDescriptor(
        window,
        "Notification",
      );
      delete (window as { Notification?: unknown }).Notification;

      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isSupported).toBe(false);

      // Restore
      if (originalNotificationDesc) {
        Object.defineProperty(window, "Notification", originalNotificationDesc);
      }
    });
  });

  describe("Subscribe Flow", () => {
    it("should request permission when subscribing", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(window.Notification.requestPermission).toHaveBeenCalled();
    });

    it("should subscribe to push manager with VAPID key", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(mockPushManager.subscribe).toHaveBeenCalledWith({
        userVisibleOnly: true,
        applicationServerKey: expect.any(Uint8Array),
      });
    });

    it("should send subscription to backend", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/notifications/push/subscribe",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
          body: expect.any(String),
        }),
      );
    });

    it("should update isSubscribed after successful subscription", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(result.current.isSubscribed).toBe(true);
      expect(result.current.subscription).not.toBeNull();
    });

    it("should handle permission denied", async () => {
      (
        window.Notification.requestPermission as ReturnType<typeof vi.fn>
      ).mockResolvedValue("denied");

      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(result.current.isSubscribed).toBe(false);
      expect(result.current.permission).toBe("denied");
    });

    it("should handle subscribe error gracefully", async () => {
      mockPushManager.subscribe.mockRejectedValue(
        new Error("Subscribe failed"),
      );

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(result.current.isSubscribed).toBe(false);
      expect(result.current.error).toBeDefined();

      consoleSpy.mockRestore();
    });

    it("should handle non-Error exception in subscribe", async () => {
      // Throw a non-Error value
      mockPushManager.subscribe.mockRejectedValue("string error");

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe("string error");

      consoleSpy.mockRestore();
    });

    it("should handle backend API failure on subscribe", async () => {
      // Mock API returning error
      mockFetch.mockResolvedValue({
        ok: false,
        status: 500,
      });

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const { result } = renderHook(() => usePushNotifications());

      await act(async () => {
        await result.current.subscribe();
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe(
        "Failed to register subscription with server",
      );

      consoleSpy.mockRestore();
    });

    it("should set error when not supported", async () => {
      // Remove PushManager to simulate unsupported
      const originalPushManagerDesc = Object.getOwnPropertyDescriptor(
        window,
        "PushManager",
      );
      delete (window as { PushManager?: unknown }).PushManager;

      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.subscribe();
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe(
        "Push notifications are not supported",
      );

      // Restore
      if (originalPushManagerDesc) {
        Object.defineProperty(window, "PushManager", originalPushManagerDesc);
      }
    });
  });

  describe("Unsubscribe Flow", () => {
    it("should unsubscribe from push manager after subscribing", async () => {
      const { result } = renderHook(() => usePushNotifications());

      // Wait for initial loading
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // First subscribe
      await act(async () => {
        await result.current.subscribe();
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });

      // Then unsubscribe (mock already has unsubscribe method)
      await act(async () => {
        await result.current.unsubscribe();
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(false);
      });
    });

    it("should send unsubscribe request to backend", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // First subscribe
      await act(async () => {
        await result.current.subscribe();
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });

      mockFetch.mockClear();

      // Then unsubscribe
      await act(async () => {
        await result.current.unsubscribe();
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/notifications/push/unsubscribe",
        expect.objectContaining({
          method: "DELETE",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );
    });

    it("should update isSubscribed after unsubscribe", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // First subscribe
      await act(async () => {
        await result.current.subscribe();
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });

      // Then unsubscribe
      await act(async () => {
        await result.current.unsubscribe();
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(false);
      });

      expect(result.current.subscription).toBeNull();
    });

    it("should handle unsubscribe error with Error object", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // First subscribe
      await act(async () => {
        await result.current.subscribe();
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });

      // Make unsubscribe fail
      const mockSub = result.current.subscription as PushSubscription & {
        unsubscribe: ReturnType<typeof vi.fn>;
      };
      mockSub.unsubscribe = vi
        .fn()
        .mockRejectedValue(new Error("Unsubscribe failed"));

      await act(async () => {
        await result.current.unsubscribe();
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe("Unsubscribe failed");

      consoleSpy.mockRestore();
    });

    it("should handle unsubscribe error with non-Error exception", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // First subscribe
      await act(async () => {
        await result.current.subscribe();
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });

      // Make unsubscribe fail with non-Error
      const mockSub = result.current.subscription as PushSubscription & {
        unsubscribe: ReturnType<typeof vi.fn>;
      };
      mockSub.unsubscribe = vi.fn().mockRejectedValue("string unsubscribe error");

      await act(async () => {
        await result.current.unsubscribe();
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe("string unsubscribe error");

      consoleSpy.mockRestore();
    });

    it("should do nothing when unsubscribing without subscription", async () => {
      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.subscription).toBeNull();

      // Unsubscribe should be a no-op
      await act(async () => {
        await result.current.unsubscribe();
      });

      // No error should occur
      expect(result.current.error).toBeNull();
    });
  });

  describe("Existing Subscription Detection", () => {
    it("should detect existing subscription on mount", async () => {
      // Set up the mock BEFORE rendering the hook
      const mockExistingSubscription = {
        endpoint: "https://push.example.com/existing",
        toJSON: () => ({ endpoint: "https://push.example.com/existing" }),
      };
      mockPushManager.getSubscription.mockResolvedValue(
        mockExistingSubscription,
      );

      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await waitFor(() => {
        expect(result.current.isSubscribed).toBe(true);
      });

      expect(result.current.subscription).not.toBeNull();
    });

    it("should handle error when checking subscription on mount", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      // Make getSubscription reject with an Error
      mockPushManager.getSubscription.mockRejectedValue(
        new Error("Failed to get subscription"),
      );

      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe("Failed to get subscription");

      consoleSpy.mockRestore();
    });

    it("should handle non-Error exception in checkSubscription", async () => {
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      // Make getSubscription reject with a non-Error value
      mockPushManager.getSubscription.mockRejectedValue("string error on mount");

      const { result } = renderHook(() => usePushNotifications());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBeDefined();
      expect(result.current.error?.message).toBe("string error on mount");

      consoleSpy.mockRestore();
    });
  });
});
