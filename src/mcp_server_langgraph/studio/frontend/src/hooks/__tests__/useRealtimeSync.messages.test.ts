/**
 * useRealtimeSync Hook Tests - Messages Shard
 *
 * Tests for message handling, sending messages, error handling,
 * manual disconnect/reconnect.
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

// Mock websocketAuth BEFORE imports (hoisting requirement)
vi.mock("../../utils/websocketAuth", async () => {
  const actual = await vi.importActual("../../utils/websocketAuth");
  return {
    ...actual,
    ensureValidTokenForWebSocket: () => mockEnsureValidTokenForWebSocket(),
  };
});

import { useRealtimeSync } from "../useRealtimeSync";

describe("useRealtimeSync - Messages", () => {
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
});
