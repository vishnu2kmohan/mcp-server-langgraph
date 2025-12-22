/**
 * useSessionIntelligence Hooks
 *
 * Sprint 2: Session Intelligence
 * - useSessionSummary: Generate AI summaries per session
 * - useSessionGroups: Cluster sessions by topic/project
 * - useSessionSimilarity: Find related sessions
 *
 * Uses the StudioOrchestrator backend via useStudioAI hook.
 *
 * @example
 * ```tsx
 * const { summary, keyTopics, isLoading } = useSessionSummary({
 *   userId: 'user-123',
 *   sessionId: 'session-456',
 * });
 * ```
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useStudioAnalyzeMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

/**
 * Session group returned by session_group task
 */
export interface SessionGroup {
  /** Topic name for the group */
  topic: string;
  /** Session IDs in this group */
  session_ids: string[];
  /** Confidence score (0-1) */
  confidence: number;
}

/**
 * Similar session returned by session_similarity task
 */
export interface SimilarSession {
  /** Session ID */
  session_id: string;
  /** Similarity score (0-1) */
  similarity_score: number;
  /** Common topics between sessions */
  common_topics: string[];
}

/**
 * Options for useSessionSummary hook
 */
export interface UseSessionSummaryOptions {
  /** User ID */
  userId: string;
  /** Session ID to summarize */
  sessionId: string;
  /** Whether to run the analysis (default: true) */
  enabled?: boolean;
}

/**
 * Result from useSessionSummary hook
 */
export interface UseSessionSummaryResult {
  /** AI-generated summary */
  summary: string | null;
  /** Key topics extracted from session */
  keyTopics: string[];
  /** Number of messages in session */
  messageCount: number;
  /** Loading state */
  isLoading: boolean;
  /** Error if request failed */
  error: Error | null;
  /** Refetch the summary */
  refetch: () => void;
}

/**
 * Options for useSessionGroups hook
 */
export interface UseSessionGroupsOptions {
  /** User ID */
  userId: string;
  /** Session IDs to group */
  sessionIds: string[];
  /** Whether to run the analysis (default: true) */
  enabled?: boolean;
}

/**
 * Result from useSessionGroups hook
 */
export interface UseSessionGroupsResult {
  /** Grouped sessions */
  groups: SessionGroup[];
  /** Sessions that couldn't be grouped */
  ungrouped: string[];
  /** Loading state */
  isLoading: boolean;
  /** Error if request failed */
  error: Error | null;
  /** Refetch the groups */
  refetch: () => void;
}

/**
 * Options for useSessionSimilarity hook
 */
export interface UseSessionSimilarityOptions {
  /** User ID */
  userId: string;
  /** Source session ID */
  sessionId: string;
  /** Maximum number of similar sessions to return */
  limit?: number;
  /** Whether to run the analysis (default: true) */
  enabled?: boolean;
}

/**
 * Result from useSessionSimilarity hook
 */
export interface UseSessionSimilarityResult {
  /** Similar sessions */
  similarSessions: SimilarSession[];
  /** Loading state */
  isLoading: boolean;
  /** Error if request failed */
  error: Error | null;
  /** Refetch similar sessions */
  refetch: () => void;
}

// =============================================================================
// useSessionSummary Hook
// =============================================================================

/**
 * Hook for generating AI summary of a session.
 *
 * Uses session_summarize task type via StudioOrchestrator.
 *
 * @param options - Hook configuration
 * @returns Session summary result
 */
export function useSessionSummary(
  options: UseSessionSummaryOptions
): UseSessionSummaryResult {
  const { userId, sessionId, enabled = true } = options;

  const [studioAnalyzeMutation, { isLoading: isMutationLoading }] =
    useStudioAnalyzeMutation();

  const [summary, setSummary] = useState<string | null>(null);
  const [keyTopics, setKeyTopics] = useState<string[]>([]);
  const [messageCount, setMessageCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const hasFetchedRef = useRef(false);

  const fetchSummary = useCallback(async () => {
    if (!enabled || !sessionId) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await studioAnalyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "session",
            type: "session_summarize",
            data: {},
          },
        ],
      }).unwrap();

      const sessionResult = data.analyses?.session_summarize;
      if (sessionResult) {
        setSummary(sessionResult.summary || null);
        setKeyTopics(sessionResult.key_topics || []);
        setMessageCount(sessionResult.message_count || 0);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to get summary"));
      setSummary(null);
      setKeyTopics([]);
      setMessageCount(0);
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  }, [userId, sessionId, enabled, studioAnalyzeMutation]);

  const refetch = useCallback(() => {
    hasFetchedRef.current = false;
    fetchSummary();
  }, [fetchSummary]);

  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    if (!hasFetchedRef.current) {
      fetchSummary();
    }
  }, [enabled, sessionId, fetchSummary]);

  return {
    summary,
    keyTopics,
    messageCount,
    isLoading: isLoading || isMutationLoading,
    error,
    refetch,
  };
}

