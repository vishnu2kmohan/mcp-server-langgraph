/**
 * useAISuggestionsFetch Hook Tests
 *
 * TDD - Comprehensive tests for AI suggestions fetch hook.
 *
 * Features:
 * - Fetches suggestions from API with debounce
 * - Caches suggestions using useAISuggestionsCache
 * - Auto-invalidates on session/artifact context change
 * - Tracks cache staleness
 * - Supports accept/dismiss/clear operations
 *
 * Reference: Phase 6 AI-Native Integration (UX Audit Plan)
 *
 * Memory Safety:
 * - Uses explicit cleanup() in afterEach
 * - Restores all mocks to prevent accumulation
 * - Uses vi.runAllTimersAsync() instead of waitFor where possible
 * - Clears storage between tests
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { http, HttpResponse, delay } from "msw";
import { server } from "../mocks/server";
import { useAISuggestionsFetch } from "./useAISuggestionsFetch";
import type { CachedSuggestion } from "./useAISuggestionsCache";

// =============================================================================
// Test Data
// =============================================================================

const mockSuggestions: CachedSuggestion[] = [
  { id: "sug-1", type: "completion", content: "Complete this code", confidence: 0.95 },
  { id: "sug-2", type: "fix", content: "Fix this bug", confidence: 0.85 },
  { id: "sug-3", type: "refactor", content: "Refactor for readability", confidence: 0.75 },
];

// =============================================================================
// Mocks
// =============================================================================

// Mock getAuthToken
vi.mock("../utils/storage", async () => {
  const actual = await vi.importActual("../utils/storage");
  return {
    ...actual,
    getAuthToken: vi.fn(() => "test-token"),
  };
});

// Mock devLogger to prevent console noise
vi.mock("../utils/devLogger", () => ({
  devLogger: {
    withPrefix: () => ({
      debug: vi.fn(),
      info: vi.fn(),
      warn: vi.fn(),
      error: vi.fn(),
    }),
  },
}));

// =============================================================================
// MSW Handler Helpers
// =============================================================================

/**
 * Create an MSW handler that returns the given suggestions
 */
function createSuggestionsHandler(suggestions: CachedSuggestion[]) {
  return http.get("/api/v1/ai/suggestions", async () => {
    // No delay for faster tests
    return HttpResponse.json({ suggestions });
  });
}

/**
 * Create an MSW handler that returns an error
 */
function createErrorHandler(status: number, statusText: string) {
  return http.get("/api/v1/ai/suggestions", async () => {
    return new HttpResponse(null, { status, statusText });
  });
}

/**
 * Create an MSW handler with delay
 */
function _createDelayedHandler(suggestions: CachedSuggestion[], delayMs: number) {
  return http.get("/api/v1/ai/suggestions", async () => {
    await delay(delayMs);
    return HttpResponse.json({ suggestions });
  });
}

// =============================================================================
// Tests
// =============================================================================

