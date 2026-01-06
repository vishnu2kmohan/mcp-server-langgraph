/**
 * useAINudges Hook
 *
 * Sprint 3 - Phase 6.3: AI-Driven Smart Nudges
 *
 * @deprecated Use `useNudges` with `enableAI=true` instead.
 * This hook provides Redux integration but was never adopted in production.
 * The simpler `useNudges` hook is the standard for all nudge functionality.
 *
 * Migration example:
 * ```tsx
 * // Instead of:
 * const { activeNudge } = useAINudges({ enabled: true, pageContext: "chat" });
 *
 * // Use:
 * const { activeNudge } = useNudges({ enableAI: true, pageContext: "chat" });
 * ```
 *
 * ---
 * Original description:
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
import { selectUser } from "../store/slices/authSlice";
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
// Constants
// =============================================================================

const DEFAULT_DEBOUNCE_MS = 500;

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

export function useAINudges(
  options: UseAINudgesOptions = {},
): UseAINudgesResult {
  const {
    enabled = false,
    pageContext,
    maxPerSession = 5,
    userMotivation: _userMotivation,
    userAbility: _userAbility,
    debounceMs = DEFAULT_DEBOUNCE_MS,
  } = options;

  // RTK Query mutation
  const [fetchNudgeRecommendation, { isLoading: isMutationLoading }] =
    useGetNudgeRecommendationMutation();

  const dispatch = useAppDispatch();
  const currentUser = useAppSelector(selectUser);
  const activeNudge = useAppSelector(selectActiveNudge);
  const history = useAppSelector(selectNudgeHistory);
  const canShowMore = useAppSelector(selectCanShowMoreNudges);
  const stats = useAppSelector(selectNudgeStats);

  const [recommendation, setRecommendation] =
    useState<NudgeRecommendation | null>(null);
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
      // Build nudge history for fatigue prevention
      // NudgeHistoryEntry has: id, action ("shown"|"dismissed"|"accepted"), timestamp
      const nudgeHistoryItems = history.slice(0, 10).map((h) => ({
        id: h.id,
        shown_at: new Date(h.timestamp).toISOString(),
        action: h.action === "shown" ? "dismissed" : h.action,
      }));

      // Request matches NudgeRecommendRequest from generated-api.ts (ADR-0091)
      const data = await fetchNudgeRecommendation({
        user_id: currentUser?.id || "anonymous",
        current_context: {
          page: pageContext || "default",
          action: "viewing",
          time_on_page: 0,
        },
        nudge_history: nudgeHistoryItems,
      }).unwrap();

      if (!mountedRef.current) return;

      // Transform generated NudgeRecommendResponse to hook's expected format
      // Response structure: { should_show, confidence, nudge?: { id, type, message, priority, show_after_ms } }
      const nudge: Nudge | null = data.nudge
        ? {
            id: data.nudge.id,
            type: data.nudge.type as NudgeType,
            message: data.nudge.message,
            priority: data.nudge.priority as NudgePriority,
            category: data.nudge.type,
            showAfterMs: data.nudge.show_after_ms,
            targetElement: data.nudge.target_element ?? undefined,
          }
        : null;

      const transformed: NudgeRecommendation = {
        nudge,
        shouldShow: data.should_show,
        confidence: data.confidence,
        reasoning: undefined,
        timing: nudge?.showAfterMs
          ? {
              optimalDelayMs: nudge.showAfterMs,
              urgency:
                data.confidence >= 0.8
                  ? "high"
                  : data.confidence >= 0.6
                    ? "medium"
                    : "low",
            }
          : undefined,
      };

      setRecommendation(transformed);

      // Schedule nudge display if should show
      if (transformed.shouldShow && transformed.nudge && canShowMore) {
        const showDelay =
          transformed.nudge.showAfterMs ??
          transformed.timing?.optimalDelayMs ??
          0;

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
      const fetchError =
        err instanceof Error ? err : new Error("Unknown error");
      setError(fetchError);
    }
  }, [
    pageContext,
    canShowMore,
    dispatch,
    fetchNudgeRecommendation,
    currentUser?.id,
    history,
  ]);

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
    [dispatch],
  );

  /**
   * Dismiss a nudge
   */
  const dismissNudge = useCallback(
    (nudgeId: string) => {
      dispatch(dismissNudgeAction(nudgeId));
    },
    [dispatch],
  );

  /**
   * Track any interaction for learning
   */
  const trackInteraction = useCallback((_nudgeId: string, _action: string) => {
    // Could send to analytics endpoint for learning
    // For now, just log
  }, []);

  /**
   * Check if a nudge has been shown
   */
  const hasShownNudge = useCallback(
    (nudgeId: string): boolean => {
      return history.some((h) => h.id === nudgeId);
    },
    [history],
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
