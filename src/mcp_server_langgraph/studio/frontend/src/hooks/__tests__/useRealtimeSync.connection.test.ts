/**
 * useRealtimeSync Hook Tests - Connection Shard
 *
 * Tests for WebSocket connection establishment, protocol version handling,
 * URL validation, and cleanup.
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

describe("useRealtimeSync - Connection", () => {
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

  describe("Protocol Version in URL", () => {
    it("should append protocol version as query parameter", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      renderHook(() => useRealtimeSync({ url: "ws://test.com/realtime" }));

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();

      expect(ws?.url).toContain("v=");
      expect(ws?.url).toMatch(/v=\d+\.\d+\.\d+/);
    });

    it("should preserve existing query parameters", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      renderHook(() =>
        useRealtimeSync({ url: "ws://test.com/realtime?token=abc123" }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();

      expect(ws?.url).toContain("token=abc123");
      expect(ws?.url).toContain("v=");
    });

    it("should use ampersand for version param when URL has existing params", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      renderHook(() =>
        useRealtimeSync({ url: "ws://test.com/realtime?existing=param" }),
      );

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();

      expect(ws?.url).toMatch(/\?existing=param&v=/);
    });

    it("should use question mark for version param when URL has no params", async () => {
      mockEnsureValidTokenForWebSocket.mockResolvedValue(true);

      renderHook(() => useRealtimeSync({ url: "ws://test.com/realtime" }));

      await waitForTokenValidation();
      const ws = MockWebSocket.getLastInstance();

      expect(ws?.url).toMatch(/realtime\?v=/);
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
});
