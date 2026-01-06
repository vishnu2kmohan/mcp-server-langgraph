/**
 * useRealtimeSync Hook Tests - Recovery Shard
 *
 * Tests for reconnection logic, token expiration handling (4010),
 * proactive token refresh, reconnection metrics, and protocol version
 * mismatch handling (4009).
 *
 * Part of OOM prevention strategy: Split from 1,509-line monolithic test file.
 *
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  MockWebSocket,
  mockEnsureValidTokenForWebSocket,
  waitForTokenValidation,
} from "./useRealtimeSync.fixtures";
import {
  WS_CLOSE_TOKEN_EXPIRED,
  WS_CLOSE_PROTOCOL_VERSION,
} from "../../utils/websocketAuth";

// Mock websocketAuth BEFORE imports (hoisting requirement)
vi.mock("../../utils/websocketAuth", async () => {
  const actual = await vi.importActual("../../utils/websocketAuth");
  return {
    ...actual,
    ensureValidTokenForWebSocket: () => mockEnsureValidTokenForWebSocket(),
  };
});

import { useRealtimeSync } from "../useRealtimeSync";

describe("useRealtimeSync - Recovery", () => {
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
    // Force GC to prevent mock accumulation
    if (global.gc) {
      global.gc();
    }
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

  describe("Protocol Version Mismatch Handling (4009)", () => {
    it("should NOT attempt reconnection on close code 4009", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

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

      expect(result.current.status).toBe("connected");
      const instanceCountBefore = MockWebSocket.instances.length;

      // Simulate protocol version mismatch close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_PROTOCOL_VERSION);
      });

      // Should NOT have created a new WebSocket connection
      expect(MockWebSocket.instances.length).toBe(instanceCountBefore);

      // Should NOT be in reconnecting state
      expect(result.current.status).not.toBe("reconnecting");

      // Wait for what would be reconnection time
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Still should not have reconnected
      expect(MockWebSocket.instances.length).toBe(instanceCountBefore);
    });

    it("should set status to error on close code 4009", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // Simulate protocol version mismatch close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_PROTOCOL_VERSION);
      });

      // Should be in error state (not disconnected - indicates action needed)
      expect(result.current.status).toBe("error");
    });

    it("should call onProtocolVersionMismatch callback on 4009", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);
      const onProtocolVersionMismatch = vi.fn();
      const onDisconnect = vi.fn();

      renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          onProtocolVersionMismatch,
          onDisconnect,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // Simulate protocol version mismatch close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_PROTOCOL_VERSION);
      });

      expect(onProtocolVersionMismatch).toHaveBeenCalledTimes(1);
      // onDisconnect should also be called
      expect(onDisconnect).toHaveBeenCalledTimes(1);
    });

    it("should track protocol_version_mismatch in failure metrics", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // Simulate protocol version mismatch close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_PROTOCOL_VERSION);
      });

      expect(
        result.current.metrics.failuresByReason.protocol_version_mismatch,
      ).toBe(1);
    });

    it("should not count 4009 as a normal reconnection attempt", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          maxReconnectAttempts: 5,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // Simulate protocol version mismatch close
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_PROTOCOL_VERSION);
      });

      // Should not have incremented reconnect attempts (not applicable for 4009)
      expect(result.current.reconnectAttempts).toBe(0);
    });
  });
});
