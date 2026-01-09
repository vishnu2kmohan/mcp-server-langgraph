/**
 * useAIEmptyState Hook
 *
 * AI-powered empty state suggestions hook.
 * Phase 6.2: AI-Native Integration Layer
 *
 * Fetches contextual, personalized suggestions from the AI backend
 * and provides fallback to EmptyStateRegistry when AI is unavailable.
 *
 * Features:
 * - Contextual AI suggestions based on page context
 * - Persona-aware personalization
 * - Graceful fallback to static registry
 * - Caching to prevent unnecessary refetches
 * - Manual refresh capability
 *
 * @example
 * ```tsx
 * const {
 *   suggestions,
 *   primarySuggestion,
 *   fallbackConfig,
 *   isLoading,
 *   isAIAvailable,
 *   refresh,
 * } = useAIEmptyState({ context: 'workflows' });
 *
 * // Use AI suggestion if available, otherwise fallback
 * const actionText = primarySuggestion?.text ?? fallbackConfig.action;
 * const actionTarget = primarySuggestion?.target ?? fallbackConfig.target;
 * ```
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useSelector } from "react-redux";
import { selectSubPersona, selectPersona } from "../store/slices/personaSlice";
import { selectCurrentSession } from "../store/slices/sessionSlice";
import {
  getEmptyStateConfig,
  type EmptyStateConfig,
  type Persona,
} from "../components/EmptyState/EmptyStateRegistry";
import type { EmptyStateContext } from "../components/EmptyState/EmptyState";
import { useGetEmptyStateSuggestionsMutation } from "../api";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";

// ==========================================================================
// Module-level cache for suggestions (Sprint 2)
// Persists across hook instances to prevent redundant API calls
// ==========================================================================
interface CachedSuggestions {
  suggestions: AISuggestion[];
  timestamp: number;
  persona: string;
}

const suggestionCache = new Map<string, CachedSuggestions>();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Get cache key for context + persona combination
 */
function getCacheKey(context: string, persona: string): string {
  return `empty-state-${context}-${persona}`;
}

/**
 * Check if cached data is still valid
 */
function isCacheValid(
  cached: CachedSuggestions | undefined,
): cached is CachedSuggestions {
  if (!cached) return false;
  return Date.now() - cached.timestamp < CACHE_TTL_MS;
}

/**
 * Clear all cached suggestions (useful for testing)
 */
export function clearSuggestionCache(): void {
  suggestionCache.clear();
}

/**
 * AI suggestion from backend
 */
export interface AISuggestion {
  /** Display text for the suggestion */
  text: string;
  /** Action type: navigate, modal, focus */
  action: "navigate" | "modal" | "focus";
  /** Target path or element ID */
  target: string;
  /** AI confidence score (0-1) */
  confidence: number;
  /** Suggestion category for analytics */
  category: string;
}

/**
 * Hook configuration options
 */
export interface UseAIEmptyStateOptions {
  /** Empty state context (e.g., 'workflows', 'sessions') */
  context: EmptyStateContext;
  /** Whether to fetch AI suggestions (default: true) */
  enabled?: boolean;
  /** Request timeout in milliseconds (default: 3000ms) */
  timeoutMs?: number;
}

/**
 * Hook result
 */
export interface UseAIEmptyStateResult {
  /** AI-generated suggestions */
  suggestions: AISuggestion[];
  /** Primary suggestion (highest confidence) */
  primarySuggestion: AISuggestion | null;
  /** Fallback config from EmptyStateRegistry */
  fallbackConfig: EmptyStateConfig;
  /** Whether suggestions are being fetched */
  isLoading: boolean;
  /** Error if fetch failed */
  error: Error | null;
  /** Whether AI service is available */
  isAIAvailable: boolean;
  /** Manually refresh suggestions */
  refresh: () => void;
  /** Whether current data is from cache (Sprint 2) */
  isFromCache: boolean;
}

// Map API action types to hook action types
const mapActionType = (
  actionType: "navigate" | "create" | "learn" | "import",
): "navigate" | "modal" | "focus" => {
  switch (actionType) {
    case "navigate":
      return "navigate";
    case "create":
    case "import":
      return "modal";
    case "learn":
      return "focus";
    default:
      return "navigate";
  }
};

/**
 * Hook for AI-powered empty state suggestions.
 *
 * @param options - Hook options
 * @returns AI suggestions and fallback configuration
 */
