/**
 * useConnectionsRealtimeWebSocket Hook Tests
 *
 * TDD tests for real-time connection status updates WebSocket hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useConnectionsRealtimeWebSocket } from "./useConnectionsRealtimeWebSocket";

// Type for test WebSocket handlers
interface TestWsHandlers {
  onMessage: (data: unknown) => void;
  onConnect: () => void;
}

// Module-scoped handler storage for tests
let testWsHandlers: TestWsHandlers | null = null;

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn(({ onMessage, onConnect }) => {
    // Store handlers for test access
    testWsHandlers = { onMessage, onConnect };
    return {
      status: "connected" as const,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
    };
  }),
}));

describe("useConnectionsRealtimeWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    testWsHandlers = null;
  });

  afterEach(() => {
    testWsHandlers = null;
    cleanup();
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should initialize with default state", () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      expect(result.current.status).toBe("connected");
      expect(result.current.connections).toEqual([]);
      expect(result.current.subscribedConnections).toEqual(new Set());
      expect(result.current.subscribedAll).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should use default WebSocket URL", async () => {
      renderHook(() => useConnectionsRealtimeWebSocket());

      const { useRealtimeSync } = vi.mocked(await import("./useRealtimeSync"));
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("/api/v1/ws/connections/realtime"),
        }),
      );
    });
  });

  describe("connection list", () => {
    it("should handle connection_list message", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());
      const handlers = testWsHandlers;

      const connections = [
        { id: "conn-1", name: "MCP Server 1", status: "connected" },
        { id: "conn-2", name: "MCP Server 2", status: "disconnected" },
      ];

      act(() => {
        handlers.onMessage({
          type: "connection_list",
          connections,
        });
      });

      expect(result.current.connections).toEqual(connections);
    });
  });

  describe("subscription", () => {
    it("should subscribe to specific connection", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      act(() => {
        result.current.subscribeConnection("conn-1");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        connection_id: "conn-1",
      });
    });

    it("should track subscribed connections", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());
      const handlers = testWsHandlers;

      act(() => {
        result.current.subscribeConnection("conn-1");
      });

      // Simulate server confirmation
      act(() => {
        handlers.onMessage({
          type: "connection_status",
          payload: {
            connection: { id: "conn-1", status: "connected" },
          },
        });
      });

      expect(result.current.subscribedConnections.has("conn-1")).toBe(true);
    });

    it("should subscribe to all connections", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      act(() => {
        result.current.subscribeAll();
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe_all",
      });
    });

    it("should update subscribedAll on confirmation", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "subscribed_all",
          payload: { subscribed: true },
        });
      });

      expect(result.current.subscribedAll).toBe(true);
    });

    it("should unsubscribe from connection", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      act(() => {
        result.current.subscribeConnection("conn-1");
        result.current.unsubscribeConnection("conn-1");
      });

      expect(mockSend).toHaveBeenLastCalledWith({
        type: "unsubscribe",
        connection_id: "conn-1",
      });
    });
  });

  describe("connection updates", () => {
    it("should handle connection_updated message", async () => {
      const onConnectionUpdate = vi.fn();
      const { result } = renderHook(() =>
        useConnectionsRealtimeWebSocket({ onConnectionUpdate }),
      );
      const handlers = testWsHandlers;

      // Set initial connections
      act(() => {
        handlers.onMessage({
          type: "connection_list",
          connections: [
            { id: "conn-1", name: "MCP Server 1", status: "connected" },
          ],
        });
      });

      // Receive update
      act(() => {
        handlers.onMessage({
          type: "connection_updated",
          payload: {
            connection: {
              id: "conn-1",
              name: "MCP Server 1",
              status: "disconnected",
            },
          },
        });
      });

      expect(onConnectionUpdate).toHaveBeenCalledWith({
        id: "conn-1",
        name: "MCP Server 1",
        status: "disconnected",
      });

      // Connection list should be updated
      expect(result.current.connections[0].status).toBe("disconnected");
    });

    it("should handle connection_status message", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "connection_status",
          payload: {
            connection: { id: "conn-1", status: "connected" },
          },
        });
      });

      // Should be tracked as subscribed
      expect(result.current.subscribedConnections.has("conn-1")).toBe(true);
    });
  });

  describe("health check", () => {
    it("should request health check", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      act(() => {
        result.current.requestHealthCheck("conn-1");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "request_health_check",
        connection_id: "conn-1",
      });
    });

    it("should handle health_check_result message", async () => {
      const onHealthCheckResult = vi.fn();
      renderHook(() =>
        useConnectionsRealtimeWebSocket({ onHealthCheckResult }),
      );
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "health_check_result",
          payload: {
            connection_id: "conn-1",
            healthy: true,
            latency_ms: 45,
          },
        });
      });

      expect(onHealthCheckResult).toHaveBeenCalledWith({
        connection_id: "conn-1",
        healthy: true,
        latency_ms: 45,
      });
    });
  });

  describe("error handling", () => {
    it("should handle error messages", async () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useConnectionsRealtimeWebSocket({ onError }),
      );
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "error",
          payload: {
            code: "connection_not_found",
            message: "Connection conn-1 not found",
          },
        });
      });

      expect(result.current.error).toBe("Connection conn-1 not found");
      expect(onError).toHaveBeenCalledWith("Connection conn-1 not found");
    });
  });

  describe("utility methods", () => {
    it("should get connection by ID", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());
      const handlers = testWsHandlers;

      act(() => {
        handlers.onMessage({
          type: "connection_list",
          connections: [
            { id: "conn-1", name: "MCP Server 1", status: "connected" },
            { id: "conn-2", name: "MCP Server 2", status: "disconnected" },
          ],
        });
      });

      const conn = result.current.getConnection("conn-1");
      expect(conn?.name).toBe("MCP Server 1");
    });

    it("should return undefined for unknown connection", () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      const conn = result.current.getConnection("unknown");
      expect(conn).toBeUndefined();
    });

    it("should provide disconnect and reconnect methods", () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      expect(typeof result.current.disconnect).toBe("function");
      expect(typeof result.current.reconnect).toBe("function");

      act(() => {
        result.current.disconnect();
      });

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should refresh connection list", async () => {
      const { result } = renderHook(() => useConnectionsRealtimeWebSocket());

      act(() => {
        result.current.refresh();
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "refresh",
      });
    });
  });
});
