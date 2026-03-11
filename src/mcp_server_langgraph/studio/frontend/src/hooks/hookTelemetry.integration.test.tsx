/**
 * Hook Telemetry Integration Tests
 *
 * Tests that verify error handling is properly integrated into WebSocket hooks.
 * These tests verify that error state is set and onError callbacks are called
 * when hooks receive error messages from the WebSocket server.
 *
 * Following TDD: Tests verify real integration behavior.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../api";

// =============================================================================
// Mocks - use vi.hoisted() for proper initialization before mock hoisting
// =============================================================================

const { mockUseRealtimeSync } = vi.hoisted(() => ({
  mockUseRealtimeSync: vi.fn(),
}));

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: unknown) => mockUseRealtimeSync(options),
}));

// Mock auth hooks
vi.mock("../store/hooks", () => ({
  useAppSelector: (selector: () => unknown) => selector(),
  useAppDispatch: () => vi.fn(),
}));

vi.mock("../store/slices/authSlice", async () => {
  const actual = await vi.importActual("../store/slices/authSlice");
  return {
    ...actual,
    selectIsAuthenticated: () => true,
    selectWebSocketPermissions: () => ({
      heart_metrics: true,
      cost_tracking: true,
      connections_realtime: true,
    }),
    logout: () => ({ type: "auth/logout" }),
  };
});
vi.mock("../store/slices/notificationSlice", () => ({
  addNotification: vi.fn(),
}));

vi.mock("../utils/storage", async () => {
  const actual = await vi.importActual("../utils/storage");
  return {
    ...actual,
    getAuthToken: () => "test-token",
  };
});
vi.mock("../utils/websocketTelemetry", () => ({
  reportWebSocketMetrics: vi.fn(),
}));

vi.mock("../utils/websocketAuth", () => ({
  PROTOCOL_VERSION_MISMATCH_NOTIFICATION: {
    type: "error",
    message: "Protocol version mismatch",
  },
  showProtocolVersionMismatchToast: vi.fn(),
}));

// Import hooks after mocking
import { useHeartMetricsWebSocket } from "./useHeartMetricsWebSocket";
import { useCostTrackingWebSocket } from "./useCostTrackingWebSocket";
import { useConnectionsRealtimeWebSocket } from "./useConnectionsRealtimeWebSocket";

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Shared Test Utilities
// =============================================================================

interface CapturedCallbacks {
  onMessage: ((data: unknown) => void) | null;
  onConnect: (() => void) | null;
}

const createMockRealtimeReturn = () => ({
  status: "connected" as const,
  send: vi.fn(),
  disconnect: vi.fn(),
  reconnect: vi.fn(),
  reconnectAttempts: 0,
  lastMessageTime: null,
  metrics: {
    totalAttempts: 0,
    totalReconnections: 0,
    consecutiveFailures: 0,
    lastReconnectionTime: null,
    lastDisconnectionTime: null,
    avgReconnectionDurationMs: 0,
    totalReconnectionTimeMs: 0,
    failuresByReason: {},
    recentAttempts: [],
    successRate: 100,
  },
  resetMetrics: vi.fn(),
});

// =============================================================================
// Tests
// =============================================================================

describe("hookTelemetry integration", () => {
  let capturedCallbacks: CapturedCallbacks;

  beforeEach(() => {
    vi.resetAllMocks();
    capturedCallbacks = { onMessage: null, onConnect: null };

    // Default mock that captures callbacks
    mockUseRealtimeSync.mockImplementation(
      (options?: {
        onMessage?: (data: unknown) => void;
        onConnect?: () => void;
      }) => {
        if (options?.onMessage) {
          capturedCallbacks.onMessage = options.onMessage;
        }
        if (options?.onConnect) {
          capturedCallbacks.onConnect = options.onConnect;
        }
        return createMockRealtimeReturn();
      },
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("useHeartMetricsWebSocket error handling", () => {
    it("sets error state when receiving error message", () => {
      const onError = vi.fn();
      const { result } = renderHook(
        () => useHeartMetricsWebSocket({ onError }),
        { wrapper },
      );

      // Simulate server sending an error message
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          message: "Server error occurred",
        });
      });

      // Verify error state is set
      expect(result.current.error).toBe("Server error occurred");
      // Verify onError callback is called
      expect(onError).toHaveBeenCalledWith("Server error occurred");
    });
  });

  describe("useCostTrackingWebSocket error handling", () => {
    it("sets error state when receiving error message", () => {
      const onError = vi.fn();
      const { result } = renderHook(
        () => useCostTrackingWebSocket({ onError }),
        { wrapper },
      );

      // Simulate server sending an error message
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: {
            code: "BUDGET_EXCEEDED",
            message: "Budget limit exceeded",
          },
        });
      });

      // Verify error state is set
      expect(result.current.error).toBe("Budget limit exceeded");
      // Verify onError callback is called
      expect(onError).toHaveBeenCalledWith("Budget limit exceeded");
    });
  });

  describe("useConnectionsRealtimeWebSocket error handling", () => {
    it("sets error state when receiving error message", () => {
      const onError = vi.fn();
      const { result } = renderHook(
        () => useConnectionsRealtimeWebSocket({ onError }),
        { wrapper },
      );

      // Simulate server sending an error message
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: {
            code: "CONNECTION_FAILED",
            message: "Failed to connect to service",
          },
        });
      });

      // Verify error state is set
      expect(result.current.error).toBe("Failed to connect to service");
      // Verify onError callback is called
      expect(onError).toHaveBeenCalledWith("Failed to connect to service");
    });
  });

  describe("error context enrichment", () => {
    it("calls onError callback for heart metrics errors", () => {
      const onError = vi.fn();
      renderHook(() => useHeartMetricsWebSocket({ onError }), { wrapper });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          message: "Test error",
        });
      });

      expect(onError).toHaveBeenCalledWith("Test error");
    });

    it("calls onError callback for cost tracking errors", () => {
      const onError = vi.fn();
      renderHook(() => useCostTrackingWebSocket({ onError }), { wrapper });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: { code: "ERR", message: "Test error" },
        });
      });

      expect(onError).toHaveBeenCalledWith("Test error");
    });

    it("calls onError callback for connections realtime errors", () => {
      const onError = vi.fn();
      renderHook(() => useConnectionsRealtimeWebSocket({ onError }), {
        wrapper,
      });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: { code: "ERR", message: "Test error" },
        });
      });

      expect(onError).toHaveBeenCalledWith("Test error");
    });
  });

  describe("error state stability", () => {
    it("clears error state on successful connection", () => {
      const { result } = renderHook(() => useHeartMetricsWebSocket(), {
        wrapper,
      });

      // Simulate error
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          message: "Test error",
        });
      });

      expect(result.current.error).toBe("Test error");

      // Simulate successful connection (onConnect callback clears error)
      act(() => {
        capturedCallbacks.onConnect?.();
      });

      expect(result.current.error).toBeNull();
    });
  });
});