describe("useAISuggestionsFetch", () => {
  beforeEach(() => {
    // Clear storage before each test
    localStorage.clear();
    sessionStorage.clear();

    // Use fake timers for debounce testing
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();

    // Default successful MSW handler
    server.use(createSuggestionsHandler(mockSuggestions));
  });

  afterEach(async () => {
    // CRITICAL: Cleanup in correct order to prevent memory leaks
    // 1. First, cleanup React testing library
    cleanup();

    // 2. Run any pending timers to completion
    await vi.runAllTimersAsync();

    // 3. Clear storage
    localStorage.clear();
    sessionStorage.clear();

    // 4. Restore real timers
    vi.useRealTimers();

    // 5. Restore all mocks to prevent accumulation
    vi.restoreAllMocks();
  });

  describe("Basic Initialization", () => {
    it("returns empty suggestions when disabled", () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: false,
        })
      );

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("returns empty suggestions when artifactId is null", () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: null,
          sessionId: "session-1",
          enabled: true,
        })
      );

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });

    it("provides all expected interface methods", () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
        })
      );

      expect(typeof result.current.acceptSuggestion).toBe("function");
      expect(typeof result.current.dismissSuggestion).toBe("function");
      expect(typeof result.current.clearSuggestions).toBe("function");
      expect(typeof result.current.refresh).toBe("function");
      expect(typeof result.current.getCacheAge).toBe("function");
    });

    it("has isStale property", () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
        })
      );

      expect(typeof result.current.isStale).toBe("boolean");
    });
  });

  describe("API Fetching", () => {
    it("fetches suggestions after debounce delay", async () => {
      // Track if the handler was called
      let handlerCalled = false;
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          handlerCalled = true;
          return HttpResponse.json({ suggestions: mockSuggestions });
        })
      );

      renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 500,
        })
      );

      // Should not have fetched yet
      expect(handlerCalled).toBe(false);

      // Advance past debounce
      await act(async () => {
        await vi.advanceTimersByTimeAsync(500);
      });

      // Wait for the fetch to complete
      await waitFor(() => {
        expect(handlerCalled).toBe(true);
      });
    });

    it("returns fetched suggestions after successful API call", async () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions);
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("handles API errors gracefully", async () => {
      server.use(createErrorHandler(500, "Internal Server Error"));

      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      expect(result.current.error?.message).toContain("500");
      expect(result.current.suggestions).toEqual([]);
    });
  });

  describe("Debouncing", () => {
    it("uses default debounce of 500ms", async () => {
      let fetchCount = 0;
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          fetchCount++;
          return HttpResponse.json({ suggestions: mockSuggestions });
        })
      );

      renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
        })
      );

      // At 400ms, should not have fetched
      await act(async () => {
        await vi.advanceTimersByTimeAsync(400);
      });
      expect(fetchCount).toBe(0);

      // At 500ms, should fetch
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(fetchCount).toBe(1);
      });
    });

    it("respects custom debounce value", async () => {
      let fetchCount = 0;
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          fetchCount++;
          return HttpResponse.json({ suggestions: mockSuggestions });
        })
      );

      renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 1000,
        })
      );

      // At 900ms, should not have fetched
      await act(async () => {
        await vi.advanceTimersByTimeAsync(900);
      });
      expect(fetchCount).toBe(0);

      // At 1000ms, should fetch
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(fetchCount).toBe(1);
      });
    });
  });

  describe("Cache Integration", () => {
    it("caches suggestions after fetch", async () => {
      let fetchCount = 0;
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          fetchCount++;
          return HttpResponse.json({ suggestions: mockSuggestions });
        })
      );

      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions);
      });

      // Verify suggestions are available (cached in hook state)
      expect(fetchCount).toBe(1);
      expect(result.current.suggestions).toHaveLength(3);
    });

    it("getCacheAge returns time since cache creation", async () => {
      const now = Date.now();
      vi.setSystemTime(now);

      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions);
      });

      // Advance time by 30 seconds
      act(() => {
        vi.advanceTimersByTime(30000);
      });

      expect(result.current.getCacheAge()).toBeGreaterThanOrEqual(30000);
    });
  });

  describe("Accept/Dismiss/Clear Operations", () => {
    it("acceptSuggestion removes suggestion from list", async () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(3);
      });

      act(() => {
        result.current.acceptSuggestion("sug-1");
      });

      expect(result.current.suggestions).toHaveLength(2);
      expect(result.current.suggestions.find((s) => s.id === "sug-1")).toBeUndefined();
    });

    it("dismissSuggestion removes suggestion from list", async () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(3);
      });

      act(() => {
        result.current.dismissSuggestion("sug-2");
      });

      expect(result.current.suggestions).toHaveLength(2);
    });

    it("clearSuggestions removes all suggestions", async () => {
      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toHaveLength(3);
      });

      act(() => {
        result.current.clearSuggestions();
      });

      expect(result.current.suggestions).toEqual([]);
    });
  });

  describe("Refresh Functionality", () => {
    it("refresh bypasses cache and fetches new suggestions", async () => {
      let fetchCount = 0;
      const newSuggestions: CachedSuggestion[] = [
        { id: "new-1", type: "explain", content: "New suggestion", confidence: 0.99 },
      ];

      // Handler that returns different data on second call
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          fetchCount++;
          // Return mock data on first call, new data on subsequent calls
          const data = fetchCount === 1 ? mockSuggestions : newSuggestions;
          return HttpResponse.json({ suggestions: data });
        })
      );

      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions);
      });

      expect(fetchCount).toBe(1);

      // Call refresh
      await act(async () => {
        result.current.refresh();
        await vi.runAllTimersAsync();
      });

      await waitFor(() => {
        expect(fetchCount).toBe(2);
      });

      expect(result.current.suggestions).toEqual(newSuggestions);
    });
  });

  describe("Context Changes", () => {
    it("refetches when artifactId changes", async () => {
      let fetchCount = 0;
      let lastArtifactId = "";
      server.use(
        http.get("/api/v1/ai/suggestions", async ({ request }) => {
          fetchCount++;
          const url = new URL(request.url);
          lastArtifactId = url.searchParams.get("artifactId") ?? "";
          return HttpResponse.json({ suggestions: mockSuggestions });
        })
      );

      const { result, rerender } = renderHook(
        ({ artifactId }) =>
          useAISuggestionsFetch({
            artifactId,
            sessionId: "session-1",
            enabled: true,
            debounceMs: 100,
          }),
        { initialProps: { artifactId: "artifact-1" } }
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions);
      });

      expect(fetchCount).toBe(1);
      expect(lastArtifactId).toBe("artifact-1");

      // Change artifact
      rerender({ artifactId: "artifact-2" });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(fetchCount).toBe(2);
      });

      expect(lastArtifactId).toBe("artifact-2");
    });

    it("clears suggestions when disabled", async () => {
      const { result, rerender } = renderHook(
        ({ enabled }) =>
          useAISuggestionsFetch({
            artifactId: "artifact-1",
            sessionId: "session-1",
            enabled,
            debounceMs: 100,
          }),
        { initialProps: { enabled: true } }
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.suggestions).toEqual(mockSuggestions);
      });

      // Disable
      rerender({ enabled: false });

      expect(result.current.suggestions).toEqual([]);
    });
  });

  describe("Abort Handling", () => {
    it("handles rapid context changes without errors", async () => {
      // This test verifies that abort handling works correctly by
      // triggering multiple rapid fetches (which internally aborts previous ones)
      let _fetchCount = 0;
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          _fetchCount++;
          // Add delay to allow abort to happen
          await delay(50);
          return HttpResponse.json({ suggestions: mockSuggestions });
        })
      );

      const { result, rerender } = renderHook(
        ({ artifactId }) =>
          useAISuggestionsFetch({
            artifactId,
            sessionId: "session-1",
            enabled: true,
            debounceMs: 50,
          }),
        { initialProps: { artifactId: "artifact-1" } }
      );

      // Trigger first fetch
      await act(async () => {
        await vi.advanceTimersByTimeAsync(50);
      });

      // Immediately change artifact (should abort first fetch)
      rerender({ artifactId: "artifact-2" });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(50);
      });

      // Wait for completion
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // Should not have any errors from aborted requests
      expect(result.current.error).toBeNull();
    });
  });

  describe("Cleanup on Unmount", () => {
    it("does not call fetch after unmount", async () => {
      let fetchCount = 0;
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          fetchCount++;
          return HttpResponse.json({ suggestions: mockSuggestions });
        })
      );

      const { unmount } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      // Unmount before debounce completes
      unmount();

      // Advance past debounce
      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      // Fetch should not have been called since we unmounted first
      expect(fetchCount).toBe(0);
    });
  });

  describe("Empty Response Handling", () => {
    it("handles empty suggestions array", async () => {
      let fetchCalled = false;
      server.use(
        http.get("/api/v1/ai/suggestions", async () => {
          fetchCalled = true;
          return HttpResponse.json({ suggestions: [] });
        })
      );

      const { result } = renderHook(() =>
        useAISuggestionsFetch({
          artifactId: "artifact-1",
          sessionId: "session-1",
          enabled: true,
          debounceMs: 100,
        })
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      // Wait for fetch to complete
      await waitFor(() => {
        expect(fetchCalled).toBe(true);
      });

      // Give time for state to update
      await act(async () => {
        await vi.advanceTimersByTimeAsync(50);
      });

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.error).toBeNull();
    });
  });
});
