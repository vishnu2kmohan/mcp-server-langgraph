/**
 * useAINudges Hook
 *
 * Sprint 3 - Phase 6.3: AI-Driven Smart Nudges
 *
 * Uses AI to intelligently time and target nudges based on user behavior.
 * Integrates with the Fogg Behavior Model (Motivation + Ability = Trigger).
 *
 * Features:
 * - Predict optimal nudge timing (not too early, not too late)
 * - Personalize nudge content based on user patterns
 * - Learn from nudge acceptance/dismissal rates
 * - Integration with nudgeSlice Redux state
 *
 * Backend endpoint: POST /api/v1/ai/nudges/recommend
 *
 * @example
 * ```tsx
 * const {
 *   activeNudge,
 *   acceptNudge,
 *   dismissNudge,
 *   recommendation,
 * } = useAINudges({
 *   enabled: true,
 *   pageContext: "chat",
 * });
 *
 * {activeNudge && (
 *   <NudgeTooltip
 *     nudge={activeNudge}
 *     onDismiss={() => dismissNudge(activeNudge.id)}
 *     onAccept={() => acceptNudge(activeNudge.id)}
 *   />
 * )}
 * ```
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  setActiveNudge,
  dismissNudge as dismissNudgeAction,
  acceptNudge as acceptNudgeAction,
  setSessionLimit,
  selectActiveNudge,
  selectNudgeHistory,
  selectCanShowMoreNudges,
  selectNudgeStats,
  type StoredNudge,
  type NudgeStats,
} from "../store/slices/nudgeSlice";
import type { Nudge, NudgeType, NudgePriority } from "./useNudges";
import { useGetNudgeRecommendationMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

export interface NudgeRecommendation {
  nudge: Nudge | null;
  shouldShow: boolean;
  confidence: number;
  reasoning?: string;
  timing?: {
    optimalDelayMs: number;
    urgency: "low" | "medium" | "high";
  };
}

export interface UseAINudgesOptions {
  /** Enable AI nudge recommendations (default: false) */
  enabled?: boolean;
  /** Current page context for recommendation */
  pageContext?: string;
  /** Maximum nudges per session (default: 5) */
  maxPerSession?: number;
  /** User motivation level (Fogg model) */
  userMotivation?: "low" | "medium" | "high";
  /** User ability level (Fogg model) */
  userAbility?: "beginner" | "intermediate" | "advanced" | "expert";
  /** Debounce delay in ms (default: 500) */
  debounceMs?: number;
}

export interface UseAINudgesResult {
  /** Currently active nudge */
  activeNudge: Nudge | null;
  /** Latest AI recommendation */
  recommendation: NudgeRecommendation | null;
  /** Whether a fetch is in progress */
  isLoading: boolean;
  /** Error from API */
  error: Error | null;
  /** Whether more nudges can be shown */
  canShowMore: boolean;
  /** Manually fetch a recommendation */
  fetchRecommendation: () => void;
  /** Accept/acknowledge a nudge */
  acceptNudge: (nudgeId: string) => void;
  /** Dismiss a nudge */
  dismissNudge: (nudgeId: string) => void;
  /** Track any interaction for learning */
  trackInteraction: (nudgeId: string, action: string) => void;
  /** Check if a nudge has been shown */
  hasShownNudge: (nudgeId: string) => boolean;
  /** Get comprehensive stats */
  getStats: () => NudgeStats;
}

// =============================================================================
// API Response Types (snake_case from backend)
// =============================================================================

