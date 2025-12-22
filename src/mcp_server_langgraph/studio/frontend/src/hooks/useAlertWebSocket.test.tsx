/**
 * useAlertWebSocket Hook Tests
 *
 * TDD tests for the alert WebSocket hook.
 * Features:
 * - Connect to alerts WebSocket endpoint
 * - Dispatch alerts to Redux store
 * - Handle different alert message types
 * - Trigger toast for critical alerts
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";

import { useAlertWebSocket, parseAlertMessage, type AlertMessage } from "./useAlertWebSocket";
import alertReducer, { selectAlerts, type Alert } from "../store/slices/alertSlice";

// =============================================================================
// Mocks
// =============================================================================

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockStatus = "connected";
let mockOnMessage: ((data: unknown) => void) | undefined;

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: { onMessage?: (data: unknown) => void }) => {
    mockOnMessage = options.onMessage;
    return {
      status: mockStatus,
      reconnectAttempts: 0,
      lastMessageTime: null,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
    };
  },
}));

// Mock getAuthToken
vi.mock("../utils/storage", () => ({
  getAuthToken: vi.fn(() => "mock-token"),
}));

// Mock toast
const mockToastError = vi.fn();
const mockToastWarning = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    error: (message: string, options?: unknown) => mockToastError(message, options),
    warning: (message: string, options?: unknown) => mockToastWarning(message, options),
  },
}));

// =============================================================================
// Test Helpers
// =============================================================================

const createTestStore = () => {
  return configureStore({
    reducer: {
      alerts: alertReducer,
    },
  });
};

function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

const createMockAlertMessage = (overrides: Partial<Alert> = {}): AlertMessage => ({
  type: "alert",
  payload: {
    alert_id: `alert-${Math.random().toString(36).slice(2, 9)}`,
    name: "TestAlert",
    severity: "critical",
    state: "firing",
    message: "Test alert message",
    labels: { service: "test-service" },
    annotations: {},
    started_at: new Date().toISOString(),
    ended_at: null,
    fingerprint: `fp-${Math.random().toString(36).slice(2, 9)}`,
    ...overrides,
  },
});

// =============================================================================
// Tests
// =============================================================================

describe("useAlertWebSocket", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    mockStatus = "connected";
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("Connection", () => {
    it("should return connection status", () => {
      const { result } = renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.status).toBe("connected");
    });

    it("should return disconnect function", () => {
      const { result } = renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.disconnect).toBe("function");
    });

    it("should return reconnect function", () => {
      const { result } = renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.reconnect).toBe("function");
    });

    it("should disable connection when enabled is false", () => {
      mockStatus = "disconnected";
      const { result } = renderHook(
        () => useAlertWebSocket({ enabled: false }),
        { wrapper: createWrapper(store) }
      );

      expect(result.current.status).toBe("disconnected");
    });
  });

  describe("Message Handling", () => {
    it("should add alert to store when receiving alert message", async () => {
      renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      const alertMessage = createMockAlertMessage({ alert_id: "alert-123" });

      act(() => {
        mockOnMessage?.(alertMessage);
      });

      await waitFor(() => {
        const alerts = selectAlerts(store.getState());
        expect(alerts).toHaveLength(1);
        expect(alerts[0].alert_id).toBe("alert-123");
      });
    });

    it("should handle alert update messages", async () => {
      renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      // First message - add alert
      const alertMessage = createMockAlertMessage({
        alert_id: "alert-123",
        state: "firing",
      });

      act(() => {
        mockOnMessage?.(alertMessage);
      });

      // Second message - update same alert
      const updateMessage = createMockAlertMessage({
        alert_id: "alert-123",
        state: "resolved",
      });

      act(() => {
        mockOnMessage?.(updateMessage);
      });

      await waitFor(() => {
        const alerts = selectAlerts(store.getState());
        expect(alerts).toHaveLength(1);
        expect(alerts[0].state).toBe("resolved");
      });
    });

    it("should handle batch alert messages", async () => {
      renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      const batchMessage = {
        type: "alert_batch",
        payload: [
          createMockAlertMessage({ alert_id: "alert-1" }).payload,
          createMockAlertMessage({ alert_id: "alert-2" }).payload,
          createMockAlertMessage({ alert_id: "alert-3" }).payload,
        ],
      };

      act(() => {
        mockOnMessage?.(batchMessage);
      });

      await waitFor(() => {
        const alerts = selectAlerts(store.getState());
        expect(alerts).toHaveLength(3);
      });
    });

    it("should ignore invalid messages", async () => {
      renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        mockOnMessage?.({ type: "unknown", data: {} });
      });

      await waitFor(() => {
        const alerts = selectAlerts(store.getState());
        expect(alerts).toHaveLength(0);
      });
    });
  });

  describe("Toast Notifications", () => {
    it("should trigger error toast for critical alerts", async () => {
      renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      const alertMessage = createMockAlertMessage({
        severity: "critical",
        name: "CriticalAlert",
        message: "Critical issue detected",
      });

      act(() => {
        mockOnMessage?.(alertMessage);
      });

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalled();
      });
    });

    it("should not trigger toast for warning alerts by default", async () => {
      renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      const alertMessage = createMockAlertMessage({
        severity: "warning",
        name: "WarningAlert",
      });

      act(() => {
        mockOnMessage?.(alertMessage);
      });

      // Toast should not be called for warnings by default
      expect(mockToastError).not.toHaveBeenCalled();
    });

    it("should include alert name in toast title", async () => {
      renderHook(() => useAlertWebSocket(), {
        wrapper: createWrapper(store),
      });

      const alertMessage = createMockAlertMessage({
        severity: "critical",
        name: "CPUHigh",
        message: "CPU usage above threshold",
      });

      act(() => {
        mockOnMessage?.(alertMessage);
      });

      await waitFor(() => {
        expect(mockToastError).toHaveBeenCalledWith(
          expect.stringContaining("CPUHigh"),
          expect.anything()
        );
      });
    });
  });

  describe("parseAlertMessage", () => {
    it("should parse valid alert message", () => {
      const message = createMockAlertMessage();
      const result = parseAlertMessage(message);

      expect(result).not.toBeNull();
      expect(result?.type).toBe("alert");
    });

    it("should parse alert_batch message", () => {
      const message = {
        type: "alert_batch",
        payload: [createMockAlertMessage().payload],
      };
      const result = parseAlertMessage(message);

      expect(result).not.toBeNull();
      expect(result?.type).toBe("alert_batch");
    });

    it("should return null for invalid message", () => {
      const result = parseAlertMessage({ foo: "bar" });
      expect(result).toBeNull();
    });

    it("should return null for null input", () => {
      const result = parseAlertMessage(null);
      expect(result).toBeNull();
    });

    it("should return null for non-object input", () => {
      const result = parseAlertMessage("not an object");
      expect(result).toBeNull();
    });
  });
});
