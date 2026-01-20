/**
 * Hook Telemetry Integration Tests
 *
 * Tests that verify hookTelemetry is properly integrated into WebSocket hooks.
 * These tests verify that telemetry.logError is called when hooks receive
 * error messages from the WebSocket server.
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

const {
  mockDevLoggerError,
  mockDevLoggerWarn,
  mockDevLoggerDebug,
  mockWithPrefix,
  mockUseRealtimeSync,
} = vi.hoisted(() => ({
  mockDevLoggerError: vi.fn(),
  mockDevLoggerWarn: vi.fn(),
  mockDevLoggerDebug: vi.fn(),
  mockWithPrefix: vi.fn(),
  mockUseRealtimeSync: vi.fn(),
}));

// Reset mockWithPrefix to return the logger mocks
mockWithPrefix.mockReturnValue({
  debug: mockDevLoggerDebug,
  warn: mockDevLoggerWarn,
  error: mockDevLoggerError,
});

vi.mock("../utils/devLogger", () => ({
  devLogger: {
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    withPrefix: mockWithPrefix,
  },
}));

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: unknown) => mockUseRealtimeSync(options),
}));

// Mock auth hooks
vi.mock("../store/hooks", () => ({
  useAppSelector: (selector: () => unknown) => selector(),
  useAppDispatch: () => vi.fn(),
}));

vi.mock("../store/slices/authSlice", () => ({
  selectIsAuthenticated: () => true,
  selectWebSocketPermissions: () => ({
    heart_metrics: true,
    cost_tracking: true,
    connections_realtime: true,
  }),
  logout: () => ({ type: "auth/logout" }),
}));

vi.mock("../store/slices/notificationSlice", () => ({
  addNotification: vi.fn(),
}));

vi.mock("../utils/storage", () => ({
  getAuthToken: () => "test-token",
}));

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

    // Re-setup mockWithPrefix after reset
    mockWithPrefix.mockReturnValue({
      debug: mockDevLoggerDebug,
      warn: mockDevLoggerWarn,
      error: mockDevLoggerError,
    });

    // Default mock that captures callbacks
    mockUseRealtimeSync.mockImplementation(
      (options?: { onMessage?: (data: unknown) => void; onConnect?: () => void }) => {
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

  describe("useHeartMetricsWebSocket telemetry integration", () => {
    it("logs error via telemetry when receiving error message", () => {
      renderHook(() => useHeartMetricsWebSocket(), { wrapper });

      // Simulate server sending an error message - wrapped in act for state updates
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          message: "Server error occurred",
        });
      });

      // Verify telemetry logged the error
      expect(mockDevLoggerError).toHaveBeenCalledWith(
        "Error occurred",
        expect.objectContaining({
          error: "Server error occurred",
          messageType: "error",
          endpoint: "heart_metrics",
        }),
      );
    });

    it("includes hook prefix in telemetry logs", () => {
      renderHook(() => useHeartMetricsWebSocket(), { wrapper });

      expect(mockWithPrefix).toHaveBeenCalledWith("[useHeartMetricsWebSocket]");
    });
  });

  describe("useCostTrackingWebSocket telemetry integration", () => {
    it("logs error via telemetry when receiving error message", () => {
      renderHook(() => useCostTrackingWebSocket(), { wrapper });

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

      // Verify telemetry logged the error
      expect(mockDevLoggerError).toHaveBeenCalledWith(
        "Error occurred",
        expect.objectContaining({
          error: "Budget limit exceeded",
          messageType: "error",
          endpoint: "cost_tracking",
        }),
      );
    });

    it("includes hook prefix in telemetry logs", () => {
      renderHook(() => useCostTrackingWebSocket(), { wrapper });

      expect(mockWithPrefix).toHaveBeenCalledWith("[useCostTrackingWebSocket]");
    });
  });

  describe("useConnectionsRealtimeWebSocket telemetry integration", () => {
    it("logs error via telemetry when receiving error message", () => {
      renderHook(() => useConnectionsRealtimeWebSocket(), { wrapper });

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

      // Verify telemetry logged the error
      expect(mockDevLoggerError).toHaveBeenCalledWith(
        "Error occurred",
        expect.objectContaining({
          error: "Failed to connect to service",
          messageType: "error",
          endpoint: "connections_realtime",
        }),
      );
    });

    it("includes hook prefix in telemetry logs", () => {
      renderHook(() => useConnectionsRealtimeWebSocket(), { wrapper });

      expect(mockWithPrefix).toHaveBeenCalledWith(
        "[useConnectionsRealtimeWebSocket]",
      );
    });
  });

  describe("telemetry callback stability", () => {
    it("uses stable telemetry instance across re-renders", () => {
      const { rerender } = renderHook(() => useHeartMetricsWebSocket(), {
        wrapper,
      });

      const firstCallCount = mockWithPrefix.mock.calls.length;

      // Force re-render
      rerender();

      const secondCallCount = mockWithPrefix.mock.calls.length;

      // withPrefix should only be called once (stable instance via useMemo)
      expect(secondCallCount).toBe(firstCallCount);
    });
  });

  describe("error context enrichment", () => {
    it("includes endpoint identifier in error context for heart metrics", () => {
      renderHook(() => useHeartMetricsWebSocket(), { wrapper });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          message: "Test error",
        });
      });

      expect(mockDevLoggerError).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          endpoint: "heart_metrics",
        }),
      );
    });

    it("includes endpoint identifier in error context for cost tracking", () => {
      renderHook(() => useCostTrackingWebSocket(), { wrapper });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: { code: "ERR", message: "Test error" },
        });
      });

      expect(mockDevLoggerError).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          endpoint: "cost_tracking",
        }),
      );
    });

    it("includes endpoint identifier in error context for connections realtime", () => {
      renderHook(() => useConnectionsRealtimeWebSocket(), { wrapper });

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: { code: "ERR", message: "Test error" },
        });
      });

      expect(mockDevLoggerError).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          endpoint: "connections_realtime",
        }),
      );
    });
  });
});
