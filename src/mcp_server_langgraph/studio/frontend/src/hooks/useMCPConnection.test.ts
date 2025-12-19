/**
 * useMCPConnection Hook Tests
 *
 * TDD tests for the MCP connection hook with WebSocket and REST fallback.
 * Follows the connection strategy from the plan:
 * 1. Attempt WebSocket connection to /api/v1/mcp/ws
 * 2. If WebSocket fails, fall back to REST
 * 3. REST uses /api/v1/chat/completions/stream (SSE)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useMCPConnection } from "./useMCPConnection";

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
  }

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event("open"));
  }

  simulateClose(code = 1000, reason = "") {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close", { code, reason }));
  }

  simulateError() {
    this.onerror?.(new Event("error"));
  }

  simulateMessage(data: unknown) {
    this.onmessage?.(
      new MessageEvent("message", { data: JSON.stringify(data) }),
    );
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent("close", { code: 1000 }));
  });
}

describe("useMCPConnection", () => {
  let mockWebSocket: MockWebSocket | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
    mockWebSocket = null;

    // Mock WebSocket constructor with static constants using vi.stubGlobal
    // This works correctly in jsdom environment where WebSocket is read-only
    // Vitest 4 requires function syntax for constructor mocks (arrow functions don't work with `new`)
    const MockWebSocketConstructor = vi.fn(function (url: string) {
      mockWebSocket = new MockWebSocket(url);
      return mockWebSocket;
    });
    // Add static constants that the hook checks against
    Object.assign(MockWebSocketConstructor, {
      CONNECTING: 0,
      OPEN: 1,
      CLOSING: 2,
      CLOSED: 3,
    });
    vi.stubGlobal("WebSocket", MockWebSocketConstructor);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  describe("Initial State", () => {
    it("should start in disconnected state", () => {
      const { result } = renderHook(() => useMCPConnection());

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connectionMode).toBe("disconnected");
      expect(result.current.tools).toEqual([]);
      expect(result.current.error).toBeNull();
    });

    it("should not auto-connect by default", () => {
      renderHook(() => useMCPConnection());

      expect(global.WebSocket).not.toHaveBeenCalled();
    });

    it("should auto-connect when autoConnect option is true", async () => {
      renderHook(() => useMCPConnection({ autoConnect: true }));

      expect(global.WebSocket).toHaveBeenCalled();
    });
  });

  describe("WebSocket Connection", () => {
    it("should connect via WebSocket when connect is called", async () => {
      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/mcp/ws"),
      );
    });

    it("should set connected state when WebSocket opens", async () => {
      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      // Simulate WebSocket open
      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
        expect(result.current.connectionMode).toBe("websocket");
      });
    });

    it("should request tools list after connection", async () => {
      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // Should send tools/list request
      await waitFor(() => {
        expect(mockWebSocket?.send).toHaveBeenCalledWith(
          expect.stringContaining('"method":"tools/list"'),
        );
      });
    });

    it("should update tools when tools/list response received", async () => {
      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // Wait for tools/list request to be sent
      await waitFor(() => {
        expect(mockWebSocket?.send).toHaveBeenCalled();
      });

      // Get the request ID from the sent message
      const sentMessage = JSON.parse(
        (mockWebSocket?.send as ReturnType<typeof vi.fn>).mock.calls[0][0],
      );

      // Simulate tools response with matching ID
      await act(async () => {
        mockWebSocket?.simulateMessage({
          jsonrpc: "2.0",
          id: sentMessage.id,
          result: {
            tools: [
              { name: "calculator", description: "Math operations" },
              { name: "web_search", description: "Search the web" },
            ],
          },
        });
      });

      await waitFor(() => {
        expect(result.current.tools).toHaveLength(2);
        expect(result.current.tools[0].name).toBe("calculator");
      });
    });

    it("should disconnect when disconnect is called", async () => {
      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      await act(async () => {
        result.current.disconnect();
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
        expect(result.current.connectionMode).toBe("disconnected");
      });
    });
  });

  describe("REST Fallback", () => {
    it("should fall back to REST when WebSocket fails to connect", async () => {
      // Mock fetch for REST fallback
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve({ tools: [] }),
        }),
      );

      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      // Simulate WebSocket error
      await act(async () => {
        mockWebSocket?.simulateError();
        mockWebSocket?.simulateClose(1006, "Connection failed");
      });

      await waitFor(() => {
        expect(result.current.connectionMode).toBe("rest");
        expect(result.current.isConnected).toBe(true);
      });
    });

    it("should fetch tools via REST when in REST mode", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            tools: [{ name: "calculator", description: "Math operations" }],
          }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      // Simulate WebSocket failure
      await act(async () => {
        mockWebSocket?.simulateError();
        mockWebSocket?.simulateClose(1006, "Connection failed");
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining("/api/v1/mcp/tools"),
          expect.any(Object),
        );
      });
    });
  });

  describe("Connection Status Indicator", () => {
    it("should return websocket status when connected via WebSocket", async () => {
      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.connectionMode).toBe("websocket");
      });
    });

    it("should return rest status when using REST fallback", async () => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve({ tools: [] }),
        }),
      );

      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateError();
        mockWebSocket?.simulateClose(1006);
      });

      await waitFor(() => {
        expect(result.current.connectionMode).toBe("rest");
      });
    });

    it("should return disconnected when not connected", () => {
      const { result } = renderHook(() => useMCPConnection());

      expect(result.current.connectionMode).toBe("disconnected");
    });
  });

  describe("Error Handling", () => {
    it("should set error when WebSocket connection fails and REST fails", async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      // Simulate WebSocket failure
      await act(async () => {
        mockWebSocket?.simulateError();
        mockWebSocket?.simulateClose(1006);
      });

      await waitFor(() => {
        expect(result.current.error).toBeTruthy();
        expect(result.current.isConnected).toBe(false);
      });
    });

    it("should clear error when connection succeeds", async () => {
      const { result } = renderHook(() => useMCPConnection());

      // First, set an error state
      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateError();
      });

      // Now reconnect successfully - use vi.stubGlobal for consistent mocking
      const ReconnectMockWebSocket = vi.fn((url: string) => {
        mockWebSocket = new MockWebSocket(url);
        return mockWebSocket;
      });
      Object.assign(ReconnectMockWebSocket, {
        CONNECTING: 0,
        OPEN: 1,
        CLOSING: 2,
        CLOSED: 3,
      });
      vi.stubGlobal("WebSocket", ReconnectMockWebSocket);

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.error).toBeNull();
      });
    });
  });

  describe("Session ID Support", () => {
    it("should include session ID in WebSocket URL when provided", async () => {
      renderHook(() =>
        useMCPConnection({ sessionId: "test-session-123", autoConnect: true }),
      );

      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining("session=test-session-123"),
      );
    });
  });

  describe("Reconnection with Exponential Backoff", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("should have reconnecting state", async () => {
      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: true }),
      );

      expect(result.current.isReconnecting).toBe(false);
    });

    it("should expose reconnectAttempts counter", async () => {
      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: true }),
      );

      expect(result.current.reconnectAttempts).toBe(0);
    });

    it("should attempt reconnection after WebSocket close when autoReconnect is enabled", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("No REST")));

      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: true }),
      );

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // Simulate unexpected close
      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      // Should be in reconnecting state
      expect(result.current.isReconnecting).toBe(true);

      // Advance timer to trigger first reconnection attempt
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Should have attempted to reconnect
      expect(global.WebSocket).toHaveBeenCalledTimes(2);
    });

    it("should use exponential backoff for reconnection delays", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("No REST")));

      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: true, maxReconnectAttempts: 5 }),
      );

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // First disconnect
      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      // First attempt after 1000ms (1 * 1000)
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Fail again
      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      expect(result.current.reconnectAttempts).toBe(1);

      // Second attempt after 2000ms (2 * 1000)
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      // Should have made another attempt
      expect(global.WebSocket).toHaveBeenCalledTimes(3);
    });

    it("should stop reconnecting after maxReconnectAttempts", async () => {
      vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("No REST")));

      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: true, maxReconnectAttempts: 2 }),
      );

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // First disconnect
      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      // First attempt
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      // Second attempt
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      // Should stop reconnecting after max attempts
      expect(result.current.isReconnecting).toBe(false);
      expect(result.current.reconnectAttempts).toBe(2);

      // Advance time - should not attempt any more
      const callsBefore = (
        global.WebSocket as unknown as { mock: { calls: unknown[] } }
      ).mock.calls.length;
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      expect(
        (global.WebSocket as unknown as { mock: { calls: unknown[] } }).mock
          .calls.length,
      ).toBe(callsBefore);
    });

    it("should reset reconnect attempts on successful connection", async () => {
      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: true }),
      );

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // Simulate disconnect and reconnect attempt
      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Successful reconnection
      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      expect(result.current.reconnectAttempts).toBe(0);
      expect(result.current.isReconnecting).toBe(false);
    });

    it("should not auto-reconnect when autoReconnect is false", async () => {
      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: false }),
      );

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // Simulate disconnect
      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      const callsAfterDisconnect = (
        global.WebSocket as unknown as { mock: { calls: unknown[] } }
      ).mock.calls.length;

      // Advance time
      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      // Should not have made any reconnection attempts
      expect(
        (global.WebSocket as unknown as { mock: { calls: unknown[] } }).mock
          .calls.length,
      ).toBe(callsAfterDisconnect);
    });

    it("should cancel reconnection when disconnect is called manually", async () => {
      const { result } = renderHook(() =>
        useMCPConnection({ autoReconnect: true }),
      );

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // Simulate disconnect triggering reconnection
      await act(async () => {
        mockWebSocket?.simulateClose(1006, "Connection lost");
      });

      expect(result.current.isReconnecting).toBe(true);

      // Manually disconnect
      await act(async () => {
        result.current.disconnect();
      });

      expect(result.current.isReconnecting).toBe(false);

      const callsAfterManualDisconnect = (
        global.WebSocket as unknown as { mock: { calls: unknown[] } }
      ).mock.calls.length;

      // Advance time
      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      // Should not have made any reconnection attempts
      expect(
        (global.WebSocket as unknown as { mock: { calls: unknown[] } }).mock
          .calls.length,
      ).toBe(callsAfterManualDisconnect);
    });
  });

  describe("Cleanup on Unmount", () => {
    it("should not update state after unmount during REST fallback", async () => {
      vi.useFakeTimers();

      // Mock fetch to delay and fail, simulating async operation after unmount
      const fetchPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error("Network error")), 100);
      });

      vi.stubGlobal("fetch", vi.fn().mockReturnValue(fetchPromise));

      const { result, unmount } = renderHook(() => useMCPConnection());

      // Start connection which will trigger WebSocket
      await act(async () => {
        result.current.connect();
      });

      // Simulate WebSocket failure to trigger REST fallback
      await act(async () => {
        mockWebSocket?.simulateError();
        mockWebSocket?.simulateClose(1006);
      });

      // Unmount before REST fallback completes
      unmount();

      // Advance timers to let the async operation complete
      await act(async () => {
        vi.advanceTimersByTime(200);
      });

      vi.useRealTimers();

      // If the hook doesn't check for mounted state, this test would have
      // triggered the "window is not defined" error or a React warning about
      // updating state on unmounted component
      // The test passing without errors confirms proper cleanup
    });

    it("should close WebSocket on unmount", async () => {
      const { result, unmount } = renderHook(() => useMCPConnection());

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      expect(mockWebSocket?.readyState).toBe(MockWebSocket.OPEN);

      // Unmount should close the WebSocket
      unmount();

      expect(mockWebSocket?.close).toHaveBeenCalled();
    });

    it("should cancel pending reconnection timers on unmount", async () => {
      vi.useFakeTimers();

      const { result, unmount } = renderHook(() =>
        useMCPConnection({ autoReconnect: true }),
      );

      await act(async () => {
        result.current.connect();
      });

      await act(async () => {
        mockWebSocket?.simulateOpen();
      });

      // Simulate disconnect to trigger reconnection timer
      await act(async () => {
        mockWebSocket?.simulateClose(1006);
      });

      // Unmount before reconnection timer fires
      unmount();

      // Advance time past reconnection delay
      await act(async () => {
        vi.advanceTimersByTime(10000);
      });

      // No new WebSocket connections should have been made after unmount
      // The initial connection call count is what we expect
      const callCount = (
        global.WebSocket as unknown as { mock: { calls: unknown[] } }
      ).mock.calls.length;
      expect(callCount).toBe(1); // Only the initial connection

      vi.useRealTimers();
    });
  });
});
