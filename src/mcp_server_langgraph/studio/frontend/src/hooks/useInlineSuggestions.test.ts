/**
 * useInlineSuggestions Hook Tests
 *
 * Tests for AI inline suggestions hook following TDD.
 * This hook manages the AI suggestion lifecycle for chat input.
 */

import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock react-router
const mockNavigate = vi.fn();
vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
}));

// Mock authenticatedFetch
const mockAuthenticatedFetch = vi.fn();
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: (...args: unknown[]) => mockAuthenticatedFetch(...args),
}));

// Mock intendedRoute
const mockSetIntendedRoute = vi.fn();
vi.mock("../utils/intendedRoute", () => ({
  setIntendedRoute: (...args: unknown[]) => mockSetIntendedRoute(...args),
}));

import { useInlineSuggestions } from "./useInlineSuggestions";

// Mock debounce to execute immediately in tests
vi.mock("lodash/debounce", () => ({
  default: vi.fn((fn) => {
    const debouncedFn = fn;
    debouncedFn.cancel = vi.fn();
    return debouncedFn;
  }),
}));

describe("useInlineSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("initialization", () => {
    it("should return empty suggestion initially", () => {
      const { result } = renderHook(() => useInlineSuggestions());

      expect(result.current.suggestion).toBe("");
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should respect enabled option", () => {
      const { result } = renderHook(() =>
        useInlineSuggestions({ enabled: false }),
      );

      expect(result.current.suggestion).toBe("");

      // Updating input should not trigger fetch when disabled
      act(() => {
        result.current.updateInput("Hello ");
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("input handling", () => {
    it("should not fetch suggestions for short input", () => {
      const { result } = renderHook(() =>
        useInlineSuggestions({ minLength: 5 }),
      );

      act(() => {
        result.current.updateInput("Hi");
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.suggestion).toBe("");
    });

    it("should trigger loading for valid input", async () => {
      const mockFetch = vi.fn().mockResolvedValue("world!");
      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          minLength: 3,
          fetchSuggestion: mockFetch,
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
      });

      expect(mockFetch).toHaveBeenCalledWith("Hello ", expect.anything());
    });

    it("should clear suggestion when input is cleared", () => {
      const { result } = renderHook(() => useInlineSuggestions());

      act(() => {
        result.current.updateInput("Hello ");
      });

      act(() => {
        result.current.updateInput("");
      });

      expect(result.current.suggestion).toBe("");
    });
  });

  describe("suggestion lifecycle", () => {
    it("should accept suggestion and clear it", () => {
      const onAccept = vi.fn();
      const { result } = renderHook(() => useInlineSuggestions({ onAccept }));

      // Manually set suggestion for testing
      act(() => {
        result.current.setSuggestion("world!");
      });

      expect(result.current.suggestion).toBe("world!");

      act(() => {
        result.current.acceptSuggestion();
      });

      expect(onAccept).toHaveBeenCalledWith("world!");
      expect(result.current.suggestion).toBe("");
    });

    it("should dismiss suggestion and clear it", () => {
      const onDismiss = vi.fn();
      const { result } = renderHook(() => useInlineSuggestions({ onDismiss }));

      act(() => {
        result.current.setSuggestion("world!");
      });

      act(() => {
        result.current.dismissSuggestion();
      });

      expect(onDismiss).toHaveBeenCalled();
      expect(result.current.suggestion).toBe("");
    });
  });

  describe("debouncing", () => {
    it("should call fetch for each input change with mocked debounce", async () => {
      const mockFetch = vi.fn().mockResolvedValue("suggestion");
      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          fetchSuggestion: mockFetch,
          debounceMs: 300,
        }),
      );

      // With mocked debounce (no delay), each call triggers fetch
      await act(async () => {
        result.current.updateInput("Hello");
      });

      // Should have called fetch
      expect(mockFetch).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("should set error when fetch fails", async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error("Network error"));
      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          fetchSuggestion: mockFetch,
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
        // Wait for the promise to resolve/reject
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(result.current.error).toBe("Network error");
      });
      expect(result.current.suggestion).toBe("");
    });

    it("should clear error on new input", async () => {
      const mockFetch = vi
        .fn()
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce("world!");

      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          fetchSuggestion: mockFetch,
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(result.current.error).toBe("Network error");
      });

      // New input should clear error
      act(() => {
        result.current.updateInput("Hello world ");
      });

      // Error should be cleared immediately
      expect(result.current.error).toBeNull();
    });
  });

  describe("cleanup", () => {
    it("should have abort controller for cleanup", () => {
      const { result, unmount } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
        }),
      );

      // Trigger a fetch to create abort controller
      act(() => {
        result.current.updateInput("Hello ");
      });

      // Unmount should not throw
      expect(() => unmount()).not.toThrow();
    });
  });

  describe("session context", () => {
    it("should pass session ID to fetch function", async () => {
      const mockFetch = vi.fn().mockResolvedValue("suggestion");
      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          fetchSuggestion: mockFetch,
          sessionId: "session-123",
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
      });

      expect(mockFetch).toHaveBeenCalledWith(
        "Hello ",
        expect.objectContaining({
          sessionId: "session-123",
        }),
      );
    });
  });

  describe("authentication", () => {
    it("should use authenticatedFetch for default suggestion fetch", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            suggestions: [{ text: "world!", confidence: 0.8 }],
          }),
      });

      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          sessionId: "session-123",
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(mockAuthenticatedFetch).toHaveBeenCalledWith(
          "/api/v1/ai/chat-suggestions",
          expect.objectContaining({
            method: "POST",
            onAuthFailure: expect.any(Function),
          }),
        );
      });
    });

    it("should navigate to login on auth failure", async () => {
      mockAuthenticatedFetch.mockImplementationOnce(
        async (_url: string, options: { onAuthFailure?: () => void }) => {
          options.onAuthFailure?.();
          return { ok: false, status: 401 };
        },
      );

      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          sessionId: "session-123",
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(mockSetIntendedRoute).toHaveBeenCalled();
      });

      expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
    });

    it("should gracefully degrade when API returns non-401 error", async () => {
      mockAuthenticatedFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          sessionId: "session-123",
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should gracefully degrade - no redirect, empty suggestion
      expect(mockNavigate).not.toHaveBeenCalled();
      expect(result.current.suggestion).toBe("");
    });
  });

  describe("confidence threshold", () => {
    it("should not show suggestions below confidence threshold", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        text: "world!",
        confidence: 0.3,
      });

      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          fetchSuggestion: mockFetch,
          minConfidence: 0.5,
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.suggestion).toBe("");
    });

    it("should show suggestions above confidence threshold", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        text: "world!",
        confidence: 0.8,
      });

      const { result } = renderHook(() =>
        useInlineSuggestions({
          enabled: true,
          fetchSuggestion: mockFetch,
          minConfidence: 0.5,
        }),
      );

      await act(async () => {
        result.current.updateInput("Hello ");
        await Promise.resolve();
      });

      await waitFor(() => {
        expect(result.current.suggestion).toBe("world!");
      });
    });
  });
});
