/**
 * useFollowUpSuggestions Hook
 *
 * Generates AI-powered follow-up suggestions based on the last assistant message.
 * Features:
 * - Automatic suggestion generation on content change
 * - Debouncing to prevent excessive API calls
 * - Loading and error states
 * - Manual refresh capability
 * - Maximum suggestions limit
 * - RTK Query integration for caching and deduplication
 */

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import type {
  FollowUpSuggestion,
  SuggestionFeedbackType,
} from "../components/Chat/AIFollowUpSuggestions";
import {
  useGetChatFollowUpSuggestionsMutation,
  useTrackSuggestionClickMutation,
  useSubmitSuggestionFeedbackMutation,
} from "../api";

// =============================================================================
// Types
// =============================================================================

export interface UseFollowUpSuggestionsOptions {
  /** Content to generate suggestions from (usually the last assistant message) */
  content: string;
  /** Whether suggestion generation is enabled. Default: true */
  enabled?: boolean;
  /** Maximum number of suggestions to return. Default: 4 */
  maxSuggestions?: number;
  /** Debounce delay in milliseconds. Default: 500 */
  debounceMs?: number;
  /** Session ID for context. Optional. */
  sessionId?: string;
}

export interface UseFollowUpSuggestionsReturn {
  /** Generated suggestions */
  suggestions: FollowUpSuggestion[];
  /** Whether suggestions are being generated */
  isLoading: boolean;
  /** Error message if generation failed */
  error: string | null;
  /** Manually refresh suggestions */
  refresh: () => void;
  /** Track a suggestion click for analytics */
  trackClick: (suggestion: FollowUpSuggestion) => void;
  /** Submit feedback (thumbs up/down) for a suggestion */
  submitFeedback: (
    suggestion: FollowUpSuggestion,
    feedback: SuggestionFeedbackType,
  ) => void;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_MAX_SUGGESTIONS = 4;
const DEFAULT_DEBOUNCE_MS = 500;

// =============================================================================
// Hook Implementation
// =============================================================================

export function useFollowUpSuggestions({
  content,
  enabled = true,
  maxSuggestions = DEFAULT_MAX_SUGGESTIONS,
  debounceMs = DEFAULT_DEBOUNCE_MS,
  sessionId,
}: UseFollowUpSuggestionsOptions): UseFollowUpSuggestionsReturn {
  // RTK Query mutation hook for fetching suggestions
  const [
    fetchSuggestions,
    { data: rtkData, isLoading: rtkLoading, error: rtkError, reset },
  ] = useGetChatFollowUpSuggestionsMutation();

  // RTK Query mutation hook for tracking clicks (fire-and-forget)
  const [trackSuggestionClick] = useTrackSuggestionClickMutation();

  // RTK Query mutation hook for submitting feedback (fire-and-forget)
  const [submitSuggestionFeedback] = useSubmitSuggestionFeedbackMutation();

  // Track debouncing state separately (for immediate UI feedback)
  const [isDebouncing, setIsDebouncing] = useState(false);

  // Ref for debounce timer
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  // Ref to track previous content for change detection
  const prevContentRef = useRef<string>("");
  // Ref for refresh trigger
  const refreshTriggerRef = useRef(0);

  /**
   * Trigger suggestion fetch via RTK Query
   */
  const triggerFetch = useCallback(
    (contentToAnalyze: string) => {
      fetchSuggestions({
        content: contentToAnalyze,
        session_id: sessionId,
        max_suggestions: maxSuggestions,
      });
    },
    [fetchSuggestions, sessionId, maxSuggestions],
  );

  /**
   * Debounced suggestion generation
   */
  useEffect(() => {
    // Don't fetch if disabled or no content
    if (!enabled || !content || content.trim() === "") {
      // Reset RTK Query state when disabled
      reset();
      setIsDebouncing(false);
      prevContentRef.current = "";
      return;
    }

    // Skip if content hasn't changed (prevents re-fetching on other state changes)
    if (content === prevContentRef.current && refreshTriggerRef.current === 0) {
      return;
    }

    // Clear previous debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Set debouncing state immediately to show loading UI
    setIsDebouncing(true);

    // Debounce the fetch
    debounceTimerRef.current = setTimeout(() => {
      prevContentRef.current = content;
      setIsDebouncing(false);
      triggerFetch(content);
    }, debounceMs);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, enabled, debounceMs, triggerFetch, refreshTriggerRef.current]);

  /**
   * Manual refresh function
   */
  const refresh = useCallback(() => {
    if (!enabled || !content || content.trim() === "") {
      return;
    }
    // Trigger refresh by updating the trigger ref
    refreshTriggerRef.current += 1;
    // Force refetch immediately (skip debounce for manual refresh)
    triggerFetch(content);
  }, [enabled, content, triggerFetch]);

  /**
   * Track suggestion click for analytics (fire-and-forget)
   * Called when user clicks on a suggestion
   */
  const trackClick = useCallback(
    (suggestion: FollowUpSuggestion) => {
      // Fire-and-forget: don't await, don't block UI
      trackSuggestionClick({
        suggestion_id: suggestion.id,
        suggestion_type: "chat_followup",
        category: suggestion.category,
        session_id: sessionId,
      }).catch(() => {
        // Silently ignore tracking errors - analytics should never impact UX
      });
    },
    [trackSuggestionClick, sessionId],
  );

  /**
   * Submit feedback (thumbs up/down) for a suggestion (fire-and-forget)
   * Called when user provides feedback on a suggestion
   */
  const submitFeedback = useCallback(
    (suggestion: FollowUpSuggestion, feedback: SuggestionFeedbackType) => {
      // Fire-and-forget: don't await, don't block UI
      submitSuggestionFeedback({
        suggestion_id: suggestion.id,
        suggestion_type: "chat_followup",
        feedback,
        category: suggestion.category,
        session_id: sessionId,
      }).catch(() => {
        // Silently ignore feedback errors - analytics should never impact UX
      });
    },
    [submitSuggestionFeedback, sessionId],
  );

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  // Compute suggestions from RTK Query data
  const suggestions = useMemo<FollowUpSuggestion[]>(() => {
    if (!enabled || !content || content.trim() === "") {
      return [];
    }
    const rawSuggestions = rtkData?.suggestions ?? [];
    // Limit to max count
    return rawSuggestions.slice(0, maxSuggestions) as FollowUpSuggestion[];
  }, [rtkData, enabled, content, maxSuggestions]);

  // Compute error message from RTK Query error
  const error = useMemo<string | null>(() => {
    if (!rtkError) return null;
    if ("status" in rtkError) {
      // FetchBaseQueryError
      return `API error: ${rtkError.status}`;
    }
    // SerializedError
    return rtkError.message ?? "Failed to generate suggestions";
  }, [rtkError]);

  // Combined loading state: either debouncing or RTK fetching
  const isLoading = isDebouncing || rtkLoading;

  return {
    suggestions,
    isLoading,
    error,
    refresh,
    trackClick,
    submitFeedback,
  };
}

export default useFollowUpSuggestions;