interface NudgeRecommendationResponse {
  nudge: {
    id: string;
    type: NudgeType;
    target_element?: string;
    message: string;
    priority: NudgePriority;
    show_after_ms?: number;
    category: string;
  } | null;
  should_show: boolean;
  confidence: number;
  reasoning?: string;
  timing?: {
    optimal_delay_ms: number;
    urgency: "low" | "medium" | "high";
  };
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_DEBOUNCE_MS = 500;

// =============================================================================
// Helper Functions
// =============================================================================

function _transformResponse(response: NudgeRecommendationResponse): NudgeRecommendation {
  return {
    nudge: response.nudge
      ? {
          id: response.nudge.id,
          type: response.nudge.type,
          targetElement: response.nudge.target_element,
          message: response.nudge.message,
          priority: response.nudge.priority,
          showAfterMs: response.nudge.show_after_ms,
          category: response.nudge.category,
        }
      : null,
    shouldShow: response.should_show,
    confidence: response.confidence,
    reasoning: response.reasoning,
    timing: response.timing
      ? {
          optimalDelayMs: response.timing.optimal_delay_ms,
          urgency: response.timing.urgency,
        }
      : undefined,
  };
}

function toStoredNudge(nudge: Nudge): StoredNudge {
  return {
    id: nudge.id,
    type: nudge.type,
    message: nudge.message,
    priority: nudge.priority,
    category: nudge.category,
    targetElement: nudge.targetElement,
    showAfterMs: nudge.showAfterMs,
  };
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAINudges(options: UseAINudgesOptions = {}): UseAINudgesResult {
  const {
    enabled = false,
    pageContext,
    maxPerSession = 5,
    userMotivation: _userMotivation,
    userAbility,
    debounceMs = DEFAULT_DEBOUNCE_MS,
  } = options;

  // RTK Query mutation
  const [fetchNudgeRecommendation, { isLoading: isMutationLoading }] =
    useGetNudgeRecommendationMutation();

  const dispatch = useAppDispatch();
  const activeNudge = useAppSelector(selectActiveNudge);
  const history = useAppSelector(selectNudgeHistory);
  const canShowMore = useAppSelector(selectCanShowMoreNudges);
  const stats = useAppSelector(selectNudgeStats);

  const [recommendation, setRecommendation] = useState<NudgeRecommendation | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const mountedRef = useRef(true);
  const showTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debounceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevContextRef = useRef<string | undefined>(undefined);

  // Sync maxPerSession to Redux store
  useEffect(() => {
    dispatch(setSessionLimit(maxPerSession));
  }, [dispatch, maxPerSession]);

  /**
   * Fetch nudge recommendation from AI via RTK Query
   */
  const doFetch = useCallback(async () => {
    if (!mountedRef.current) {
      return;
    }

    setError(null);

    try {
      const data = (await fetchNudgeRecommendation({
        context: pageContext || "default",
        current_feature: pageContext,
        persona: userAbility,
      }).unwrap()) as {
        nudge_type: string;
        message: string;
        confidence: number;
        action_cta?: string;
        action_target?: string;
        dismiss_duration_ms?: number;
        trigger_delay_ms?: number;
      };

      if (!mountedRef.current) return;

      // Transform RTK Query response to hook's expected format
      // RTK Query returns: { nudge_type, message, confidence, action_cta, trigger_delay_ms }
      // Hook expects: NudgeRecommendation with nudge, shouldShow, confidence, etc.
      const nudge: Nudge | null = data.nudge_type
        ? {
            id: `nudge-${Date.now()}`,
            type: data.nudge_type as NudgeType,
            message: data.message,
            priority: "medium" as NudgePriority,
            category: data.nudge_type,
            showAfterMs: data.trigger_delay_ms,
          }
        : null;

      const transformed: NudgeRecommendation = {
        nudge,
        shouldShow: data.confidence >= 0.5 && !!nudge,
        confidence: data.confidence,
        reasoning: undefined,
        timing: data.trigger_delay_ms
          ? {
              optimalDelayMs: data.trigger_delay_ms,
              urgency: data.confidence >= 0.8 ? "high" : data.confidence >= 0.6 ? "medium" : "low",
            }
          : undefined,
      };

      setRecommendation(transformed);

      // Schedule nudge display if should show
      if (transformed.shouldShow && transformed.nudge && canShowMore) {
        const showDelay = transformed.nudge.showAfterMs ?? transformed.timing?.optimalDelayMs ?? 0;

        if (showTimeoutRef.current) {
          clearTimeout(showTimeoutRef.current);
        }

        if (showDelay > 0) {
          showTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current && transformed.nudge) {
              dispatch(setActiveNudge(toStoredNudge(transformed.nudge)));
            }
          }, showDelay);
        } else {
          dispatch(setActiveNudge(toStoredNudge(transformed.nudge)));
        }
      }
    } catch (err) {
      if (!mountedRef.current) return;
      const fetchError = err instanceof Error ? err : new Error("Unknown error");
      setError(fetchError);
    }
  }, [pageContext, userAbility, canShowMore, dispatch, fetchNudgeRecommendation]);

  /**
   * Manually trigger a fetch (public API)
   */
  const fetchRecommendation = useCallback(() => {
    doFetch();
  }, [doFetch]);

  /**
   * Accept a nudge
   */
  const acceptNudge = useCallback(
    (nudgeId: string) => {
      dispatch(acceptNudgeAction(nudgeId));
    },
    [dispatch]
  );

  /**
   * Dismiss a nudge
   */
  const dismissNudge = useCallback(
    (nudgeId: string) => {
      dispatch(dismissNudgeAction(nudgeId));
    },
    [dispatch]
  );

  /**
   * Track any interaction for learning
   */
  const trackInteraction = useCallback(
    (_nudgeId: string, _action: string) => {
      // Could send to analytics endpoint for learning
      // For now, just log
    },
    []
  );

  /**
   * Check if a nudge has been shown
   */
  const hasShownNudge = useCallback(
    (nudgeId: string): boolean => {
      return history.some((h) => h.id === nudgeId);
    },
    [history]
  );

  /**
   * Get comprehensive stats
   */
  const getStats = useCallback((): NudgeStats => {
    return stats;
  }, [stats]);

  // Auto-fetch on context change when enabled
  useEffect(() => {
    if (!enabled) {
      return;
    }

    if (pageContext !== prevContextRef.current) {
      prevContextRef.current = pageContext;

      // Debounce the fetch
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }

      debounceTimeoutRef.current = setTimeout(() => {
        doFetch();
      }, debounceMs);
    }

    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, [enabled, pageContext, debounceMs, doFetch]);

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (showTimeoutRef.current) {
        clearTimeout(showTimeoutRef.current);
      }
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  // Convert StoredNudge back to Nudge for public API
  const activeNudgeResult: Nudge | null = activeNudge
    ? {
        id: activeNudge.id,
        type: activeNudge.type,
        message: activeNudge.message,
        priority: activeNudge.priority,
        category: activeNudge.category,
        targetElement: activeNudge.targetElement,
        showAfterMs: activeNudge.showAfterMs,
      }
    : null;

  return {
    activeNudge: activeNudgeResult,
    recommendation,
    isLoading: isMutationLoading,
    error,
    canShowMore,
    fetchRecommendation,
    acceptNudge,
    dismissNudge,
    trackInteraction,
    hasShownNudge,
    getStats,
  };
}

export default useAINudges;
