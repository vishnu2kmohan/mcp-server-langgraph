/**
 * useRealtimeSync Hook Tests - Metrics Shard
 *
 * Tests for reconnection metrics tracking and statistics:
 * - Initial metrics state
 * - Attempt tracking
 * - Success/failure counting
 * - Failure reason categorization
 * - Success rate calculation
 * - Attempt history
 * - Metrics reset
 *
 * Part of OOM prevention strategy: Split from recovery shard to stay under 1,000 lines.
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

describe("useRealtimeSync - Metrics", () => {
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

  describe("Reconnection Metrics", () => {
    it("should provide initial metrics with zero counts", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({ url: "ws://test.com" }),
      );

      expect(result.current.metrics).toBeDefined();
      expect(result.current.metrics.totalReconnections).toBe(0);
      expect(result.current.metrics.totalAttempts).toBe(0);
      expect(result.current.metrics.consecutiveFailures).toBe(0);
    });

    it("should track reconnection attempt on abnormal close", async () => {
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
        ws?.simulateClose(1006);
      });

      expect(result.current.metrics.totalAttempts).toBe(1);
      expect(result.current.metrics.lastDisconnectionTime).not.toBeNull();
    });

    it("should increment totalReconnections on successful reconnection", async () => {
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

      // Trigger abnormal close
      await act(async () => {
        ws?.simulateClose(1006);
      });

      // Wait for reconnection
      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      // Simulate new connection open
      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateOpen();
      });

      expect(result.current.metrics.totalReconnections).toBe(1);
      expect(result.current.metrics.lastReconnectionTime).not.toBeNull();
    });

    it("should track failure reasons by close code", async () => {
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

      // Trigger network error close
      await act(async () => {
        ws?.simulateClose(1006);
      });

      expect(result.current.metrics.failuresByReason.network_error).toBe(1);
    });

    it("should track max_attempts_exceeded when reaching limit", async () => {
      const { result } = renderHook(() =>
        useRealtimeSync({
          url: "ws://test.com",
          reconnectInterval: 100,
          maxReconnectAttempts: 1,
        }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();
      await act(async () => {
        ws?.simulateOpen();
      });

      // First close - will attempt reconnect
      await act(async () => {
        ws?.simulateClose(1006);
      });

      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      // Second close - max attempts reached
      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateClose(1006);
      });

      expect(
        result.current.metrics.failuresByReason.max_attempts_exceeded,
      ).toBe(1);
    });

    it("should reset consecutiveFailures on successful reconnection", async () => {
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

      // First failure
      await act(async () => {
        ws?.simulateClose(1006);
      });

      expect(result.current.metrics.consecutiveFailures).toBe(1);

      // Wait and reconnect
      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateOpen();
      });

      expect(result.current.metrics.consecutiveFailures).toBe(0);
    });

    it("should calculate success rate correctly", async () => {
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

      // First reconnection attempt
      await act(async () => {
        ws?.simulateClose(1006);
      });

      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateOpen();
      });

      // Success rate should be 100% (1 success / 1 attempt)
      expect(result.current.metrics.successRate).toBe(100);
    });

    it("should track recent attempts history", async () => {
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

      // Trigger reconnection
      await act(async () => {
        ws?.simulateClose(1006);
      });

      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateOpen();
      });

      expect(result.current.metrics.recentAttempts.length).toBeGreaterThan(0);
      const attempt = result.current.metrics.recentAttempts[0];
      expect(attempt.succeeded).toBe(true);
      expect(attempt.triggerCloseCode).toBe(1006);
    });

    it("should track token expiration failures", async () => {
      mockEnsureValidTokenForWebSocket
        .mockResolvedValueOnce(true) // Initial proactive check passes
        .mockResolvedValueOnce(false); // 4010 handler fails

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

      // Simulate token expiration close with failed refresh
      await act(async () => {
        ws?.simulateClose(WS_CLOSE_TOKEN_EXPIRED);
        await Promise.resolve();
      });

      expect(result.current.metrics.failuresByReason.token_refresh_failed).toBe(
        1,
      );
    });

    it("should provide resetMetrics function", async () => {
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

      // Trigger some metrics
      await act(async () => {
        ws?.simulateClose(1006);
      });

      expect(result.current.metrics.totalAttempts).toBe(1);

      // Reset metrics
      await act(async () => {
        result.current.resetMetrics();
      });

      expect(result.current.metrics.totalAttempts).toBe(0);
      expect(result.current.metrics.totalReconnections).toBe(0);
    });

    it("should calculate average reconnection duration", async () => {
      vi.setSystemTime(new Date("2024-01-01T12:00:00Z"));

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

      // Trigger reconnection
      await act(async () => {
        ws?.simulateClose(1006);
      });

      // Advance time by 100ms for reconnect delay + 50ms for "connection time"
      await act(async () => {
        vi.advanceTimersByTime(100);
        await Promise.resolve();
      });

      // Simulate some time passing during connection
      vi.advanceTimersByTime(50);

      const ws2 = MockWebSocket.getLastInstance();
      await act(async () => {
        ws2?.simulateOpen();
      });

      expect(result.current.metrics.avgReconnectionDurationMs).not.toBeNull();
      expect(result.current.metrics.totalReconnectionTimeMs).toBeGreaterThan(0);
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
  });
});
