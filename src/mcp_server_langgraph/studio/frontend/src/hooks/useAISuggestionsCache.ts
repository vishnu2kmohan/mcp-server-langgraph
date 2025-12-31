/**
 * useAISuggestionsCache Hook
 *
 * Provides caching for AI suggestions with TTL support.
 * Uses localStorage for persistent cache and sessionStore for per-session context.
 *
 * Features:
 * - Cache AI suggestions with configurable TTL (default: 5 minutes)
 * - Automatic cache invalidation when context changes
 * - Per-session context tracking via sessionStore
 * - Cache age tracking for staleness detection
 *
 * @example
 * ```tsx
 * const { suggestions, cacheSuggestions, invalidateCache, setContext } = useAISuggestionsCache();
 *
 * // Cache new suggestions
 * cacheSuggestions(fetchedSuggestions);
 *
 * // Use cached suggestions
 * {suggestions.map(s => <SuggestionChip key={s.id} suggestion={s} />)}
 *
 * // Track context changes (auto-invalidates on change)
 * setContext({ sessionId: currentSession, artifactId: selectedArtifact });
 * ```
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { storage, sessionStore, STORAGE_KEYS } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

export type SuggestionType = "completion" | "refactor" | "fix" | "explain";

export interface CachedSuggestion {
  id: string;
  type: SuggestionType;
  content: string;
  confidence: number;
  position?: { line: number; column: number };
}

export interface AIContextRef {
  sessionId: string;
  artifactId: string | null;
}

export interface UseAISuggestionsCacheOptions {
  /** TTL in milliseconds for cached suggestions (default: 5 minutes) */
  ttlMs?: number;
  /** Whether to auto-invalidate cache on context change (default: true) */
  invalidateOnContextChange?: boolean;
}

