/**
 * useAISuggestionsFetch Hook
 *
 * Fetches AI suggestions for artifacts with caching support.
 *
 * Features:
 * - Fetches suggestions from API with debounce
 * - Caches suggestions using useAISuggestionsCache
 * - Auto-invalidates on session/artifact context change
 * - Tracks cache staleness
 * - Supports accept/dismiss/clear operations
 *
 * @example
 * ```tsx
 * const {
 *   suggestions,
 *   isLoading,
 *   error,
 *   acceptSuggestion,
 *   dismissSuggestion,
 *   refresh,
 * } = useAISuggestionsFetch({
 *   artifactId: selectedArtifactId,
 *   sessionId: currentSessionId,
 *   enabled: aiSuggestionsEnabled,
 * });
 * ```
 */

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import {
  useAISuggestionsCache,
  type CachedSuggestion,
} from "./useAISuggestionsCache";
import { getAuthToken } from "../utils/storage";
import { devLogger } from "../utils/devLogger";

// =============================================================================
// Types
// =============================================================================

export interface UseAISuggestionsFetchOptions {
  /** Artifact ID to fetch suggestions for */
  artifactId: string | null;
  /** Current session ID for context tracking */
  sessionId: string;
  /** Whether suggestions fetching is enabled */
  enabled: boolean;
  /** Debounce delay in milliseconds (default: 500) */
  debounceMs?: number;
  /** TTL for cached suggestions in milliseconds (default: 5 minutes) */
  ttlMs?: number;
}

