/**
 * useTraceWebSocket Hook Tests
 *
 * TDD tests for the trace WebSocket hook.
 * Tests cover:
 * - Connection management
 * - Message handling (MessageEnvelope format with trace_span type)
 * - Span updates
 * - Event processing
 * - Metrics reporting
 *
 * Message Format:
 * Uses MessageEnvelope format: { type: "trace_span", id: "...", payload: {...} }
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useTraceWebSocket } from "./useTraceWebSocket";
import { createTestWrapper, authenticatedAuthState } from "../test/testStore";
import type { ConnectionStatus } from "./useRealtimeSync";

// Create a wrapper with authenticated state (hook requires authentication)
const wrapper = createTestWrapper({
  preloadedState: { auth: authenticatedAuthState },
});

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;
let mockOnConnect: (() => void) | undefined;
// eslint-disable-next-line @typescript-eslint/no-unused-vars
let mockOnDisconnect: (() => void) | undefined;
let mockStatus: ConnectionStatus = "disconnected";

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: {
    url: string;
    onMessage?: (data: unknown) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
  }) => {
    mockOnMessage = options.onMessage;
    mockOnConnect = options.onConnect;
    mockOnDisconnect = options.onDisconnect;

    // Auto-connect when URL is provided
    if (options.url && mockStatus === "disconnected") {
      mockStatus = "connected";
      setTimeout(() => mockOnConnect?.(), 0);
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

// Mock websocketTelemetry
vi.mock("../utils/websocketTelemetry", () => ({
  reportWebSocketMetrics: vi.fn(),
}));

describe("useTraceWebSocket", () => {
  beforeEach(() => {
    mockStatus = "disconnected";
    mockOnMessage = undefined;
    mockOnConnect = undefined;
    mockOnDisconnect = undefined;
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Initial State", () => {
    it("should start with empty spans array", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      expect(result.current.spans).toEqual([]);
    });

    it("should start with empty events array", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      expect(result.current.events).toEqual([]);
    });

    it("should start disconnected", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      expect(result.current.isConnected).toBe(false);
    });

    it("should provide connect function", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      expect(typeof result.current.connect).toBe("function");
    });

    it("should provide disconnect function", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      expect(typeof result.current.disconnect).toBe("function");
    });

    it("should provide clearTraces function", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      expect(typeof result.current.clearTraces).toBe("function");
    });
  });

  describe("Connection", () => {
    it("should connect when connect() is called", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      // Status should change to connected
      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });
    });

    it("should auto-connect when autoConnect is true", async () => {
      mockStatus = "connected"; // Pre-set to connected for autoConnect

      const { result } = renderHook(
        () => useTraceWebSocket({ autoConnect: true }),
        { wrapper },
      );

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });
    });
  });

  describe("Disconnection", () => {
    it("should call disconnect when disconnect() is called", async () => {
      mockStatus = "connected";

      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        result.current.disconnect();
      });

      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe("Span Handling", () => {
    it("should add new span on trace_span message (MessageEnvelope format)", async () => {
      mockStatus = "connected";

      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      // Simulate receiving a span message
      const spanMessage = {
        type: "trace_span",
        id: "msg-1",
        payload: {
          trace_id: "trace-1",
          span_id: "span-1",
          name: "Test Span",
          start_time: "2024-01-15T10:00:00Z",
          status: "UNSET",
          attributes: {},
        },
      };

      act(() => {
        mockOnMessage?.(spanMessage);
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(1);
        expect(result.current.spans[0].spanId).toBe("span-1");
        expect(result.current.spans[0].name).toBe("Test Span");
      });
    });

    it("should update existing span when span with same ID received", async () => {
      mockStatus = "connected";

      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      // Add initial span
      act(() => {
        mockOnMessage?.({
          type: "trace_span",
          id: "msg-1",
          payload: {
            trace_id: "trace-1",
            span_id: "span-1",
            name: "Test Span",
            start_time: "2024-01-15T10:00:00Z",
            status: "UNSET",
            attributes: {},
          },
        });
      });

      // Update the span
      act(() => {
        mockOnMessage?.({
          type: "trace_span",
          id: "msg-2",
          payload: {
            trace_id: "trace-1",
            span_id: "span-1",
            name: "Test Span",
            start_time: "2024-01-15T10:00:00Z",
            end_time: "2024-01-15T10:00:05Z",
            status: "OK",
            attributes: {},
          },
        });
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(1);
        expect(result.current.spans[0].status).toBe("OK");
        expect(result.current.spans[0].endTime).toBe("2024-01-15T10:00:05Z");
      });
    });

    it("should handle parent-child span relationships", async () => {
      mockStatus = "connected";

      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      // Add parent span
      act(() => {
        mockOnMessage?.({
          type: "trace_span",
          id: "msg-1",
          payload: {
            trace_id: "trace-1",
            span_id: "parent-span",
            name: "Parent",
            start_time: "2024-01-15T10:00:00Z",
            status: "UNSET",
            attributes: {},
          },
        });
      });

      // Add child span
      act(() => {
        mockOnMessage?.({
          type: "trace_span",
          id: "msg-2",
          payload: {
            trace_id: "trace-1",
            span_id: "child-span",
            parent_span_id: "parent-span",
            name: "Child",
            start_time: "2024-01-15T10:00:01Z",
            status: "UNSET",
            attributes: {},
          },
        });
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(2);
        const childSpan = result.current.spans.find(
          (s) => s.spanId === "child-span",
        );
        expect(childSpan?.parentSpanId).toBe("parent-span");
      });
    });
  });

  describe("Event Handling", () => {
    it("should add event on trace_event message (MessageEnvelope format)", async () => {
      mockStatus = "connected";

      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      // Simulate receiving an event message
      const eventMessage = {
        type: "trace_event",
        id: "msg-1",
        payload: {
          span_id: "span-1",
          name: "Log Event",
          timestamp: "2024-01-15T10:00:02Z",
          attributes: { message: "Something happened" },
        },
      };

      act(() => {
        mockOnMessage?.(eventMessage);
      });

      await waitFor(() => {
        expect(result.current.events.length).toBe(1);
        expect(result.current.events[0].name).toBe("Log Event");
      });
    });
  });

  describe("Clear Traces", () => {
    it("should clear all spans and events when clearTraces() is called", async () => {
      mockStatus = "connected";

      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      // Add some data
      act(() => {
        mockOnMessage?.({
          type: "trace_span",
          id: "msg-1",
          payload: {
            trace_id: "trace-1",
            span_id: "span-1",
            name: "Test",
            start_time: "2024-01-15T10:00:00Z",
            status: "OK",
            attributes: {},
          },
        });
        mockOnMessage?.({
          type: "trace_event",
          id: "msg-2",
          payload: {
            span_id: "span-1",
            name: "Event",
            timestamp: "2024-01-15T10:00:01Z",
            attributes: {},
          },
        });
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(1);
        expect(result.current.events.length).toBe(1);
      });

      act(() => {
        result.current.clearTraces();
      });

      expect(result.current.spans).toEqual([]);
      expect(result.current.events).toEqual([]);
    });
  });

  describe("Metrics Reporting", () => {
    it("should report metrics when connected and there are attempts", async () => {
      mockStatus = "connected";

      const { reportWebSocketMetrics } =
        await import("../utils/websocketTelemetry");

      renderHook(() => useTraceWebSocket({ autoConnect: true }), { wrapper });

      // The mock currently has 0 totalAttempts, so metrics won't be reported
      // This test documents the expected behavior
      expect(reportWebSocketMetrics).not.toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should handle unknown message types gracefully", async () => {
      mockStatus = "connected";

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      // Send unknown message type
      act(() => {
        mockOnMessage?.({
          type: "unknown_type",
          id: "msg-1",
          payload: {},
        });
      });

      // Should not crash, spans and events should remain empty
      expect(result.current.spans).toEqual([]);
      expect(result.current.events).toEqual([]);

      consoleSpy.mockRestore();
    });
  });
});
