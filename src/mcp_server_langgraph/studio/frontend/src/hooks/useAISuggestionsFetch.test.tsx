/**
 * useAISuggestionsFetch Hook Tests
 *
 * TDD - Tests for AI suggestions fetching with opt-in behavior support.
 *
 * Features:
 * - Fetches suggestions from API with debounce
 * - Supports autoFetch option for opt-in behavior
 * - Caches suggestions using useAISuggestionsCache
 * - Supports accept/dismiss/clear operations
 */

import { describe, it, expect, beforeEach, afterEach, vi, Mock } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { BrowserRouter } from "react-router";
import React from "react";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// Mock dependencies
vi.mock("./useAISuggestionsCache", () => ({
  useAISuggestionsCache: vi.fn(() => ({
    suggestions: [],
    context: null,
    isStale: false,
    cacheSuggestions: vi.fn(),
    invalidateCache: vi.fn(),
    setContext: vi.fn(),
    getCacheAge: vi.fn(() => 0),
    dismissSuggestion: vi.fn(),
    clearDismissed: vi.fn(),
  })),
}));

vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: vi.fn(),
}));

vi.mock("../utils/intendedRoute", () => ({
  saveCurrentRouteAsIntended: vi.fn(),
}));

// Import after mocking
import { useAISuggestionsFetch } from "./useAISuggestionsFetch";
import { useAISuggestionsCache } from "./useAISuggestionsCache";
import { authenticatedFetch } from "../utils/authenticatedFetch";

