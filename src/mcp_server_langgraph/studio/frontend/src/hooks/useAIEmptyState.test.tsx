/**
 * useAIEmptyState Hook Tests
 *
 * Tests for the AI-powered empty state suggestions hook.
 * Phase 6.2: AI-Native Integration Layer
 *
 * Features tested:
 * - Fetching AI-powered suggestions from backend
 * - Fallback to registry when AI unavailable
 * - Loading and error states
 * - Caching and refresh
 * - Persona context integration
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";
import { http, HttpResponse, delay } from "msw";
import { server } from "../mocks/server";
import { useAIEmptyState, clearSuggestionCache } from "./useAIEmptyState";
import personaReducer from "../store/slices/personaSlice";
import sessionReducer from "../store/slices/sessionSlice";
import { api } from "../api";

// Mock feature flag - default to enabled
vi.mock("../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: vi.fn((flagName: string) => {
      // Default: ai_empty_state is enabled
      if (flagName === "ai_empty_state") return true;
      return false;
    }),
  };
});
const AI_ENDPOINT = "/api/v1/ai/empty-state/suggestions";

// Track request body for assertions
let lastRequestBody: Record<string, unknown> | null = null;

// Mock EmptyStateRegistry
vi.mock("../components/EmptyState/EmptyStateRegistry", () => ({
  getEmptyStateConfig: vi.fn((context) => ({
    title: `Default ${context} title`,
    motivation: `Default ${context} motivation`,
    ability: "Default ability",
    action: "Default Action",
    target: `/default/${context}`,
  })),
}));

// Create wrapper with Redux store (includes RTK Query API)
function createWrapper(personaState = {}, sessionState = {}) {
  const store = configureStore({
    reducer: {
      persona: personaReducer,
      session: sessionReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
    preloadedState: {
      persona: {
        persona: "developer" as const,
        subPersona: "alice-builder" as const,
        username: "alice",
        email: "alice@example.com",
        permissions: [],
        isPersonaLoading: false,
        ...personaState,
      },
      session: {
        sessions: [],
        currentSession: { id: "test-session-123", messages: [] },
        isLoadingSessions: false,
        isLoadingSession: false,
        isSending: false,
        error: null,
        hasMore: false,
        totalCount: 0,
        isLoadingMore: false,
        cursor: null,
        hasPendingMutation: false,
        ...sessionState,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

describe("useAIEmptyState", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lastRequestBody = null;
    // Clear module-level cache between tests for isolation
    clearSuggestionCache();
  });

  afterEach(() => {
    cleanup();
    server.resetHandlers();
  });

  describe("initialization", () => {
    it("should return initial loading state", () => {
      // Use a handler that delays forever
      server.use(
        http.post(AI_ENDPOINT, async () => {
          await delay("infinite");
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(true);
      expect(result.current.suggestions).toEqual([]);
      expect(result.current.error).toBeNull();
    });

    it("should expose refresh function", () => {
      server.use(
        http.post(AI_ENDPOINT, async () => {
          await delay("infinite");
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      expect(typeof result.current.refresh).toBe("function");
    });

    it("should expose fallbackConfig from registry", () => {
      server.use(
        http.post(AI_ENDPOINT, async () => {
          await delay("infinite");
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "sessions" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.fallbackConfig).toBeDefined();
      expect(result.current.fallbackConfig.title).toBe(
        "Default sessions title",
      );
    });
  });

  describe("successful fetch", () => {
    it("should fetch suggestions from AI endpoint", async () => {
      // API returns schema: { title, description, action_type, action_target, icon?, priority }
      const apiSuggestions = [
        {
          title: "Create your first workflow",
          description: "Get started with workflows",
          action_type: "navigate" as const,
          action_target: "/studio/workflows/new",
          priority: 1,
        },
      ];

      // Hook transforms to internal format
      // Confidence is calculated: 1 - (priority - 1) * 0.1 = 1 for priority 1
      const expectedSuggestions = [
        {
          text: "Create your first workflow",
          action: "navigate",
          target: "/studio/workflows/new",
          confidence: 1, // Priority 1 -> confidence 1
          category: "navigate",
        },
      ];

      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({ suggestions: apiSuggestions });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.suggestions).toEqual(expectedSuggestions);
      expect(result.current.error).toBeNull();
    });

    it("should include context in API request", async () => {
      server.use(
        http.post(AI_ENDPOINT, async ({ request }) => {
          lastRequestBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      renderHook(() => useAIEmptyState({ context: "projects" }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(lastRequestBody).not.toBeNull();
      });

      expect(lastRequestBody?.context).toBe("projects");
    });

    it("should include persona in API request", async () => {
      server.use(
        http.post(AI_ENDPOINT, async ({ request }) => {
          lastRequestBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      renderHook(() => useAIEmptyState({ context: "workflows" }), {
        wrapper: createWrapper({ subPersona: "alice-analyst" }),
      });

      await waitFor(() => {
        expect(lastRequestBody).not.toBeNull();
      });

      expect(lastRequestBody?.persona).toBe("alice-analyst");
    });

    it("should include session_id in API request", async () => {
      server.use(
        http.post(AI_ENDPOINT, async ({ request }) => {
          lastRequestBody = (await request.json()) as Record<string, unknown>;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      renderHook(() => useAIEmptyState({ context: "workflows" }), {
        wrapper: createWrapper(
          {},
          { currentSession: { id: "session-abc-123", messages: [] } },
        ),
      });

      await waitFor(() => {
        expect(lastRequestBody).not.toBeNull();
      });

      expect(lastRequestBody?.session_id).toBe("session-abc-123");
    });
  });

  describe("error handling", () => {
    it("should handle network errors gracefully", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.error();
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).not.toBeNull();
      expect(result.current.suggestions).toEqual([]);
    });

    it("should handle API errors (non-ok response)", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return new HttpResponse(null, { status: 500 });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).not.toBeNull();
      expect(result.current.isAIAvailable).toBe(false);
    });

    it("should provide fallback config when AI fails", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return new HttpResponse(null, { status: 503 });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "sessions" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should still have fallback config from registry
      expect(result.current.fallbackConfig).toBeDefined();
      expect(result.current.fallbackConfig.action).toBe("Default Action");
    });
  });

  describe("refresh functionality", () => {
    it("should refetch suggestions on refresh call", async () => {
      let callCount = 0;
      server.use(
        http.post(AI_ENDPOINT, () => {
          callCount++;
          return HttpResponse.json({
            suggestions: [
              {
                title: `Suggestion ${callCount}`,
                description: `Description ${callCount}`,
                action_type: "navigate" as const,
                action_url: `/path${callCount}`,
                priority: 1,
                confidence: 0.9,
              },
            ],
          });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.suggestions[0]?.text).toBe("Suggestion 1");
      });

      act(() => {
        result.current.refresh();
      });

      await waitFor(() => {
        expect(result.current.suggestions[0]?.text).toBe("Suggestion 2");
      });

      expect(callCount).toBe(2);
    });

    it("should set loading state during refresh", async () => {
      let resolveDelay: () => void;
      const delayPromise = new Promise<void>((resolve) => {
        resolveDelay = resolve;
      });

      server.use(
        http.post(AI_ENDPOINT, async () => {
          await delayPromise;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(true);

      // Resolve the delay
      act(() => {
        resolveDelay();
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });
  });

  describe("suggestion selection", () => {
    it("should expose primary suggestion (highest confidence)", async () => {
      // API returns priority (lower = higher priority)
      // Hook transforms to confidence (higher = better)
      // Confidence formula: 1 - (priority - 1) * 0.1
      // Priority 1 -> confidence 1.0
      // Priority 2 -> confidence 0.9
      // Priority 3 -> confidence 0.8
      const apiSuggestions = [
        {
          title: "Second best",
          description: "Second choice",
          action_type: "navigate" as const,
          action_target: "/second",
          priority: 2,
        },
        {
          title: "Best option",
          description: "Best choice",
          action_type: "navigate" as const,
          action_target: "/best",
          priority: 1,
        },
        {
          title: "Third option",
          description: "Third choice",
          action_type: "navigate" as const,
          action_target: "/third",
          priority: 3,
        },
      ];

      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({ suggestions: apiSuggestions });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.primarySuggestion).toBeDefined();
      });

      // Primary should be the one with highest confidence (priority 1)
      expect(result.current.primarySuggestion?.text).toBe("Best option");
      expect(result.current.primarySuggestion?.confidence).toBe(1); // Priority 1 -> confidence 1
    });

    it("should return null primary when no suggestions", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.primarySuggestion).toBeNull();
    });
  });

  describe("AI availability", () => {
    it("should indicate AI is available after successful fetch", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAIAvailable).toBe(true);
    });

    it("should indicate AI is unavailable after error", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.error();
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAIAvailable).toBe(false);
    });
  });

  describe("caching behavior", () => {
    it("should not refetch on every render", async () => {
      let callCount = 0;
      server.use(
        http.post(AI_ENDPOINT, () => {
          callCount++;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result, rerender } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Rerender multiple times
      rerender();
      rerender();
      rerender();

      // Should only have made one fetch call
      expect(callCount).toBe(1);
    });

    it("should refetch when context changes", async () => {
      let callCount = 0;
      server.use(
        http.post(AI_ENDPOINT, () => {
          callCount++;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result, rerender } = renderHook(
        ({ context }) => useAIEmptyState({ context }),
        {
          wrapper: createWrapper(),
          initialProps: { context: "workflows" as const },
        },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Change context
      rerender({ context: "sessions" as const });

      await waitFor(() => {
        expect(callCount).toBe(2);
      });
    });
  });

  describe("disabled mode", () => {
    it("should not fetch when disabled", async () => {
      let callCount = 0;
      server.use(
        http.post(AI_ENDPOINT, () => {
          callCount++;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows", enabled: false }),
        { wrapper: createWrapper() },
      );

      // Wait a bit to ensure no fetch was triggered
      await new Promise((r) => setTimeout(r, 50));

      expect(callCount).toBe(0);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.suggestions).toEqual([]);
    });

    it("should still provide fallback config when disabled", () => {
      const { result } = renderHook(
        () => useAIEmptyState({ context: "sessions", enabled: false }),
        { wrapper: createWrapper() },
      );

      expect(result.current.fallbackConfig).toBeDefined();
      expect(result.current.fallbackConfig.title).toBe(
        "Default sessions title",
      );
    });
  });

  describe("timeout functionality", () => {
    // Note: RTK Query handles request timeouts internally, so custom timeout
    // functionality is not supported. Error handling and fallback behavior
    // is tested in the "error handling" describe block above.

    it("should succeed if response arrives before timeout", async () => {
      // API schema: { title, description, action_type, action_target, icon?, priority }
      const apiSuggestions = [
        {
          title: "Quick response",
          description: "Fast description",
          action_type: "navigate" as const,
          action_target: "/quick",
          priority: 1,
        },
      ];

      // Confidence formula: 1 - (priority - 1) * 0.1
      // Priority 1 -> confidence 1.0
      const expectedSuggestions = [
        {
          text: "Quick response",
          action: "navigate",
          target: "/quick",
          confidence: 1, // Priority 1 -> confidence 1
          category: "navigate",
        },
      ];

      server.use(
        http.post(AI_ENDPOINT, async () => {
          await delay(50); // Fast response
          return HttpResponse.json({ suggestions: apiSuggestions });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows", timeoutMs: 1000 }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.suggestions).toEqual(expectedSuggestions);
      expect(result.current.isAIAvailable).toBe(true);
      expect(result.current.error).toBeNull();
    });
  });

  describe("feature flag gating (Sprint 2)", () => {
    it("should not fetch when ai_empty_state feature flag is disabled", async () => {
      // Override the mock to return false for ai_empty_state
      const { useFeatureFlag } = await import("../contexts/FeatureFlagContext");
      vi.mocked(useFeatureFlag).mockReturnValue(false);

      let callCount = 0;
      server.use(
        http.post(AI_ENDPOINT, () => {
          callCount++;
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      // Wait a bit to ensure no fetch was triggered
      await new Promise((r) => setTimeout(r, 100));

      // Feature flag should prevent fetch
      expect(callCount).toBe(0);
      expect(result.current.isAIAvailable).toBe(false);
      expect(result.current.suggestions).toEqual([]);
    });

    it("should fetch when ai_empty_state feature flag is enabled", async () => {
      // Ensure the mock returns true
      const { useFeatureFlag } = await import("../contexts/FeatureFlagContext");
      vi.mocked(useFeatureFlag).mockReturnValue(true);

      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({
            suggestions: [
              {
                title: "Test suggestion",
                description: "Test",
                action_type: "navigate" as const,
                action_target: "/test",
                priority: 1,
              },
            ],
          });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isAIAvailable).toBe(true);
      expect(result.current.suggestions.length).toBe(1);
    });
  });

  describe("module-level cache (Sprint 2)", () => {
    it("should use cached data for same context across hook instances", async () => {
      // Ensure the feature flag is enabled
      const { useFeatureFlag } = await import("../contexts/FeatureFlagContext");
      vi.mocked(useFeatureFlag).mockReturnValue(true);

      let callCount = 0;
      server.use(
        http.post(AI_ENDPOINT, () => {
          callCount++;
          return HttpResponse.json({
            suggestions: [
              {
                title: `Suggestion from call ${callCount}`,
                description: "Test",
                action_type: "navigate" as const,
                action_target: "/test",
                priority: 1,
              },
            ],
          });
        }),
      );

      // First hook instance
      const { result: result1, unmount: unmount1 } = renderHook(
        () => useAIEmptyState({ context: "alerts" }), // Use unique context
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false);
      });

      expect(result1.current.suggestions[0]?.text).toBe(
        "Suggestion from call 1",
      );
      expect(result1.current.isFromCache).toBe(false); // First call is not from cache

      // Unmount first instance
      unmount1();

      // Second hook instance - should use cached data
      const { result: result2 } = renderHook(
        () => useAIEmptyState({ context: "alerts" }), // Same context
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result2.current.isLoading).toBe(false);
      });

      // Should still have data from first call (cached)
      expect(result2.current.suggestions[0]?.text).toBe(
        "Suggestion from call 1",
      );
      // Should only have made 1 API call total
      expect(callCount).toBe(1);
      expect(result2.current.isFromCache).toBe(true);
    });

    it("should indicate when data is from cache", async () => {
      // Ensure the feature flag is enabled
      const { useFeatureFlag } = await import("../contexts/FeatureFlagContext");
      vi.mocked(useFeatureFlag).mockReturnValue(true);

      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({
            suggestions: [
              {
                title: "Cached suggestion",
                description: "Test",
                action_type: "navigate" as const,
                action_target: "/test",
                priority: 1,
              },
            ],
          });
        }),
      );

      // First call to populate cache
      const { result: result1, unmount: unmount1 } = renderHook(
        () => useAIEmptyState({ context: "connections" }), // Use unique context
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result1.current.isLoading).toBe(false);
      });

      expect(result1.current.isFromCache).toBe(false); // First call

      unmount1();

      // Second call should indicate data is from cache
      const { result: result2 } = renderHook(
        () => useAIEmptyState({ context: "connections" }), // Same context
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result2.current.isLoading).toBe(false);
      });

      expect(result2.current.isFromCache).toBe(true);
    });
  });

  describe("interface completeness", () => {
    it("should expose all required properties and functions", async () => {
      server.use(
        http.post(AI_ENDPOINT, () => {
          return HttpResponse.json({ suggestions: [] });
        }),
      );

      const { result } = renderHook(
        () => useAIEmptyState({ context: "workflows" }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Properties
      expect(result.current.suggestions).toBeDefined();
      expect(result.current.primarySuggestion).toBeDefined();
      expect(result.current.fallbackConfig).toBeDefined();
      expect(result.current.isLoading).toBeDefined();
      expect(result.current.error).toBeDefined();
      expect(result.current.isAIAvailable).toBeDefined();

      // Functions
      expect(typeof result.current.refresh).toBe("function");
    });
  });
});
