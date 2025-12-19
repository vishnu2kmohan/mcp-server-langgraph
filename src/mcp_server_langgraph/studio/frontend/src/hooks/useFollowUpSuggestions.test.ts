/**
 * useFollowUpSuggestions Hook Tests
 *
 * TDD tests for the hook that generates AI-powered follow-up suggestions
 * based on the last assistant message.
 *
 * Uses RTK Query mutation mocking for isolated testing.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { useFollowUpSuggestions } from "./useFollowUpSuggestions";
import { api } from "../api";

// Short debounce for tests to keep them fast
const TEST_DEBOUNCE_MS = 10;

// Mock the RTK Query mutation hooks
const mockMutationFn = vi.fn();
const mockReset = vi.fn();
const mockTrackClickFn = vi
  .fn()
  .mockReturnValue(Promise.resolve({ data: { tracked: true } }));
const mockSubmitFeedbackFn = vi
  .fn()
  .mockReturnValue(Promise.resolve({ data: { recorded: true } }));
let mockMutationState = {
  data: undefined as unknown,
  isLoading: false,
  error: undefined as unknown,
};

vi.mock("../api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api")>();
  return {
    ...original,
    useGetChatFollowUpSuggestionsMutation: () => [
      mockMutationFn,
      { ...mockMutationState, reset: mockReset },
    ],
    useTrackSuggestionClickMutation: () => [mockTrackClickFn, {}],
    useSubmitSuggestionFeedbackMutation: () => [mockSubmitFeedbackFn, {}],
  };
});

/**
 * Create a wrapper with Redux Provider for RTK Query
 */
function createWrapper() {
  const store = configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(Provider, { store }, children);
  };
}

