/**
 * useAISuggestionsWebSocket Hook Tests (TDD)
 *
 * Tests for the AI Suggestions real-time WebSocket hook.
 * This hook provides real-time AI suggestion streaming for typing assistance.
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { api } from "../api";

// Mock the useRealtimeSync hook
const mockUseRealtimeSync = vi.fn();
vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: (options: unknown) => mockUseRealtimeSync(options),
}));

// Mock auth - useAppSelector must call the selector to get proper mocked values
vi.mock("../store/hooks", () => ({
  useAppSelector: (selector: () => unknown) => selector(),
  useAppDispatch: () => vi.fn(),
}));

vi.mock("../store/slices/authSlice", async () => {
  const actual = await vi.importActual("../store/slices/authSlice");
  return {
    ...actual,
    selectIsAuthenticated: () => true,
    selectWebSocketPermissions: () => ({ ai_suggestions: true }),
    logout: () => ({ type: "auth/logout" }),
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
import { useAISuggestionsWebSocket } from "./useAISuggestionsWebSocket";

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

describe("useAISuggestionsWebSocket", () => {
  const mockDisconnect = vi.fn();
  const mockReconnect = vi.fn();
  const mockSend = vi.fn();
  const capturedCallbacks: {
    onMessage: ((data: unknown) => void) | null;
  } = {
    onMessage: null,
  };

  beforeEach(() => {
    vi.resetAllMocks();
    capturedCallbacks.onMessage = null;

    // Default mock that captures callbacks
    mockUseRealtimeSync.mockImplementation(
      (options?: { onMessage?: (data: unknown) => void }) => {
        if (options?.onMessage) {
          capturedCallbacks.onMessage = options.onMessage;
        }
        return {
          status: "connected",
          send: mockSend,
          disconnect: mockDisconnect,
          reconnect: mockReconnect,
          reconnectAttempts: 0,
          lastMessageTime: null,
          metrics: {
            totalAttempts: 0,
            totalReconnections: 0,
            consecutiveFailures: 0,
            lastReconnectionTime: null,
            lastDisconnectionTime: null,
            avgReconnectionDurationMs: 0,
            totalReconnectionTimeMs: 0,
            failuresByReason: {},
            recentAttempts: [],
            successRate: 100,
          },
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

  // Shared mock return value structure for consistent testing
  const createMockReturn = (overrides: { status?: string } = {}) => ({
    status: overrides.status ?? "connected",
    send: mockSend,
    disconnect: mockDisconnect,
    reconnect: mockReconnect,
    reconnectAttempts: 0,
    lastMessageTime: null,
    metrics: {
      totalAttempts: 0,
      totalReconnections: 0,
      consecutiveFailures: 0,
      lastReconnectionTime: null,
      lastDisconnectionTime: null,
      avgReconnectionDurationMs: 0,
      totalReconnectionTimeMs: 0,
      failuresByReason: {},
      recentAttempts: [],
      successRate: 100,
    },
    resetMetrics: vi.fn(),
  });

  describe("connection status", () => {
    it("returns connected status when WebSocket is connected", () => {
      mockUseRealtimeSync.mockReturnValue(
        createMockReturn({ status: "connected" }),
      );

      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "test-session" }),
        { wrapper },
      );

      expect(result.current.status).toBe("connected");
    });

    it("returns disconnected status when WebSocket is disconnected", () => {
      mockUseRealtimeSync.mockReturnValue(
        createMockReturn({ status: "disconnected" }),
      );

      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "test-session" }),
        { wrapper },
      );

      expect(result.current.status).toBe("disconnected");
    });
  });

  describe("suggestion requests", () => {
    it("requestSuggestion sends suggestion_request message", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      act(() => {
        result.current.requestSuggestion("Hello, I need help with", 25);
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "suggestion_request",
          payload: {
            session_id: "session-123",
            input_text: "Hello, I need help with",
            cursor_position: 25,
            context_window: 500,
          },
        }),
      );
    });

    it("requestSuggestion accepts custom context_window", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      act(() => {
        result.current.requestSuggestion("Hello", 5, 1000);
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          payload: expect.objectContaining({
            context_window: 1000,
          }),
        }),
      );
    });

    it("requestSuggestion sets isPending to true", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      expect(result.current.isPending).toBe(false);

      act(() => {
        result.current.requestSuggestion("test", 4);
      });

      expect(result.current.isPending).toBe(true);
    });

    it("does not send request without sessionId", () => {
      const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

      const { result } = renderHook(() => useAISuggestionsWebSocket({}), {
        wrapper,
      });

      act(() => {
        result.current.requestSuggestion("test", 4);
      });

      expect(mockSend).not.toHaveBeenCalled();
      expect(warnSpy).toHaveBeenCalledWith(
        "Session ID required for AI suggestions",
      );

      warnSpy.mockRestore();
    });
  });

  describe("suggestion responses", () => {
    it("handles suggestion_response and stores suggestion", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      // Request a suggestion first
      act(() => {
        result.current.requestSuggestion("Hello", 5);
      });

      // Receive response
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "suggestion_response",
          payload: {
            suggestion_id: "sug-123",
            text: "I can help you with that!",
            confidence: 0.85,
            reasoning: "Based on greeting pattern",
          },
        });
      });

      expect(result.current.currentSuggestion).toMatchObject({
        suggestionId: "sug-123",
        text: "I can help you with that!",
        confidence: 0.85,
        reasoning: "Based on greeting pattern",
      });
      expect(result.current.isPending).toBe(false);
    });

    it("calls onSuggestion callback when suggestion is received", () => {
      const onSuggestion = vi.fn();
      renderHook(
        () =>
          useAISuggestionsWebSocket({
            sessionId: "session-123",
            onSuggestion,
          }),
        { wrapper },
      );

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "suggestion_response",
          payload: {
            suggestion_id: "sug-456",
            text: "Suggestion text",
            confidence: 0.9,
          },
        });
      });

      expect(onSuggestion).toHaveBeenCalledWith(
        expect.objectContaining({
          suggestionId: "sug-456",
          text: "Suggestion text",
          confidence: 0.9,
        }),
      );
    });
  });

  describe("error handling", () => {
    it("handles error messages and stores error", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      // Request a suggestion first
      act(() => {
        result.current.requestSuggestion("Hello", 5);
      });

      // Receive error
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: {
            code: "rate_limited",
            message: "Too many requests",
            retryable: true,
          },
        });
      });

      expect(result.current.lastError).toMatchObject({
        code: "rate_limited",
        message: "Too many requests",
        retryable: true,
      });
      expect(result.current.isPending).toBe(false);
    });

    it("calls onError callback when error is received", () => {
      const onError = vi.fn();
      renderHook(
        () =>
          useAISuggestionsWebSocket({
            sessionId: "session-123",
            onError,
          }),
        { wrapper },
      );

      act(() => {
        capturedCallbacks.onMessage?.({
          type: "error",
          payload: {
            code: "internal_error",
            message: "Something went wrong",
            retryable: false,
          },
        });
      });

      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          code: "internal_error",
        }),
      );
    });
  });

  describe("suggestion feedback", () => {
    it("acceptSuggestion sends suggestion_accept message", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      // Receive a suggestion first
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "suggestion_response",
          payload: {
            suggestion_id: "sug-789",
            text: "Test suggestion",
            confidence: 0.8,
          },
        });
      });

      act(() => {
        result.current.acceptSuggestion("sug-789");
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "suggestion_accept",
          payload: { suggestion_id: "sug-789" },
        }),
      );
      expect(result.current.currentSuggestion).toBeNull();
    });

    it("rejectSuggestion sends suggestion_reject message", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      act(() => {
        result.current.rejectSuggestion("sug-789", "Not helpful");
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "suggestion_reject",
          payload: {
            suggestion_id: "sug-789",
            reason: "Not helpful",
          },
        }),
      );
    });
  });

  describe("context updates", () => {
    it("updateContext sends context_update message", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      act(() => {
        result.current.updateContext("User is working on a Python project");
      });

      expect(mockSend).toHaveBeenCalledWith(
        expect.objectContaining({
          type: "context_update",
          payload: {
            session_id: "session-123",
            context: "User is working on a Python project",
          },
        }),
      );
    });

    it("does not send context update without sessionId", () => {
      const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});

      const { result } = renderHook(() => useAISuggestionsWebSocket({}), {
        wrapper,
      });

      act(() => {
        result.current.updateContext("some context");
      });

      expect(mockSend).not.toHaveBeenCalled();
      expect(warnSpy).toHaveBeenCalledWith(
        "Session ID required for context update",
      );

      warnSpy.mockRestore();
    });
  });

  describe("clearSuggestion", () => {
    it("clears current suggestion and pending state", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      // Set a suggestion
      act(() => {
        capturedCallbacks.onMessage?.({
          type: "suggestion_response",
          payload: {
            suggestion_id: "sug-123",
            text: "Test",
            confidence: 0.8,
          },
        });
      });

      expect(result.current.currentSuggestion).not.toBeNull();

      act(() => {
        result.current.clearSuggestion();
      });

      expect(result.current.currentSuggestion).toBeNull();
      expect(result.current.isPending).toBe(false);
    });
  });

  describe("initial state", () => {
    it("starts with null currentSuggestion", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      expect(result.current.currentSuggestion).toBeNull();
    });

    it("starts with isPending false", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      expect(result.current.isPending).toBe(false);
    });

    it("starts with null lastError", () => {
      const { result } = renderHook(
        () => useAISuggestionsWebSocket({ sessionId: "session-123" }),
        { wrapper },
      );

      expect(result.current.lastError).toBeNull();
    });
  });
});