export function useAIEmptyState(
  options: UseAIEmptyStateOptions,
): UseAIEmptyStateResult {
  const { context, enabled = true } = options;

  // Feature flag gate (Sprint 2)
  const aiEmptyStateEnabled = useFeatureFlag("ai_empty_state");
  const isEffectivelyEnabled = enabled && aiEmptyStateEnabled;

  // RTK Query mutation
  const [fetchSuggestions, { isLoading: isMutationLoading }] =
    useGetEmptyStateSuggestionsMutation();

  // Get persona context from Redux
  const subPersona = useSelector(selectSubPersona);
  const persona = useSelector(selectPersona);
  const currentSession = useSelector(selectCurrentSession);
  const sessionId = currentSession?.id;

  // Effective persona (subPersona takes precedence)
  const effectivePersona = (subPersona || persona || "default") as Persona;

  // Cache key for this context + persona (reserved for future caching implementation)
  const _cacheKey = getCacheKey(context, effectivePersona);

  // State
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [isAIAvailable, setIsAIAvailable] = useState(false);
  const [lastFetchedContext, setLastFetchedContext] = useState<string | null>(
    null,
  );
  const [isInitialLoad, setIsInitialLoad] = useState(enabled);
  const [isFromCache, setIsFromCache] = useState(false);
  const isMounted = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  // Fallback config from registry (always available)
  const fallbackConfig = getEmptyStateConfig(context, effectivePersona);

  /**
   * Fetch suggestions from AI backend via RTK Query
   */
  const doFetch = useCallback(
    async (forContext: string, skipCache = false) => {
      setError(null);
      setIsFromCache(false);

      // Check module-level cache first (Sprint 2)
      const fetchCacheKey = getCacheKey(forContext, effectivePersona);
      const cached = suggestionCache.get(fetchCacheKey);
      if (!skipCache && isCacheValid(cached)) {
        setSuggestions(cached.suggestions);
        setIsAIAvailable(true);
        setIsFromCache(true);
        setLastFetchedContext(forContext);
        setIsInitialLoad(false);
        return;
      }

      try {
        const data = await fetchSuggestions({
          context: forContext,
          persona: effectivePersona,
          ...(sessionId && { session_id: sessionId }),
        } as Parameters<typeof fetchSuggestions>[0]).unwrap();

        if (!isMounted.current) return;

        // Transform API response to hook's expected format
        // API schema: { title, description, action_type, action_target, icon?, priority }
        const transformedSuggestions: AISuggestion[] = (
          data.suggestions || []
        ).map((s) => ({
          text: s.title || s.description,
          action: mapActionType(s.action_type),
          target: s.action_target,
          // Convert priority (1=highest) to confidence (1=highest confidence)
          // Priority 1-3 maps to confidence 0.9-0.7
          confidence: Math.max(0.5, 1 - (s.priority - 1) * 0.1),
          category: s.action_type,
        }));

        // Store in module-level cache (Sprint 2)
        suggestionCache.set(fetchCacheKey, {
          suggestions: transformedSuggestions,
          timestamp: Date.now(),
          persona: effectivePersona,
        });

        setSuggestions(transformedSuggestions);
        setIsAIAvailable(true);
      } catch (err) {
        if (!isMounted.current) return;
        setError(err instanceof Error ? err : new Error(String(err)));
        setSuggestions([]);
        setIsAIAvailable(false);
      } finally {
        if (isMounted.current) {
          setLastFetchedContext(forContext);
          setIsInitialLoad(false);
        }
      }
    },
    [effectivePersona, fetchSuggestions, sessionId],
  );

  /**
   * Refresh suggestions (skips cache for manual refresh)
   */
  const refresh = useCallback(() => {
    doFetch(context, true); // skipCache = true
  }, [doFetch, context]);

  // Initial fetch on mount or context change
  useEffect(() => {
    // Guard: Skip if not effectively enabled (either prop or feature flag)
    if (!isEffectivelyEnabled) {
      setIsInitialLoad(false);
      return;
    }

    // Only fetch if context changed from last fetch
    if (context !== lastFetchedContext) {
      doFetch(context);
    }
  }, [context, isEffectivelyEnabled, lastFetchedContext, doFetch]);

  // Compute loading state
  const isLoading = isInitialLoad || isMutationLoading;

  /**
   * Get primary suggestion (highest confidence)
   */
  const primarySuggestion =
    suggestions.length > 0
      ? suggestions.reduce((best, current) =>
          current.confidence > best.confidence ? current : best,
        )
      : null;

  return {
    suggestions,
    primarySuggestion,
    fallbackConfig,
    isLoading,
    error,
    isAIAvailable,
    refresh,
    isFromCache,
  };
}

export default useAIEmptyState;
