/**
 * useConnectionHealth Hook Tests
 *
 * Tests for the WebSocket-based connection health monitoring hook.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useConnectionHealth } from "./useConnectionHealth";

// Store the created WebSocket instance
let createdWebSocket: MockWebSocket | null = null;

// Helper to set created WebSocket (avoids this-alias ESLint warning)
function setCreatedWebSocket(ws: MockWebSocket): void {
  createdWebSocket = ws;
}

// Mock WebSocket class
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  public onopen: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public readyState: number = MockWebSocket.CONNECTING;
  public url: string;

  constructor(url: string) {
    this.url = url;
    // Store reference for test assertions (assigned after construction)
    setCreatedWebSocket(this);
  }

  send = vi.fn();

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({} as CloseEvent);
  }

  // Helper to simulate open
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({} as Event);
  }

  // Helper to simulate message
  simulateMessage(data: object) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }
}

describe("useConnectionHealth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createdWebSocket = null;
    vi.stubGlobal("WebSocket", MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    createdWebSocket = null;
  });

  describe("Initial State", () => {
    it("should start disconnected", () => {
      const { result } = renderHook(() => useConnectionHealth());

      expect(result.current.isConnected).toBe(false);
      expect(result.current.connections).toEqual([]);
    });

    it("should not auto-connect by default", () => {
      renderHook(() => useConnectionHealth({ autoConnect: false }));

      expect(createdWebSocket).toBeNull();
    });
  });

  describe("Connection", () => {
    it("should connect when autoConnect is true", () => {
      renderHook(() => useConnectionHealth({ autoConnect: true }));

      expect(createdWebSocket).not.toBeNull();
    });

    it("should connect to correct WebSocket URL", () => {
      renderHook(() => useConnectionHealth({ autoConnect: true }));

      // Standardized URL per ADR-0068: /api/v1/ws/connections/health
      expect(createdWebSocket?.url).toContain("/api/v1/ws/connections/health");
    });

    it("should update isConnected when connected", async () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      expect(createdWebSocket).not.toBeNull();

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      expect(result.current.isConnected).toBe(true);
    });

    it("should handle connection error", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.onerror?.({} as Event);
      });

      expect(result.current.error).toBeTruthy();
    });
  });

  describe("Message Handling", () => {
    it("should parse connection_status messages", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      const mockConnections = [
        {
          id: "1",
          name: "GitHub MCP",
          status: "connected",
          url: "https://github.com",
        },
        {
          id: "2",
          name: "Slack MCP",
          status: "disconnected",
          url: "https://slack.com",
        },
      ];

      act(() => {
        createdWebSocket!.simulateMessage({
          type: "connection_status",
          connections: mockConnections,
        });
      });

      expect(result.current.connections).toHaveLength(2);
      expect(result.current.connections[0].name).toBe("GitHub MCP");
    });

    it("should update specific connection on connection_update", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      // Initial status
      act(() => {
        createdWebSocket!.simulateMessage({
          type: "connection_status",
          connections: [
            { id: "1", name: "GitHub MCP", status: "disconnected" },
          ],
        });
      });

      expect(result.current.connections[0].status).toBe("disconnected");

      // Update
      act(() => {
        createdWebSocket!.simulateMessage({
          type: "connection_update",
          connection: { id: "1", name: "GitHub MCP", status: "connected" },
        });
      });

      expect(result.current.connections[0].status).toBe("connected");
    });

    it("should handle pong responses", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      act(() => {
        createdWebSocket!.simulateMessage({
          type: "pong",
          timestamp: new Date().toISOString(),
        });
      });

      expect(result.current.lastPong).toBeTruthy();
    });
  });

  describe("Commands", () => {
    it("should send refresh command", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      act(() => {
        result.current.refresh();
      });

      expect(createdWebSocket!.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "refresh" }),
      );
    });

    it("should send check_health command", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      act(() => {
        result.current.checkHealth("conn-123");
      });

      expect(createdWebSocket!.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "check_health", connection_id: "conn-123" }),
      );
    });

    it("should send subscribe command", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      act(() => {
        result.current.subscribe("conn-123");
      });

      expect(createdWebSocket!.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "subscribe", connection_id: "conn-123" }),
      );
    });
  });

  describe("Health Summary", () => {
    it("should compute health summary from connections", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      act(() => {
        createdWebSocket!.simulateMessage({
          type: "connection_status",
          connections: [
            { id: "1", status: "connected" },
            { id: "2", status: "connected" },
            { id: "3", status: "disconnected" },
            { id: "4", status: "error" },
          ],
        });
      });

      expect(result.current.summary.total).toBe(4);
      expect(result.current.summary.connected).toBe(2);
      expect(result.current.summary.disconnected).toBe(1);
      expect(result.current.summary.error).toBe(1);
    });
  });

  describe("Disconnection", () => {
    it("should handle disconnection gracefully", () => {
      const { result } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      expect(result.current.isConnected).toBe(true);

      act(() => {
        createdWebSocket!.close();
      });

      expect(result.current.isConnected).toBe(false);
    });

    it("should cleanup on unmount", () => {
      const { unmount } = renderHook(() =>
        useConnectionHealth({ autoConnect: true }),
      );

      act(() => {
        createdWebSocket!.simulateOpen();
      });

      const closeSpy = vi.spyOn(createdWebSocket!, "close");

      unmount();

      expect(closeSpy).toHaveBeenCalled();
    });
  });
});
