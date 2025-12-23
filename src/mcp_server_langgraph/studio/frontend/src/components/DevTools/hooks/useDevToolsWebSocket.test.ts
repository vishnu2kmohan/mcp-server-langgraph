/**
 * useDevToolsWebSocket Hook Tests
 *
 * TDD tests for WebSocket integration with DevTools console and network tabs.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

import { useDevToolsWebSocket } from "./useDevToolsWebSocket";
// Types used for type-checking in tests
import type {
  ConsoleEntry as _ConsoleEntry,
  NetworkEntry as _NetworkEntry,
} from "../types";

// =============================================================================
// Mock WebSocket
// =============================================================================

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  readyState: number = WebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(_data: string): void {}
  close(): void {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.();
  }

  simulateOpen(): void {
    this.readyState = WebSocket.OPEN;
    this.onopen?.();
  }

  simulateMessage(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateError(): void {
    this.onerror?.();
  }
}

// =============================================================================
// Tests
// =============================================================================

describe("useDevToolsWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  describe("connection", () => {
    it("should connect to WebSocket when enabled", () => {
      renderHook(() => useDevToolsWebSocket({ enabled: true }));

      expect(MockWebSocket.instances).toHaveLength(1);
    });

    it("should not connect when disabled", () => {
      renderHook(() => useDevToolsWebSocket({ enabled: false }));

      expect(MockWebSocket.instances).toHaveLength(0);
    });

    it("should track connection status", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      // Initially connecting
      expect(result.current.status).toBe("connecting");

      // Simulate open
      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      await waitFor(() => {
        expect(result.current.status).toBe("connected");
      });
    });

    it("should handle connection errors", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateError();
      });

      await waitFor(() => {
        expect(result.current.status).toBe("error");
      });
    });

    it("should disconnect when unmounted", () => {
      const { unmount } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      const ws = MockWebSocket.instances[0];
      unmount();

      expect(ws.readyState).toBe(WebSocket.CLOSED);
    });
  });

  describe("console entries", () => {
    it("should receive console entries from WebSocket", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      const consoleMessage = {
        type: "console",
        payload: {
          id: "log-1",
          level: "info",
          source: "system",
          message: "Test log message",
          timestamp: Date.now(),
        },
      };

      act(() => {
        MockWebSocket.instances[0].simulateMessage(consoleMessage);
      });

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(1);
        expect(result.current.consoleEntries[0].message).toBe(
          "Test log message",
        );
      });
    });

    it("should accumulate multiple console entries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      for (let i = 0; i < 3; i++) {
        act(() => {
          MockWebSocket.instances[0].simulateMessage({
            type: "console",
            payload: {
              id: `log-${i}`,
              level: "info",
              source: "system",
              message: `Message ${i}`,
              timestamp: Date.now(),
            },
          });
        });
      }

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(3);
      });
    });

    it("should limit console entries to maxEntries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true, maxConsoleEntries: 5 }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      for (let i = 0; i < 10; i++) {
        act(() => {
          MockWebSocket.instances[0].simulateMessage({
            type: "console",
            payload: {
              id: `log-${i}`,
              level: "info",
              source: "system",
              message: `Message ${i}`,
              timestamp: Date.now(),
            },
          });
        });
      }

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(5);
        // Should keep newest entries
        expect(result.current.consoleEntries[0].message).toBe("Message 5");
      });
    });
  });

  describe("network entries", () => {
    it("should receive network entries from WebSocket", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      const networkMessage = {
        type: "network",
        payload: {
          id: "req-1",
          method: "GET",
          url: "/api/v1/test",
          status: "completed",
          statusCode: 200,
          startTime: Date.now(),
          duration: 150,
        },
      };

      act(() => {
        MockWebSocket.instances[0].simulateMessage(networkMessage);
      });

      await waitFor(() => {
        expect(result.current.networkEntries).toHaveLength(1);
        expect(result.current.networkEntries[0].url).toBe("/api/v1/test");
      });
    });

    it("should update pending network entries when completed", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      // Send pending request
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "network",
          payload: {
            id: "req-1",
            method: "GET",
            url: "/api/v1/test",
            status: "pending",
            startTime: Date.now(),
          },
        });
      });

      await waitFor(() => {
        expect(result.current.networkEntries[0].status).toBe("pending");
      });

      // Update with completed status
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "network_update",
          payload: {
            id: "req-1",
            status: "completed",
            statusCode: 200,
            duration: 150,
          },
        });
      });

      await waitFor(() => {
        expect(result.current.networkEntries[0].status).toBe("completed");
        expect(result.current.networkEntries[0].statusCode).toBe(200);
      });
    });
  });

  describe("clear operations", () => {
    it("should clear console entries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
        MockWebSocket.instances[0].simulateMessage({
          type: "console",
          payload: {
            id: "log-1",
            level: "info",
            source: "system",
            message: "Test",
            timestamp: Date.now(),
          },
        });
      });

      await waitFor(() => {
        expect(result.current.consoleEntries).toHaveLength(1);
      });

      act(() => {
        result.current.clearConsoleEntries();
      });

      expect(result.current.consoleEntries).toHaveLength(0);
    });

    it("should clear network entries", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({ enabled: true }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
        MockWebSocket.instances[0].simulateMessage({
          type: "network",
          payload: {
            id: "req-1",
            method: "GET",
            url: "/test",
            status: "completed",
            startTime: Date.now(),
          },
        });
      });

      await waitFor(() => {
        expect(result.current.networkEntries).toHaveLength(1);
      });

      act(() => {
        result.current.clearNetworkEntries();
      });

      expect(result.current.networkEntries).toHaveLength(0);
    });
  });

  describe("message filtering", () => {
    it("should filter console entries by contextEntityId", async () => {
      const { result } = renderHook(() =>
        useDevToolsWebSocket({
          enabled: true,
          contextEntityId: "session-123",
        }),
      );

      act(() => {
        MockWebSocket.instances[0].simulateOpen();
      });

      // Global entry (no session)
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "console",
          payload: {
            id: "log-1",
            level: "info",
            source: "system",
            message: "Global message",
            timestamp: Date.now(),
          },
        });
      });

      // Entry for matching session
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "console",
          payload: {
            id: "log-2",
            level: "info",
            source: "execution",
            message: "Session message",
            timestamp: Date.now(),
            data: { sessionId: "session-123" },
          },
        });
      });

      // Entry for different session
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "console",
          payload: {
            id: "log-3",
            level: "info",
            source: "execution",
            message: "Other session message",
            timestamp: Date.now(),
            data: { sessionId: "session-456" },
          },
        });
      });

      await waitFor(() => {
        // Should include global and matching session entries
        expect(result.current.consoleEntries).toHaveLength(2);
        expect(result.current.consoleEntries.map((e) => e.id)).toEqual([
          "log-1",
          "log-2",
        ]);
      });
    });
  });
});