export interface UseAISuggestionsFetchResult {
  /** Current suggestions (from cache or fresh fetch) */
  suggestions: CachedSuggestion[];
  /** Whether a fetch is in progress */
  isLoading: boolean;
  /** Error from fetch (if any) */
  error: Error | null;
  /** Whether cached data is stale */
  isStale: boolean;
  /** Accept a suggestion (removes it from list) */
  acceptSuggestion: (id: string) => void;
  /** Dismiss a suggestion (removes it from list) */
  dismissSuggestion: (id: string) => void;
  /** Clear all suggestions */
  clearSuggestions: () => void;
  /** Force refresh suggestions (bypasses cache) */
  refresh: () => void;
  /** Get cache age in milliseconds */
  getCacheAge: () => number;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_DEBOUNCE_MS = 500;
const logger = devLogger.withPrefix("[useAISuggestionsFetch]");

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAISuggestionsFetch(
  options: UseAISuggestionsFetchOptions
): UseAISuggestionsFetchResult {
  const {
    artifactId,
    sessionId,
    enabled,
    debounceMs = DEFAULT_DEBOUNCE_MS,
    ttlMs,
  } = options;

  // Cache management
  const {
    suggestions: cachedSuggestions,
    context: cachedContext,
    isStale,
    cacheSuggestions,
    invalidateCache,
    setContext,
    getCacheAge,
  } = useAISuggestionsCache({ ttlMs });

  // Local state for suggestions (allows immediate updates for accept/dismiss)
  const [localSuggestions, setLocalSuggestions] = useState<CachedSuggestion[]>(
    []
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Refs for cleanup, abort, and tracking context changes
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const forceRefreshRef = useRef(false);
  const mountedRef = useRef(true);
  // Track previous context to avoid re-renders from setContext
  const prevContextKeyRef = useRef<string | null>(null);

  // Generate stable context key for cache hit detection
  const currentContextKey = useMemo(
    () => (artifactId ? `${sessionId}:${artifactId}` : null),
    [sessionId, artifactId]
  );

  // Check if we have a cache hit for current context
  const hasCacheHit = useMemo(() => {
    return (
      cachedContext?.artifactId === artifactId &&
      cachedContext?.sessionId === sessionId &&
      cachedSuggestions.length > 0
    );
  }, [cachedContext, artifactId, sessionId, cachedSuggestions.length]);

  /**
   * Accept a suggestion (removes from list, updates cache)
   */
  const acceptSuggestion = useCallback(
    (id: string) => {
      setLocalSuggestions((prev) => {
        const updated = prev.filter((s) => s.id !== id);
        cacheSuggestions(updated);
        return updated;
      });
      logger.debug("Accepted suggestion:", id);
    },
    [cacheSuggestions]
  );

  /**
   * Dismiss a suggestion (removes from list, updates cache)
   */
  const dismissSuggestion = useCallback(
    (id: string) => {
      setLocalSuggestions((prev) => {
        const updated = prev.filter((s) => s.id !== id);
        cacheSuggestions(updated);
        return updated;
      });
      logger.debug("Dismissed suggestion:", id);
    },
    [cacheSuggestions]
  );

  /**
   * Clear all suggestions
   */
  const clearSuggestions = useCallback(() => {
    setLocalSuggestions([]);
    invalidateCache();
    logger.debug("Cleared all suggestions");
  }, [invalidateCache]);

  /**
   * Fetch suggestions from API (internal function, stable reference)
   */
  const doFetch = useCallback(async () => {
    if (!artifactId || !enabled || !mountedRef.current) {
      return;
    }

    // Abort any pending request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setIsLoading(true);
    setError(null);

    try {
      const token = getAuthToken();
      const response = await fetch(
        `/api/v1/ai/suggestions?artifactId=${artifactId}`,
        {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            ...(token && { Authorization: `Bearer ${token}` }),
          },
          credentials: "include",
          signal: abortController.signal,
        }
      );

      if (abortController.signal.aborted || !mountedRef.current) {
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const fetchedSuggestions = (data.suggestions ?? []) as CachedSuggestion[];

      if (!abortController.signal.aborted && mountedRef.current) {
        // Update cache and context
        cacheSuggestions(fetchedSuggestions);
        setContext({ sessionId, artifactId });

        // Update local state
        setLocalSuggestions(fetchedSuggestions);
        setError(null);

        logger.debug("Fetched suggestions:", fetchedSuggestions.length);
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        // Ignore abort errors
        return;
      }

      if (!abortController.signal.aborted && mountedRef.current) {
        const fetchError = err instanceof Error ? err : new Error("Unknown error");
        setError(fetchError);
        setLocalSuggestions([]);
        logger.error("Failed to fetch suggestions:", fetchError.message);
      }
    } finally {
      if (!abortController.signal.aborted && mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [artifactId, enabled, sessionId, cacheSuggestions, setContext]);

  /**
   * Force refresh suggestions (bypasses cache)
   */
  const refresh = useCallback(() => {
    forceRefreshRef.current = true;
    doFetch();
  }, [doFetch]);

  // Effect: Update context when props change (separate from fetch to avoid cycles)
  useEffect(() => {
    if (!enabled || !artifactId) {
      return;
    }

    // Only update context if it actually changed
    if (prevContextKeyRef.current !== currentContextKey) {
      prevContextKeyRef.current = currentContextKey;
      setContext({ sessionId, artifactId });
    }
  }, [enabled, artifactId, sessionId, currentContextKey, setContext]);

  // Effect: Sync from cache when we have a cache hit
  useEffect(() => {
    if (!enabled) {
      setLocalSuggestions([]);
      setIsLoading(false);
      return;
    }

    if (!artifactId) {
      setLocalSuggestions([]);
      setIsLoading(false);
      return;
    }

    // If we have cached data for this context, use it
    if (hasCacheHit && !forceRefreshRef.current) {
      setLocalSuggestions(cachedSuggestions);
      setIsLoading(false);
      logger.debug("Using cached suggestions:", cachedSuggestions.length);
      return;
    }

    // Reset force refresh flag
    forceRefreshRef.current = false;

    // Set loading state and debounce the fetch
    setIsLoading(true);

    // Clear previous debounce
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    // Debounce the fetch
    debounceTimeoutRef.current = setTimeout(() => {
      doFetch();
    }, debounceMs);

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [
    enabled,
    artifactId,
    debounceMs,
    hasCacheHit,
    cachedSuggestions,
    doFetch,
  ]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  return {
    suggestions: localSuggestions,
    isLoading,
    error,
    isStale,
    acceptSuggestion,
    dismissSuggestion,
    clearSuggestions,
    refresh,
    getCacheAge,
  };
}

export default useAISuggestionsFetch;
