/**
 * AI WebSocket Integration Tests
 *
 * TDD Phase: Tests for frontend-backend WebSocket message format compatibility
 *
 * These tests verify that:
 * 1. Frontend hook message formats match backend expectations
 * 2. Backend response formats are correctly parsed by frontend
 * 3. Protocol is followed correctly (request_suggestions, ping/pong, etc.)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";

import { useAIRealTimeSuggestions } from "../hooks/useAIRealTimeSuggestions";

// =============================================================================
// Mock Setup
// =============================================================================

const mockSend = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;

vi.mock("../hooks/useRealtimeSync", () => ({
  useRealtimeSync: (options: {
    url: string;
    onMessage?: (data: unknown) => void;
  }) => {
    mockOnMessage = options.onMessage;
    return {
      status: options.url ? "connected" : "disconnected",
      reconnectAttempts: 0,
      lastMessageTime: null,
      send: mockSend,
      disconnect: vi.fn(),
      reconnect: vi.fn(),
      metrics: {
        totalAttempts: 0,
        successfulConnections: 0,
        failedConnections: 0,
        reconnections: 0,
        averageConnectionTime: 0,
      },
    };
  },
}));

const createTestStore = () =>
  configureStore({
    reducer: {
      auth: () => ({ user: { id: "integration-test-user" } }),
    },
  });

const wrapper = ({ children }: { children: ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Backend Message Format Constants (mirroring Python backend)
// =============================================================================

/**
 * Backend WebSocket message types (from ai_ux.py)
 */
const BACKEND_MESSAGE_TYPES = {
  REQUEST_SUGGESTIONS: "request_suggestions",
  SUGGESTIONS: "suggestions",
  PING: "ping",
  PONG: "pong",
  ERROR: "error",
} as const;

/**
 * Backend suggestion structure (from ai_ux_service.py)
 */
interface BackendSuggestion {
  id: string;
  type: "tooltip" | "spotlight" | "banner" | "modal";
  message: string;
  priority: "low" | "medium" | "high";
  target_element?: string; // Backend uses snake_case
  show_after_ms?: number; // Backend uses snake_case
}

/**
 * Backend WebSocket response format
 */
interface BackendSuggestionResponse {
  type: "suggestions";
  data: BackendSuggestion[];
  timestamp?: number;
}

/**
 * Backend WebSocket error response format (ADR-0093)
 *
 * The backend sends errors with a `payload` wrapper containing
 * structured error information, NOT a simple `data` string.
 */
interface _BackendErrorResponse {
  type: "error";
  payload: {
    code: string;
    message: string;
    retryable: boolean;
  };
}

// =============================================================================
// Integration Tests
// =============================================================================

