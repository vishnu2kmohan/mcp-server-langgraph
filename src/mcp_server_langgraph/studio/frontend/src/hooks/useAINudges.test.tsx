/**
 * useAINudges Hook Tests
 *
 * TDD - Sprint 3 - Phase 6.3: AI-Driven Smart Nudges
 *
 * Features tested:
 * - AI-powered nudge timing and recommendations
 * - Fogg model integration (motivation + ability = trigger)
 * - Nudge personalization based on user behavior
 * - Learning from nudge acceptance/dismissal patterns
 * - Integration with nudgeSlice Redux state
 *
 * Backend endpoint: POST /api/v1/ai/nudges/recommend
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { http, HttpResponse, delay } from "msw";
import { server } from "../mocks/server";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import { useAINudges } from "./useAINudges";
import nudgeReducer from "../store/slices/nudgeSlice";
import type { NudgePriority, NudgeType } from "./useNudges";
import { api } from "../api";

// =============================================================================
// Test Data (RTK Query format)
// =============================================================================

// RTK Query returns: { nudge_type, message, confidence, action_cta, trigger_delay_ms }
const mockNudgeRecommendation = {
  nudge_type: "tooltip",
  message: "Pro tip: Press Cmd+K for quick search",
  confidence: 0.88,
  action_cta: "Try it now",
  trigger_delay_ms: 5000,
};

const mockNoNudgeRecommendation = {
  nudge_type: "",
  message: "",
  confidence: 0.2,
  action_cta: undefined,
  trigger_delay_ms: undefined,
};

// Keep old format for reference - these types are unused now
type _OldNudgeType = NudgeType;
type _OldNudgePriority = NudgePriority;

// =============================================================================
// Test Utilities
// =============================================================================

function createTestStore() {
  return configureStore({
    reducer: {
      nudge: nudgeReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
}

function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

// =============================================================================
// MSW Handler Helpers
// =============================================================================

function createNudgeHandler(
  response: typeof mockNudgeRecommendation | typeof mockNoNudgeRecommendation,
) {
  // Use wildcard prefix to match any origin (RTK Query uses full URL like http://127.0.0.1:3000/...)
  return http.post("*/api/v1/ai/nudges/recommend", async () => {
    return HttpResponse.json(response);
  });
}

function _createDelayedHandler(
  response: typeof mockNudgeRecommendation,
  delayMs: number,
) {
  return http.post("*/api/v1/ai/nudges/recommend", async () => {
    await delay(delayMs);
    return HttpResponse.json(response);
  });
}

function createErrorHandler(status: number) {
  return http.post("*/api/v1/ai/nudges/recommend", async () => {
    return new HttpResponse(null, { status });
  });
}

// =============================================================================
// Tests
// =============================================================================

