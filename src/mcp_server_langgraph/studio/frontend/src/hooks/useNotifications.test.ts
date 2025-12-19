/**
 * useNotifications Tests
 *
 * TDD tests for the Desktop Notifications hook.
 * Tests cover:
 * - Permission request
 * - Permission state tracking
 * - Notification sending
 * - Browser API integration
 * - Fallback behavior
 * - Preferences integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useNotifications } from "./useNotifications";

describe("useNotifications", () => {
  let originalNotification: typeof Notification;
  let mockNotification: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();

    // Store original Notification
    originalNotification = window.Notification;

    // Mock Notification constructor
    mockNotification = vi.fn().mockImplementation(() => ({
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));

    // Mock Notification static properties and methods
    Object.defineProperty(mockNotification, "permission", {
      value: "default",
      writable: true,
      configurable: true,
    });

    mockNotification.requestPermission = vi.fn().mockResolvedValue("granted");

    // Replace Notification
    Object.defineProperty(window, "Notification", {
      value: mockNotification,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "Notification", {
      value: originalNotification,
      writable: true,
      configurable: true,
    });
  });

  describe("permission state", () => {
    it("should return initial permission state", () => {
      const { result } = renderHook(() => useNotifications());
      expect(result.current.permission).toBe("default");
    });

    it("should detect granted permission", () => {
      Object.defineProperty(mockNotification, "permission", {
        value: "granted",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications());
      expect(result.current.permission).toBe("granted");
    });

    it("should detect denied permission", () => {
      Object.defineProperty(mockNotification, "permission", {
        value: "denied",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications());
      expect(result.current.permission).toBe("denied");
    });

    it("should check if notifications are supported", () => {
      const { result } = renderHook(() => useNotifications());
      expect(result.current.isSupported).toBe(true);
    });

    it("should detect when notifications are not supported", () => {
      Object.defineProperty(window, "Notification", {
        value: undefined,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications());
      expect(result.current.isSupported).toBe(false);
    });
  });

  describe("request permission", () => {
    it("should request permission", async () => {
      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        await result.current.requestPermission();
      });

      expect(mockNotification.requestPermission).toHaveBeenCalled();
    });

    it("should update permission after request is granted", async () => {
      mockNotification.requestPermission.mockResolvedValueOnce("granted");

      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        const granted = await result.current.requestPermission();
        expect(granted).toBe(true);
      });
    });

    it("should return false when permission is denied", async () => {
      mockNotification.requestPermission.mockResolvedValueOnce("denied");

      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        const granted = await result.current.requestPermission();
        expect(granted).toBe(false);
      });
    });

    it("should not request if already granted", async () => {
      Object.defineProperty(mockNotification, "permission", {
        value: "granted",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        await result.current.requestPermission();
      });

      expect(mockNotification.requestPermission).not.toHaveBeenCalled();
    });
  });

  describe("send notification", () => {
    beforeEach(() => {
      Object.defineProperty(mockNotification, "permission", {
        value: "granted",
        writable: true,
        configurable: true,
      });
    });

    it("should send a notification with title", async () => {
      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        result.current.notify("Test Title");
      });

      expect(mockNotification).toHaveBeenCalledWith(
        "Test Title",
        expect.any(Object),
      );
    });

    it("should send a notification with title and body", async () => {
      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        result.current.notify("Test Title", { body: "Test body" });
      });

      expect(mockNotification).toHaveBeenCalledWith("Test Title", {
        body: "Test body",
      });
    });

    it("should send a notification with icon", async () => {
      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        result.current.notify("Test Title", { icon: "/icon.png" });
      });

      expect(mockNotification).toHaveBeenCalledWith("Test Title", {
        icon: "/icon.png",
      });
    });

    it("should not send notification when permission denied", async () => {
      Object.defineProperty(mockNotification, "permission", {
        value: "denied",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        result.current.notify("Test Title");
      });

      expect(mockNotification).not.toHaveBeenCalled();
    });

    it("should return the notification instance", async () => {
      const mockInstance = { close: vi.fn() };
      mockNotification.mockReturnValueOnce(mockInstance);

      const { result } = renderHook(() => useNotifications());

      let notification: unknown;
      await act(async () => {
        notification = result.current.notify("Test Title");
      });

      expect(notification).toBe(mockInstance);
    });
  });

  describe("notifications disabled", () => {
    it("should respect enabled flag", async () => {
      Object.defineProperty(mockNotification, "permission", {
        value: "granted",
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications({ enabled: false }));

      await act(async () => {
        result.current.notify("Test Title");
      });

      expect(mockNotification).not.toHaveBeenCalled();
    });
  });

  describe("notification types", () => {
    beforeEach(() => {
      Object.defineProperty(mockNotification, "permission", {
        value: "granted",
        writable: true,
        configurable: true,
      });
    });

    it("should send success notification", async () => {
      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        result.current.success("Task completed");
      });

      expect(mockNotification).toHaveBeenCalledWith(
        "Task completed",
        expect.objectContaining({ tag: "success" }),
      );
    });

    it("should send error notification", async () => {
      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        result.current.error("Something went wrong");
      });

      expect(mockNotification).toHaveBeenCalledWith(
        "Something went wrong",
        expect.objectContaining({ tag: "error" }),
      );
    });

    it("should send info notification", async () => {
      const { result } = renderHook(() => useNotifications());

      await act(async () => {
        result.current.info("New update available");
      });

      expect(mockNotification).toHaveBeenCalledWith(
        "New update available",
        expect.objectContaining({ tag: "info" }),
      );
    });
  });

  describe("close notification", () => {
    beforeEach(() => {
      Object.defineProperty(mockNotification, "permission", {
        value: "granted",
        writable: true,
        configurable: true,
      });
    });

    it("should close notification", async () => {
      const closeMock = vi.fn();
      mockNotification.mockReturnValueOnce({ close: closeMock });

      const { result } = renderHook(() => useNotifications());

      let notification: { close: () => void } | undefined;
      await act(async () => {
        notification = result.current.notify("Test Title");
      });

      notification?.close();
      expect(closeMock).toHaveBeenCalled();
    });
  });

  describe("fallback for unsupported browsers", () => {
    it("should not throw when notifications not supported", async () => {
      Object.defineProperty(window, "Notification", {
        value: undefined,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications());

      await expect(async () => {
        await act(async () => {
          result.current.requestPermission();
        });
      }).not.toThrow();
    });

    it("should not throw when sending notification without support", async () => {
      Object.defineProperty(window, "Notification", {
        value: undefined,
        writable: true,
        configurable: true,
      });

      const { result } = renderHook(() => useNotifications());

      await expect(async () => {
        await act(async () => {
          result.current.notify("Test Title");
        });
      }).not.toThrow();
    });
  });
});
