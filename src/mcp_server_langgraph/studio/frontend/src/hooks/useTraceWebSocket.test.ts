/**
 * useTraceWebSocket Hook Tests
 *
 * TDD tests for the trace WebSocket hook.
 * Tests cover:
 * - Connection management
 * - Message handling
 * - Span updates
 * - Event processing
 * - Reconnection logic
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useTraceWebSocket } from "./useTraceWebSocket";
import { createTestWrapper, authenticatedAuthState } from "../test/testStore";

// Create a wrapper with authenticated state (hook requires authentication)
const wrapper = createTestWrapper({
  preloadedState: { auth: authenticatedAuthState },
});

// Mock WebSocket class
let mockWebSocketInstances: MockWebSocket[] = [];

class MockWebSocket {
  url: string;
  readyState: number = 0; // CONNECTING

  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    mockWebSocketInstances.push(this);
  }

  send(_data: string): void {
    // Mock send
  }

  close(): void {
    this.readyState = 3; // CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent("close"));
    }
  }

  // Helper to simulate receiving a message
  simulateMessage(data: object): void {
    if (this.onmessage) {
      this.onmessage(
        new MessageEvent("message", { data: JSON.stringify(data) }),
      );
    }
  }

  // Helper to simulate connection open
  simulateOpen(): void {
    this.readyState = 1; // OPEN
    if (this.onopen) {
      this.onopen(new Event("open"));
    }
  }

  // Helper to simulate error
  simulateError(): void {
    if (this.onerror) {
      this.onerror(new Event("error"));
    }
  }

  // Static constants
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
}

describe("useTraceWebSocket", () => {
  beforeEach(() => {
    mockWebSocketInstances = [];

    // Use vi.stubGlobal for consistent mocking in jsdom environment
    vi.stubGlobal("WebSocket", MockWebSocket);

    // Mock window.location
    Object.defineProperty(window, "location", {
      value: {
        protocol: "http:",
        host: "localhost:3000",
      },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    // Restore all globals
    vi.unstubAllGlobals();
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
    it("should connect when connect() is called", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      expect(mockWebSocketInstances.length).toBe(1);
    });

    it("should use default URL when not provided", () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];
      expect(ws.url).toContain("/api/v1/ws/mcp");
    });

    it("should use custom URL when provided", () => {
      const { result } = renderHook(
        () => useTraceWebSocket({ url: "/custom/ws" }),
        { wrapper },
      );

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];
      expect(ws.url).toContain("/custom/ws");
    });

    it("should include session ID in URL when provided", () => {
      const { result } = renderHook(
        () => useTraceWebSocket({ sessionId: "test-session" }),
        { wrapper },
      );

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];
      expect(ws.url).toContain("test-session");
    });

    it("should set isConnected to true on connection open", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });
    });

    it("should auto-connect when autoConnect is true", () => {
      renderHook(() => useTraceWebSocket({ autoConnect: true }), {
        wrapper,
      });

      expect(mockWebSocketInstances.length).toBe(1);
    });
  });

  describe("Disconnection", () => {
    it("should disconnect when disconnect() is called", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        result.current.disconnect();
      });

      expect(ws.readyState).toBe(3); // CLOSED
    });

    it("should set isConnected to false on disconnect", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        result.current.disconnect();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
      });
    });
  });

  describe("Span Handling", () => {
    it("should add new span on $/trace/span message", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      const spanMessage = {
        method: "$/trace/span",
        params: {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test Span",
          startTime: "2024-01-15T10:00:00Z",
          status: "UNSET",
          attributes: {},
        },
      };

      act(() => {
        ws.simulateMessage(spanMessage);
      });

      await waitFor(() => {
        expect(result.current.spans.length).toBe(1);
        expect(result.current.spans[0].spanId).toBe("span-1");
        expect(result.current.spans[0].name).toBe("Test Span");
      });
    });

    it("should update existing span when span with same ID received", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Add initial span
      act(() => {
        ws.simulateMessage({
          method: "$/trace/span",
          params: {
            traceId: "trace-1",
            spanId: "span-1",
            name: "Test Span",
            startTime: "2024-01-15T10:00:00Z",
            status: "UNSET",
            attributes: {},
          },
        });
      });

      // Update the span
      act(() => {
        ws.simulateMessage({
          method: "$/trace/span",
          params: {
            traceId: "trace-1",
            spanId: "span-1",
            name: "Test Span",
            startTime: "2024-01-15T10:00:00Z",
            endTime: "2024-01-15T10:00:05Z",
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
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Add parent span
      act(() => {
        ws.simulateMessage({
          method: "$/trace/span",
          params: {
            traceId: "trace-1",
            spanId: "parent-span",
            name: "Parent",
            startTime: "2024-01-15T10:00:00Z",
            status: "UNSET",
            attributes: {},
          },
        });
      });

      // Add child span
      act(() => {
        ws.simulateMessage({
          method: "$/trace/span",
          params: {
            traceId: "trace-1",
            spanId: "child-span",
            parentSpanId: "parent-span",
            name: "Child",
            startTime: "2024-01-15T10:00:01Z",
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
    it("should add event on $/trace/event message", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      const eventMessage = {
        method: "$/trace/event",
        params: {
          spanId: "span-1",
          name: "Log Event",
          timestamp: "2024-01-15T10:00:02Z",
          attributes: { message: "Something happened" },
        },
      };

      act(() => {
        ws.simulateMessage(eventMessage);
      });

      await waitFor(() => {
        expect(result.current.events.length).toBe(1);
        expect(result.current.events[0].name).toBe("Log Event");
      });
    });
  });

  describe("Clear Traces", () => {
    it("should clear all spans and events when clearTraces() is called", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Add some data
      act(() => {
        ws.simulateMessage({
          method: "$/trace/span",
          params: {
            traceId: "trace-1",
            spanId: "span-1",
            name: "Test",
            startTime: "2024-01-15T10:00:00Z",
            status: "OK",
            attributes: {},
          },
        });
        ws.simulateMessage({
          method: "$/trace/event",
          params: {
            spanId: "span-1",
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

  describe("Error Handling", () => {
    it("should set isConnected to false on error", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        ws.simulateError();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
      });

      consoleSpy.mockRestore();
    });

    it("should handle malformed JSON messages gracefully", async () => {
      const { result } = renderHook(() => useTraceWebSocket(), { wrapper });

      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      act(() => {
        result.current.connect();
      });

      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      // Send malformed JSON
      act(() => {
        if (ws.onmessage) {
          ws.onmessage(new MessageEvent("message", { data: "not valid json" }));
        }
      });

      // Should not crash, just log error
      expect(consoleSpy).toHaveBeenCalled();
      expect(result.current.spans).toEqual([]);

      consoleSpy.mockRestore();
    });
  });
});
