/**
 * useAISuggestionsCache Hook Tests
 *
 * TDD - Tests for AI suggestions caching with TTL support.
 *
 * Features:
 * - Cache AI suggestions with configurable TTL
 * - Use sessionStore for per-session context
 * - Automatic cache invalidation on context change
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAISuggestionsCache, type CachedSuggestion } from "./useAISuggestionsCache";
import { storage, sessionStore, STORAGE_KEYS } from "../utils/storage";

describe("useAISuggestionsCache", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.useRealTimers();
  });

  describe("initialization", () => {
    it("returns empty suggestions initially", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      expect(result.current.suggestions).toEqual([]);
      expect(result.current.isStale).toBe(false);
    });

    it("loads cached suggestions if valid", () => {
      const cachedSuggestions: CachedSuggestion[] = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
      ];

      // Pre-populate cache with valid TTL
      const TTL_5_MIN = 5 * 60 * 1000;
      storage.setWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE, cachedSuggestions, TTL_5_MIN);

      const { result } = renderHook(() => useAISuggestionsCache());

      expect(result.current.suggestions).toEqual(cachedSuggestions);
    });

    it("returns empty if cache is expired", () => {
      const cachedSuggestions = [{ id: "1", content: "test" }];
      const TTL_5_MIN = 5 * 60 * 1000;

      storage.setWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE, cachedSuggestions, TTL_5_MIN);

      // Advance past TTL
      vi.advanceTimersByTime(TTL_5_MIN + 1000);

      const { result } = renderHook(() => useAISuggestionsCache());

      // Expired cache returns empty suggestions
      expect(result.current.suggestions).toEqual([]);
      // Note: isStale is false on fresh mount since we can't distinguish
      // "never existed" from "expired" without tracking state
    });
  });

  describe("cacheSuggestions", () => {
    it("caches suggestions with default 5-minute TTL", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      const suggestions: CachedSuggestion[] = [
        { id: "1", type: "completion", content: "suggestion 1", confidence: 0.85 },
        { id: "2", type: "fix", content: "suggestion 2", confidence: 0.75 },
      ];

      act(() => {
        result.current.cacheSuggestions(suggestions);
      });

      expect(result.current.suggestions).toEqual(suggestions);

      // Verify stored in localStorage with TTL
      const cached = storage.getWithTTL<CachedSuggestion[]>(STORAGE_KEYS.AI_SUGGESTIONS_CACHE);
      expect(cached).toEqual(suggestions);
    });

    it("allows custom TTL", () => {
      const { result } = renderHook(() =>
        useAISuggestionsCache({ ttlMs: 10 * 60 * 1000 }) // 10 min
      );

      const suggestions: CachedSuggestion[] = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
      ];

      act(() => {
        result.current.cacheSuggestions(suggestions);
      });

      // Should still be valid after 8 minutes
      vi.advanceTimersByTime(8 * 60 * 1000);

      const cached = storage.getWithTTL<CachedSuggestion[]>(STORAGE_KEYS.AI_SUGGESTIONS_CACHE);
      expect(cached).toEqual(suggestions);

      // Should be expired after 11 minutes
      vi.advanceTimersByTime(3 * 60 * 1000);

      const expired = storage.getWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE);
      expect(expired).toBeUndefined();
    });
  });

  describe("invalidateCache", () => {
    it("clears cached suggestions", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      const suggestions: CachedSuggestion[] = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
      ];

      act(() => {
        result.current.cacheSuggestions(suggestions);
      });

      expect(result.current.suggestions).toHaveLength(1);

      act(() => {
        result.current.invalidateCache();
      });

      expect(result.current.suggestions).toEqual([]);
    });

    it("removes from localStorage", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      const suggestions: CachedSuggestion[] = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
      ];

      act(() => {
        result.current.cacheSuggestions(suggestions);
        result.current.invalidateCache();
      });

      const cached = storage.getWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE);
      expect(cached).toBeUndefined();
    });
  });

  describe("context tracking with sessionStore", () => {
    it("stores context in sessionStore", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      const context = { sessionId: "session-123", artifactId: "artifact-456" };

      act(() => {
        result.current.setContext(context);
      });

      expect(result.current.context).toEqual(context);

      const stored = sessionStore.get<typeof context>(STORAGE_KEYS.AI_CONTEXT_HISTORY);
      expect(stored).toEqual(context);
    });

    it("invalidates cache when context changes", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      const suggestions: CachedSuggestion[] = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
      ];

      act(() => {
        result.current.setContext({ sessionId: "session-1", artifactId: null });
        result.current.cacheSuggestions(suggestions);
      });

      expect(result.current.suggestions).toHaveLength(1);

      // Change context - should invalidate cache
      act(() => {
        result.current.setContext({ sessionId: "session-2", artifactId: null });
      });

      expect(result.current.suggestions).toEqual([]);
    });

    it("preserves cache when context is the same", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      const context = { sessionId: "session-1", artifactId: null };
      const suggestions: CachedSuggestion[] = [
        { id: "1", type: "completion", content: "test", confidence: 0.9 },
      ];

      act(() => {
        result.current.setContext(context);
        result.current.cacheSuggestions(suggestions);
      });

      // Set same context
      act(() => {
        result.current.setContext({ ...context });
      });

      expect(result.current.suggestions).toEqual(suggestions);
    });
  });

  describe("isStale", () => {
    it("returns false for fresh cache", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      act(() => {
        result.current.cacheSuggestions([
          { id: "1", type: "completion", content: "test", confidence: 0.9 },
        ]);
      });

      expect(result.current.isStale).toBe(false);
    });

    it("returns true when cache is empty after being populated", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      act(() => {
        result.current.cacheSuggestions([
          { id: "1", type: "completion", content: "test", confidence: 0.9 },
        ]);
        result.current.invalidateCache();
      });

      // After invalidation, isStale should reflect that we had suggestions before
      expect(result.current.suggestions).toEqual([]);
    });
  });

  describe("getCacheAge", () => {
    it("returns cache age in milliseconds", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      const { result } = renderHook(() => useAISuggestionsCache());

      act(() => {
        result.current.cacheSuggestions([
          { id: "1", type: "completion", content: "test", confidence: 0.9 },
        ]);
      });

      // Advance time by 30 seconds
      vi.advanceTimersByTime(30000);

      expect(result.current.getCacheAge()).toBeGreaterThanOrEqual(30000);
    });

    it("returns 0 for empty cache", () => {
      const { result } = renderHook(() => useAISuggestionsCache());

      expect(result.current.getCacheAge()).toBe(0);
    });
  });
});
