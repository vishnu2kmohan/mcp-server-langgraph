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

  // State
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [isAIAvailable, setIsAIAvailable] = useState(false);
  const [lastFetchedContext, setLastFetchedContext] = useState<string | null>(
    null,
  );
  const [isInitialLoad, setIsInitialLoad] = useState(enabled);
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
    async (forContext: string) => {
      setError(null);

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
   * Refresh suggestions
   */
  const refresh = useCallback(() => {
    doFetch(context);
  }, [doFetch, context]);

  // Initial fetch on mount or context change
  useEffect(() => {
    if (!enabled) {
      setIsInitialLoad(false);
      return;
    }

    // Only fetch if context changed from last fetch
    if (context !== lastFetchedContext) {
      doFetch(context);
    }
  }, [context, enabled, lastFetchedContext, doFetch]);

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
  };
}

export default useAIEmptyState;