export interface UseAISuggestionsCacheResult {
  /** Current cached suggestions (excludes dismissed) */
  suggestions: CachedSuggestion[];
  /** Current AI context (session, artifact) */
  context: AIContextRef | null;
  /** Whether cache is stale (expired or invalidated) */
  isStale: boolean;
  /** IDs of dismissed suggestions for current context */
  dismissedIds: string[];
  /** Cache suggestions with TTL (filters out dismissed) */
  cacheSuggestions: (suggestions: CachedSuggestion[]) => void;
  /** Invalidate (clear) the cache */
  invalidateCache: () => void;
  /** Set AI context (triggers invalidation if context changes) */
  setContext: (context: AIContextRef) => void;
  /** Get cache age in milliseconds */
  getCacheAge: () => number;
  /** Dismiss a suggestion by ID (persists across refetches) */
  dismissSuggestion: (id: string) => void;
  /** Check if a suggestion is dismissed */
  isDismissed: (id: string) => boolean;
  /** Clear all dismissed IDs for current context */
  clearDismissed: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_TTL_MS = 5 * 60 * 1000; // 5 minutes

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAISuggestionsCache(
  options: UseAISuggestionsCacheOptions = {},
): UseAISuggestionsCacheResult {
  const { ttlMs = DEFAULT_TTL_MS, invalidateOnContextChange = true } = options;

  // Track cache creation time for age calculation
  const cacheCreatedAt = useRef<number>(0);
  const previousContextRef = useRef<string | null>(null);

  // Initialize dismissed IDs from sessionStore (per-session persistence)
  const [dismissedIds, setDismissedIds] = useState<string[]>(() => {
    const stored = sessionStore.get<string[]>(STORAGE_KEYS.AI_DISMISSED_IDS);
    return stored ?? [];
  });

  // Initialize suggestions from cache (filtering out dismissed)
  const [suggestions, setSuggestions] = useState<CachedSuggestion[]>(() => {
    const cached = storage.getWithTTL<CachedSuggestion[]>(
      STORAGE_KEYS.AI_SUGGESTIONS_CACHE,
    );
    const dismissed =
      sessionStore.get<string[]>(STORAGE_KEYS.AI_DISMISSED_IDS) ?? [];
    // Filter out dismissed suggestions on initial load
    return (cached ?? []).filter((s) => !dismissed.includes(s.id));
  });

  // Initialize context from sessionStore
  const [context, setContextState] = useState<AIContextRef | null>(() => {
    const stored = sessionStore.get<AIContextRef>(
      STORAGE_KEYS.AI_CONTEXT_HISTORY,
    );
    return stored ?? null;
  });

  // Track staleness (cache was invalidated during this session)
  const [isStale, setIsStale] = useState<boolean>(false);

  /**
   * Cache suggestions with TTL (filters out dismissed IDs)
   */
  const cacheSuggestions = useCallback(
    (newSuggestions: CachedSuggestion[]) => {
      // Filter out any dismissed suggestions before caching
      const filtered = newSuggestions.filter(
        (s) => !dismissedIds.includes(s.id),
      );
      storage.setWithTTL(STORAGE_KEYS.AI_SUGGESTIONS_CACHE, filtered, ttlMs);
      setSuggestions(filtered);
      cacheCreatedAt.current = Date.now();
      setIsStale(false);
    },
    [ttlMs, dismissedIds],
  );

  /**
   * Invalidate (clear) the cache
   */
  const invalidateCache = useCallback(() => {
    storage.remove(STORAGE_KEYS.AI_SUGGESTIONS_CACHE);
    setSuggestions([]);
    cacheCreatedAt.current = 0;
  }, []);

  /**
   * Clear dismissed IDs (internal helper)
   */
  const clearDismissedInternal = useCallback(() => {
    sessionStore.remove(STORAGE_KEYS.AI_DISMISSED_IDS);
    setDismissedIds([]);
  }, []);

  /**
   * Set AI context and optionally invalidate cache if context changed
   */
  const setContext = useCallback(
    (newContext: AIContextRef) => {
      // Store in sessionStore for per-session persistence
      sessionStore.set(STORAGE_KEYS.AI_CONTEXT_HISTORY, newContext);

      // Check if context actually changed
      const newContextKey = `${newContext.sessionId}:${newContext.artifactId ?? "null"}`;
      const contextChanged =
        previousContextRef.current !== null &&
        previousContextRef.current !== newContextKey;

      previousContextRef.current = newContextKey;
      setContextState(newContext);

      // Invalidate cache and clear dismissed IDs if context changed
      if (invalidateOnContextChange && contextChanged) {
        invalidateCache();
        clearDismissedInternal();
      }
    },
    [invalidateOnContextChange, invalidateCache, clearDismissedInternal],
  );

  /**
   * Get cache age in milliseconds
   */
  const getCacheAge = useCallback((): number => {
    if (cacheCreatedAt.current === 0 || suggestions.length === 0) {
      return 0;
    }
    return Date.now() - cacheCreatedAt.current;
  }, [suggestions.length]);

  // Initialize previous context ref when context is first set
  useEffect(() => {
    if (context && previousContextRef.current === null) {
      previousContextRef.current = `${context.sessionId}:${context.artifactId ?? "null"}`;
    }
  }, [context]);

  /**
   * Dismiss a suggestion by ID (persists across refetches)
   */
  const dismissSuggestion = useCallback((id: string) => {
    setDismissedIds((prev) => {
      if (prev.includes(id)) return prev;
      const updated = [...prev, id];
      sessionStore.set(STORAGE_KEYS.AI_DISMISSED_IDS, updated);
      return updated;
    });
    // Also remove from current suggestions
    setSuggestions((prev) => prev.filter((s) => s.id !== id));
  }, []);

  /**
   * Check if a suggestion is dismissed
   */
  const isDismissed = useCallback(
    (id: string): boolean => {
      return dismissedIds.includes(id);
    },
    [dismissedIds],
  );

  /**
   * Clear all dismissed IDs for current context (public API)
   */
  const clearDismissed = useCallback(() => {
    clearDismissedInternal();
  }, [clearDismissedInternal]);

  return {
    suggestions,
    context,
    isStale,
    dismissedIds,
    cacheSuggestions,
    invalidateCache,
    setContext,
    getCacheAge,
    dismissSuggestion,
    isDismissed,
    clearDismissed,
  };
}

export default useAISuggestionsCache;