// Wrapper with router context
const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe("useAISuggestionsFetch", () => {
  const mockCacheSuggestions = vi.fn();
  const mockSetContext = vi.fn();
  const mockDismissFromCache = vi.fn();
  const mockInvalidateCache = vi.fn();
  const mockClearDismissed = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Reset cache mock
    (useAISuggestionsCache as Mock).mockReturnValue({
      suggestions: [],
      context: null,
      isStale: false,
      cacheSuggestions: mockCacheSuggestions,
      invalidateCache: mockInvalidateCache,
      setContext: mockSetContext,
      getCacheAge: vi.fn(() => 0),
      dismissSuggestion: mockDismissFromCache,
      clearDismissed: mockClearDismissed,
    });

    // Default fetch mock - successful response
    (authenticatedFetch as Mock).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          suggestions: [
            { id: "1", type: "completion", content: "test", confidence: 0.9 },
          ],
        }),
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ==========================================================================
  // Opt-In Behavior Tests (autoFetch option)
  // ==========================================================================

  describe("autoFetch option (opt-in behavior)", () => {
    it("does NOT auto-fetch when autoFetch is false", async () => {
      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: false, // Opt-in mode
          }),
        { wrapper },
      );

      // Advance past debounce
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      // Should NOT have fetched
      expect(authenticatedFetch).not.toHaveBeenCalled();
      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });

    it("fetches only when refresh() is called with autoFetch=false", async () => {
      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: false,
          }),
        { wrapper },
      );

      // Initially no fetch
      await act(async () => {
        vi.advanceTimersByTime(1000);
      });
      expect(authenticatedFetch).not.toHaveBeenCalled();

      // Explicitly request suggestions
      await act(async () => {
        result.current.refresh();
        // Flush microtasks to allow async fetch to complete
        await Promise.resolve();
      });

      // Now should have fetched
      expect(authenticatedFetch).toHaveBeenCalledWith(
        "/api/v1/ai/suggestions?artifactId=artifact-123",
        expect.any(Object),
      );
    });

    it("auto-fetches when autoFetch is explicitly true", async () => {
      renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: true, // Explicit opt-in
          }),
        { wrapper },
      );

      // Advance past debounce
      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      // Should have auto-fetched
      expect(authenticatedFetch).toHaveBeenCalled();
    });

    it("does not re-fetch after dismiss when autoFetch=false", async () => {
      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: false,
          }),
        { wrapper },
      );

      // Manually trigger fetch
      await act(async () => {
        result.current.refresh();
        await Promise.resolve();
      });

      expect(authenticatedFetch).toHaveBeenCalledTimes(1);

      // Dismiss a suggestion
      act(() => {
        result.current.dismissSuggestion("1");
      });

      // Advance time - should NOT trigger another fetch
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      // Still only one fetch
      expect(authenticatedFetch).toHaveBeenCalledTimes(1);
    });

    it("clears all suggestions without re-fetching when autoFetch=false", async () => {
      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: false,
          }),
        { wrapper },
      );

      // Manually fetch first
      await act(async () => {
        result.current.refresh();
        await Promise.resolve();
      });

      expect(authenticatedFetch).toHaveBeenCalledTimes(1);

      // Clear suggestions
      act(() => {
        result.current.clearSuggestions();
      });

      // Advance time - should NOT re-fetch
      await act(async () => {
        vi.advanceTimersByTime(2000);
      });

      expect(authenticatedFetch).toHaveBeenCalledTimes(1);
      expect(result.current.suggestions).toEqual([]);
    });
  });

  // ==========================================================================
  // Opt-in Pattern Tests
  // ==========================================================================

  describe("opt-in pattern (autoFetch=false default)", () => {
    it("does NOT auto-fetch by default (opt-in pattern)", async () => {
      renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            // No autoFetch specified - should default to false
          }),
        { wrapper },
      );

      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      // Should NOT auto-fetch because autoFetch defaults to false
      expect(authenticatedFetch).not.toHaveBeenCalled();
    });

    it("re-fetches on artifact change when autoFetch=true", async () => {
      const { rerender } = renderHook(
        ({ artifactId }) =>
          useAISuggestionsFetch({
            artifactId,
            sessionId: "session-456",
            enabled: true,
            autoFetch: true,
          }),
        { wrapper, initialProps: { artifactId: "artifact-1" } },
      );

      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      expect(authenticatedFetch).toHaveBeenCalledTimes(1);

      // Change artifact
      rerender({ artifactId: "artifact-2" });

      await act(async () => {
        vi.advanceTimersByTime(600);
      });

      expect(authenticatedFetch).toHaveBeenCalledTimes(2);
    });
  });

  // ==========================================================================
  // Core Functionality Tests
  // ==========================================================================

  describe("core functionality", () => {
    it("returns initial empty state", () => {
      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: null,
            sessionId: "session-456",
            enabled: false,
          }),
        { wrapper },
      );

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("does not fetch when enabled is false", async () => {
      renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: false,
          }),
        { wrapper },
      );

      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      expect(authenticatedFetch).not.toHaveBeenCalled();
    });

    it("does not fetch when artifactId is null", async () => {
      renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: null,
            sessionId: "session-456",
            enabled: true,
          }),
        { wrapper },
      );

      await act(async () => {
        vi.advanceTimersByTime(1000);
      });

      expect(authenticatedFetch).not.toHaveBeenCalled();
    });

    it("handles fetch errors gracefully", async () => {
      (authenticatedFetch as Mock).mockRejectedValue(
        new Error("Network error"),
      );

      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: true,
          }),
        { wrapper },
      );

      await act(async () => {
        vi.advanceTimersByTime(600);
        // Flush microtasks to let the rejected promise propagate
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(result.current.error).toEqual(new Error("Network error"));
      expect(result.current.suggestions).toEqual([]);
    });

    it("acceptSuggestion removes suggestion from list", async () => {
      const mockSuggestions = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
        { id: "2", type: "fix", content: "fix this", confidence: 0.8 },
      ];

      (authenticatedFetch as Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ suggestions: mockSuggestions }),
      });

      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: true,
          }),
        { wrapper },
      );

      await act(async () => {
        vi.advanceTimersByTime(600);
        // Flush microtasks to let the resolved promise propagate
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(result.current.suggestions.length).toBe(2);

      act(() => {
        result.current.acceptSuggestion("1");
      });

      expect(result.current.suggestions.length).toBe(1);
      expect(result.current.suggestions[0].id).toBe("2");
    });

    it("dismissSuggestion removes suggestion and persists in cache", async () => {
      const mockSuggestions = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
      ];

      (authenticatedFetch as Mock).mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ suggestions: mockSuggestions }),
      });

      const { result } = renderHook(
        () =>
          useAISuggestionsFetch({
            artifactId: "artifact-123",
            sessionId: "session-456",
            enabled: true,
            autoFetch: true,
          }),
        { wrapper },
      );

      await act(async () => {
        vi.advanceTimersByTime(600);
        // Flush microtasks to let the resolved promise propagate
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(result.current.suggestions.length).toBe(1);

      act(() => {
        result.current.dismissSuggestion("1");
      });

      expect(result.current.suggestions.length).toBe(0);
      expect(mockDismissFromCache).toHaveBeenCalledWith("1");
    });
  });
});