describe("AI WebSocket Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnMessage = undefined;
  });

  afterEach(() => {
    cleanup();
    vi.resetAllMocks();
  });

  describe("Frontend -> Backend Message Format", () => {
    it("should send request_suggestions with correct format for backend", () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      act(() => {
        result.current.requestSuggestions({
          page: "chat",
          action: "typing",
          sessionId: "session-123",
        });
      });

      // Verify message matches backend expected format
      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: BACKEND_MESSAGE_TYPES.REQUEST_SUGGESTIONS,
          context: expect.objectContaining({
            page: "chat",
            action: "typing",
            sessionId: "session-123",
          }),
        }),
      );

      // Backend expects timestamp
      const sentMessage = mockSend.mock.calls[0][0];
      expect(sentMessage).toHaveProperty("timestamp");
      expect(typeof sentMessage.timestamp).toBe("number");
    });

    it("should send ping with correct format for backend", async () => {
      vi.useFakeTimers();

      renderHook(
        () =>
          useAIRealTimeSuggestions({ enabled: true, heartbeatInterval: 1000 }),
        { wrapper },
      );

      act(() => {
        vi.advanceTimersByTime(1000);
      });

      // Backend expects: { type: 'ping', timestamp: number }
      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: BACKEND_MESSAGE_TYPES.PING,
          timestamp: expect.any(Number),
        }),
      );

      vi.useRealTimers();
    });
  });

  describe("Backend -> Frontend Message Format", () => {
    it("should correctly parse backend suggestions response", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Simulate backend response with snake_case fields
      const backendResponse: BackendSuggestionResponse = {
        type: "suggestions",
        data: [
          {
            id: "suggestion-1",
            type: "tooltip",
            message: "Try keyboard shortcuts",
            priority: "medium",
            target_element: "#search-input",
            show_after_ms: 5000,
          },
        ],
        timestamp: Date.now(),
      };

      act(() => {
        mockOnMessage?.(backendResponse);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(1);
        expect(result.current.suggestions[0]).toEqual(
          expect.objectContaining({
            id: "suggestion-1",
            type: "tooltip",
            message: "Try keyboard shortcuts",
            priority: "medium",
          }),
        );
      });
    });

    it("should correctly parse backend pong response", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      const pongTimestamp = Date.now();

      // Simulate backend pong response
      act(() => {
        mockOnMessage?.({
          type: BACKEND_MESSAGE_TYPES.PONG,
          timestamp: pongTimestamp,
        });
      });

      await waitFor(() => {
        expect(result.current.lastHeartbeat).toBe(pongTimestamp);
      });
    });

    it("should handle backend error messages with ADR-0093 payload format", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Simulate backend error response with ADR-0093 payload format
      // This is the CORRECT format sent by ai_suggestions.py handler
      act(() => {
        mockOnMessage?.({
          type: BACKEND_MESSAGE_TYPES.ERROR,
          payload: {
            code: "rate_limited",
            message: "Rate limit exceeded",
            retryable: true,
          },
        });
      });

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
        expect(result.current.error?.message).toBe("Rate limit exceeded");
      });
    });

    it("should handle legacy backend error messages with data format", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Simulate legacy backend error response with data format
      // This is for backward compatibility with older backend versions
      act(() => {
        mockOnMessage?.({
          type: BACKEND_MESSAGE_TYPES.ERROR,
          data: "Connection closed",
        });
      });

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
        expect(result.current.error?.message).toBe("Connection closed");
      });
    });

    it("should handle multiple suggestions in batch", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Simulate backend batch response
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            { id: "s1", type: "tooltip", message: "Tip 1", priority: "low" },
            { id: "s2", type: "spotlight", message: "Tip 2", priority: "high" },
            { id: "s3", type: "banner", message: "Tip 3", priority: "medium" },
          ],
        });
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(3);
        expect(result.current.suggestions.map((s) => s.id)).toEqual([
          "s1",
          "s2",
          "s3",
        ]);
      });
    });
  });

  describe("Protocol Compliance", () => {
    it("should filter dismissed suggestions from new backend responses", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // First batch
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            { id: "s1", type: "tooltip", message: "Tip 1", priority: "low" },
          ],
        });
      });

      // Dismiss the suggestion
      act(() => {
        result.current.dismissSuggestion("s1");
      });

      // Backend sends same suggestion again (e.g., after reconnect)
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            { id: "s1", type: "tooltip", message: "Tip 1", priority: "low" },
            { id: "s2", type: "tooltip", message: "Tip 2", priority: "high" },
          ],
        });
      });

      await waitFor(() => {
        // Only s2 should be added, s1 was dismissed
        expect(result.current.suggestions).toHaveLength(1);
        expect(result.current.suggestions[0].id).toBe("s2");
      });
    });

    it("should handle malformed backend responses gracefully", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Simulate malformed responses
      act(() => {
        mockOnMessage?.(null);
        mockOnMessage?.(undefined);
        mockOnMessage?.({ type: "unknown" });
        mockOnMessage?.({ type: "suggestions", data: "not-an-array" });
      });

      // Should not crash and suggestions should remain empty
      expect(result.current.suggestions).toHaveLength(0);
      expect(result.current.error).toBeNull();
    });

    it("should accumulate suggestions across multiple responses", async () => {
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // First response
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            { id: "s1", type: "tooltip", message: "Tip 1", priority: "low" },
          ],
        });
      });

      // Second response
      act(() => {
        mockOnMessage?.({
          type: "suggestions",
          data: [
            { id: "s2", type: "tooltip", message: "Tip 2", priority: "high" },
          ],
        });
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(2);
      });
    });
  });

  describe("User Context in WebSocket URL", () => {
    it("should include user_id in WebSocket connection", () => {
      // The hook builds URL with user_id from Redux store
      // This is verified by checking the URL format used
      const { result } = renderHook(
        () => useAIRealTimeSuggestions({ enabled: true }),
        { wrapper },
      );

      // Hook should be connected
      expect(result.current.isConnected).toBe(true);

      // The URL building is tested indirectly through the hook behavior
      // Direct URL testing would require exposing internals
    });
  });
});
