/**
 * useMCPAggregatedUpdates Hook Tests (TDD)
 *
 * Tests for the MCP aggregated capabilities real-time updates hook.
 * This hook listens to WebSocket notifications for capability changes
 * and invalidates RTK Query cache to trigger refetches.
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../api";
import { createInitialReconnectionMetrics } from "../types/websocket-metrics";

// Mock the useRealtimeSync hook
const mockUseRealtimeSync = vi.fn();
vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: unknown) => mockUseRealtimeSync(options),
}));

// Mock auth
vi.mock("../store/hooks", () => ({
  useAppSelector: () => true,
  useAppDispatch: () => vi.fn(),
}));

vi.mock("../store/slices/authSlice", async () => {
  const actual = await vi.importActual("../store/slices/authSlice");
  return {
    ...actual,
    selectIsAuthenticated: () => true,
  };
});
vi.mock("../utils/storage", async () => {
  const actual = await vi.importActual("../utils/storage");
  return {
    ...actual,
    getAuthToken: () => "test-token",
  };
});
// Import after mocking
import { useMCPAggregatedUpdates } from "./useMCPAggregatedUpdates";

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Tests
// =============================================================================

describe("useMCPAggregatedUpdates", () => {
  const mockDisconnect = vi.fn();
  const mockReconnect = vi.fn();
  // Shared reference for capturing onMessage across renders
  const capturedCallbacks: { onMessage: ((data: unknown) => void) | null } = {
    onMessage: null,
  };

  beforeEach(() => {
    vi.resetAllMocks();
    capturedCallbacks.onMessage = null;

    // Default mock that captures the message handler
    mockUseRealtimeSync.mockImplementation(
      (options?: { onMessage?: (data: unknown) => void }) => {
        if (options?.onMessage) {
          capturedCallbacks.onMessage = options.onMessage;
        }
        return {
          status: "connected",
          send: vi.fn(),
          disconnect: mockDisconnect,
          reconnect: mockReconnect,
          metrics: createInitialReconnectionMetrics(),
          resetMetrics: vi.fn(),
        };
      },
    );
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
    capturedCallbacks.onMessage = null;
  });

  describe("connection status", () => {
    it("returns connected status when WebSocket is connected", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "connected",
        send: vi.fn(),
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: createInitialReconnectionMetrics(),
        resetMetrics: vi.fn(),
      });

      const { result } = renderHook(() => useMCPAggregatedUpdates(), {
        wrapper,
      });

      expect(result.current.status).toBe("connected");
    });

    it("returns disconnected status when WebSocket is disconnected", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "disconnected",
        send: vi.fn(),
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: createInitialReconnectionMetrics(),
        resetMetrics: vi.fn(),
      });

      const { result } = renderHook(() => useMCPAggregatedUpdates(), {
        wrapper,
      });

      expect(result.current.status).toBe("disconnected");
    });

    it("provides disconnect function", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "connected",
        send: vi.fn(),
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: createInitialReconnectionMetrics(),
        resetMetrics: vi.fn(),
      });

      const { result } = renderHook(() => useMCPAggregatedUpdates(), {
        wrapper,
      });

      result.current.disconnect();

      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("provides reconnect function", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "disconnected",
        send: vi.fn(),
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: createInitialReconnectionMetrics(),
        resetMetrics: vi.fn(),
      });

      const { result } = renderHook(() => useMCPAggregatedUpdates(), {
        wrapper,
      });

      result.current.reconnect();

      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("capability change notifications", () => {
    it("tracks tools_list_changed notifications", () => {
      const { result } = renderHook(() => useMCPAggregatedUpdates(), {
        wrapper,
      });

      expect(result.current.lastToolsUpdate).toBeNull();

      // Simulate receiving a tools_list_changed notification
      act(() => {
        capturedCallbacks.onMessage!({
          jsonrpc: "2.0",
          method: "notifications/tools/list_changed",
          params: { serverName: "test-server" },
        });
      });

      expect(result.current.lastToolsUpdate).not.toBeNull();
    });

    it("tracks resources_list_changed notifications", () => {
      const { result } = renderHook(() => useMCPAggregatedUpdates(), {
        wrapper,
      });

      expect(result.current.lastResourcesUpdate).toBeNull();

      // Simulate receiving a resources_list_changed notification
      act(() => {
        capturedCallbacks.onMessage!({
          jsonrpc: "2.0",
          method: "notifications/resources/list_changed",
          params: { serverName: "test-server" },
        });
      });

      expect(result.current.lastResourcesUpdate).not.toBeNull();
    });

    it("tracks prompts_list_changed notifications", () => {
      const { result } = renderHook(() => useMCPAggregatedUpdates(), {
        wrapper,
      });

      expect(result.current.lastPromptsUpdate).toBeNull();

      // Simulate receiving a prompts_list_changed notification
      act(() => {
        capturedCallbacks.onMessage!({
          jsonrpc: "2.0",
          method: "notifications/prompts/list_changed",
          params: { serverName: "test-server" },
        });
      });

      expect(result.current.lastPromptsUpdate).not.toBeNull();
    });
  });

  describe("callback invocation", () => {
    it("calls onToolsChanged callback when tools list changes", () => {
      const onToolsChanged = vi.fn();

      renderHook(() => useMCPAggregatedUpdates({ onToolsChanged }), {
        wrapper,
      });

      // Simulate receiving a tools_list_changed notification
      act(() => {
        capturedCallbacks.onMessage!({
          jsonrpc: "2.0",
          method: "notifications/tools/list_changed",
          params: { serverName: "test-server" },
        });
      });

      expect(onToolsChanged).toHaveBeenCalledWith("test-server");
    });

    it("calls onResourcesChanged callback when resources list changes", () => {
      const onResourcesChanged = vi.fn();

      renderHook(() => useMCPAggregatedUpdates({ onResourcesChanged }), {
        wrapper,
      });

      // Simulate receiving a resources_list_changed notification
      act(() => {
        capturedCallbacks.onMessage!({
          jsonrpc: "2.0",
          method: "notifications/resources/list_changed",
          params: { serverName: "test-server" },
        });
      });

      expect(onResourcesChanged).toHaveBeenCalledWith("test-server");
    });

    it("calls onPromptsChanged callback when prompts list changes", () => {
      const onPromptsChanged = vi.fn();

      renderHook(() => useMCPAggregatedUpdates({ onPromptsChanged }), {
        wrapper,
      });

      // Simulate receiving a prompts_list_changed notification
      act(() => {
        capturedCallbacks.onMessage!({
          jsonrpc: "2.0",
          method: "notifications/prompts/list_changed",
          params: { serverName: "test-server" },
        });
      });

      expect(onPromptsChanged).toHaveBeenCalledWith("test-server");
    });
  });

  describe("options", () => {
    it("respects enabled option", () => {
      mockUseRealtimeSync.mockReturnValue({
        status: "disconnected",
        send: vi.fn(),
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        metrics: createInitialReconnectionMetrics(),
        resetMetrics: vi.fn(),
      });

      const { result } = renderHook(
        () => useMCPAggregatedUpdates({ enabled: false }),
        { wrapper },
      );

      expect(result.current.status).toBe("disconnected");
    });
  });
});
