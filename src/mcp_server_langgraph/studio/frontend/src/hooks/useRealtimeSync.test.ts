/**
 * useRealtimeSync Hook Tests
 *
 * Tests for WebSocket real-time sync hook including:
 * - Connection establishment
 * - Reconnection logic
 * - Message handling
 * - Error states
 * - Manual disconnect/reconnect
 * - Token expiration handling (4010)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useRealtimeSync } from "./useRealtimeSync";
import { WS_CLOSE_TOKEN_EXPIRED } from "../utils/websocketAuth";

// Mock websocketAuth
const mockEnsureValidTokenForWebSocket = vi.fn();
vi.mock("../utils/websocketAuth", async () => {
  const actual = await vi.importActual("../utils/websocketAuth");
  return {
    ...actual,
    ensureValidTokenForWebSocket: () => mockEnsureValidTokenForWebSocket(),
  };
});

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

/**
 * Helper to wait for proactive token validation promise to resolve.
 * The new createConnection() calls ensureValidTokenForWebSocket().then(...)
 * which is async, so we need to flush promises before accessing WebSocket.
 */
async function waitForTokenValidation() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe("useRealtimeSync", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.reset();
    vi.stubGlobal("WebSocket", MockWebSocket);
    mockEnsureValidTokenForWebSocket.mockReset();
    // Default: token is valid (proactive validation succeeds)
    mockEnsureValidTokenForWebSocket.mockResolvedValue(true);
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

      // Wait for proactive token validation promise to resolve
      await act(async () => {
        await Promise.resolve();
      });

      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      expect(result.current.status).toBe("connected");
      expect(onConnect).toHaveBeenCalled();
    });

    it("should reset reconnect attempts on successful connection", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      // Wait for proactive token validation promise to resolve
      await act(async () => {
        await Promise.resolve();
      });

      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      expect(result.current.reconnectAttempts).toBe(0);
    });
  });

  describe("Message Handling", () => {
    it("should call onMessage with parsed JSON data", async () => {
      const onMessage = vi.fn();
      renderHook(() => useRealtimeSync({ url: "ws://test.com", onMessage }));

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
        ws?.simulateMessage({ type: "test", data: 123 });
      });

      expect(onMessage).toHaveBeenCalledWith({ type: "test", data: 123 });
    });

    it("should handle non-JSON messages", async () => {
      const onMessage = vi.fn();
      renderHook(() => useRealtimeSync({ url: "ws://test.com", onMessage }));

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
        ws?.simulateRawMessage("plain text message");
      });

      expect(onMessage).toHaveBeenCalledWith("plain text message");
    });

    it("should update lastMessageTime on message receipt", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      expect(result.current.lastMessageTime).toBeNull();

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      vi.setSystemTime(new Date("2024-01-01T12:00:00Z"));

      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
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

      await waitForTokenValidation();
      let ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
        ws?.simulateClose(1006);
      });
      expect(result.current.reconnectAttempts).toBe(1);

      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateClose(1006);
      });
      expect(result.current.reconnectAttempts).toBe(2);

      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      ws = MockWebSocket.getLastInstance();
      await act(async () => {
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

      await waitForTokenValidation();
      const initialWs = MockWebSocket.getLastInstance();
      await act(async () => {
        initialWs?.simulateOpen();
      });

      const instanceCountBefore = MockWebSocket.instances.length;

      await act(async () => {
        initialWs?.simulateClose(1006);
      });

      expect(MockWebSocket.instances.length).toBe(instanceCountBefore);

      await act(async () => {
        vi.advanceTimersByTime(1000);
        await Promise.resolve();
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

      await waitForTokenValidation();
      const initialWs = MockWebSocket.getLastInstance();
      await act(async () => {
        initialWs?.simulateOpen();
      });

      // First close - should wait ~1000ms for first reconnect
      await act(async () => {
        initialWs?.simulateClose(1006);
      });

      const countAfterFirstClose = MockWebSocket.instances.length;

      // After 999ms - should NOT have reconnected yet
      await act(async () => {
        vi.advanceTimersByTime(999);
      });
      expect(MockWebSocket.instances.length).toBe(countAfterFirstClose);

      // After total 1000ms - should have reconnected
      await act(async () => {
        vi.advanceTimersByTime(1);
        await Promise.resolve();
      });
      expect(MockWebSocket.instances.length).toBe(countAfterFirstClose + 1);

      // Second close - should wait ~2000ms
      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateClose(1006);
      });

      const countAfterSecondClose = MockWebSocket.instances.length;

      // After 1999ms - should NOT have reconnected yet
      await act(async () => {
        vi.advanceTimersByTime(1999);
      });
      expect(MockWebSocket.instances.length).toBe(countAfterSecondClose);

      // After total 2000ms - should have reconnected
      await act(async () => {
        vi.advanceTimersByTime(1);
        await Promise.resolve();
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

      await waitForTokenValidation();
      const initialWs = MockWebSocket.getLastInstance();
      await act(async () => {
        initialWs?.simulateOpen();
      });

      // Trigger closes to reach attempt 3
      for (let i = 0; i < 2; i++) {
        const ws = MockWebSocket.getLastInstance();
        await act(async () => {
          ws?.simulateClose(1006);
        });
        await act(async () => {
          vi.advanceTimersByTime(10000);
          await Promise.resolve();
        });
      }

      // Third close - should use capped delay of 2000ms (not 4000ms)
      const ws3 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws3?.simulateClose(1006);
      });

      const countAfterThirdClose = MockWebSocket.instances.length;

      // After 2000ms - should have reconnected (capped)
      await act(async () => {
        vi.advanceTimersByTime(2000);
        await Promise.resolve();
      });
      expect(MockWebSocket.instances.length).toBe(countAfterThirdClose + 1);
    });
  });

  describe("Manual Disconnect", () => {
    it("should close connection on manual disconnect", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
        result.current.disconnect();
      });

      const instanceCount = MockWebSocket.instances.length;
      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
        ws?.simulateClose(1006);
      });

      const instanceCountBefore = MockWebSocket.instances.length;

      await act(async () => {
        result.current.reconnect();
        await Promise.resolve();
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();

      await act(async () => {
        result.current.send({ type: "queued" });
      });

      expect(ws?.send).not.toHaveBeenCalled();
    });

    it("should flush queued messages when connection opens", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();

      await act(async () => {
        result.current.send({ type: "msg1" });
        result.current.send({ type: "msg2" });
      });

      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
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

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      await act(async () => {
        ws?.simulateClose(1006);
      });

      const instanceCount = MockWebSocket.instances.length;
      unmount();

      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      expect(MockWebSocket.instances.length).toBe(instanceCount);
    });
  });

  describe("URL Validation", () => {
    it("should reject URLs without ws:// or wss:// protocol", () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "/api/v1/ws/notifications", // relative URL - invalid for WebSocket
          onError,
        }),
      );

      // Should not attempt connection with invalid URL
      expect(result.current.status).toBe("error");
      expect(onError).toHaveBeenCalled();
      expect(MockWebSocket.instances.length).toBe(0);
    });

    it("should reject URLs with http:// protocol", () => {
      const onError = vi.fn();
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "http://localhost/api/v1/ws/test",
          onError,
        }),
      );

      expect(result.current.status).toBe("error");
      expect(onError).toHaveBeenCalled();
      expect(MockWebSocket.instances.length).toBe(0);
    });

    it("should accept valid ws:// URLs", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://localhost/api/v1/ws/test" }),
      );

      expect(result.current.status).toBe("connecting");
      await waitForTokenValidation();
      expect(MockWebSocket.instances.length).toBe(1);
    });

    it("should accept valid wss:// URLs", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "wss://localhost/api/v1/ws/test" }),
      );

      expect(result.current.status).toBe("connecting");
      await waitForTokenValidation();
      expect(MockWebSocket.instances.length).toBe(1);
    });
  });

  describe("Token Expiration Handling (4010)", () => {
    it("should refresh token and reconnect on close code 4010", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 100,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      expect(result.current.status).toBe("connected");
      const instanceCountBefore = MockWebSocket.instances.length;
      // Reset the call count to only count the 4010 handler call
      mockEnsureValidTokenForWebSocket.mockClear();

      // Simulate token expiration close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_TOKEN_EXPIRED);
        // Allow promise to resolve
        await Promise.resolve();
      });

      // Should have attempted token refresh
      expect(mockEnsureValidTokenForWebSocket).toHaveBeenCalledTimes(1);

      // Should have created a new WebSocket connection
      expect(MockWebSocket.instances.length).toBe(instanceCountBefore + 1);
    });

    it("should reset reconnect attempts before reconnecting on 4010", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 100,
          maxReconnectAttempts: 2,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // Trigger a normal close to increment attempts
      await act(async () => {
        ws?.simulateClose(1006);
      });

      expect(result.current.reconnectAttempts).toBe(1);

      // Wait for reconnection
      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateOpen();
      });

      // Now trigger token expiration
      await act(async () => {
        ws2?.simulateClose(WS_CLOSE_TOKEN_EXPIRED);
        await Promise.resolve();
      });

      // Should have reset attempts to 0
      expect(result.current.reconnectAttempts).toBe(0);
    });

    it("should call onTokenExpired when refresh fails", async () => {
      // First allow initial connection, then fail on 4010 handler
      mockEnsureValidTokenForWebSocket
        .mockResolvedValueOnce(true) // Initial proactive check passes
        .mockResolvedValueOnce(false); // 4010 handler fails
      const onTokenExpired = vi.fn();
      const onDisconnect = vi.fn();

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          onTokenExpired,
          onDisconnect,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // Simulate token expiration close with failed refresh
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_TOKEN_EXPIRED);
        await Promise.resolve();
      });

      expect(mockEnsureValidTokenForWebSocket).toHaveBeenCalledTimes(2);
      expect(onTokenExpired).toHaveBeenCalledTimes(1);
      expect(onDisconnect).toHaveBeenCalledTimes(1);
      expect(result.current.status).toBe("disconnected");
    });

    it("should not use normal reconnection flow for 4010", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 1000,
          maxReconnectAttempts: 5,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      const instanceCountBefore = MockWebSocket.instances.length;

      // Simulate token expiration close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_TOKEN_EXPIRED);
        await Promise.resolve();
      });

      // Should reconnect immediately (not wait for reconnectInterval)
      expect(MockWebSocket.instances.length).toBe(instanceCountBefore + 1);

      // Should not have incremented reconnect attempts
      expect(result.current.reconnectAttempts).toBe(0);
    });

    it("should not attempt normal reconnection when 4010 refresh fails", async () => {
      // First allow initial connection, then fail on 4010 handler
      mockEnsureValidTokenForWebSocket
        .mockResolvedValueOnce(true) // Initial proactive check passes
        .mockResolvedValueOnce(false); // 4010 handler fails

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 100,
          maxReconnectAttempts: 5,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      const instanceCountBefore = MockWebSocket.instances.length;

      // Simulate token expiration close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_TOKEN_EXPIRED);
        await Promise.resolve();
      });

      expect(result.current.status).toBe("disconnected");

      // Wait for what would be reconnection time
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Should not have tried normal reconnection
      expect(MockWebSocket.instances.length).toBe(instanceCountBefore);
    });
  });

  describe("Proactive Token Refresh", () => {
    it("should validate token before creating WebSocket connection", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      renderHook(() => useRealtimeSync({ url: "ws://test.com" }));

      // Token validation should be called immediately
      expect(mockEnsureValidTokenForWebSocket).toHaveBeenCalledTimes(1);

      // WebSocket should not be created until token validation resolves
      expect(MockWebSocket.instances.length).toBe(0);

      // Wait for token validation to complete
      await waitForTokenValidation();

      // Now WebSocket should be created
      expect(MockWebSocket.instances.length).toBe(1);
    });

    it("should not create WebSocket if proactive token validation fails", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(false);
      const onTokenExpired = vi.fn();
      const onDisconnect = vi.fn();

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          onTokenExpired,
          onDisconnect,
        }),
      );

      // Wait for token validation to complete
      await waitForTokenValidation();

      // WebSocket should NOT be created
      expect(MockWebSocket.instances.length).toBe(0);

      // Callbacks should be called
      expect(onTokenExpired).toHaveBeenCalledTimes(1);
      expect(onDisconnect).toHaveBeenCalledTimes(1);

      // Status should be disconnected
      expect(result.current.status).toBe("disconnected");
    });

    it("should re-validate token before reconnecting after delay", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 1000,
          maxReconnectAttempts: 3,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // Clear the mock to count only reconnection calls
      mockEnsureValidTokenForWebSocket.mockClear();

      // Trigger abnormal close
      await act(async () => {
        ws?.simulateClose(1006);
      });

      expect(result.current.status).toBe("reconnecting");

      // Advance timer to trigger reconnection
      await act(async () => {
        vi.advanceTimersByTime(1000);
        await Promise.resolve();
      });

      // Should have validated token before reconnecting
      expect(mockEnsureValidTokenForWebSocket).toHaveBeenCalledTimes(1);
    });
  });
});
