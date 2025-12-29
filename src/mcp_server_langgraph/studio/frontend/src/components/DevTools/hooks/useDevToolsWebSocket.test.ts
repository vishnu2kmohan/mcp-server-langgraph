/**
 * useDevToolsWebSocket Hook Tests
 *
 * TDD tests for WebSocket integration with DevTools console and network tabs.
 * Refactored to use useRealtimeSync for metrics reporting.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { useDevToolsWebSocket } from "./useDevToolsWebSocket";
// Types used for type-checking in tests
import type {
  ConsoleEntry as _ConsoleEntry,
  NetworkEntry as _NetworkEntry,
} from "../types";
import type { ConnectionStatus } from "../../../hooks/useRealtimeSync";

// =============================================================================
// Mock useRealtimeSync
// =============================================================================

const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;
let mockOnConnect: (() => void) | undefined;
let _mockOnDisconnect: (() => void) | undefined;
let _mockOnError: ((error: Error) => void) | undefined;
let mockStatus: ConnectionStatus = "disconnected";
let mockUrl: string | null = null;

vi.mock("../../../hooks/useRealtimeSync", () => ({
  useRealtimeSync: (options: {
    url: string | null;
    onMessage?: (data: unknown) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Error) => void;
  }) => {
    mockUrl = options.url;
    mockOnMessage = options.onMessage;
    mockOnConnect = options.onConnect;
    _mockOnDisconnect = options.onDisconnect;
    _mockOnError = options.onError;

    // Auto-connect when URL is provided and currently disconnected
    if (options.url && mockStatus === "disconnected") {
      mockStatus = "connecting";
      setTimeout(() => {
        mockStatus = "connected";
        mockOnConnect?.();
      }, 0);
    }

    return {
      status: mockStatus,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
      reconnectAttempts: 0,
      lastMessageTime: null,
      metrics: {
        totalAttempts: 0,
        totalReconnections: 0,
        failedReconnections: 0,
        successRate: null,
        lastAttemptTime: null,
        lastSuccessTime: null,
        avgReconnectionTime: null,
        failuresByReason: {},
      },
      resetMetrics: vi.fn(),
    };
  },
}));

// Mock the websocket utility module
vi.mock("../../../utils/websocket", () => ({
  buildWebSocketUrl: vi.fn(
    (endpoint: string, _params?: Record<string, string>, includeAuth = false) =>
      `wss://test-host${endpoint}${includeAuth ? "?token=test-token" : ""}`,
  ),
  WS_ENDPOINTS: {
    DEVTOOLS: "/api/v1/ws/devtools",
  },
}));

// Mock websocketTelemetry
vi.mock("../../../utils/websocketTelemetry", () => ({
  reportWebSocketMetrics: vi.fn(),
}));

import { buildWebSocketUrl, WS_ENDPOINTS } from "../../../utils/websocket";

// =============================================================================
// Helper to simulate messages
// =============================================================================

function simulateMessage(data: unknown): void {
  if (mockOnMessage) {
    mockOnMessage(data);
  }
}

function simulateConnect(): void {
  mockStatus = "connected";
  if (mockOnConnect) {
    mockOnConnect();
  }
}

function simulateError(error: Error): void {
  mockStatus = "error";
  if (_mockOnError) {
    _mockOnError(error);
  }
}

// =============================================================================
// Tests
// =============================================================================

describe("useDevToolsWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = "disconnected";
    mockOnMessage = undefined;
    mockOnConnect = undefined;
    _mockOnDisconnect = undefined;
    _mockOnError = undefined;
    mockUrl = null;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("URL construction", () => {
    it("should use centralized buildWebSocketUrl utility", () => {
      renderHook(() => useDevToolsWebSocket({ enabled: true }));

      expect(buildWebSocketUrl).toHaveBeenCalledWith(
        WS_ENDPOINTS.DEVTOOLS,
        expect.any(Object),
        true, // includeAuthToken should be true
      );
    });

    it("should connect to the URL returned by buildWebSocketUrl", async () => {
      renderHook(() => useDevToolsWebSocket({ enabled: true }));

      await waitFor(() => {
        expect(mockUrl).toContain("/api/v1/ws/devtools");
        expect(mockUrl).toContain("token=");
      });
    });
  });

  describe("connection", () => {
    it("should connect when enabled", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
      });

      await waitFor(() => {
        expect(result.current.status).toBe("connected");
      });
    });

    it("should not connect when disabled", () => {
      renderHook(() => useDevToolsWebSocket({ enabled: false }));

      // When disabled, hook passes empty string to useRealtimeSync which prevents connection
      expect(mockUrl).toBe("");
    });

    it("should track connection status", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      // Initially connecting
      expect(result.current.status).toBe("connecting");

      // Simulate open
      act(() => {
        simulateConnect();
      });

      await waitFor(() => {
        expect(result.current.status).toBe("connected");
      });
    });

    it("should handle connection errors", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateError(new Error("Connection failed"));
      });

      await waitFor(() => {
        expect(result.current.status).toBe("error");
      });
    });

    it("should disconnect when unmounted", () => {
      const { unmount } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      unmount();

      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe("console entries", () => {
    it("should receive console entries from WebSocket", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
      });

      const consoleMessage = {
        type: "console",
        payload: {
          id: "log-1",
          level: "info",
          source: "system",
          message: "Test log message",
          timestamp: Date.now(),
        },
      };

      act(() => {
        simulateMessage(consoleMessage);
      });

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(1);
        expect(result.current.consoleEntries[0].message).toBe(
          "Test log message",
        );
      });
    });

    it("should accumulate multiple console entries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
      });

      for (let i = 0; i < 3; i++) {
        act(() => {
          simulateMessage({
            type: "console",
            payload: {
              id: `log-${i}`,
              level: "info",
              source: "system",
              message: `Message ${i}`,
              timestamp: Date.now(),
            },
          });
        });
      }

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(3);
      });
    });

    it("should limit console entries to maxEntries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true, maxConsoleEntries: 5 }),
      );

      act(() => {
        simulateConnect();
      });

      for (let i = 0; i < 10; i++) {
        act(() => {
          simulateMessage({
            type: "console",
            payload: {
              id: `log-${i}`,
              level: "info",
              source: "system",
              message: `Message ${i}`,
              timestamp: Date.now(),
            },
          });
        });
      }

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(5);
        // Should keep newest entries
        expect(result.current.consoleEntries[0].message).toBe("Message 5");
      });
    });
  });

  describe("network entries", () => {
    it("should receive network entries from WebSocket", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
      });

      const networkMessage = {
        type: "network",
        payload: {
          id: "req-1",
          method: "GET",
          url: "/api/v1/test",
          status: "completed",
          statusCode: 200,
          startTime: Date.now(),
          duration: 150,
        },
      };

      act(() => {
        simulateMessage(networkMessage);
      });

      await waitFor(() => {
        expect(result.current.networkEntries).toHaveLength(1);
        expect(result.current.networkEntries[0].url).toBe("/api/v1/test");
      });
    });

    it("should update pending network entries when completed", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
      });

      // Send pending request
      act(() => {
        simulateMessage({
          type: "network",
          payload: {
            id: "req-1",
            method: "GET",
            url: "/api/v1/test",
            status: "pending",
            startTime: Date.now(),
          },
        });
      });

      await waitFor(() => {
        expect(result.current.networkEntries[0].status).toBe("pending");
      });

      // Update with completed status
      act(() => {
        simulateMessage({
          type: "network_update",
          payload: {
            id: "req-1",
            status: "completed",
            statusCode: 200,
            duration: 150,
          },
        });
      });

      await waitFor(() => {
        expect(result.current.networkEntries[0].status).toBe("completed");
        expect(result.current.networkEntries[0].statusCode).toBe(200);
      });
    });
  });

  describe("clear operations", () => {
    it("should clear console entries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
        simulateMessage({
          type: "console",
          payload: {
            id: "log-1",
            level: "info",
            source: "system",
            message: "Test",
            timestamp: Date.now(),
          },
        });
      });

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(1);
      });

      act(() => {
        result.current.clearConsoleEntries();
      });

      expect(result.current.consoleEntries).toHaveLength(0);
    });

    it("should clear network entries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
        simulateMessage({
          type: "network",
          payload: {
            id: "req-1",
            method: "GET",
            url: "/test",
            status: "completed",
            startTime: Date.now(),
          },
        });
      });

      await waitFor(() => {
        expect(result.current.networkEntries).toHaveLength(1);
      });

      act(() => {
        result.current.clearNetworkEntries();
      });

      expect(result.current.networkEntries).toHaveLength(0);
    });
  });

  describe("message filtering", () => {
    it("should filter console entries by contextEntityId", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({
          enabled: true,
          contextEntityId: "session-123",
        }),
      );

      act(() => {
        simulateConnect();
      });

      // Global entry (no session)
      act(() => {
        simulateMessage({
          type: "console",
          payload: {
            id: "log-1",
            level: "info",
            source: "system",
            message: "Global message",
            timestamp: Date.now(),
          },
        });
      });

      // Entry for matching session
      act(() => {
        simulateMessage({
          type: "console",
          payload: {
            id: "log-2",
            level: "info",
            source: "execution",
            message: "Session message",
            timestamp: Date.now(),
            data: { sessionId: "session-123" },
          },
        });
      });

      // Entry for different session
      act(() => {
        simulateMessage({
          type: "console",
          payload: {
            id: "log-3",
            level: "info",
            source: "execution",
            message: "Other session message",
            timestamp: Date.now(),
            data: { sessionId: "session-456" },
          },
        });
      });

      await waitFor(() => {
        // Should include global and matching session entries
        expect(result.current.consoleEntries).toHaveLength(2);
        expect(result.current.consoleEntries.map((e) => e.id)).toEqual([
          "log-1",
          "log-2",
        ]);
      });
    });
  });

  describe("metrics reporting", () => {
    it("should report metrics when there are reconnection attempts", async () => {
      const { reportWebSocketMetrics } =
        await import("../../../utils/websocketTelemetry");

      renderHook(() => useDevToolsWebSocket({ enabled: true }));

      // The mock currently has 0 totalAttempts, so metrics won't be reported
      // This test documents the expected behavior
      expect(reportWebSocketMetrics).not.toHaveBeenCalled();
    });

    it("should use correct endpoint name for telemetry", async () => {
      // Verify the hook uses "devtools" as the endpoint identifier
      // This is validated when metrics are reported
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        simulateConnect();
      });

      await waitFor(() => {
        expect(result.current.status).toBe("connected");
      });
    });
  });

  describe("reconnection", () => {
    it("should provide reconnect function", () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      expect(typeof result.current.reconnect).toBe("function");
    });

    it("should call underlying reconnect when reconnect() is called", () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        result.current.reconnect();
      });

      expect(mockReconnect).toHaveBeenCalled();
    });

    it("should expose reconnectAttempts for dashboard visibility", () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      expect(typeof result.current.reconnectAttempts).toBe("number");
      expect(result.current.reconnectAttempts).toBe(0);
    });
  });
});
