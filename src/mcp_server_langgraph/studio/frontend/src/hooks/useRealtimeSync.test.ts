/**
 * useRealtimeSync Hook Tests
 *
 * TDD tests for real-time data synchronization using WebSocket.
 * Features:
 * - WebSocket connection management
 * - Automatic reconnection
 * - Message handling
 * - Connection status tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useRealtimeSync } from "./useRealtimeSync";

// Mock WebSocket class
class MockWebSocket {
  static instances: MockWebSocket[] = [];

  url: string;
  readyState: number = 0; // CONNECTING
  onopen: (() => void) | null = null;
  onclose: ((event: { code: number; reason: string }) => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    // Simulate connection delay
    setTimeout(() => {
      if (this.readyState === 0) {
        this.readyState = 1; // OPEN
        this.onopen?.();
      }
    }, 10);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = 3; // CLOSED
    this.onclose?.({ code: 1000, reason: "Normal closure" });
  });

  // Helper to simulate receiving a message
  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  // Helper to simulate an error
  simulateError(error: Error) {
    this.onerror?.(error as unknown as Event);
  }

  // Helper to simulate closing
  simulateClose(code: number, reason: string) {
    this.readyState = 3;
    this.onclose?.({ code, reason });
  }

  static clearInstances() {
    MockWebSocket.instances = [];
  }

  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;
}

describe("useRealtimeSync", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.clearInstances();
    vi.useFakeTimers();
    // Stub global WebSocket with our mock
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  describe("Connection", () => {
    it("should start with connecting status", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );
      expect(result.current.status).toBe("connecting");
    });

    it("should connect to WebSocket when mounted", () => {
      renderHook(() => useRealtimeSync({ url: "ws://localhost:8080" }));

      expect(MockWebSocket.instances.length).toBe(1);
      expect(MockWebSocket.instances[0].url).toBe("ws://localhost:8080");
    });

    it("should update status to connected when WebSocket opens", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      // Trigger the open event
      act(() => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.status).toBe("connected");
    });

    it("should update status to disconnected when WebSocket closes", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.status).toBe("connected");

      act(() => {
        MockWebSocket.instances[0].simulateClose(1000, "Normal");
      });

      expect(result.current.status).toBe("disconnected");
    });

    it("should close WebSocket on unmount", () => {
      const { unmount } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      unmount();

      expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
    });
  });

  describe("Messages", () => {
    it("should receive and process messages", () => {
      const onMessage = vi.fn();
      renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080", onMessage }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "update",
          data: "test",
        });
      });

      expect(onMessage).toHaveBeenCalledWith({ type: "update", data: "test" });
    });

    it("should send messages when connected", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.status).toBe("connected");

      act(() => {
        result.current.send({ type: "ping" });
      });

      expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
        JSON.stringify({ type: "ping" }),
      );
    });

    it("should queue messages when not connected", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      // Try to send before connected
      act(() => {
        result.current.send({ type: "ping" });
      });

      // Should not have sent yet
      expect(MockWebSocket.instances[0].send).not.toHaveBeenCalled();

      // Connect
      act(() => {
        vi.advanceTimersByTime(20);
      });

      // Message should be flushed after connection
      expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
        JSON.stringify({ type: "ping" }),
      );
    });

    it("should track last message time", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      const initialTime = result.current.lastMessageTime;

      act(() => {
        MockWebSocket.instances[0].simulateMessage({ type: "test" });
      });

      expect(result.current.lastMessageTime).not.toBe(initialTime);
    });
  });

  describe("Reconnection", () => {
    it("should attempt to reconnect on abnormal close", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://localhost:8080",
          reconnectInterval: 1000,
          maxReconnectAttempts: 3,
        }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      // Simulate abnormal close
      act(() => {
        MockWebSocket.instances[0].simulateClose(1006, "Abnormal");
      });

      expect(result.current.status).toBe("reconnecting");

      // Advance time to trigger reconnect
      act(() => {
        vi.advanceTimersByTime(1100);
      });

      // Should have created a new WebSocket
      expect(MockWebSocket.instances.length).toBe(2);
    });

    it("should not reconnect on normal close (code 1000)", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://localhost:8080",
          reconnectInterval: 1000,
        }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      // Simulate normal close
      act(() => {
        MockWebSocket.instances[0].simulateClose(1000, "Normal");
      });

      expect(result.current.status).toBe("disconnected");

      // Advance time
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      // Should NOT have created a new WebSocket
      expect(MockWebSocket.instances.length).toBe(1);
    });

    it("should stop reconnecting after max attempts", () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://localhost:8080",
          reconnectInterval: 100,
          maxReconnectAttempts: 2,
          onError,
        }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      // First disconnect (abnormal close)
      act(() => {
        MockWebSocket.instances[0].simulateClose(1006, "Error");
      });

      expect(result.current.reconnectAttempts).toBe(1);

      // First reconnect attempt - advance just enough for reconnect timeout, not for socket to open
      act(() => {
        vi.advanceTimersByTime(100);
      });

      // Instance 1 created, immediately close it before it can open
      act(() => {
        MockWebSocket.instances[1].simulateClose(1006, "Error");
      });

      expect(result.current.reconnectAttempts).toBe(2);

      // Second reconnect attempt
      act(() => {
        vi.advanceTimersByTime(100);
      });

      // Instance 2 created, close it - should not trigger another reconnect
      act(() => {
        MockWebSocket.instances[2].simulateClose(1006, "Error");
      });

      // No more reconnects should be attempted
      act(() => {
        vi.advanceTimersByTime(200);
      });

      // Should only have 3 instances (initial + 2 reconnects)
      expect(MockWebSocket.instances.length).toBe(3);
      expect(result.current.reconnectAttempts).toBe(2);
      expect(result.current.status).toBe("disconnected");
    });

    it("should reset reconnect counter on successful connection", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://localhost:8080",
          reconnectInterval: 100,
          maxReconnectAttempts: 3,
        }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      // First disconnect
      act(() => {
        MockWebSocket.instances[0].simulateClose(1006, "Error");
      });

      expect(result.current.reconnectAttempts).toBe(1);

      // Reconnect timeout + connection
      act(() => {
        vi.advanceTimersByTime(150);
      });

      // Connect the new socket
      act(() => {
        vi.advanceTimersByTime(20);
      });

      expect(result.current.status).toBe("connected");
      expect(result.current.reconnectAttempts).toBe(0);
    });
  });

  describe("Error Handling", () => {
    it("should call onError when WebSocket errors", () => {
      const onError = vi.fn();
      renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080", onError }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateError(
          new Error("Connection failed"),
        );
      });

      expect(onError).toHaveBeenCalled();
    });

    it("should update status to error on WebSocket error", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateError(
          new Error("Connection failed"),
        );
      });

      expect(result.current.status).toBe("error");
    });
  });

  describe("Manual Control", () => {
    it("should allow manual disconnect", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        result.current.disconnect();
      });

      expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
    });

    it("should allow manual reconnect", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost:8080" }),
      );

      act(() => {
        vi.advanceTimersByTime(20);
      });

      act(() => {
        MockWebSocket.instances[0].simulateClose(1000, "Normal");
      });

      expect(result.current.status).toBe("disconnected");

      act(() => {
        result.current.reconnect();
      });

      expect(MockWebSocket.instances.length).toBe(2);
    });
  });
});
