/**
 * useRealtimeSync Hook Tests
 *
 * Tests for WebSocket real-time sync hook including:
 * - Connection establishment
 * - Reconnection logic
 * - Message handling
 * - Error states
 * - Manual disconnect/reconnect
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useRealtimeSync } from "./useRealtimeSync";

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateRawMessage(data: string) {
    this.onmessage?.({ data });
  }

  simulateClose(code = 1006) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({ code });
  }

  simulateError(event: unknown) {
    this.onerror?.(event);
  }

  static instances: MockWebSocket[] = [];
  static reset() {
    MockWebSocket.instances = [];
  }
  static getLastInstance(): MockWebSocket | undefined {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1];
  }
}

describe("useRealtimeSync", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.reset();
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  describe("Connection Establishment", () => {
    it("should start in connecting state when url is provided", () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );
      expect(result.current.status).toBe("connecting");
    });

    it("should start in disconnected state when url is empty", () => {
      const { result } = renderHook(() => useRealtimeSync({ url: "" }));
      expect(result.current.status).toBe("disconnected");
    });

    it("should transition to connected when WebSocket opens", async () => {
      const onConnect = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com", onConnect }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      expect(result.current.status).toBe("connected");
      expect(onConnect).toHaveBeenCalled();
    });

    it("should reset reconnect attempts on successful connection", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      expect(result.current.reconnectAttempts).toBe(0);
    });
  });

  describe("Message Handling", () => {
    it("should call onMessage with parsed JSON data", async () => {
      const onMessage = vi.fn();
      renderHook(() => useRealtimeSync({ url: "ws://test.com", onMessage }));

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        ws?.simulateMessage({ type: "test", data: 123 });
      });

      expect(onMessage).toHaveBeenCalledWith({ type: "test", data: 123 });
    });

    it("should handle non-JSON messages", async () => {
      const onMessage = vi.fn();
      renderHook(() => useRealtimeSync({ url: "ws://test.com", onMessage }));

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        ws?.simulateRawMessage("plain text message");
      });

      expect(onMessage).toHaveBeenCalledWith("plain text message");
    });

    it("should update lastMessageTime on message receipt", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      expect(result.current.lastMessageTime).toBeNull();

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      vi.setSystemTime(new Date("2024-01-01T12:00:00Z"));

      act(() => {
        ws?.simulateMessage({ type: "test" });
      });

      expect(result.current.lastMessageTime).toBe(Date.now());
    });
  });

  describe("Error Handling", () => {
    it("should set status to error on WebSocket error", async () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com", onError }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateError(new Error("Connection failed"));
      });

      expect(result.current.status).toBe("error");
      expect(onError).toHaveBeenCalled();
    });
  });

  describe("Reconnection Logic", () => {
    it("should attempt reconnection on abnormal close", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 1000,
          maxReconnectAttempts: 3,
        }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        ws?.simulateClose(1006);
      });

      expect(result.current.status).toBe("reconnecting");
      expect(result.current.reconnectAttempts).toBe(1);
    });

    it("should not reconnect on normal close (code 1000)", async () => {
      const onDisconnect = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com", onDisconnect }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        ws?.simulateClose(1000);
      });

      expect(result.current.status).toBe("disconnected");
      expect(onDisconnect).toHaveBeenCalled();
    });

    it("should stop reconnecting after max attempts", async () => {
      const onDisconnect = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 100,
          maxReconnectAttempts: 2,
          onDisconnect,
        }),
      );

      let ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        ws?.simulateClose(1006);
      });
      expect(result.current.reconnectAttempts).toBe(1);

      act(() => {
        vi.advanceTimersByTime(100);
      });

      ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateClose(1006);
      });
      expect(result.current.reconnectAttempts).toBe(2);

      act(() => {
        vi.advanceTimersByTime(100);
      });

      ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateClose(1006);
      });

      expect(result.current.status).toBe("disconnected");
      expect(onDisconnect).toHaveBeenCalled();
    });

    it("should create new connection after reconnect interval", async () => {
      renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 1000,
          maxReconnectAttempts: 3,
        }),
      );

      const initialWs = MockWebSocket.getLastInstance();
      act(() => {
        initialWs?.simulateOpen();
      });

      const instanceCountBefore = MockWebSocket.instances.length;

      act(() => {
        initialWs?.simulateClose(1006);
      });

      expect(MockWebSocket.instances.length).toBe(instanceCountBefore);

      act(() => {
        vi.advanceTimersByTime(1000);
      });

      expect(MockWebSocket.instances.length).toBe(instanceCountBefore + 1);
    });

    it("should use exponential backoff for reconnect delays", async () => {
      // With exponentialBackoff enabled, delays should increase:
      // Attempt 1: baseDelay * 2^0 = 1000ms
      // Attempt 2: baseDelay * 2^1 = 2000ms
      // Attempt 3: baseDelay * 2^2 = 4000ms
      renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 1000,
          maxReconnectAttempts: 4,
          exponentialBackoff: true,
        }),
      );

      const initialWs = MockWebSocket.getLastInstance();
      act(() => {
        initialWs?.simulateOpen();
      });

      // First close - should wait ~1000ms for first reconnect
      act(() => {
        initialWs?.simulateClose(1006);
      });

      const countAfterFirstClose = MockWebSocket.instances.length;

      // After 999ms - should NOT have reconnected yet
      act(() => {
        vi.advanceTimersByTime(999);
      });
      expect(MockWebSocket.instances.length).toBe(countAfterFirstClose);

      // After total 1000ms - should have reconnected
      act(() => {
        vi.advanceTimersByTime(1);
      });
      expect(MockWebSocket.instances.length).toBe(countAfterFirstClose + 1);

      // Second close - should wait ~2000ms
      const ws2 = MockWebSocket.getLastInstance();
      act(() => {
        ws2?.simulateClose(1006);
      });

      const countAfterSecondClose = MockWebSocket.instances.length;

      // After 1999ms - should NOT have reconnected yet
      act(() => {
        vi.advanceTimersByTime(1999);
      });
      expect(MockWebSocket.instances.length).toBe(countAfterSecondClose);

      // After total 2000ms - should have reconnected
      act(() => {
        vi.advanceTimersByTime(1);
      });
      expect(MockWebSocket.instances.length).toBe(countAfterSecondClose + 1);
    });

    it("should cap exponential backoff at maxDelayMs", async () => {
      // With maxDelayMs of 2000, delays should cap:
      // Attempt 3: would be baseDelay * 2^2 = 4000ms, but capped to 2000ms
      renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 1000,
          maxReconnectAttempts: 5,
          exponentialBackoff: true,
          maxDelayMs: 2000,
        }),
      );

      const initialWs = MockWebSocket.getLastInstance();
      act(() => {
        initialWs?.simulateOpen();
      });

      // Trigger closes to reach attempt 3
      for (let i = 0; i < 2; i++) {
        const ws = MockWebSocket.getLastInstance();
        act(() => {
          ws?.simulateClose(1006);
        });
        act(() => {
          vi.advanceTimersByTime(10000); // Long enough for any backoff
        });
      }

      // Third close - should use capped delay of 2000ms (not 4000ms)
      const ws3 = MockWebSocket.getLastInstance();
      act(() => {
        ws3?.simulateClose(1006);
      });

      const countAfterThirdClose = MockWebSocket.instances.length;

      // After 2000ms - should have reconnected (capped)
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(MockWebSocket.instances.length).toBe(countAfterThirdClose + 1);
    });
  });

  describe("Manual Disconnect", () => {
    it("should close connection on manual disconnect", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        result.current.disconnect();
      });

      expect(ws?.close).toHaveBeenCalled();
    });

    it("should not attempt reconnection after manual disconnect", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 100,
          maxReconnectAttempts: 3,
        }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        result.current.disconnect();
      });

      const instanceCount = MockWebSocket.instances.length;
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      expect(MockWebSocket.instances.length).toBe(instanceCount);
    });
  });

  describe("Manual Reconnect", () => {
    it("should reset attempt count and create new connection", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          maxReconnectAttempts: 1,
        }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        ws?.simulateClose(1006);
      });

      const instanceCountBefore = MockWebSocket.instances.length;

      act(() => {
        result.current.reconnect();
      });

      expect(result.current.reconnectAttempts).toBe(0);
      expect(MockWebSocket.instances.length).toBe(instanceCountBefore + 1);
    });
  });

  describe("Send Messages", () => {
    it("should send JSON stringified message when connected", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        result.current.send({ type: "test", data: 123 });
      });

      expect(ws?.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "test", data: 123 }),
      );
    });

    it("should queue messages when not connected", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      const ws = MockWebSocket.getLastInstance();

      act(() => {
        result.current.send({ type: "queued" });
      });

      expect(ws?.send).not.toHaveBeenCalled();
    });

    it("should flush queued messages when connection opens", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      const ws = MockWebSocket.getLastInstance();

      act(() => {
        result.current.send({ type: "msg1" });
        result.current.send({ type: "msg2" });
      });

      act(() => {
        ws?.simulateOpen();
      });

      expect(ws?.send).toHaveBeenCalledTimes(2);
      expect(ws?.send).toHaveBeenCalledWith(JSON.stringify({ type: "msg1" }));
      expect(ws?.send).toHaveBeenCalledWith(JSON.stringify({ type: "msg2" }));
    });
  });

  describe("Cleanup", () => {
    it("should close WebSocket on unmount", async () => {
      const { unmount } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      unmount();

      expect(ws?.close).toHaveBeenCalled();
    });

    it("should clear reconnect timeout on unmount", async () => {
      const { unmount } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 1000,
        }),
      );

      const ws = MockWebSocket.getLastInstance();
      act(() => {
        ws?.simulateOpen();
      });

      act(() => {
        ws?.simulateClose(1006);
      });

      const instanceCount = MockWebSocket.instances.length;
      unmount();

      act(() => {
        vi.advanceTimersByTime(1000);
      });

      expect(MockWebSocket.instances.length).toBe(instanceCount);
    });
  });
});