describe("useAINudges", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    localStorage.clear();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.clearAllMocks();
    server.use(createNudgeHandler(mockNudgeRecommendation));
  });

  afterEach(async () => {
    cleanup();
    await vi.runAllTimersAsync();
    localStorage.clear();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe("Initialization", () => {
    it("initializes with no active nudge when disabled", () => {
      const { result } = renderHook(() => useAINudges({ enabled: false }), {
        wrapper: createWrapper(store),
      });

      expect(result.current.activeNudge).toBeNull();
      expect(result.current.isLoading).toBe(false);
    });

    it("provides all expected interface methods", () => {
      const { result } = renderHook(() => useAINudges({ enabled: false }), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.fetchRecommendation).toBe("function");
      expect(typeof result.current.acceptNudge).toBe("function");
      expect(typeof result.current.dismissNudge).toBe("function");
      expect(typeof result.current.trackInteraction).toBe("function");
      expect(typeof result.current.getStats).toBe("function");
    });
  });

  describe("Fetching Recommendations", () => {
    it("fetches nudge recommendation when enabled", async () => {
      const { result } = renderHook(
        () => useAINudges({ enabled: true, pageContext: "chat" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.recommendation).not.toBeNull();
      });

      // Nudge ID is now generated dynamically (nudge-{timestamp})
      expect(result.current.recommendation?.nudge?.id).toMatch(/^nudge-\d+$/);
      expect(result.current.recommendation?.confidence).toBe(0.88);
    });

    it("shows nudge after specified delay", async () => {
      const { result } = renderHook(
        () => useAINudges({ enabled: true, pageContext: "chat" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.recommendation).not.toBeNull();
      });

      // Nudge should not be active yet (needs to wait for show_after_ms)
      expect(result.current.activeNudge).toBeNull();

      // Advance past the show_after_ms delay (5000ms)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(5000);
      });

      expect(result.current.activeNudge).not.toBeNull();
    });

    it("does not fetch when should_show is false", async () => {
      server.use(createNudgeHandler(mockNoNudgeRecommendation));

      const { result } = renderHook(
        () => useAINudges({ enabled: true, pageContext: "chat" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.activeNudge).toBeNull();
    });

    it("handles API errors gracefully", async () => {
      server.use(createErrorHandler(500));

      const { result } = renderHook(
        () =>
          useAINudges({ enabled: true, pageContext: "chat", debounceMs: 50 }),
        { wrapper: createWrapper(store) },
      );

      // Advance past debounce
      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      // Wait for error to be set
      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      expect(result.current.activeNudge).toBeNull();
    });
  });

  describe("Nudge Lifecycle", () => {
    it("acceptNudge clears active nudge and records history", async () => {
      const { result } = renderHook(
        () => useAINudges({ enabled: true, pageContext: "chat" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5100);
      });

      await waitFor(() => {
        expect(result.current.activeNudge).not.toBeNull();
      });

      const nudgeId = result.current.activeNudge!.id;

      act(() => {
        result.current.acceptNudge(nudgeId);
      });

      expect(result.current.activeNudge).toBeNull();
      expect(result.current.hasShownNudge(nudgeId)).toBe(true);
    });

    it("dismissNudge clears active nudge and records history", async () => {
      const { result } = renderHook(
        () => useAINudges({ enabled: true, pageContext: "chat" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5100);
      });

      await waitFor(() => {
        expect(result.current.activeNudge).not.toBeNull();
      });

      const nudgeId = result.current.activeNudge!.id;

      act(() => {
        result.current.dismissNudge(nudgeId);
      });

      expect(result.current.activeNudge).toBeNull();
      expect(result.current.hasShownNudge(nudgeId)).toBe(true);
    });
  });

  describe("Context Changes", () => {
    it("refetches when pageContext changes", async () => {
      let fetchCount = 0;
      server.use(
        http.post("*/api/v1/ai/nudges/recommend", async () => {
          fetchCount++;
          return HttpResponse.json(mockNudgeRecommendation);
        }),
      );

      const { rerender } = renderHook(
        ({ pageContext }) => useAINudges({ enabled: true, pageContext }),
        {
          wrapper: createWrapper(store),
          initialProps: { pageContext: "chat" },
        },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(fetchCount).toBe(1);
      });

      rerender({ pageContext: "workflows" });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(fetchCount).toBe(2);
      });
    });
  });

  describe("Session Limits", () => {
    it("respects maxPerSession limit", async () => {
      const { result } = renderHook(
        () =>
          useAINudges({ enabled: true, pageContext: "chat", maxPerSession: 1 }),
        { wrapper: createWrapper(store) },
      );

      // Wait for sessionLimit effect to propagate
      await waitFor(() => {
        expect(store.getState().nudge.sessionLimit).toBe(1);
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5100);
      });

      await waitFor(() => {
        expect(result.current.activeNudge).not.toBeNull();
      });

      act(() => {
        result.current.dismissNudge(result.current.activeNudge!.id);
      });

      // After showing 1 nudge with maxPerSession=1, canShowMore should be false
      await waitFor(() => {
        expect(result.current.canShowMore).toBe(false);
      });
    });
  });

  describe("Statistics", () => {
    it("tracks acceptance rate", async () => {
      const { result } = renderHook(
        () => useAINudges({ enabled: true, pageContext: "chat" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(5100);
      });

      await waitFor(() => {
        expect(result.current.activeNudge).not.toBeNull();
      });

      act(() => {
        result.current.acceptNudge(result.current.activeNudge!.id);
      });

      const stats = result.current.getStats();
      expect(stats.totalShown).toBe(1);
      expect(stats.accepted).toBe(1);
      expect(stats.acceptanceRate).toBe(1);
    });
  });

  describe("Manual Fetching", () => {
    it("fetchRecommendation manually triggers fetch", async () => {
      const { result } = renderHook(
        () => useAINudges({ enabled: false, pageContext: "chat" }),
        { wrapper: createWrapper(store) },
      );

      expect(result.current.recommendation).toBeNull();

      await act(async () => {
        result.current.fetchRecommendation();
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(result.current.recommendation).not.toBeNull();
      });
    });
  });

  describe("Fogg Model Integration", () => {
    it("includes context and persona in request via RTK Query", async () => {
      // Note: RTK Query uses different request fields: current_feature, persona
      // The original motivation/ability fields are mapped to persona
      let capturedBody: Record<string, unknown> | null = null;
      server.use(
        http.post("*/api/v1/ai/nudges/recommend", async ({ request }) => {
          capturedBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json(mockNudgeRecommendation);
        }),
      );

      renderHook(
        () =>
          useAINudges({
            enabled: true,
            pageContext: "chat",
            userMotivation: "high",
            userAbility: "intermediate",
          }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await waitFor(() => {
        expect(capturedBody).not.toBeNull();
      });

      // RTK Query sends current_feature and persona instead
      expect(capturedBody?.current_feature).toBe("chat");
      expect(capturedBody?.persona).toBe("intermediate");
    });
  });
});
