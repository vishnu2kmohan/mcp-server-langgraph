/**
 * useConnectionHealthWebSocket Hook Tests
 *
 * Tests for connection health monitoring WebSocket hook following TDD.
 * RED phase: Write failing tests first.
 */

import { renderHook, act, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  useConnectionHealthWebSocket,
  type ConnectionHealth,
} from "./useConnectionHealthWebSocket";

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;
let mockOnConnect: (() => void) | undefined;
let mockOnDisconnect: (() => void) | undefined;
let mockStatus = "connected" as const;

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn((options) => {
    mockOnMessage = options.onMessage;
    mockOnConnect = options.onConnect;
    mockOnDisconnect = options.onDisconnect;
    return {
      status: mockStatus,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
    };
  }),
}));

// Mock auth store hooks and selectors
vi.mock("../store/hooks", () => ({
  useAppSelector: vi.fn(() => true), // isAuthenticated = true
  useAppDispatch: vi.fn(() => vi.fn()),
}));

// Mock getAuthToken and STORAGE_KEYS
vi.mock("../utils/storage", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../utils/storage")>();
  return {
    ...actual,
    getAuthToken: vi.fn(() => "mock-test-token"),
  };
});

describe("useConnectionHealthWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = "connected";
    mockOnMessage = undefined;
    mockOnConnect = undefined;
    mockOnDisconnect = undefined;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("connection management", () => {
    it("should return status from useRealtimeSync", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());
      expect(result.current.status).toBe("connected");
    });

    it("should have empty connections initially", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());
      expect(result.current.connections).toEqual([]);
    });

    it("should expose disconnect and reconnect functions", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());
      expect(typeof result.current.disconnect).toBe("function");
      expect(typeof result.current.reconnect).toBe("function");
    });

    it("should call disconnect when disconnect is called", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());
      result.current.disconnect();
      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should call reconnect when reconnect is called", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());
      result.current.reconnect();
      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("message handling", () => {
    it("should update connections when connection_status message is received", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      const connections: ConnectionHealth[] = [
        {
          id: "conn-1",
          name: "Test Connection",
          url: "http://localhost:3000",
          status: "connected",
          auth_type: "api_key",
          tool_count: 5,
          resource_count: 3,
          prompt_count: 2,
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "connection_status", connections });
      });

      expect(result.current.connections).toEqual(connections);
    });

    it("should update specific connection when connection_update message is received", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      // Set initial connections
      const initialConnections: ConnectionHealth[] = [
        {
          id: "conn-1",
          name: "Test Connection",
          url: "http://localhost:3000",
          status: "connected",
          auth_type: "api_key",
          tool_count: 5,
          resource_count: 3,
          prompt_count: 2,
        },
      ];

      act(() => {
        mockOnMessage?.({
          type: "connection_status",
          connections: initialConnections,
        });
      });

      // Update the connection
      const updatedConnection: ConnectionHealth = {
        ...initialConnections[0],
        status: "disconnected",
        last_error: "Connection timeout",
      };

      act(() => {
        mockOnMessage?.({
          type: "connection_update",
          connection: updatedConnection,
        });
      });

      expect(result.current.connections[0].status).toBe("disconnected");
      expect(result.current.connections[0].last_error).toBe(
        "Connection timeout",
      );
    });

    it("should add new connection when update for unknown connection is received", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      const newConnection: ConnectionHealth = {
        id: "conn-new",
        name: "New Connection",
        url: "http://example.com",
        status: "connecting",
        auth_type: "oauth2",
        tool_count: 0,
        resource_count: 0,
        prompt_count: 0,
      };

      act(() => {
        mockOnMessage?.({
          type: "connection_update",
          connection: newConnection,
        });
      });

      expect(result.current.connections).toContainEqual(newConnection);
    });

    it("should handle pong message", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        mockOnMessage?.({ type: "pong", timestamp: "2025-01-15T10:30:00Z" });
      });

      expect(result.current.lastPong).toBe("2025-01-15T10:30:00Z");
    });

    it("should handle error message", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        mockOnMessage?.({ type: "error", message: "Connection not found" });
      });

      expect(result.current.error).toBe("Connection not found");
    });

    it("should handle subscribed acknowledgment", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        mockOnMessage?.({ type: "subscribed", connection_id: "conn-1" });
      });

      expect(result.current.subscribedConnections.has("conn-1")).toBe(true);
    });

    it("should handle unsubscribed acknowledgment", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      // First subscribe
      act(() => {
        mockOnMessage?.({ type: "subscribed", connection_id: "conn-1" });
      });

      // Then unsubscribe
      act(() => {
        mockOnMessage?.({ type: "unsubscribed", connection_id: "conn-1" });
      });

      expect(result.current.subscribedConnections.has("conn-1")).toBe(false);
    });

    it("should handle health_check_started message", () => {
      const onHealthCheckStarted = vi.fn();
      renderHook(() => useConnectionHealthWebSocket({ onHealthCheckStarted }));

      act(() => {
        mockOnMessage?.({
          type: "health_check_started",
          connection_id: "conn-1",
          message: "Health check initiated",
        });
      });

      expect(onHealthCheckStarted).toHaveBeenCalledWith("conn-1");
    });
  });

  describe("commands", () => {
    it("should send ping command", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        result.current.sendPing();
      });

      expect(mockSend).toHaveBeenCalledWith({ type: "ping" });
    });

    it("should send refresh command", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        result.current.refresh();
      });

      expect(mockSend).toHaveBeenCalledWith({ type: "refresh" });
    });

    it("should send subscribe command", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        result.current.subscribe("conn-123");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        connection_id: "conn-123",
      });
    });

    it("should send unsubscribe command", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        result.current.unsubscribe("conn-123");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "unsubscribe",
        connection_id: "conn-123",
      });
    });

    it("should send check_health command", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      act(() => {
        result.current.checkHealth("conn-123");
      });

      expect(mockSend).toHaveBeenCalledWith({
        type: "check_health",
        connection_id: "conn-123",
      });
    });
  });

  describe("callbacks", () => {
    it("should call onConnectionUpdate callback when connection updates", () => {
      const onConnectionUpdate = vi.fn();
      renderHook(() => useConnectionHealthWebSocket({ onConnectionUpdate }));

      const connection: ConnectionHealth = {
        id: "conn-1",
        name: "Test",
        url: "http://test.com",
        status: "error",
        auth_type: "none",
        tool_count: 0,
        resource_count: 0,
        prompt_count: 0,
        last_error: "Timeout",
      };

      act(() => {
        mockOnMessage?.({ type: "connection_update", connection });
      });

      expect(onConnectionUpdate).toHaveBeenCalledWith(connection);
    });

    it("should call onConnectionsLoaded callback when initial connections received", () => {
      const onConnectionsLoaded = vi.fn();
      renderHook(() => useConnectionHealthWebSocket({ onConnectionsLoaded }));

      const connections: ConnectionHealth[] = [
        {
          id: "conn-1",
          name: "Test",
          url: "http://test.com",
          status: "connected",
          auth_type: "api_key",
          tool_count: 5,
          resource_count: 3,
          prompt_count: 2,
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "connection_status", connections });
      });

      expect(onConnectionsLoaded).toHaveBeenCalledWith(connections);
    });
  });

  describe("URL configuration", () => {
    it("should use default URL if not provided", async () => {
      renderHook(() => useConnectionHealthWebSocket());

      const { useRealtimeSync } = await import("./useRealtimeSync");
      // ADR-0068: Consolidated WebSocket URLs under /api/v1/ws/*
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: expect.stringContaining("/api/v1/ws/connections/health"),
        }),
      );
    });

    it("should use custom URL if provided", async () => {
      renderHook(() =>
        useConnectionHealthWebSocket({ url: "ws://custom:8000/health" }),
      );

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: "ws://custom:8000/health",
        }),
      );
    });
  });

  describe("exponential backoff configuration", () => {
    it("should configure useRealtimeSync with exponential backoff", async () => {
      renderHook(() => useConnectionHealthWebSocket());

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          exponentialBackoff: true,
          reconnectInterval: 1000,
          maxDelayMs: 30000,
          maxReconnectAttempts: 10,
        }),
      );
    });
  });

  describe("subscription restoration", () => {
    it("should restore subscriptions on reconnect", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      // Subscribe to connections via server acknowledgment
      act(() => {
        mockOnMessage?.({ type: "subscribed", connection_id: "conn-1" });
        mockOnMessage?.({ type: "subscribed", connection_id: "conn-2" });
      });

      expect(result.current.subscribedConnections.size).toBe(2);

      // Clear mock calls
      mockSend.mockClear();

      // Simulate reconnection
      act(() => {
        mockOnConnect?.();
      });

      // Should have re-subscribed to both connections
      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        connection_id: "conn-1",
      });
      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        connection_id: "conn-2",
      });
    });

    it("should only restore active subscriptions after reconnect", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      // Subscribe via server acknowledgment
      act(() => {
        mockOnMessage?.({ type: "subscribed", connection_id: "conn-1" });
        mockOnMessage?.({ type: "subscribed", connection_id: "conn-2" });
      });

      // Unsubscribe from conn-1 via server acknowledgment
      act(() => {
        mockOnMessage?.({ type: "unsubscribed", connection_id: "conn-1" });
      });

      expect(result.current.subscribedConnections.size).toBe(1);

      // Clear mock calls
      mockSend.mockClear();

      // Simulate reconnection
      act(() => {
        mockOnConnect?.();
      });

      // Should only re-subscribe to conn-2
      expect(mockSend).toHaveBeenCalledWith({
        type: "subscribe",
        connection_id: "conn-2",
      });
      expect(mockSend).not.toHaveBeenCalledWith(
        expect.objectContaining({ connection_id: "conn-1" }),
      );
    });
  });

  describe("connection lifecycle", () => {
    it("should clear error on connect", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      // First set an error
      act(() => {
        mockOnMessage?.({ type: "error", message: "Connection error" });
      });

      expect(result.current.error).toBe("Connection error");

      // Simulate reconnection
      act(() => {
        mockOnConnect?.();
      });

      expect(result.current.error).toBeNull();
    });

    it("should keep connections on disconnect for resumption", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      const connections: ConnectionHealth[] = [
        {
          id: "conn-1",
          name: "Test",
          url: "http://test.com",
          status: "connected",
          auth_type: "api_key",
          tool_count: 5,
          resource_count: 3,
          prompt_count: 2,
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "connection_status", connections });
      });

      // Simulate disconnect
      act(() => {
        mockOnDisconnect?.();
      });

      // Connections should be preserved
      expect(result.current.connections).toEqual(connections);
    });
  });

  describe("derived state", () => {
    it("should compute summary statistics", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      const connections: ConnectionHealth[] = [
        {
          id: "1",
          name: "A",
          url: "",
          status: "connected",
          auth_type: "",
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
        },
        {
          id: "2",
          name: "B",
          url: "",
          status: "connected",
          auth_type: "",
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
        },
        {
          id: "3",
          name: "C",
          url: "",
          status: "disconnected",
          auth_type: "",
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
        },
        {
          id: "4",
          name: "D",
          url: "",
          status: "error",
          auth_type: "",
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "connection_status", connections });
      });

      expect(result.current.summary.total).toBe(4);
      expect(result.current.summary.connected).toBe(2);
      expect(result.current.summary.disconnected).toBe(1);
      expect(result.current.summary.error).toBe(1);
    });

    it("should get connection by ID", () => {
      const { result } = renderHook(() => useConnectionHealthWebSocket());

      const connections: ConnectionHealth[] = [
        {
          id: "conn-1",
          name: "First",
          url: "",
          status: "connected",
          auth_type: "",
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
        },
        {
          id: "conn-2",
          name: "Second",
          url: "",
          status: "connected",
          auth_type: "",
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
        },
      ];

      act(() => {
        mockOnMessage?.({ type: "connection_status", connections });
      });

      const found = result.current.getConnection("conn-1");
      expect(found?.name).toBe("First");

      const notFound = result.current.getConnection("nonexistent");
      expect(notFound).toBeUndefined();
    });
  });
});