describe("useFollowUpSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMutationState = {
      data: undefined,
      isLoading: false,
      error: undefined,
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("initial state", () => {
    it("should return empty suggestions when no content provided", () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({ content: "", debounceMs: TEST_DEBOUNCE_MS }),
        { wrapper: createWrapper() },
      );

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should return empty suggestions when content is null", () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: null as unknown as string,
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });

    it("should return empty suggestions when disabled", () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello world",
            enabled: false,
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("suggestion generation", () => {
    it("should set loading state while debouncing", () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "This is a response about AI",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // Should be loading immediately when content is provided (debouncing)
      expect(result.current.isLoading).toBe(true);
    });

    it("should call mutation after debounce", async () => {
      const { result: _result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "This is a response about AI",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalledWith({
            content: "This is a response about AI",
            session_id: undefined,
            max_suggestions: 4,
          });
        },
        { timeout: 1000 },
      );
    });

    it("should generate suggestions from API response", async () => {
      const mockSuggestions = [
        { id: "1", text: "Tell me more about this", category: "explore" },
        { id: "2", text: "Can you give an example?", category: "example" },
      ];

      // Update the mock state to have data
      mockMutationState = {
        data: { suggestions: mockSuggestions },
        isLoading: false,
        error: undefined,
      };

      const { result, rerender } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "This is a response about AI",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // Wait for debounce
      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalled();
        },
        { timeout: 1000 },
      );

      // Force rerender to pick up new mock state
      rerender();

      await waitFor(
        () => {
          expect(result.current.suggestions).toEqual(mockSuggestions);
          expect(result.current.isLoading).toBe(false);
        },
        { timeout: 1000 },
      );
    });

    it("should handle API errors gracefully", async () => {
      mockMutationState = {
        data: undefined,
        isLoading: false,
        error: { status: 500 },
      };

      const { result, rerender } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "This is a response about AI",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // Wait for debounce
      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalled();
        },
        { timeout: 1000 },
      );

      // Force rerender to pick up new mock state
      rerender();

      expect(result.current.error).toBe("API error: 500");
      expect(result.current.suggestions).toEqual([]);
    });

    it("should handle network errors gracefully", async () => {
      mockMutationState = {
        data: undefined,
        isLoading: false,
        error: { message: "Network error" },
      };

      const { result, rerender } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "This is a response about AI",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // Wait for debounce
      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalled();
        },
        { timeout: 1000 },
      );

      // Force rerender to pick up new mock state
      rerender();

      expect(result.current.error).toBe("Network error");
      expect(result.current.suggestions).toEqual([]);
    });
  });

  describe("refresh functionality", () => {
    it("should provide a refresh function", () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      expect(typeof result.current.refresh).toBe("function");
    });

    it("should call mutation again when refresh is called", async () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // Wait for initial debounce
      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalledTimes(1);
        },
        { timeout: 1000 },
      );

      // Call refresh
      act(() => {
        result.current.refresh();
      });

      // Should be called again immediately (no debounce for manual refresh)
      expect(mockMutationFn).toHaveBeenCalledTimes(2);
    });
  });

  describe("content change handling", () => {
    it("should call mutation when content changes", async () => {
      const { rerender } = renderHook(
        ({ content }) =>
          useFollowUpSuggestions({ content, debounceMs: TEST_DEBOUNCE_MS }),
        {
          initialProps: { content: "First message" },
          wrapper: createWrapper(),
        },
      );

      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalledWith({
            content: "First message",
            session_id: undefined,
            max_suggestions: 4,
          });
        },
        { timeout: 1000 },
      );

      rerender({ content: "Second message" });

      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalledWith({
            content: "Second message",
            session_id: undefined,
            max_suggestions: 4,
          });
        },
        { timeout: 1000 },
      );
    });

    it("should debounce rapid content changes", async () => {
      const { rerender } = renderHook(
        ({ content }) => useFollowUpSuggestions({ content, debounceMs: 50 }),
        { initialProps: { content: "a" }, wrapper: createWrapper() },
      );

      // Rapid changes - each should reset the debounce timer
      rerender({ content: "ab" });
      rerender({ content: "abc" });
      rerender({ content: "abcd" });

      // Wait for debounce to settle
      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalled();
        },
        { timeout: 1000 },
      );

      // Should only be called once with the final content (debounced)
      const lastCall =
        mockMutationFn.mock.calls[mockMutationFn.mock.calls.length - 1];
      expect(lastCall[0].content).toBe("abcd");
    });
  });

  describe("maximum suggestions", () => {
    it("should limit suggestions to maxSuggestions", async () => {
      const mockSuggestions = [
        { id: "1", text: "Suggestion 1" },
        { id: "2", text: "Suggestion 2" },
        { id: "3", text: "Suggestion 3" },
        { id: "4", text: "Suggestion 4" },
        { id: "5", text: "Suggestion 5" },
      ];

      mockMutationState = {
        data: { suggestions: mockSuggestions },
        isLoading: false,
        error: undefined,
      };

      const { result, rerender } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            maxSuggestions: 3,
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // Wait for debounce
      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalled();
        },
        { timeout: 1000 },
      );

      // Force rerender to pick up new mock state
      rerender();

      expect(result.current.suggestions.length).toBe(3);
    });

    it("should pass maxSuggestions to mutation", async () => {
      const { result: _result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            maxSuggestions: 6,
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalledWith({
            content: "Hello",
            session_id: undefined,
            max_suggestions: 6,
          });
        },
        { timeout: 1000 },
      );
    });
  });

  describe("session ID", () => {
    it("should pass sessionId to mutation", async () => {
      const { result: _result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            sessionId: "session-123",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalledWith({
            content: "Hello",
            session_id: "session-123",
            max_suggestions: 4,
          });
        },
        { timeout: 1000 },
      );
    });
  });

  describe("suggestion click tracking", () => {
    beforeEach(() => {
      // Reset tracking mock and restore the promise return value
      mockTrackClickFn.mockReset();
      mockTrackClickFn.mockReturnValue(
        Promise.resolve({ data: { tracked: true } }),
      );
    });

    it("should expose a trackClick function", () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      expect(typeof result.current.trackClick).toBe("function");
    });

    it("should call trackClick with correct parameters", async () => {
      const mockSuggestions = [
        { id: "sugg-1", text: "Tell me more", category: "explore" },
      ];

      mockMutationState = {
        data: { suggestions: mockSuggestions },
        isLoading: false,
        error: undefined,
      };

      const { result, rerender } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            sessionId: "session-123",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // Wait for suggestions to load
      await waitFor(
        () => {
          expect(mockMutationFn).toHaveBeenCalled();
        },
        { timeout: 1000 },
      );

      rerender();

      // Call trackClick with a suggestion
      act(() => {
        result.current.trackClick({
          id: "sugg-1",
          text: "Tell me more",
          category: "explore",
        });
      });

      // Verify trackClick was called with correct parameters
      expect(mockTrackClickFn).toHaveBeenCalledWith({
        suggestion_id: "sugg-1",
        suggestion_type: "chat_followup",
        category: "explore",
        session_id: "session-123",
      });
    });

    it("should handle tracking errors gracefully", async () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // trackClick should not throw even if tracking fails
      expect(() => {
        act(() => {
          result.current.trackClick({
            id: "sugg-1",
            text: "Test suggestion",
            category: "explore",
          });
        });
      }).not.toThrow();
    });

    it("should include category in tracking request", async () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            sessionId: "session-456",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      act(() => {
        result.current.trackClick({
          id: "sugg-2",
          text: "Show me an example",
          category: "example",
        });
      });

      // Verify trackClick was called with the category
      expect(mockTrackClickFn).toHaveBeenCalledWith({
        suggestion_id: "sugg-2",
        suggestion_type: "chat_followup",
        category: "example",
        session_id: "session-456",
      });
    });

    it("should handle undefined category", async () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      act(() => {
        result.current.trackClick({
          id: "sugg-3",
          text: "Generic suggestion",
          // No category
        });
      });

      // Verify trackClick was called with undefined category
      expect(mockTrackClickFn).toHaveBeenCalledWith({
        suggestion_id: "sugg-3",
        suggestion_type: "chat_followup",
        category: undefined,
        session_id: undefined,
      });
    });
  });

  describe("suggestion feedback submission", () => {
    beforeEach(() => {
      // Reset feedback mock and restore the promise return value
      mockSubmitFeedbackFn.mockReset();
      mockSubmitFeedbackFn.mockReturnValue(
        Promise.resolve({ data: { recorded: true } }),
      );
    });

    it("should expose a submitFeedback function", () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      expect(typeof result.current.submitFeedback).toBe("function");
    });

    it("should call submitFeedback with correct parameters for positive feedback", async () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            sessionId: "session-123",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      act(() => {
        result.current.submitFeedback(
          { id: "sugg-1", text: "Tell me more", category: "explore" },
          "positive",
        );
      });

      // Verify submitFeedback was called with correct parameters
      expect(mockSubmitFeedbackFn).toHaveBeenCalledWith({
        suggestion_id: "sugg-1",
        suggestion_type: "chat_followup",
        feedback: "positive",
        category: "explore",
        session_id: "session-123",
      });
    });

    it("should call submitFeedback with correct parameters for negative feedback", async () => {
      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            sessionId: "session-456",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      act(() => {
        result.current.submitFeedback(
          { id: "sugg-2", text: "Show me an example", category: "example" },
          "negative",
        );
      });

      // Verify submitFeedback was called with correct parameters
      expect(mockSubmitFeedbackFn).toHaveBeenCalledWith({
        suggestion_id: "sugg-2",
        suggestion_type: "chat_followup",
        feedback: "negative",
        category: "example",
        session_id: "session-456",
      });
    });

    it("should handle feedback errors gracefully", async () => {
      mockSubmitFeedbackFn.mockReturnValue(
        Promise.reject(new Error("API error")),
      );

      const { result } = renderHook(
        () =>
          useFollowUpSuggestions({
            content: "Hello",
            debounceMs: TEST_DEBOUNCE_MS,
          }),
        { wrapper: createWrapper() },
      );

      // submitFeedback should not throw even if submission fails
      expect(() => {
        act(() => {
          result.current.submitFeedback(
            { id: "sugg-1", text: "Test suggestion", category: "explore" },
            "positive",
          );
        });
      }).not.toThrow();
    });
  });
});
