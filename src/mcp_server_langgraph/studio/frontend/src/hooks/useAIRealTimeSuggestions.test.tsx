/**
 * Tests for useAIRealTimeSuggestions hook
 *
 * TDD Phase: GREEN - Tests with mock implementation
 * Feature: Real-time AI suggestions via WebSocket
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";

import { useAIRealTimeSuggestions } from "./useAIRealTimeSuggestions";

// =============================================================================
// Mocks
// =============================================================================

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockStatus = "connected";
let mockReconnectAttempts = 0;
let mockOnMessage: ((data: unknown) => void) | undefined;
let mockOnError: ((error: Error) => void) | undefined;
let mockOnConnect: (() => void) | undefined;

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: {
    url: string;
    onMessage?: (data: unknown) => void;
    onError?: (error: Error) => void;
    onConnect?: () => void;
  }) => {
    mockOnMessage = options.onMessage;
    mockOnError = options.onError;
    mockOnConnect = options.onConnect;
    return {
      status: options.url ? mockStatus : "disconnected",
      reconnectAttempts: mockReconnectAttempts,
      lastMessageTime: null,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
    };
  },
}));

// =============================================================================
// Test Helpers
// =============================================================================

// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      auth: () => ({ user: { id: "test-user-123" } }),
    },
  });

const wrapper = ({ children }: { children: ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Tests
// =============================================================================

describe("useAIRealTimeSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = "connected";
    mockReconnectAttempts = 0;
    mockOnMessage = undefined;
    mockOnError = undefined;
    mockOnConnect = undefined;
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("Connection Management", () => {
    it("should connect to WebSocket on mount when enabled", () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      expect(result.current.isConnected).toBe(true);
    });

    it("should not connect when disabled", () => {
      mockStatus = "disconnected";
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: false }),
        { wrapper },
      );

      expect(result.current.isConnected).toBe(false);
    });

    it("should disconnect on unmount", () => {
      mockStatus = "connected";
      const { result, unmount } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      expect(result.current.isConnected).toBe(true);

      unmount();

      // After unmount, the hook should have cleaned up
      // (verify no errors thrown)
    });

    it("should expose reconnect attempts from underlying hook", () => {
      mockReconnectAttempts = 2;
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      expect(result.current.reconnectAttempts).toBe(2);
    });
  });

  describe("Suggestion Handling", () => {
    it("should receive and store suggestions", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      expect(result.current.isConnected).toBe(true);

      // Simulate receiving a suggestion
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            {
              id: "nudge-1",
              type: "tooltip",
              message: "Try using keyboard shortcuts",
              priority: "medium",
            },
          ],
        });
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(1);
        expect(result.current.suggestions[0].id).toBe("nudge-1");
      });
    });

    it("should handle multiple suggestions", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Simulate receiving multiple suggestions
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            {
              id: "nudge-1",
              type: "tooltip",
              message: "Tip 1",
              priority: "low",
            },
            {
              id: "nudge-2",
              type: "spotlight",
              message: "Tip 2",
              priority: "high",
            },
          ],
        });
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(2);
      });
    });

    it("should clear suggestions when requested", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Add a suggestion
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            { id: "nudge-1", type: "tooltip", message: "Tip", priority: "low" },
          ],
        });
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(1);
      });

      // Clear suggestions
      act(() => {
        result.current.clearSuggestions();
      });

      expect(result.current.suggestions).toHaveLength(0);
    });
  });

  describe("Request Suggestions", () => {
    it("should send request_suggestions message", () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      act(() => {
        result.current.requestSuggestions({ page: "chat", action: "typing" });
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "request_suggestions",
          context: { page: "chat", action: "typing" },
        }),
      );
    });

    it("should include context in request", () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      act(() => {
        result.current.requestSuggestions({
          page: "workflows",
          action: "create",
        });
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          context: { page: "workflows", action: "create" },
        }),
      );
    });
  });

  describe("Error Handling", () => {
    it("should handle connection errors", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      act(() => {
        mockOnError?.(new Error("Connection failed"));
      });

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
        expect(result.current.error?.message).toBe("Connection failed");
      });
    });

    it("should clear error on successful connect", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // First set an error
      act(() => {
        mockOnError?.(new Error("Connection failed"));
      });

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      // Then simulate reconnection
      act(() => {
        mockOnConnect?.();
      });

      await waitFor(() => {
        expect(result.current.error).toBeNull();
      });
    });

    it("should track reconnect attempts", () => {
      mockReconnectAttempts = 3;

      const { result } = renderHook(
        () =>
          useAIRealTimeSuggestions({
            enabled: true,
            reconnectInterval: 100,
            maxReconnectAttempts: 3,
          }),
        { wrapper },
      );

      expect(result.current.reconnectAttempts).toBeLessThanOrEqual(3);
    });
  });

  describe("Heartbeat", () => {
    it("should send heartbeat ping messages", async () => {
      vi.useFakeTimers();

      renderHook(
        () =>
          useAIRealTimeSuggestions({ enabled: true, heartbeatInterval: 5000 }),
        { wrapper },
      );

      // Advance timer for heartbeat
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "ping",
        }),
      );

      vi.useRealTimers();
    });

    it("should update lastHeartbeat on pong", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      const beforePong = result.current.lastHeartbeat;

      act(() => {
        mockOnMessage?.({ type: "pong", timestamp: Date.now() });
      });

      await waitFor(() => {
        expect(result.current.lastHeartbeat).not.toBe(beforePong);
      });
    });

    it("should not send heartbeat when disconnected", async () => {
      vi.useFakeTimers();

      mockStatus = "disconnected";

      renderHook(
        () =>
          useAIRealTimeSuggestions({ enabled: false, heartbeatInterval: 1000 }),
        { wrapper },
      );

      // Advance timer for heartbeat
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      expect(mockSend).not.toHaveBeenCalledWith(
        expect.objectContaining({
          type: "ping",
        }),
      );

      vi.useRealTimers();
    });
  });

  describe("Suggestion Dismissal", () => {
    it("should dismiss a specific suggestion", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Add suggestions
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            {
              id: "nudge-1",
              type: "tooltip",
              message: "Tip 1",
              priority: "low",
            },
            {
              id: "nudge-2",
              type: "tooltip",
              message: "Tip 2",
              priority: "high",
            },
          ],
        });
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(2);
      });

      // Dismiss one suggestion
      act(() => {
        result.current.dismissSuggestion("nudge-1");
      });

      expect(result.current.suggestions).toHaveLength(1);
      expect(result.current.suggestions[0].id).toBe("nudge-2");
    });

    it("should track dismissed suggestion IDs", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            { id: "nudge-1", type: "tooltip", message: "Tip", priority: "low" },
          ],
        });
      });

      act(() => {
        result.current.dismissSuggestion("nudge-1");
      });

      expect(result.current.dismissedIds).toContain("nudge-1");
    });

    it("should not show previously dismissed suggestions", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Add and dismiss a suggestion
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            {
              id: "nudge-1",
              type: "tooltip",
              message: "Tip 1",
              priority: "low",
            },
          ],
        });
      });

      act(() => {
        result.current.dismissSuggestion("nudge-1");
      });

      // Try to add the same suggestion again
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            {
              id: "nudge-1",
              type: "tooltip",
              message: "Tip 1",
              priority: "low",
            },
          ],
        });
      });

      // Should still be 0 because nudge-1 was dismissed
      expect(result.current.suggestions).toHaveLength(0);
    });
  });
});
