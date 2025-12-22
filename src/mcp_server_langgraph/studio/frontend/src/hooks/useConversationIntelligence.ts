/**
 * Conversation Intelligence Hooks
 *
 * Sprint 3: Conversation Intelligence
 * - Intent detection classifies user intent before submit
 * - Context optimization suggests trimming when approaching token limit
 * - Goal tracking tracks session goals across messages
 *
 * These hooks use the unified StudioOrchestrator via RTK Query.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useStudioAnalyzeMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

export interface IntentDetectionOptions {
  userId: string;
  sessionId: string;
  query: string;
  enabled?: boolean;
}

export interface IntentDetectionResult {
  intent: string | null;
  confidence: number | null;
  subIntents: string[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface ContextOptimizationOptions {
  userId: string;
  sessionId: string;
  currentTokens: number;
  maxTokens: number;
  enabled?: boolean;
}

export interface ContextSuggestion {
  type: string;
  description: string;
  tokensSaved: number;
}

export interface ContextOptimizationResult {
  suggestions: ContextSuggestion[];
  usagePercent: number | null;
  currentTokens: number | null;
  maxTokens: number | null;
  recommendedAction: string | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface GoalTrackingOptions {
  userId: string;
  sessionId: string;
  enabled?: boolean;
}

export interface GoalTrackingResult {
  primaryGoal: string | null;
  subGoals: string[];
  progressPercent: number | null;
  currentFocus: string | null;
  completedSubGoals: string[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

// =============================================================================
// useIntentDetection
// =============================================================================

/**
 * Hook for detecting user intent from a query before submission.
 *
 * Uses the StudioOrchestrator's intent_detect task type to classify
 * user input into categories like code_request, question, task, etc.
 *
 * @param options - Configuration options
 * @returns Intent detection result with confidence score
 */
export function useIntentDetection(
  options: IntentDetectionOptions,
): IntentDetectionResult {
  const { userId, sessionId, query, enabled = true } = options;

  const [analyzeIntent, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    intent: string | null;
    confidence: number | null;
    subIntents: string[];
    error: Error | null;
  }>({
    intent: null,
    confidence: null,
    subIntents: [],
    error: null,
  });

  const fetchIntent = useCallback(async () => {
    if (!enabled || !query.trim()) {
      setResult({
        intent: null,
        confidence: null,
        subIntents: [],
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeIntent({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "conversation",
            type: "intent_detect",
            data: { query },
          },
        ],
      }).unwrap();

      const intentResult = response.analyses?.intent_detect as
        | { intent?: string; confidence?: number; sub_intents?: string[] }
        | undefined;
      if (intentResult) {
        setResult({
          intent: intentResult.intent || null,
          confidence: intentResult.confidence ?? null,
          subIntents: intentResult.sub_intents || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeIntent, userId, sessionId, query, enabled]);

  useEffect(() => {
    fetchIntent();
  }, [fetchIntent]);

  return useMemo(
    () => ({
      intent: result.intent,
      confidence: result.confidence,
      subIntents: result.subIntents,
      isLoading,
      error: result.error,
      refetch: fetchIntent,
    }),
    [result, isLoading, fetchIntent],
  );
}

// =============================================================================
// useContextOptimization
// =============================================================================

/**
 * Hook for getting context optimization suggestions.
 *
 * Analyzes current token usage and provides suggestions for trimming
 * context when approaching the token limit.
 *
 * @param options - Configuration options
 * @returns Context optimization suggestions
 */
export function useContextOptimization(
  options: ContextOptimizationOptions,
): ContextOptimizationResult {
  const { userId, sessionId, currentTokens, maxTokens, enabled = true } = options;

  const [analyzeContext, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    suggestions: ContextSuggestion[];
    usagePercent: number | null;
    currentTokens: number | null;
    maxTokens: number | null;
    recommendedAction: string | null;
    error: Error | null;
  }>({
    suggestions: [],
    usagePercent: null,
    currentTokens: null,
    maxTokens: null,
    recommendedAction: null,
    error: null,
  });

  const fetchOptimization = useCallback(async () => {
    if (!enabled) {
      return;
    }

    try {
      const response = await analyzeContext({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "conversation",
            type: "context_optimize",
            data: { current_tokens: currentTokens, max_tokens: maxTokens },
          },
        ],
      }).unwrap();

      const contextResult = response.analyses?.context_optimize as
        | {
            suggestions?: { type: string; description: string; tokens_saved: number }[];
            usage_percent?: number;
            current_tokens?: number;
            max_tokens?: number;
            recommended_action?: string;
          }
        | undefined;
      if (contextResult) {
        setResult({
          suggestions: (contextResult.suggestions || []).map((s) => ({
            type: s.type,
            description: s.description,
            tokensSaved: s.tokens_saved,
          })),
          usagePercent: contextResult.usage_percent ?? null,
          currentTokens: contextResult.current_tokens ?? null,
          maxTokens: contextResult.max_tokens ?? null,
          recommendedAction: contextResult.recommended_action || null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeContext, userId, sessionId, currentTokens, maxTokens, enabled]);

  useEffect(() => {
    fetchOptimization();
  }, [fetchOptimization]);

  return useMemo(
    () => ({
      suggestions: result.suggestions,
      usagePercent: result.usagePercent,
      currentTokens: result.currentTokens,
      maxTokens: result.maxTokens,
      recommendedAction: result.recommendedAction,
      isLoading,
      error: result.error,
      refetch: fetchOptimization,
    }),
    [result, isLoading, fetchOptimization],
  );
}

// =============================================================================
// useGoalTracking
// =============================================================================

/**
 * Hook for tracking session goals across messages.
 *
 * Analyzes conversation history to identify primary goals, sub-goals,
 * and progress toward completion.
 *
 * @param options - Configuration options
 * @returns Goal tracking information
 */
export function useGoalTracking(
  options: GoalTrackingOptions,
): GoalTrackingResult {
  const { userId, sessionId, enabled = true } = options;

  const [analyzeGoals, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    primaryGoal: string | null;
    subGoals: string[];
    progressPercent: number | null;
    currentFocus: string | null;
    completedSubGoals: string[];
    error: Error | null;
  }>({
    primaryGoal: null,
    subGoals: [],
    progressPercent: null,
    currentFocus: null,
    completedSubGoals: [],
    error: null,
  });

  const fetchGoals = useCallback(async () => {
    if (!enabled) {
      return;
    }

    try {
      const response = await analyzeGoals({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "conversation",
            type: "goal_track",
            data: {},
          },
        ],
      }).unwrap();

      const goalResult = response.analyses?.goal_track as
        | {
            primary_goal?: string;
            sub_goals?: string[];
            progress_percent?: number;
            current_focus?: string;
            completed_sub_goals?: string[];
          }
        | undefined;
      if (goalResult) {
        setResult({
          primaryGoal: goalResult.primary_goal || null,
          subGoals: goalResult.sub_goals || [],
          progressPercent: goalResult.progress_percent ?? null,
          currentFocus: goalResult.current_focus || null,
          completedSubGoals: goalResult.completed_sub_goals || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeGoals, userId, sessionId, enabled]);

  useEffect(() => {
    fetchGoals();
  }, [fetchGoals]);

  return useMemo(
    () => ({
      primaryGoal: result.primaryGoal,
      subGoals: result.subGoals,
      progressPercent: result.progressPercent,
      currentFocus: result.currentFocus,
      completedSubGoals: result.completedSubGoals,
      isLoading,
      error: result.error,
      refetch: fetchGoals,
    }),
    [result, isLoading, fetchGoals],
  );
}
