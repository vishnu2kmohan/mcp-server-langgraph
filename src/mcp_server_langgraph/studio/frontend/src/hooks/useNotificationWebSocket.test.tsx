/**
 * useNotificationWebSocket Hook Tests
 *
 * TDD tests for real-time notification delivery via WebSocket.
 * Features:
 * - Connect to notifications WebSocket endpoint
 * - Dispatch notifications to Redux store
 * - Connection status tracking
 * - Automatic reconnection
 *
 * Note: This test mocks useRealtimeSync since the hook uses that for WebSocket management.
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

// Mock useRealtimeSync (the hook uses this, not native WebSocket)
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;
let _mockOnConnect: (() => void) | undefined;
let _mockOnDisconnect: (() => void) | undefined;
let _mockOnError: ((error: Error) => void) | undefined;
let mockStatus:
  | "connecting"
  | "connected"
  | "disconnected"
  | "reconnecting"
  | "error" = "connecting";

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn((options) => {
    mockOnMessage = options.onMessage;
    _mockOnConnect = options.onConnect;
    _mockOnDisconnect = options.onDisconnect;
    _mockOnError = options.onError;
    return {
      status: mockStatus,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
      metrics: { totalAttempts: 0 },
    };
  }),
}));

// Create test store with auth and notifications slices
interface TestStoreOptions {
  isAuthenticated?: boolean;
  isInitializing?: boolean;
}

const createTestStore = (options: TestStoreOptions = {}) => {
  const { isAuthenticated = true, isInitializing = false } = options;
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
              // WebSocket permissions for notifications hook
              websocketPermissions: {
                notifications: true,
              },
            }
          : null,
        tokens: null,
        organizations: [],
        currentOrg: null,
        isInitializing,
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
    mockStatus = "connecting";
    mockOnMessage = undefined;
    _mockOnConnect = undefined;
    _mockOnDisconnect = undefined;
    _mockOnError = undefined;
    store = createTestStore();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Connection", () => {
    it("should connect to the notifications WebSocket endpoint", async () => {
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("/ws/notifications"),
        }),
      );
    });

    it("should return connecting status initially", () => {
      mockStatus = "connecting";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.status).toBe("connecting");
    });

    it("should return connected status after WebSocket opens", () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.status).toBe("connected");
    });

    it("should return disconnected status after WebSocket closes", () => {
      mockStatus = "disconnected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.status).toBe("disconnected");
    });

    it("should expose disconnect function for cleanup", () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      // Verify disconnect function is exposed
      expect(typeof result.current.disconnect).toBe("function");

      // Calling disconnect should call the underlying useRealtimeSync disconnect
      result.current.disconnect();
      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe("Notification Dispatch", () => {
    it("should dispatch addNotification when receiving a notification message", () => {
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      // Simulate receiving a notification via the onMessage callback
      act(() => {
        mockOnMessage?.({
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
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        mockOnMessage?.({
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
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        mockOnMessage?.({
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
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        mockOnMessage?.({
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
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        mockOnMessage?.({
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
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(selectUnreadCount(store.getState())).toBe(0);

      act(() => {
        mockOnMessage?.({
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
        mockOnMessage?.({
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
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        mockOnMessage?.({
          type: "heartbeat",
          payload: { ts: Date.now() },
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications.length).toBe(0);
    });

    it("should handle malformed messages gracefully", () => {
      mockStatus = "connected";
      renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      // Send malformed message (missing payload)
      act(() => {
        mockOnMessage?.({
          type: "notification",
        });
      });

      const notifications = selectNotifications(store.getState());
      expect(notifications.length).toBe(0);
    });
  });

  describe("Reconnection", () => {
    it("should expose disconnect function that calls useRealtimeSync disconnect", () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      result.current.disconnect();

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should expose reconnect function that calls useRealtimeSync reconnect", () => {
      mockStatus = "disconnected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      result.current.reconnect();

      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should return error status on WebSocket error", () => {
      mockStatus = "error";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.status).toBe("error");
    });
  });

  describe("Options", () => {
    it("should allow custom WebSocket URL", async () => {
      mockStatus = "connected";
      // Test uses mock - insecure protocol is intentional for unit testing
      renderHook(
        () =>
          // nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
          useNotificationWebSocket({ url: "ws://custom.host/notifications" }),
        {
          wrapper: createWrapper(store),
        },
      );

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          // nosemgrep: javascript.lang.security.detect-insecure-websocket.detect-insecure-websocket
          url: "ws://custom.host/notifications",
        }),
      );
    });

    it("should support enabled option to control connection", () => {
      mockStatus = "connected";

      // Start disabled - status should be "disconnected" regardless of underlying connection
      const { result, rerender } = renderHook(
        ({ enabled }) => useNotificationWebSocket({ enabled }),
        {
          wrapper: createWrapper(store),
          initialProps: { enabled: false },
        },
      );

      // When disabled, status is overridden to "disconnected"
      expect(result.current.status).toBe("disconnected");

      // Enable connection
      rerender({ enabled: true });

      // After enabling, status should reflect actual connection status
      expect(result.current.status).toBe("connected");
    });
  });

  describe("Auth Initialization", () => {
    it("should not connect when auth is still initializing", async () => {
      // Create store with isInitializing=true (tokens exist but auth not validated)
      const initializingStore = createTestStore({
        isAuthenticated: true,
        isInitializing: true,
      });

      mockStatus = "connected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(initializingStore),
      });

      // Should report disconnected during initialization
      expect(result.current.status).toBe("disconnected");

      // Verify empty URL passed to prevent connection
      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: "", // Empty URL prevents connection
        }),
      );
    });

    it("should connect after auth initialization completes", async () => {
      // Start with initializing state
      const initializingStore = createTestStore({
        isAuthenticated: true,
        isInitializing: true,
      });

      mockStatus = "connected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(initializingStore),
      });

      // During initialization, status is disconnected
      expect(result.current.status).toBe("disconnected");

      // Now test with a ready store
      cleanup();
      const readyStore = createTestStore({
        isAuthenticated: true,
        isInitializing: false,
      });

      const { result: result2 } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(readyStore),
      });

      // Now should be connected
      expect(result2.current.status).toBe("connected");

      // Verify non-empty URL passed
      const { useRealtimeSync } = await import("./useRealtimeSync");
      // Last call should have a non-empty URL
      const lastCall = vi.mocked(useRealtimeSync).mock.calls.at(-1)?.[0];
      expect(lastCall?.url).toContain("/ws/notifications");
    });

    it("should stay disconnected when not authenticated even after initialization", async () => {
      const unauthenticatedStore = createTestStore({
        isAuthenticated: false,
        isInitializing: false,
      });

      mockStatus = "connected";
      const { result } = renderHook(() => useNotificationWebSocket(), {
        wrapper: createWrapper(unauthenticatedStore),
      });

      expect(result.current.status).toBe("disconnected");

      // Verify empty URL passed
      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: "",
        }),
      );
    });
  });
});
