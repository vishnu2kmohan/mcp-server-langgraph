/**
 * useNotificationWebSocket Hook Tests
 *
 * TDD tests for real-time notification delivery via WebSocket.
 * Features:
 * - Connect to notifications WebSocket endpoint
 * - Dispatch notifications to Redux store
 * - Connection status tracking
 * - Automatic reconnection
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useNotificationWebSocket } from "./useNotificationWebSocket";
import notificationReducer, {
  selectNotifications,
  selectUnreadCount,
} from "../store/slices/notificationSlice";
import authReducer from "../store/slices/authSlice";
import type { ReactNode } from "react";

// Mock WebSocket class
class MockWebSocket {
  static instances: MockWebSocket[] = [];

  url: string;
  readyState: number = 0; // CONNECTING
  onopen: (() => void) | null = null;
  onclose: ((event: { code: number; reason: string }) => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    // Simulate connection delay
    setTimeout(() => {
      if (this.readyState === 0) {
        this.readyState = 1; // OPEN
        this.onopen?.();
      }
    }, 10);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = 3; // CLOSED
    this.onclose?.({ code: 1000, reason: "Normal closure" });
  });

  // Helper to simulate receiving a message
  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  // Helper to simulate an error
  simulateError(error: Error) {
    this.onerror?.(error as unknown as Event);
  }

  // Helper to simulate closing
  simulateClose(code: number, reason: string) {
    this.readyState = 3;
    this.onclose?.({ code, reason });
  }

  static clearInstances() {
    MockWebSocket.instances = [];
  }

  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
}

// Create test store with auth and notifications slices
const createTestStore = (isAuthenticated = true) => {
  return configureStore({
    reducer: {
      notifications: notificationReducer,
      auth: authReducer,
    },
    preloadedState: {
      auth: {
        user: isAuthenticated
          ? {
              id: "test-user",
              email: "test@example.com",
              roles: ["user"],
              persona: "user" as const,
            }
          : null,
        tokens: null,
        organizations: [],
        currentOrganization: null,
        permissions: [],
        lastSynced: null,
        isLoading: false,
        error: null,
      },
    },
  });
};

// Wrapper with Redux provider
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return ({ children }: { children: ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
};

describe("useNotificationWebSocket", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.clearInstances();
    vi.useFakeTimers();
    vi.stubGlobal("WebSocket", MockWebSocket);
    store = createTestStore();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  describe("Connection", () => {
    it("should connect to the notifications WebSocket endpoint", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(MockWebSocket.instances.length).toBe(1);
      expect(MockWebSocket.instances[0].url).toContain("/ws/notifications");
    });

    it("should return connecting status initially", () => {
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.status).toBe("connecting");
    });

    it("should return connected status after WebSocket opens", () => {
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.status).toBe("connected");
    });

    it("should return disconnected status after WebSocket closes", () => {
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateClose(1000, "Normal");
      });

      expect(result.current.status).toBe("disconnected");
    });

    it("should close WebSocket on unmount", () => {
      const { unmount } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      unmount();

      expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
    });
  });

  describe("Notification Dispatch", () => {
    it("should dispatch addNotification when receiving a notification message", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      // Simulate receiving a notification
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
          payload: {
            type: "info",
            title: "Test Notification",
            message: "This is a test message",
          },
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications.length).toBe(1);
      expect(notifications[0].title).toBe("Test Notification");
      expect(notifications[0].message).toBe("This is a test message");
      expect(notifications[0].type).toBe("info");
    });

    it("should dispatch success notification", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
          payload: {
            type: "success",
            title: "Operation Complete",
            message: "Workflow executed successfully",
          },
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications[0].type).toBe("success");
    });

    it("should dispatch warning notification", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
          payload: {
            type: "warning",
            title: "High Usage",
            message: "Token usage is above 80%",
          },
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications[0].type).toBe("warning");
    });

    it("should dispatch error notification", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
          payload: {
            type: "error",
            title: "Workflow Failed",
            message: "An error occurred during execution",
          },
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications[0].type).toBe("error");
    });

    it("should dispatch notification with action", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
          payload: {
            type: "info",
            title: "Session Complete",
            message: "Your session has finished",
            action: {
              label: "View Results",
              href: "/studio/sessions/123",
            },
          },
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications[0].action).toBeDefined();
      expect(notifications[0].action?.label).toBe("View Results");
      expect(notifications[0].action?.href).toBe("/studio/sessions/123");
    });

    it("should update unread count when receiving notifications", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      expect(selectUnreadCount(store.getState())).toBe(0);

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
          payload: {
            type: "info",
            title: "Test 1",
            message: "Message 1",
          },
        });
      });

      expect(selectUnreadCount(store.getState())).toBe(1);

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
          payload: {
            type: "info",
            title: "Test 2",
            message: "Message 2",
          },
        });
      });

      expect(selectUnreadCount(store.getState())).toBe(2);
    });

    it("should ignore non-notification messages", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "heartbeat",
          payload: { ts: Date.now() },
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications.length).toBe(0);
    });

    it("should handle malformed messages gracefully", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      // Send malformed message (missing payload)
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "notification",
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications.length).toBe(0);
    });
  });

  describe("Reconnection", () => {
    it("should attempt to reconnect on abnormal close", () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateClose(1006, "Abnormal");
      });

      // Advance time to trigger reconnect
      act(() => {
        vi.advanceTimersByTime(5100);
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(1);
    });

    it("should provide reconnect function", () => {
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateClose(1000, "Normal");
      });

      expect(result.current.status).toBe("disconnected");

      act(() => {
        result.current.reconnect();
      });

      expect(MockWebSocket.instances.length).toBe(2);
    });

    it("should provide disconnect function", () => {
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.status).toBe("connected");

      act(() => {
        result.current.disconnect();
      });

      expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should return error status on WebSocket error", () => {
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateError(
          new Error("Connection failed"),
        );
      });

      expect(result.current.status).toBe("error");
    });
  });

  describe("Options", () => {
    it("should allow custom WebSocket URL", () => {
      // Test uses mock WebSocket - insecure protocol is intentional for unit testing
      renderHook(
        () =>
          // nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
          useNotificationWebSocket({ url: "ws://custom.host/notifications" }),
        {
          wrapper: createWrapper(store),
        },
      );

      expect(MockWebSocket.instances[0].url).toBe(
        // nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
        "ws://custom.host/notifications",
      );
    });

    it("should support enabled option to control connection", () => {
      const { result, rerender } = renderHook(
        ({ enabled }) => useNotificationWebSocket({ enabled }),
        {
          wrapper: createWrapper(store),
          initialProps: { enabled: false },
        },
      );

      // When disabled, status should be 'disconnected' regardless of internal connection
      // Note: Due to hooks rules, the underlying WebSocket may still be created but
      // the hook reports 'disconnected' status and closes the connection
      expect(result.current.status).toBe("disconnected");

      // Enable connection
      rerender({ enabled: true });

      // After enabling, status should reflect actual connection status
      act(() => {
        vi.advanceTimersByTime(20);
      });
      expect(result.current.status).toBe("connected");
    });
  });
});