// =============================================================================
// useSessionGroups Hook
// =============================================================================

/**
 * Hook for grouping sessions by topic/project.
 *
 * Uses session_group task type via StudioOrchestrator.
 *
 * @param options - Hook configuration
 * @returns Session groups result
 */
export function useSessionGroups(
  options: UseSessionGroupsOptions
): UseSessionGroupsResult {
  const { userId, sessionIds, enabled = true } = options;

  const [studioAnalyzeMutation, { isLoading: isMutationLoading }] =
    useStudioAnalyzeMutation();

  const [groups, setGroups] = useState<SessionGroup[]>([]);
  const [ungrouped, setUngrouped] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(enabled && sessionIds.length > 0);
  const [error, setError] = useState<Error | null>(null);
  const hasFetchedRef = useRef(false);

  const fetchGroups = useCallback(async () => {
    if (!enabled || sessionIds.length === 0) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await studioAnalyzeMutation({
        user_id: userId,
        session_id: sessionIds[0], // Use first session as reference
        tasks: [
          {
            category: "session",
            type: "session_group",
            data: { session_ids: sessionIds },
          },
        ],
      }).unwrap();

      const groupResult = data.analyses?.session_group;
      if (groupResult) {
        setGroups(groupResult.groups || []);
        setUngrouped(groupResult.ungrouped || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to group sessions"));
      setGroups([]);
      setUngrouped([]);
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  }, [userId, sessionIds, enabled, studioAnalyzeMutation]);

  const refetch = useCallback(() => {
    hasFetchedRef.current = false;
    fetchGroups();
  }, [fetchGroups]);

  // Serialize sessionIds for dependency comparison
  const sessionIdsKey = JSON.stringify(sessionIds);

  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    if (!hasFetchedRef.current) {
      fetchGroups();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, sessionIdsKey]);

  return {
    groups,
    ungrouped,
    isLoading: isLoading || isMutationLoading,
    error,
    refetch,
  };
}

// =============================================================================
// useSessionSimilarity Hook
// =============================================================================

/**
 * Hook for finding sessions similar to a given session.
 *
 * Uses session_similarity task type via StudioOrchestrator.
 *
 * @param options - Hook configuration
 * @returns Similar sessions result
 */
export function useSessionSimilarity(
  options: UseSessionSimilarityOptions
): UseSessionSimilarityResult {
  const { userId, sessionId, limit = 5, enabled = true } = options;

  const [studioAnalyzeMutation, { isLoading: isMutationLoading }] =
    useStudioAnalyzeMutation();

  const [similarSessions, setSimilarSessions] = useState<SimilarSession[]>([]);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const hasFetchedRef = useRef(false);

  const fetchSimilar = useCallback(async () => {
    if (!enabled || !sessionId) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await studioAnalyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "session",
            type: "session_similarity",
            data: { limit },
          },
        ],
      }).unwrap();

      const similarResult = data.analyses?.session_similarity;
      if (similarResult) {
        setSimilarSessions(similarResult.similar_sessions || []);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to find similar sessions")
      );
      setSimilarSessions([]);
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  }, [userId, sessionId, limit, enabled, studioAnalyzeMutation]);

  const refetch = useCallback(() => {
    hasFetchedRef.current = false;
    fetchSimilar();
  }, [fetchSimilar]);

  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    if (!hasFetchedRef.current) {
      fetchSimilar();
    }
  }, [enabled, sessionId, fetchSimilar]);

  return {
    similarSessions,
    isLoading: isLoading || isMutationLoading,
    error,
    refetch,
  };
}

export default {
  useSessionSummary,
  useSessionGroups,
  useSessionSimilarity,
};
