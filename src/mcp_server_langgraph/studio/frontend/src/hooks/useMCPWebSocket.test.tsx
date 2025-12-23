/**
 * Tests for useMCPWebSocket hook
 *
 * Unit tests for MCP WebSocket React hook functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { useMCPWebSocket } from "./useMCPWebSocket";
import authReducer from "../store/slices/authSlice";

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;
let _mockOnConnect: (() => void) | undefined;
let mockOnDisconnect: (() => void) | undefined;
let mockStatus = "disconnected";

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: {
    onMessage?: (data: unknown) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
  }) => {
    mockOnMessage = options.onMessage;
    _mockOnConnect = options.onConnect;
    mockOnDisconnect = options.onDisconnect;
    return {
      status: mockStatus,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
      reconnectAttempts: 0,
      lastMessageTime: null,
    };
  },
}));

// Create test store with auth slice
function createTestStore(isAuthenticated = true) {
  return configureStore({
    reducer: {
      auth: authReducer,
    },
    preloadedState: {
      auth: {
        user: isAuthenticated
          ? { id: "test-user", email: "test@example.com", roles: ["user"], persona: "user" as const }
          : null,
        tokens: null,
        organizations: [],
        currentOrganization: null,
        permissions: [],
        lastSynced: null,
        isLoading: false,
        error: null,
      },
    },
  });
}

// Test wrapper with Redux Provider
function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

describe("useMCPWebSocket", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = "disconnected";
    store = createTestStore();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("hook structure", () => {
    it("should return required properties and methods", () => {
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      // Status properties
      expect(result.current).toHaveProperty("status");
      expect(result.current).toHaveProperty("isInitialized");
      expect(result.current).toHaveProperty("serverInfo");
      expect(result.current).toHaveProperty("capabilities");
      expect(result.current).toHaveProperty("tools");
      expect(result.current).toHaveProperty("resources");
      expect(result.current).toHaveProperty("prompts");
      expect(result.current).toHaveProperty("error");

      // MCP methods
      expect(result.current).toHaveProperty("initialize");
      expect(result.current).toHaveProperty("listTools");
      expect(result.current).toHaveProperty("listResources");
      expect(result.current).toHaveProperty("listPrompts");
      expect(result.current).toHaveProperty("callTool");
      expect(result.current).toHaveProperty("readResource");
      expect(result.current).toHaveProperty("getPrompt");

      // Connection methods
      expect(result.current).toHaveProperty("disconnect");
      expect(result.current).toHaveProperty("reconnect");
    });

    it("should return initial disconnected state", () => {
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      expect(result.current.status).toBe("disconnected");
      expect(result.current.isInitialized).toBe(false);
      expect(result.current.serverInfo).toBeNull();
      expect(result.current.capabilities).toBeNull();
      expect(result.current.tools).toEqual([]);
      expect(result.current.resources).toEqual([]);
      expect(result.current.prompts).toEqual([]);
      expect(result.current.error).toBeNull();
    });

    it("should return callable functions", () => {
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      expect(typeof result.current.initialize).toBe("function");
      expect(typeof result.current.listTools).toBe("function");
      expect(typeof result.current.callTool).toBe("function");
      expect(typeof result.current.disconnect).toBe("function");
      expect(typeof result.current.reconnect).toBe("function");
    });
  });

  describe("connection management", () => {
    it("should provide disconnect function", () => {
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      act(() => {
        result.current.disconnect();
      });

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should provide reconnect function", () => {
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      act(() => {
        result.current.reconnect();
      });

      expect(mockReconnect).toHaveBeenCalled();
    });

    it("should clear state on disconnect", async () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      // Simulate disconnect
      await act(async () => {
        mockOnDisconnect?.();
      });

      expect(result.current.isInitialized).toBe(false);
    });

    it("should respect enabled option", () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useMCPWebSocket({ enabled: false }), {
        wrapper: createWrapper(store),
      });

      // Status should be disconnected when not enabled
      expect(result.current.status).toBe("disconnected");
    });
  });

  describe("request handling", () => {
    it("should throw error when not connected", async () => {
      mockStatus = "disconnected";
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      await act(async () => {
        await expect(result.current.initialize()).rejects.toThrow(
          "Not connected to MCP server",
        );
      });
    });

    it("should send initialize request with correct format when connected", async () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      // Don't await - just check that send was called with correct format
      result.current.initialize().catch(() => {});

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          jsonrpc: "2.0",
          method: "initialize",
          params: expect.objectContaining({
            protocolVersion: "2025-11-25",
            capabilities: {},
            clientInfo: { name: "studio-frontend", version: "1.0.0" },
          }),
        }),
      );
    });

    it("should send tools/call with correct format", async () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      // Don't await - just check that send was called with correct format
      result.current
        .callTool("langgraph-run", { query: "test" })
        .catch(() => {});

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          jsonrpc: "2.0",
          method: "tools/call",
          params: {
            name: "langgraph-run",
            arguments: { query: "test" },
          },
        }),
      );
    });

    it("should include unique message IDs", () => {
      mockStatus = "connected";
      const { result } = renderHook(() => useMCPWebSocket(), { wrapper: createWrapper(store) });

      // Make two requests
      result.current.listTools().catch(() => {});
      result.current.listResources().catch(() => {});

      const call1 = mockSend.mock.calls[0][0] as { id: number };
      const call2 = mockSend.mock.calls[1][0] as { id: number };

      expect(call1.id).toBeDefined();
      expect(call2.id).toBeDefined();
      expect(call1.id).not.toBe(call2.id);
    });
  });

  describe("streaming notifications", () => {
    it("should handle streaming start notification", () => {
      const onStreamingStart = vi.fn();
      mockStatus = "connected";

      renderHook(
        () =>
          useMCPWebSocket({
            onStreamingStart,
          }),
        { wrapper: createWrapper(store) },
      );

      // Simulate streaming start notification
      act(() => {
        mockOnMessage?.({
          jsonrpc: "2.0",
          method: "$/streaming/start",
          params: { streamId: "stream-123", toolCallId: 1 },
        });
      });

      expect(onStreamingStart).toHaveBeenCalledWith("stream-123", 1);
    });

    it("should handle streaming chunk notification", () => {
      const onStreamingChunk = vi.fn();
      mockStatus = "connected";

      renderHook(
        () =>
          useMCPWebSocket({
            onStreamingChunk,
          }),
        { wrapper: createWrapper(store) },
      );

      // Simulate streaming chunk notification
      act(() => {
        mockOnMessage?.({
          jsonrpc: "2.0",
          method: "$/streaming/chunk",
          params: {
            streamId: "stream-123",
            content: { type: "text", text: "Hello" },
          },
        });
      });

      expect(onStreamingChunk).toHaveBeenCalledWith({
        streamId: "stream-123",
        content: { type: "text", text: "Hello" },
      });
    });

    it("should handle streaming end notification", () => {
      const onStreamingEnd = vi.fn();
      mockStatus = "connected";

      renderHook(
        () =>
          useMCPWebSocket({
            onStreamingEnd,
          }),
        { wrapper: createWrapper(store) },
      );

      // Simulate streaming end notification
      act(() => {
        mockOnMessage?.({
          jsonrpc: "2.0",
          method: "$/streaming/end",
          params: { streamId: "stream-123" },
        });
      });

      expect(onStreamingEnd).toHaveBeenCalledWith("stream-123");
    });
  });

  describe("options", () => {
    it("should use custom client info", () => {
      mockStatus = "connected";
      const { result } = renderHook(
        () =>
          useMCPWebSocket({
            clientInfo: { name: "custom-client", version: "2.0.0" },
          }),
        { wrapper: createWrapper(store) },
      );

      result.current.initialize().catch(() => {});

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          params: expect.objectContaining({
            clientInfo: { name: "custom-client", version: "2.0.0" },
          }),
        }),
      );
    });
  });
});
